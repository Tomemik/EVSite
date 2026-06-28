from collections import defaultdict
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from ..models import MatchRound, MatchKill


class StatsService:
    def __init__(self):
        self.verified_rounds = MatchRound.objects.filter(is_verified=True).select_related('match')

    def get_filtered_stats(self, filter_player=None, filter_vehicle=None):
        # Track rounds_won and matches_won
        player_stats = defaultdict(
            lambda: {'kills': 0, 'deaths': 0, 'spawns': 0, 'rounds_won': 0, 'matches': set(), 'matches_won': set(),
                     'vehicles_driven': set()})
        vehicle_stats = defaultdict(
            lambda: {'kills': 0, 'deaths': 0, 'spawns': 0, 'rounds_won': 0, 'matches': set(), 'matches_won': set(),
                     'players_list': set()})
        combo_stats = defaultdict(
            lambda: {'kills': 0, 'deaths': 0, 'spawns': 0, 'rounds_won': 0, 'matches': set(), 'matches_won': set()})

        # 1. Aggregate Spawns, Matches, and Wins
        for round_obj in self.verified_rounds:
            match_id = round_obj.match_id
            round_winner = round_obj.winning_team

            # Safely get the overall match winner if it has been calculated
            try:
                match_winner = round_obj.match.match_result.winning_side
            except ObjectDoesNotExist:
                match_winner = None
            except AttributeError:
                match_winner = None

            for team_name, spawn_list in round_obj.player_spawns.items():
                if not isinstance(spawn_list, list):
                    continue

                is_round_winner = (round_winner == team_name)
                is_match_winner = (match_winner == team_name)

                player_vehicles_this_round = defaultdict(set)

                for spawn in spawn_list:
                    player_name = spawn.get('player')
                    veh = spawn.get('vehicle') or spawn.get('veh')

                    if player_name and veh:
                        player_vehicles_this_round[player_name].add(veh)

                for player, vehicles in player_vehicles_this_round.items():
                    if filter_player and player != filter_player:
                        continue

                    player_stats[player]['matches'].add(match_id)
                    if is_match_winner:
                        player_stats[player]['matches_won'].add(match_id)

                    for veh in vehicles:
                        if filter_vehicle and veh != filter_vehicle:
                            continue

                        combo_key = f"{player}::{veh}"

                        # Update Player
                        player_stats[player]['spawns'] += 1
                        player_stats[player]['vehicles_driven'].add(veh)
                        if is_round_winner:
                            player_stats[player]['rounds_won'] += 1

                        # Update Vehicle
                        vehicle_stats[veh]['spawns'] += 1
                        vehicle_stats[veh]['matches'].add(match_id)
                        vehicle_stats[veh]['players_list'].add(player)
                        if is_round_winner:
                            vehicle_stats[veh]['rounds_won'] += 1
                        if is_match_winner:
                            vehicle_stats[veh]['matches_won'].add(match_id)

                        # Update Combo
                        combo_stats[combo_key]['spawns'] += 1
                        combo_stats[combo_key]['matches'].add(match_id)
                        if is_round_winner:
                            combo_stats[combo_key]['rounds_won'] += 1
                        if is_match_winner:
                            combo_stats[combo_key]['matches_won'].add(match_id)

        # 2. Aggregate Kills and Deaths
        valid_round_ids = self.verified_rounds.values_list('id', flat=True)
        kills = MatchKill.objects.filter(match_round_id__in=valid_round_ids)

        for kill in kills:
            attacker = kill.attacker
            attacker_veh = kill.attacker_veh
            victim = kill.victim
            victim_veh = kill.victim_veh

            if attacker:
                if (not filter_player or attacker == filter_player) and (
                        not filter_vehicle or attacker_veh == filter_vehicle):
                    player_stats[attacker]['kills'] += 1
                    vehicle_stats[attacker_veh]['kills'] += 1
                    combo_stats[f"{attacker}::{attacker_veh}"]['kills'] += 1

            if victim:
                if (not filter_player or victim == filter_player) and (
                        not filter_vehicle or victim_veh == filter_vehicle):
                    player_stats[victim]['deaths'] += 1
                    vehicle_stats[victim_veh]['deaths'] += 1
                    combo_stats[f"{victim}::{victim_veh}"]['deaths'] += 1

        return self._finalize_data(player_stats, vehicle_stats, combo_stats)

    def _finalize_data(self, player_stats, vehicle_stats, combo_stats):
        final_players = {}
        final_vehicles = {}
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
                    'matches': len(data['matches']),
                    'matches_won': len(data['matches_won']),
                    'players_list': list(data['players_list']),
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
            "combos": final_combos
        }

    def _calculate_ratios(self, data):
        kills = data['kills']
        deaths = data['deaths']
        spawns = data['spawns']

        # Calculate sets into lengths for winrate math
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