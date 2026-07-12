from collections import defaultdict
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from ..models import MatchRound, MatchKill, Tank


class StatsService:
    def __init__(self):
        self.verified_rounds = MatchRound.objects.filter(is_verified=True).select_related('match')

    def get_filtered_stats(self, filter_players=None, filter_vehicle=None,
                           filter_team=None, filter_tier_context=None,
                           min_br=None, max_br=None, tank_type=None, tank_rank=None):

        # 1. Base Tank Query & Filtering
        tank_qs = Tank.objects.all()

        if tank_type:
            type_clumps = {
                'LT': ['LT', 'LT/SPG', 'LT/TD', 'PWLT'],
                'MT': ['MT', 'MT/SPG', 'PWMT', 'MBT'],
                'HT': ['HT', 'HT/A', 'PWHT'],
                'TD': ['TD', 'TD/A', 'TD/SPG', 'PWTD', 'PWTD/SPG']
            }
            allowed_types = type_clumps.get(tank_type.upper(), [tank_type])
            tank_qs = tank_qs.filter(type__in=allowed_types)

        if min_br is not None: tank_qs = tank_qs.filter(battle_rating__gte=float(min_br))
        if max_br is not None: tank_qs = tank_qs.filter(battle_rating__lte=float(max_br))
        if tank_rank: tank_qs = tank_qs.filter(rank=int(tank_rank))

        valid_tanks = {t.name: t for t in tank_qs}
        all_tank_brs = {t.name: t.battle_rating for t in Tank.objects.all()}

        player_stats = defaultdict(
            lambda: {'kills': 0, 'deaths': 0, 'spawns': 0, 'rounds_won': 0, 'matches': set(), 'matches_won': set(),
                     'vehicles_driven': set()})
        vehicle_stats = defaultdict(
            lambda: {'kills': 0, 'deaths': 0, 'spawns': 0, 'rounds_won': 0, 'matches': set(), 'matches_won': set(),
                     'unique_matches': set(), 'players_list': set()})  # <--- ADDED unique_matches
        combo_stats = defaultdict(
            lambda: {'kills': 0, 'deaths': 0, 'spawns': 0, 'rounds_won': 0, 'matches': set(), 'matches_won': set()})

        # Track valid spawns to ensure Kills/Deaths match the filters
        valid_spawns = set()
        total_valid_matches = set()

        # 2. Aggregate Spawns, Matches, and Wins
        for round_obj in self.verified_rounds:
            match_id = round_obj.match_id

            # Map "team_1" and "team_2" to actual DB Team Names
            team_map = {tm.side: tm.team.name for tm in round_obj.match.teammatch_set.all()}

            try:
                match_winner_side = round_obj.match.match_result.winning_side
                match_winner = team_map.get(match_winner_side)
            except (ObjectDoesNotExist, AttributeError):
                match_winner = None

            round_winner = team_map.get(round_obj.winning_team)

            # Calculate Match Max BR for Tier Context
            round_tanks = []
            for side, spawn_list in round_obj.player_spawns.items():
                if isinstance(spawn_list, list):
                    for s in spawn_list:
                        v = s.get('vehicle') or s.get('veh')
                        if v in all_tank_brs:
                            round_tanks.append(all_tank_brs[v])
            match_max_br = max(round_tanks) if round_tanks else 0.0

            for side, spawn_list in round_obj.player_spawns.items():
                if not isinstance(spawn_list, list):
                    continue

                actual_team_name = team_map.get(side)

                # Apply Team Filter
                if filter_team and actual_team_name != filter_team:
                    continue

                is_round_winner = (round_winner == actual_team_name)
                is_match_winner = (match_winner == actual_team_name)

                for spawn in spawn_list:
                    player_name = spawn.get('player')
                    veh = spawn.get('vehicle') or spawn.get('veh')

                    if not player_name or not veh:
                        continue

                    # Apply Player & Exact Vehicle Filters (From Popup Dialog)
                    if filter_players and player_name not in filter_players:
                        continue
                    if filter_vehicle and veh != filter_vehicle:
                        continue

                    # Apply BR/Rank/Type Filters
                    if veh not in valid_tanks:
                        continue

                    if filter_tier_context and veh in all_tank_brs:
                        diff = round(match_max_br - all_tank_brs[veh], 1)

                        if filter_tier_context == 'top' and diff > 0.0:
                            continue
                        elif filter_tier_context == 'mid' and (diff <= 0.0 or diff > 1.0):
                            continue
                        elif filter_tier_context == 'bottom' and diff <= 1.0:
                            continue

                    # Register as a strictly valid spawn
                    valid_spawns.add((round_obj.id, player_name, veh))
                    total_valid_matches.add(match_id)

                    combo_key = f"{player_name}::{veh}"
                    veh_match_participation = f"{match_id}_{actual_team_name}"

                    # Update Player
                    player_stats[player_name]['spawns'] += 1
                    player_stats[player_name]['vehicles_driven'].add(veh)
                    player_stats[player_name]['matches'].add(match_id)
                    if is_round_winner: player_stats[player_name]['rounds_won'] += 1
                    if is_match_winner: player_stats[player_name]['matches_won'].add(match_id)

                    # Update Vehicle
                    vehicle_stats[veh]['spawns'] += 1
                    vehicle_stats[veh]['players_list'].add(player_name)
                    vehicle_stats[veh]['matches'].add(veh_match_participation)  # Triggers accurate WR split
                    vehicle_stats[veh]['unique_matches'].add(match_id)  # <--- Triggers accurate raw count
                    if is_round_winner: vehicle_stats[veh]['rounds_won'] += 1
                    if is_match_winner: vehicle_stats[veh]['matches_won'].add(veh_match_participation)

                    # Update Combo
                    combo_stats[combo_key]['spawns'] += 1
                    combo_stats[combo_key]['matches'].add(match_id)
                    if is_round_winner: combo_stats[combo_key]['rounds_won'] += 1
                    if is_match_winner: combo_stats[combo_key]['matches_won'].add(match_id)

        # 3. Aggregate Kills and Deaths safely matching the filtered spawns
        valid_round_ids = self.verified_rounds.values_list('id', flat=True)
        kills = MatchKill.objects.filter(match_round_id__in=valid_round_ids)

        for kill in kills:
            attacker = kill.attacker
            attacker_veh = kill.attacker_veh
            victim = kill.victim
            victim_veh = kill.victim_veh

            if attacker and (kill.match_round_id, attacker, attacker_veh) in valid_spawns:
                player_stats[attacker]['kills'] += 1
                vehicle_stats[attacker_veh]['kills'] += 1
                combo_stats[f"{attacker}::{attacker_veh}"]['kills'] += 1

            if victim and (kill.match_round_id, victim, victim_veh) in valid_spawns:
                player_stats[victim]['deaths'] += 1
                vehicle_stats[victim_veh]['deaths'] += 1
                combo_stats[f"{victim}::{victim_veh}"]['deaths'] += 1

        return self._finalize_data(player_stats, vehicle_stats, combo_stats, valid_tanks, len(total_valid_matches))

    def _finalize_data(self, player_stats, vehicle_stats, combo_stats, valid_tanks, total_matches):
        final_players = {}
        final_vehicles = {}
        final_all_tanks = {}
        final_combos = {}

        for p, data in player_stats.items():
            if data['spawns'] > 0 or data['kills'] > 0 or data['deaths'] > 0:
                final_players[p] = {
                    **data,
                    'matches': len(data['matches']),
                    'matches_won': len(data['matches_won']),
                    'vehicles_driven': list(data['vehicles_driven']),
                    **self._calculate_ratios(data)
                }

        for v, data in vehicle_stats.items():
            if data['spawns'] > 0 or data['kills'] > 0 or data['deaths'] > 0:
                final_vehicles[v] = {
                    **data,
                    'matches': len(data.get('unique_matches', set())),  # <--- Output exact real number
                    'matches_won': len(data['matches_won']),
                    'players_list': list(data['players_list']),
                    **self._calculate_ratios(data)
                }

        # Build "All DB Tanks" tracking 0-stats for unplayed vehicles
        for tank_name, tank_obj in valid_tanks.items():
            data = vehicle_stats.get(tank_name, {
                'kills': 0, 'deaths': 0, 'spawns': 0, 'rounds_won': 0,
                'matches': set(), 'matches_won': set(), 'unique_matches': set(), 'players_list': set()
            })

            unique_matches_count = len(data.get('unique_matches', set()))
            participation_rate = round((unique_matches_count / total_matches) * 100, 2) if total_matches > 0 else 0.0

            final_all_tanks[tank_name] = {
                **data,
                'matches': unique_matches_count,  # <--- Output exact real number
                'matches_won': len(data.get('matches_won', [])),
                'players_list': list(data.get('players_list', [])),
                'participation_rate': participation_rate,
                **self._calculate_ratios(data)
            }

        for c, data in combo_stats.items():
            if data['spawns'] > 0 or data['kills'] > 0 or data['deaths'] > 0:
                p_name, v_name = c.split('::')
                final_combos[c] = {
                    'player': p_name,
                    'vehicle': v_name,
                    **data,
                    'matches': len(data['matches']),
                    'matches_won': len(data['matches_won']),
                    **self._calculate_ratios(data)
                }

        return {
            "players": final_players,
            "vehicles": final_vehicles,
            "all_tanks": final_all_tanks,
            "combos": final_combos
        }

    def _calculate_ratios(self, data):
        kills = data['kills']
        deaths = data['deaths']
        spawns = data['spawns']

        # Win Rate Math MUST still use the separated participation list
        # so mirror matchups resolve as exactly 1 W / 1 L (50% WR)
        matches_played = len(data.get('matches', []))
        matches_won = len(data.get('matches_won', []))
        rounds_won = data.get('rounds_won', 0)

        match_wr = (matches_won / matches_played * 100) if matches_played > 0 else 0.0
        round_wr = (rounds_won / spawns * 100) if spawns > 0 else 0.0

        return {
            'kd_ratio': round(kills / deaths, 2) if deaths > 0 else float(kills),
            'kills_per_spawn': round(kills / spawns, 2) if spawns > 0 else 0.0,
            'match_winrate': round(match_wr, 1),
            'round_winrate': round(round_wr, 1)
        }