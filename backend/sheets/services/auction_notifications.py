import logging
import math
from datetime import timedelta, timezone as dt_timezone

import requests
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ..models import AuctionCycle

logger = logging.getLogger(__name__)


def _when(value):
    utc = value.astimezone(dt_timezone.utc)
    return f"{utc:%A %d %b, %H:%M} UTC (<t:{int(value.timestamp())}:F>)"


def announcement_payload(cycle, event):
    link = settings.AUCTIONS_PUBLIC_URL
    opens = _when(cycle.auction_starts_at)

    role_ids = getattr(settings, 'DISCORD_AUCTION_ROLE_IDS', [])
    mention = ""
    if role_ids:
        mention = " ".join([f"<@&{r_id}>" for r_id in role_ids]) + "\n"

    if event == 'voting_open_announced_at':
        content = (
            f"{mention}**Auction #{cycle.pk}: voting is open!**\n"
            f"Choose the tanks you want to see in the auction. "
            f"Each team has {cycle.max_votes_per_team} votes.\n"
            f"Voting closes: {_when(cycle.voting_ends_at)}\n"
            f"Bidding opens: {opens}\nVote here: {link}"
        )
    elif event == 'voting_closed_announced_at':
        content = (
            f"{mention}**Auction #{cycle.pk}: voting has ended.**\n"
            f"The results are in: {cycle.lots.count()} tank lots selected.\n"
            f"Bidding opens: {opens}\nView the auction: {link}"
        )
    elif event == 'auction_result_announced_at':
        content_lines = [
            f"{mention}**Auction #{cycle.pk}: bidding has ended!**",
            f"Here are the final results:\n"
        ]

        for lot in cycle.lots.select_related('candidate__tank', 'winner').order_by('position'):
            tank_name = lot.candidate.tank.name
            if lot.winner:
                content_lines.append(f"• Lot #{lot.position} ({tank_name}): Won by **{lot.winner.name}** for **${lot.winning_bid:,}**")
            else:
                content_lines.append(f"• Lot #{lot.position} ({tank_name}): Passed (No bids)")

        content = "\n".join(content_lines)
    else:
        content = (
            f"{mention}**Auction #{cycle.pk}: bidding opens soon!**\n"
            f"Bidding opens: {opens} — <t:{int(cycle.auction_starts_at.timestamp())}:R>\n"
            f"Get ready to bid on {cycle.lots.count()} tank lots.\n"
            f"Auction: {link}"
        )

    if role_ids:
        return {
            'content': content,
            'allowed_mentions': {'roles': role_ids}
        }

    return {
        'content': content,
        'allowed_mentions': {'parse': []}
    }


def _due_events(cycle, at):
    if not cycle.auction_starts_at or not cycle.voting_ends_at:
        return []

    if cycle.status == AuctionCycle.Status.VOTING:
        if cycle.voting_starts_at and cycle.voting_starts_at <= at < cycle.voting_ends_at:
            return ['voting_open_announced_at']
    elif cycle.status == AuctionCycle.Status.SCHEDULED and cycle.voting_ends_at <= at < cycle.auction_starts_at:
        events = ['voting_closed_announced_at']
        if cycle.auction_starts_at - timedelta(hours=1) <= at:
            events.append('auction_reminder_announced_at')
        return events
    elif cycle.status == AuctionCycle.Status.FINISHED:
        return ['auction_result_announced_at']

    return []

def _retry_seconds(response):
    delay = 60
    if response is not None and response.status_code == 429:
        try:
            value = float(response.json().get('retry_after', 60))
            if math.isfinite(value):
                delay = max(60, value)
        except (ValueError, TypeError, AttributeError):
            pass
    return delay


def send_due_auction_announcements(at=None):
    at = at or timezone.now()
    webhook = settings.DISCORD_WEBHOOK_URL_AUCTIONS
    result = {'announcements_sent': 0, 'announcements_failed': 0}
    if not webhook:
        return result

    ids = AuctionCycle.objects.filter(
        Q(status__in=[AuctionCycle.Status.VOTING, AuctionCycle.Status.SCHEDULED]) |
        Q(status=AuctionCycle.Status.FINISHED, auction_result_announced_at__isnull=True)
    ).values_list('pk', flat=True)

    for cycle_id in list(ids):
        with transaction.atomic():
            cycle = AuctionCycle.objects.select_for_update().get(pk=cycle_id)
            if cycle.discord_retry_after and cycle.discord_retry_after > at:
                continue
            for event in _due_events(cycle, at):
                if getattr(cycle, event) is not None:
                    continue
                response = None
                confirmed = False
                try:
                    response = requests.post(
                        webhook,
                        params={'wait': 'true'},
                        json=announcement_payload(cycle, event),
                        timeout=(3, 10),
                        allow_redirects=False,
                    )
                    confirmed = response.status_code == 200 and bool(response.json().get('id'))
                except (requests.RequestException, ValueError, AttributeError):
                    pass
                if not confirmed:
                    cycle.discord_retry_after = at + timedelta(seconds=_retry_seconds(response))
                    cycle.save(update_fields=['discord_retry_after'])
                    logger.warning('Auction %s announcement %s failed (HTTP %s); will retry.',
                                   cycle.pk, event, response.status_code if response is not None else 'unavailable')
                    result['announcements_failed'] += 1
                    break
                setattr(cycle, event, at)
                cycle.discord_retry_after = None
                cycle.save(update_fields=[event, 'discord_retry_after'])
                result['announcements_sent'] += 1
    return result