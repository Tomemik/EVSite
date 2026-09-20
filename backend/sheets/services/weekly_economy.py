"""Read-only inputs and diagnostics for the weekly soft-cap calculation."""

import math
import re
from datetime import timedelta
from statistics import mean, median

from django.db.models import Avg, Exists, F, OuterRef, Q
from django.utils.timezone import now

from .reward_logs import get_log_match_id


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def _uncapped_reward(log):
    breakdown = log.new_value.get('breakdown') or {}
    reward = _number(breakdown.get('pre_cap_reward'))
    if reward is None:
        previous = _number(log.previous_value.get('balance'))
        current = _number(log.new_value.get('balance'))
        multiplier = _number(breakdown.get('soft_cap_multiplier', 1))
        if previous is None or current is None or multiplier is None or not 0 < multiplier <= 1:
            return None
        # Older breakdowns retain the penalty multiplier, but not the original
        # reward. Undo it rather than feeding cap-reduced payouts into the cap.
        reward = (current - previous) / multiplier
    return max(0, reward)


def calculate_cap(settings, current_time=None):
    from sheets.models import TeamLog, TeamMatch, TeamResult, TeamTank

    end = current_time or now()
    start = end - timedelta(days=7)
    absent = TeamResult.objects.filter(
        match_result__match_id=OuterRef('match_id'),
        team_id=OuterRef('team_id'),
        was_present=False,
    )
    completed = TeamMatch.objects.filter(
        match__was_played=True,
        match__datetime__lte=end,
    ).annotate(absent=Exists(absent)).filter(absent=False)

    winners = set(completed.filter(
        match__match_result__is_calced=True,
        match__mode__in=['advanced', 'evolved'],
        match__datetime__gte=start,
        side=F('match__match_result__winning_side'),
    ).values_list('match_id', 'team_id'))
    logs = TeamLog.objects.filter(
        method_name='calc_rewards',
        timestamp__gte=start,
        timestamp__lte=end,
        team_id__in={team_id for _, team_id in winners},
    ).only('team_id', 'new_value', 'previous_value', 'description').order_by('-timestamp', '-pk')

    rewards = []
    seen = set()
    for log in logs:
        key = (get_log_match_id(log), log.team_id)
        if key not in winners or key in seen:
            continue
        seen.add(key)
        # Forfeit compensation is not a reward from a played victory.
        if re.search(r'^(?:Enemy )?No Show\s*$', log.description, re.MULTILINE):
            continue
        reward = _uncapped_reward(log)
        if reward is not None:
            rewards.append(reward)

    rewards.sort()
    trim_count = int(len(rewards) * settings.reward_trim_fraction)
    retained = rewards[trim_count:len(rewards) - trim_count] if trim_count else rewards
    reward_mean = mean(retained) if retained else settings.fallback_match_reward

    active_ids = completed.filter(
        match__datetime__gte=end - timedelta(days=settings.active_team_window_days),
    ).values('team_id').distinct()
    # Average the garages first, then the teams, so large garages don't dominate.
    # Traditional loan tanks and models unavailable in either relevant mode do
    # not measure progression of the Advanced/Evolved economy.
    garages = list(TeamTank.objects.filter(
        team_id__in=active_ids,
        is_trad=False,
        tank__rank__gte=1,
    ).filter(
        Q(tank__is_allowed_in_advanced=True) | Q(tank__is_allowed_in_evolved=True)
    ).values('team_id').annotate(
        average_rank=Avg('tank__rank'),
        average_br=Avg('tank__battle_rating'),
    ))
    average_rank = mean(row['average_rank'] for row in garages) if garages else None
    average_br = mean(row['average_br'] for row in garages) if garages else None
    progression = 1.0
    if average_rank is not None:
        progression = min(
            settings.progression_max_multiplier,
            1 + max(0, average_rank - settings.progression_reference_rank) * settings.progression_per_rank,
        )

    target = reward_mean * settings.target_matches_for_cap * progression
    new_cap = max(1, int(settings.ema_weight * target + (1 - settings.ema_weight) * settings.current_cap))
    return {
        'sample_count': len(rewards),
        'trimmed_per_tail': trim_count,
        'retained_count': len(retained),
        'raw_mean': mean(rewards) if rewards else None,
        'median': median(rewards) if rewards else None,
        'reward_mean': reward_mean,
        'used_fallback': not retained,
        'active_team_count': active_ids.count(),
        'progression_team_count': len(garages),
        'average_rank': average_rank,
        'average_br': average_br,
        'progression_multiplier': progression,
        'target_cap': target,
        'previous_cap': settings.current_cap,
        'new_cap': new_cap,
    }
