import multiprocessing
import sys
import os
import math
from pathlib import Path
import statistics

# =========================================================
#                    CONFIGURATION
# =========================================================

# Get the absolute path to the directory containing this script (services/)
CURRENT_DIR = Path(__file__).resolve().parent

# Traverse up to the project root, then into the _vendor directory
VENDOR_DIR = CURRENT_DIR.parent.parent / '_vendor'

PARSER_DIR = str(VENDOR_DIR / 'py_parser')
wt_directory = str(VENDOR_DIR / 'wt_binaries')
TIME_BUCKET_MS = 500

# =========================================================
#                 HELPER FUNCTIONS
# =========================================================

def get_player_name(player):
    try:
        return player.uid.data.player_name or ''
    except Exception:
        return ''


def get_team(player):
    try:
        return player.team.data
    except Exception:
        return '?'


def build_pid_map(state):
    pid_map = {}
    for player in state.players:
        name = get_player_name(player)
        if not name: continue

        # 1. Map the Global Unique ID (player_id)
        player_id = getattr(player.uid.data, 'player_id', None)
        if player_id is not None:
            pid_map[player_id] = name

        # 2. Scan all owned units to map their 'owner_pid' to the player
        # This fixes the CriticalDamageMessage resolution for IDs like 12
        for u in player.allOwnedUnits:
            owner_pid = getattr(u, 'owner_pid', None)
            if owner_pid is not None:
                pid_map[owner_pid] = name

    return pid_map


def build_unit_owner_map(state):
    unit_map = {}
    seen_pids = set()
    for player in state.players:
        name = get_player_name(player)
        if not name: continue
        pid = player.uid.data.player_id
        if pid in seen_pids: continue
        seen_pids.add(pid)
        for unit in player.allOwnedUnits:
            uid = getattr(unit, 'uid', None)
            if uid is not None:
                unit_map[uid] = name
    return unit_map


def resolve_name(pid, unit, pid_map, unit_map):
    name = pid_map.get(pid)
    if name: return name
    uid = getattr(unit, 'uid', None)
    if uid is not None: name = unit_map.get(uid)
    return name or f'pid:{pid}'


# =========================================================
#                 MAIN PARSING WORKER
# =========================================================

def parse_merged_replays(file_paths, return_dict, start_time_str="0:00"):
    """
    Parses multiple replay files from the same round.
    Merges POV data, corrects teams spatially, applies start/end time windows, and deduplicates kills.
    """
    if PARSER_DIR not in sys.path:
        sys.path.insert(0, PARSER_DIR)

    dll_cookie = None
    if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
        try:
            dll_cookie = os.add_dll_directory(wt_directory)
        except Exception as e:
            print(f"[-] Warning: Could not add DLL directory: {e}")

    try:
        import PyReplayParser

        # --- Parse Match Start Time ---
        start_ms = 0
        if start_time_str:
            try:
                parts = str(start_time_str).split(':')
                if len(parts) == 2:
                    start_ms = (int(parts[0]) * 60 + int(parts[1])) * 1000
                elif len(parts) == 1:
                    start_ms = int(parts[0]) * 1000
            except ValueError:
                pass

        master_chat = {}
        master_spawns = {}
        master_teams = {}
        master_kills = {}
        master_crits = {}
        master_movement = {}
        master_areas = []
        master_zones = []
        map_context = {"level_name": "unknown", "postfix": ""}

        for file_idx, file_path in enumerate(file_paths):
            try:
                PyReplayParser.initialize(
                    VromfsPath=wt_directory,
                    logfile_path="parser_temp.log",
                    fonts=False,
                    lang=True,
                    mis=True
                )

                replay = PyReplayParser.replay.Replay(file_path)
                if hasattr(replay, 'isValid') and not replay.isValid:
                    continue

                state = PyReplayParser.ParserState(replay)
                reader = replay.getReplayReader() if hasattr(replay, 'getReplayReader') else replay.get_replay_reader()
                state.LoadFromReader(reader)

                if map_context["level_name"] == "unknown" and hasattr(replay, 'headerBlk'):
                    header_data = replay.headerBlk.toDict()
                    raw_level = header_data.get("level", "")
                    if raw_level:
                        map_context["level_name"] = raw_level.split('/')[-1].replace('.bin', '')
                    map_context["postfix"] = header_data.get("postfix", "")
                    map_context["loc_name"] = header_data.get("locName", "")

                print(header_data, flush=True)

                pid_map = build_pid_map(state)
                unit_map = build_unit_owner_map(state)

                for player in state.players:
                    name = get_player_name(player)
                    if not name: continue

                    team_id = str(get_team(player))
                    if team_id not in master_teams:
                        master_teams[team_id] = set()
                    master_teams[team_id].add(name)

                    if name not in master_spawns:
                        master_spawns[name] = set()
                    if name not in master_movement:
                        master_movement[name] = {}

                    for u in player.allOwnedUnits:
                        unit_name = getattr(u, 'unit_name', 'unknown')
                        unit_name = getattr(unit_name, 'data', unit_name)
                        if isinstance(unit_name, str):
                            unit_name = unit_name.split('/')[-1]
                        if 'dummy' in str(unit_name).lower():
                            continue

                        master_spawns[name].add(unit_name)

                        positions = getattr(u, 'positions', [])
                        if positions:
                            if unit_name not in master_movement[name]:
                                master_movement[name][unit_name] = {}
                            # Keep track of WHICH file recorded this movement
                            if file_idx not in master_movement[name][unit_name]:
                                master_movement[name][unit_name][file_idx] = {}

                            for p in positions:
                                try:
                                    time_ms = p.time_ms
                                    bucket = time_ms // 5000

                                    loc = p.location
                                    x, z = None, None

                                    try:
                                        if len(loc) == 3:
                                            x, z = float(loc[0]), float(loc[2])
                                        elif len(loc) >= 4:
                                            x, z = float(loc[3][0]), float(loc[3][2])
                                    except TypeError:
                                        loc_str = str(loc).strip('[]')
                                        parts = loc_str.split(',')
                                        if len(parts) >= 3:
                                            x, z = float(parts[0]), float(parts[2])

                                    if x is not None and z is not None:
                                        # Save the data under the specific file index
                                        master_movement[name][unit_name][file_idx][bucket] = (time_ms, x, z)
                                except Exception:
                                    pass

                for msg in state.battle_messages:
                    msg_type = type(msg).__name__

                    if msg_type == "KillMessage":
                        offender_name = resolve_name(msg.offender_pid, msg.offender_unit, pid_map, unit_map)
                        victim_pid = getattr(msg, 'VictimPid', -1)
                        victim_name = pid_map.get(victim_pid) or resolve_name(victim_pid, msg.offended_unit, pid_map,
                                                                              unit_map)

                        kill_time_s = msg.time_ms / 1000.0

                        # Proximity Deduplication: Prevent duplicate kills across rigid boundaries
                        is_dup = False
                        for existing_kill in master_kills.values():
                            if existing_kill["attacker"] == offender_name and existing_kill["victim"] == victim_name:
                                # If the same attacker kills the same victim within 15 seconds,
                                # it is guaranteed to be a latency offset of the same event.
                                if abs(existing_kill["time"] - kill_time_s) <= 15.0:
                                    is_dup = True
                                    break

                        if not is_dup:
                            # Use exact time in the key to ensure uniqueness if not a duplicate
                            kill_key = f"{msg.time_ms}_{offender_name}_{victim_name}"
                            master_kills[kill_key] = {
                                "time": kill_time_s,
                                "attacker": offender_name,
                                "attacker_veh": getattr(msg, 'offender_vehicle', 'unknown').split('/')[-1],
                                "weapon": msg.used_weapon or getattr(msg, 'destroyed_weapon', '?'),
                                "victim": victim_name,
                                "victim_veh": getattr(msg.offended_unit, 'unit_name', '?')
                            }

                    elif msg_type == "CriticalDamageMessage":
                        # 1. Resolve Attacker (using player_pid and the offender_unit object)
                        offender_name = resolve_name(msg.player_pid, msg.offender_unit, pid_map, unit_map)

                        # 2. Resolve Victim (using the offended_unit object directly, no PID available)
                        victim_name = resolve_name(None, msg.offended_unit, pid_map, unit_map)

                        # 4. Extract Victim Vehicle Name
                        victim_veh = getattr(msg.offended_unit, 'unit_name', '?')
                        victim_veh = getattr(victim_veh, 'data', victim_veh)
                        if isinstance(victim_veh, str):
                            victim_veh = victim_veh.split('/')[-1]

                        crit_time_s = msg.time_ms / 1000.0
                        is_fire = bool(getattr(msg, 'is_fire', False))

                        # Proximity Deduplication for crits (smaller 5-second window)
                        is_dup = False
                        for existing_crit in master_crits.values():
                            if existing_crit["attacker"] == offender_name and existing_crit["victim"] == victim_name:
                                if abs(existing_crit["time"] - crit_time_s) <= 5.0 and existing_crit[
                                    "is_fire"] == is_fire:
                                    is_dup = True
                                    break

                        if not is_dup:
                            crit_key = f"{msg.time_ms}_{offender_name}_{victim_name}"
                            master_crits[crit_key] = {
                                "time": crit_time_s,
                                "attacker": offender_name,
                                "victim": victim_name,
                                "attacker_veh": msg.vehicle,
                                "victim_veh": victim_veh,
                                "is_fire": is_fire,
                            }

                if hasattr(state, 'chat_messages'):
                    for chat in state.chat_messages:
                        # Use a windowed key to prevent duplicate chat lines from multi-parsing
                        bucket = chat.time_ms // TIME_BUCKET_MS
                        chat_key = (bucket, chat.player_name, chat.message)

                        master_chat[chat_key] = {
                            "time": chat.time_ms / 1000.0,
                            "sender": chat.player_name,
                            "text": chat.message
                        }

                if not master_areas and not master_zones:
                    for area in state.areas:
                        tm = getattr(area, 'tm', None)
                        if tm is None: continue

                        try:
                            # Extract Flags
                            area_flags_list = []
                            if hasattr(area.areaFlags, 'data'):
                                flag_data = area.areaFlags.data
                                area_val = int(flag_data.value)
                                enum_class = type(flag_data)
                                if hasattr(enum_class, '__members__'):
                                    for name, enum_member in enum_class.__members__.items():
                                        if name in ['name', 'value']: continue
                                        if (area_val & int(enum_member.value)) == int(enum_member.value):
                                            area_flags_list.append(name.lower())  # Normalize to lowercase

                            # We only want zones that have the 'kill' flag AND ('team1' or 'team2')
                            is_kill = 'killarea' in area_flags_list
                            has_team1 = 'team1' in area_flags_list
                            has_team2 = 'team2' in area_flags_list

                            if is_kill and (has_team1 ^ has_team2):
                                # Calculate metrics
                                tm_matrix = [[float(v) for v in row] for row in tm]
                                center_x, center_z = float(tm[3][0]), float(tm[3][2])
                                size_x, size_z = abs(float(tm[0][0])), abs(float(tm[2][2]))

                                # Determine which side this spawn belongs to:
                                # If a zone kills Team 1, it is Team 2's spawn (and vice versa)
                                spawn_side = 'team2' if has_team1 else 'team1'

                                master_areas.append({
                                    'type': 'spawn_zone',
                                    'spawn_side': spawn_side,
                                    'flags': area_flags_list,
                                    'center': (center_x, center_z),
                                    'size': (size_x, size_z),
                                    'tm': tm_matrix
                                })

                        except Exception:
                            continue

                        # --- ADD THIS: Extract Capture Zones ---
                    if hasattr(state, 'zones'):
                        zones_list = state.zones.values() if isinstance(state.zones, dict) else state.zones
                        for i, z in enumerate(zones_list):
                            try:
                                z_dict = {}
                                zone_area = getattr(z, 'area', None)

                                # Matrix Extraction
                                if hasattr(z, 'tm'):
                                    z_dict['tm'] = [[float(v) for v in row] for row in z.tm]
                                elif hasattr(z, 'transform'):
                                    z_dict['tm'] = [[float(v) for v in row] for row in z.transform]
                                elif zone_area and hasattr(zone_area, 'tm'):
                                    z_dict['tm'] = [[float(v) for v in row] for row in zone_area.tm]

                                # Pos/Radius Extraction
                                if hasattr(z, 'radius'):
                                    z_dict['radius'] = float(z.radius)
                                elif zone_area and hasattr(zone_area, 'radius'):
                                    z_dict['radius'] = float(zone_area.radius)

                                if hasattr(z, 'pos'):
                                    z_dict['pos'] = [float(z.pos[0]), float(z.pos[2])]
                                elif zone_area and hasattr(zone_area, 'pos'):
                                    z_dict['pos'] = [float(zone_area.pos[0]), float(zone_area.pos[2])]

                                # Name naming
                                z_dict['name'] = f"{chr(65 + i)}"

                                master_zones.append(z_dict)
                            except Exception:
                                continue

            except Exception as e:
                print(f"[!] Failed to parse a file ({file_path}): {str(e)}")

        # =========================================================
        #   1.5 TELEMETRY DEDUPLICATION (Fix Jumps & Sequential Files)
        # =========================================================
        # We temporarily stored telemetry by file index. Now we merge them intelligently.
        consolidated_movement = {}
        for p_name, vehicles in master_movement.items():
            consolidated_movement[p_name] = {}
            for v_name, file_buckets in vehicles.items():
                if not file_buckets:
                    continue

                # Rank files by how much data they have for this specific vehicle (descending).
                # The file with the most points becomes the "Primary POV", others are "Fallbacks".
                ranked_files = sorted(file_buckets.keys(), key=lambda idx: len(file_buckets[idx]), reverse=True)

                merged_buckets = {}

                # Layer the data: Primary file goes first, fallbacks fill in the empty gaps.
                for file_idx in ranked_files:
                    for bucket, point_data in file_buckets[file_idx].items():
                        # Only add the telemetry if a higher-quality file hasn't already provided data for this 5-second window
                        if bucket not in merged_buckets:
                            merged_buckets[bucket] = point_data

                consolidated_movement[p_name][v_name] = merged_buckets

        # Overwrite master_movement so the rest of your script runs perfectly without modifications
        master_movement = consolidated_movement

        # =========================================================
        #   2. SPATIAL TEAM CORRECTION (Fix Leaving/Rejoining Bug)
        # =========================================================

        player_initial_spawns = {}
        for p_name, vehicles in master_movement.items():
            earliest_time = float('inf')
            earliest_pos = None
            for v_name, buckets in vehicles.items():
                if buckets:
                    # Find the earliest absolute point recorded for this vehicle
                    first_pt = min(buckets.values(), key=lambda pt: pt[0])
                    if first_pt[0] < earliest_time:
                        earliest_time = first_pt[0]
                        earliest_pos = (first_pt[1], first_pt[2])
            if earliest_pos:
                player_initial_spawns[p_name] = earliest_pos

        # Calculate starting baseline centers for combat teams '1' and '2'
        team_centroids = {}
        for t_id in ['1', '2']:
            positions = [player_initial_spawns[name] for name in master_teams.get(t_id, set()) if
                         name in player_initial_spawns]
            if positions:
                # Use median instead of mean so air spawns do not drag the centroid off the map
                med_x = statistics.median([p[0] for p in positions])
                med_z = statistics.median([p[1] for p in positions])
                team_centroids[t_id] = (med_x, med_z)

        # If we have two clear spawn locations, fix team allocations dynamically
        if len(team_centroids) == 2:
            corrected_teams = {'1': set(), '2': set()}

            # Preserve any non-combat/spectator flags just in case
            for t_id, names in master_teams.items():
                if t_id not in ['1', '2']:
                    corrected_teams[t_id] = names

            for p_name, pos in player_initial_spawns.items():
                dist_1 = math.hypot(pos[0] - team_centroids['1'][0], pos[1] - team_centroids['1'][1])
                dist_2 = math.hypot(pos[0] - team_centroids['2'][0], pos[1] - team_centroids['2'][1])

                true_team = '1' if dist_1 < dist_2 else '2'
                corrected_teams[true_team].add(p_name)

            # Fallback: catch players without telemetry (spectators) so they aren't lost
            all_moved_players = set(player_initial_spawns.keys())
            for t_id in ['1', '2']:
                orig_names = master_teams.get(t_id, set())
                for name in orig_names:
                    if name not in all_moved_players:
                        corrected_teams[t_id].add(name)

            master_teams = corrected_teams

        # =========================================================
        #   3. VEHICLE NAME CLEANUP
        # =========================================================

        generic_names = {"tank", "aircraft", "ship", "helicopter", "dummy", "none", "unknown", "?", ""}
        true_vehicles = {}
        clean_spawns = {}

        for player, spawns in master_spawns.items():
            real_vehs = [v for v in spawns if v.lower() not in generic_names and not v.startswith("Entity_")]
            if real_vehs:
                true_vehicles[player] = real_vehs[0]
            clean_spawns[player] = list(set(real_vehs)) if real_vehs else ["Unknown"]

        for k in master_kills.values():
            if k['attacker_veh'].lower() in generic_names and k['attacker'] in true_vehicles:
                k['attacker_veh'] = true_vehicles[k['attacker']]
            if k['victim_veh'].lower() in generic_names and k['victim'] in true_vehicles:
                k['victim_veh'] = true_vehicles[k['victim']]

        # =========================================================
        #   4. LOGICAL FILTERING (Time Windows & Eliminations)
        # =========================================================

        # A: Determine true active combatants who survived until the match started.
        combatants = set(true_vehicles.keys())
        active_combatants = set()

        for p_name in combatants:
            moved_after_start = False
            if p_name in master_movement:
                for buckets in master_movement[p_name].values():
                    if any(t >= start_ms for t, _, _ in buckets.values()):
                        moved_after_start = True
                        break

            died_after_start = any(
                k["victim"] == p_name and k["time"] * 1000.0 >= start_ms for k in master_kills.values())

            # If they respawned/moved after start OR suffered a death after start, they are an active player
            if moved_after_start or died_after_start:
                active_combatants.add(p_name)

        # Calculate active combat team sizes
        team_1_active = {p for p in master_teams.get('1', set()) if p in active_combatants}
        team_2_active = {p for p in master_teams.get('2', set()) if p in active_combatants}

        team_1_size = len(team_1_active)
        team_2_size = len(team_2_active)

        # B: Tally kills chronologically to find exact Elimination time
        team_1_deaths = 0
        team_2_deaths = 0
        end_ms = float('inf')
        valid_kills = []

        sorted_raw_kills = sorted(master_kills.values(), key=lambda x: x["time"])
        for kill in sorted_raw_kills:
            time_ms = kill["time"] * 1000.0

            if time_ms < start_ms:
                continue
            if time_ms > end_ms:
                continue

            valid_kills.append(kill)

            victim = kill["victim"]
            if victim in team_1_active:
                team_1_deaths += 1
            elif victim in team_2_active:
                team_2_deaths += 1

            # Elimination Cutoff Trigger
            if (team_1_size > 0 and team_1_deaths >= team_1_size) or \
                    (team_2_size > 0 and team_2_deaths >= team_2_size):
                end_ms = time_ms

        clean_movement = {}
        MAX_SPEED_MPS = 25

        for p_name, vehicles in master_movement.items():
            clean_movement[p_name] = {}
            for v_name, buckets in vehicles.items():
                raw_points = [pt for bucket_idx, pt in sorted(buckets.items())]
                if not raw_points:
                    continue

                valid_points = []
                last_pt = None
                rejected_streak = 0

                # War Thunder uses the initial spawn coordinate as a placeholder
                # when an enemy drops out of render/spotting distance.
                spawn_x, spawn_z = raw_points[0][1], raw_points[0][2]
                has_left_spawn = False

                for pt in raw_points:
                    time_ms, x, z = pt

                    # 1. Skip absolute origin glitches
                    if x == 0.0 and z == 0.0:
                        continue

                    dist_to_spawn = math.hypot(x - spawn_x, z - spawn_z)

                    # 2. If they already rolled out but suddenly report back EXACTLY at spawn,
                    # it's the client dropping their telemetry. Ignore it permanently.
                    if has_left_spawn and dist_to_spawn < 1.0:
                        continue

                    # 3. Filter other impossible speed jumps
                    if last_pt is not None:
                        last_time, last_x, last_z = last_pt
                        dt = (time_ms - last_time) / 1000.0

                        if dt > 0:
                            dist = math.hypot(x - last_x, z - last_z)
                            speed = dist / dt

                            if speed > MAX_SPEED_MPS:
                                rejected_streak += 1
                                # Self-correction: if we rejected 3 points in a row,
                                # the tracker likely locked onto a glitch. Reset to new track.
                                if rejected_streak >= 3:
                                    last_pt = pt
                                    valid_points.append(pt)
                                    rejected_streak = 0

                                    # Set has_left_spawn if the new locked track is far away
                                    if dist_to_spawn > 50.0:
                                        has_left_spawn = True
                                continue

                    # Point is accepted
                    valid_points.append(pt)
                    last_pt = pt
                    rejected_streak = 0

                    # Confirm they've left spawn on a valid accepted point
                    if not has_left_spawn and dist_to_spawn > 50.0:
                        has_left_spawn = True

                if valid_points:
                    clean_movement[p_name][v_name] = valid_points

        # D: Preserve Full Rosters (Convert sets to lists for JSON)
        clean_teams = {str(t_id): list(players) for t_id, players in master_teams.items()}

        return_dict["result"] = {
            "status": "success",
            "data": {
                "chat": master_chat,
                "spawns": clean_spawns,
                "kills": valid_kills,
                "crits": list(master_crits.values()),
                "movement": clean_movement,
                "teams": clean_teams,
                "map_context": map_context,
                "areas": master_areas,
                "zones": master_zones,
            }
        }

    finally:
        if dll_cookie:
            dll_cookie.close()


# =========================================================
#             CRASH-PROOF PROCESS MANAGER
# =========================================================

def execute_safe_worker(file_paths, start_time_str="0:00"):
    """
    Runs the C++ bindings in an isolated process.
    Takes a LIST of absolute file paths to be merged into a single match round.
    """
    if PARSER_DIR in sys.path:
        sys.path.remove(PARSER_DIR)
    sys.path.insert(0, PARSER_DIR)

    with multiprocessing.Manager() as manager:
        return_dict = manager.dict()
        p = multiprocessing.Process(target=parse_merged_replays, args=(file_paths, return_dict, start_time_str))
        p.start()
        p.join()

        if p.exitcode != 0:
            return {"status": "failed", "error": f"Hard C++ Crash (Exit code {p.exitcode})"}

        return return_dict.get("result", {"status": "failed", "error": "Unknown execution error inside parser"})