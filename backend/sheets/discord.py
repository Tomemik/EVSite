import pytz
import datetime
from .models import TeamMatch, TeamTank, Match, Substitute, MatchResult
from django.conf import settings


def discord_message_url(channel_id, message_id):
    guild_id = settings.DISCORD_GUILD_ID
    if not message_id:
        return None
    base = "https://discord.com/channels"
    return f"{base}/{guild_id}/{channel_id}/{message_id}"

def format_match_message(match):

    teams_by_side = {
        'team_1': [],
        'team_2': [],
    }

    tanks_by_side = {
        'team_1': [],
        'team_2': [],
    }

    team_mentions = {
        'team_1': [],
        'team_2': [],
    }


    team_matches = TeamMatch.objects.filter(match=match)
    for team_match in team_matches:
        teams_by_side[team_match.side].append(f"**{team_match.team.name}**")
        team_mentions[team_match.side].append(f"<@&{team_match.team.discord_role_id}>")

        tanks = TeamTank.objects.filter(team_matches=team_match).order_by('-tank__battle_rating')
        tanks_by_side[team_match.side].append([tank.tank.name for tank in tanks])  # Store list of tank names

    team_1_names = ", ".join(teams_by_side['team_1'])
    team_2_names = ", ".join(teams_by_side['team_2'])
    team_1_mentions = " ".join(team_mentions['team_1'])
    team_2_mentions = " ".join(team_mentions['team_2'])


    team_1_tanks = ""
    for idx, team_name in enumerate(teams_by_side['team_1']):
        team_1_tanks += f"{team_name}:\n"
        team_1_tanks += "\n".join(tanks_by_side['team_1'][idx]) + "\n\n"

    team_2_tanks = ""
    for idx, team_name in enumerate(teams_by_side['team_2']):
        team_2_tanks += f"{team_name}:\n"
        team_2_tanks += "\n".join(tanks_by_side['team_2'][idx]) + "\n\n"

    match_date_utc = match.datetime  # Assuming 'datetime' is UTC or can be converted
    formatted_utc_date = match_date_utc.strftime('%A, %d.%m.%Y - %H:%M UTC')

    utc_timestamp = int(match_date_utc.timestamp())  # Absolute timestamp in seconds (for Discord)
    local_timestamp = int(match_date_utc.timestamp())  # Local absolute timestamp for Discord

    utc_time = f"<t:{utc_timestamp}>"
    local_time = f"<t:{local_timestamp}>"
    time_remaining = f"<t:{local_timestamp}:R>"  # Relative timestamp (e.g., "in 6 hours")

    match_mode = dict(Match.MODE_CHOICES).get(match.mode, "Unknown Mode")
    gamemode = dict(Match.GAMEMODE_CHOICES).get(match.gamemode, "Unknown Game Mode")
    money_rules = dict(Match.MONEY_RULES).get(match.money_rules, "None")

    message = f"""
{team_1_mentions} vs {team_2_mentions}
{formatted_utc_date} - {local_time} ; {time_remaining}
{match_mode}, {gamemode} - Bo{match.best_of_number} {match.map_selection}
{money_rules}
{match.special_rules if match.special_rules else "No Special Rules"}

{team_1_tanks} --- vs. ---

{team_2_tanks}
"""

    return message


def format_match_result_message(match):
    # Retrieve the MatchResult via reverse query
    match_result = getattr(match, 'match_result', None)
    if not match_result:
        return "No results found for this match."

    # Match details
    match_date_utc = match.datetime
    formatted_utc_date = match_date_utc.strftime('%A, %d.%m.%Y - %H:%M UTC')
    match_mode = dict(Match.MODE_CHOICES).get(match.mode, "Unknown Mode")
    gamemode = dict(Match.GAMEMODE_CHOICES).get(match.gamemode, "Unknown Game Mode")
    map_selection = match.map_selection
    best_of_number = match.best_of_number
    money_rules = dict(Match.MONEY_RULES).get(match.money_rules, "None")
    special_rules = match.special_rules if match.special_rules else "No Special Rules"

    # Judge and score
    judge_name = match_result.judge.name if match_result.judge else "None"
    winning_side = dict(TeamMatch.SIDE_CHOICES).get(match_result.winning_side, "Unknown")
    round_score = match_result.round_score if match_result.round_score else "N/A"

    schedule_url = discord_message_url(match.channel_id_schedule, match.webhook_id_schedule)
    schedule_link = f"[View Schedule]({schedule_url})" if schedule_url else "Schedule link unavailable."

    # Initialize teams and data
    teams_by_side = {
        'team_1': [],
        'team_2': [],
    }

    bonuses_by_side = {
        'team_1': [],
        'team_2': [],
    }

    penalties_by_side = {
        'team_1': [],
        'team_2': [],
    }

    substitutes_by_side = {
        'team_1': [],
        'team_2': [],
    }

    tanks_lost_by_side = {
        'team_1': [],
        'team_2': [],
    }

    # Populate team results
    team_results = match_result.team_results.all()
    tanks_lost = match_result.tanks_lost.all()
    substitutes = match_result.substitutes.all()

    team_matches = TeamMatch.objects.filter(match=match)
    for team_match in team_matches:
        side = team_match.side
        teams_by_side[side].append(f"**{team_match.team.name}**")

        # Bonuses and penalties
        team_result = team_results.filter(team=team_match.team).first()
        if team_result:
            bonuses_by_side[side].append(team_result.bonuses or 0)
            penalties_by_side[side].append(team_result.penalties or 0)

        # Tanks lost
        team_tanks_lost = tanks_lost.filter(team=team_match.team).order_by('-tank__battle_rating')
        tanks_lost_by_side[side].append([
            f"x{tank.quantity} - {tank.tank.name}" for tank in team_tanks_lost
        ])

        # Substitutes
        team_substitutes = substitutes.filter(team_played_for=team_match.team)
        substitutes_by_side[side].append([
            f"{sub.team.name} - {sub.get_activity_display()}"
            for sub in team_substitutes
        ])

    def format_side(side):
        side_message = ""
        for idx, team_name in enumerate(teams_by_side[side]):
            side_message += f"{team_name}:\n"
            side_message += f"Bonuses: {bonuses_by_side[side][idx]}\n"
            side_message += f"Penalties: {penalties_by_side[side][idx]}\n"

            substitutes = substitutes_by_side[side][idx]
            substitutes_text = "\n".join(substitutes) if substitutes else "None"
            side_message += f"Substitutes:\n{substitutes_text}\n\n"

            tanks_lost = tanks_lost_by_side[side][idx]
            tanks_lost_text = "\n".join(tanks_lost) if tanks_lost else "None"
            side_message += f"Tanks Lost:\n{tanks_lost_text}\n\n"

        return side_message

    winning_side_teams = [
        team_match.team.name for team_match in team_matches if team_match.side == match_result.winning_side
    ]

    winning_side_names = ", ".join(winning_side_teams) if winning_side_teams else "Unknown"

    message = f"""
{formatted_utc_date}
{gamemode}, {match_mode}, Bo{best_of_number}, {map_selection}
{money_rules}
{special_rules}

Judge: {judge_name}

{winning_side_names} win {round_score}

{format_side('team_1')}--- vs. ---\n\n{format_side('team_2')}
{schedule_link}
"""

    return message


def format_match_calc_message(match, rewards_summary):
    match_date_utc = match.datetime
    formatted_utc_date = match_date_utc.strftime('%A, %d.%m.%Y - %H:%M UTC')
    match_mode = dict(Match.MODE_CHOICES).get(match.mode, "Unknown Mode")
    gamemode = dict(Match.GAMEMODE_CHOICES).get(match.gamemode, "Unknown Game Mode")
    map_selection = match.map_selection
    best_of_number = match.best_of_number
    money_rules = dict(Match.MONEY_RULES).get(match.money_rules, "None")
    special_rules = match.special_rules if match.special_rules else "No Special Rules"

    schedule_url = discord_message_url(match.channel_id_schedule, match.webhook_id_schedule)
    result_url = discord_message_url(match.channel_id_result, match.webhook_id_result)

    schedule_link = f"[View Schedule]({schedule_url})" if schedule_url else "Schedule link unavailable."
    result_link = f"[View Result]({result_url})" if result_url else "Result link unavailable."

    teams_by_side = {
        'team_1': [],
        'team_2': [],
    }

    team_matches = TeamMatch.objects.filter(match=match)
    for team_match in team_matches:
        teams_by_side[team_match.side].append(f"**{team_match.team.name}**")
        team_1_names = ", ".join(teams_by_side['team_1'])
        team_2_names = ", ".join(teams_by_side['team_2'])

    message = f"""
{team_1_names} Vs. {team_2_names}
{formatted_utc_date}
{gamemode}, {match_mode}, Bo{best_of_number}, {map_selection}
{money_rules}
{special_rules}\n\n"""

    if rewards_summary["winning_teams"]:
        message += "**Winning Teams:**\n"
        for team_name, team_data in rewards_summary["winning_teams"].items():
            message += f" - {team_name}: {team_data['reward']}\n"

    if rewards_summary["losing_teams"]:
        message += "\n**Losing Teams:**\n"
        for team_name, team_data in rewards_summary["losing_teams"].items():
            message += f" - {team_name}: {team_data['reward']}\n"

    if rewards_summary.get("kits"):
        message += "\n**Kits Distributed:**\n"
        for team_name, kit_data in rewards_summary["kits"].items():
            message += f" - {team_name}: {kit_data['T1_kits_received']} T1 kits\n"

    if rewards_summary["substitutes"]:
        message += "\n**Substitutes:**\n"
        for sub_team_name, sub_data in rewards_summary["substitutes"].items():
            message += f" - {sub_team_name}: {sub_data['reward']}\n"

    if rewards_summary["judge"]:
        judge_data = rewards_summary["judge"]
        message += f"\n**Judge:**\n - {judge_data['name']}: {judge_data['reward']}\n"

    message += f"\n{schedule_link} | {result_link}"


    return message