import heapq
from datetime import datetime, time, timedelta, timezone as dt_timezone
from fractions import Fraction

from django.db import transaction
from django.db.models import Count, Max, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from ..models import (
    Team,
    TeamTank,
    TeamLog,
    ImportTank,
    AuctionCycle,
    AuctionImportBatch,
    AuctionCandidate,
    AuctionCandidateSource,
    AuctionVote,
    AuctionLot,
    AuctionBid, AuctionIgnoredImportBatch,
)


AUCTION_DURATION = timedelta(hours=1)
BID_EXTENSION_WINDOW = timedelta(
    minutes=5
)

AUCTION_START_HOUR_UTC = 17


def _user_label(user):
    if user is None:
        return 'system'

    username = getattr(user, 'username', None)
    if username:
        return username

    return str(user)


def next_sunday_17utc(after_datetime):
    """
    Return the first Sunday at 17:00 UTC strictly after after_datetime.
    """

    after_utc = after_datetime.astimezone(dt_timezone.utc)

    days_until_sunday = (6 - after_utc.weekday()) % 7
    target_date = after_utc.date() + timedelta(
        days=days_until_sunday
    )

    candidate = datetime.combine(
        target_date,
        time(
            hour=AUCTION_START_HOUR_UTC,
            minute=0,
            second=0,
            tzinfo=dt_timezone.utc,
        ),
    )

    if candidate <= after_utc:
        candidate += timedelta(days=7)

    return candidate


def get_or_create_collecting_cycle():
    """
    There should normally be exactly one collecting cycle.

    This cycle represents the NEXT auction and can exist while the
    previous cycle is voting/scheduled/live.
    """

    cycle = (
        AuctionCycle.objects
        .filter(status=AuctionCycle.Status.COLLECTING)
        .order_by('created_at')
        .first()
    )

    if cycle:
        return cycle

    return AuctionCycle.objects.create(
        status=AuctionCycle.Status.COLLECTING,
    )


def start_voting(cycle, at=None):
    """
    Open voting until the next Saturday night (Sunday 00:00 UTC).
    """

    at = at or timezone.now()

    if cycle.status != AuctionCycle.Status.COLLECTING:
        return cycle

    voting_ends_at = next_voting_close(at)
    auction_starts_at = next_sunday_17utc(voting_ends_at)

    cycle.status = AuctionCycle.Status.VOTING

    cycle.voting_starts_at = at
    cycle.voting_ends_at = voting_ends_at

    cycle.auction_starts_at = auction_starts_at
    cycle.auction_ends_at = (
        auction_starts_at + AUCTION_DURATION
    )

    cycle.save(
        update_fields=[
            'status',
            'voting_starts_at',
            'voting_ends_at',
            'auction_starts_at',
            'auction_ends_at',
        ]
    )

    return cycle


def next_voting_close(after_datetime):
    """First Sunday 00:00 UTC strictly after voting opens."""
    after_utc = after_datetime.astimezone(dt_timezone.utc)
    target_date = after_utc.date() + timedelta(days=(6 - after_utc.weekday()) % 7)
    deadline = datetime.combine(target_date, time(tzinfo=dt_timezone.utc))
    if deadline <= after_utc:
        deadline += timedelta(days=7)
    return deadline


def sync_expired_import_batches(at=None):
    """
    Process historical/current expired import batches into auction cycles.

    Rules:
      - expired batches are processed oldest first
      - collecting cycles contain at most `batch_target` import batches
      - only ONE auction cycle may be voting/scheduled/live at once
      - while an auction is active, the NEXT auction cycle may continue
        collecting up to 8/8
      - if a collecting cycle reaches 8/8 while another auction is active,
        it simply waits at 8/8
      - once the active auction finishes, the next tick opens voting
    """

    at = at or timezone.now()

    processed_batch_times = (
        AuctionImportBatch.objects
        .values_list(
            'available_from',
            flat=True,
        )
    )

    ignored_batch_times = (
        AuctionIgnoredImportBatch.objects
        .values_list(
            'available_from',
            flat=True,
        )
    )

    expired_batches = list(
        ImportTank.objects
        .values('available_from')
        .annotate(
            batch_expires_at=Max('available_until'),
            total_imports=Count('id'),
        )
        .filter(
            batch_expires_at__lte=at
        )
        .exclude(
            available_from__in=processed_batch_times
        )
        .exclude(
            available_from__in=ignored_batch_times
        )
        .order_by('available_from')
    )

    processed_count = 0
    candidate_source_count = 0
    opened_voting_count = 0

    for batch_data in expired_batches:
        batch_available_from = (
            batch_data['available_from']
        )

        batch_expires_at = (
            batch_data['batch_expires_at']
        )

        with transaction.atomic():
            # Another tick/process could have handled it.
            if AuctionImportBatch.objects.filter(
                available_from=batch_available_from
            ).exists():
                continue

            cycle = get_or_create_collecting_cycle()

            cycle = (
                AuctionCycle.objects
                .select_for_update()
                .get(pk=cycle.pk)
            )

            # -----------------------------------------------------
            # This collecting cycle is already full.
            #
            # If another auction is active, leave this one waiting
            # rather than putting import #9 into the same cycle.
            # -----------------------------------------------------

            if (
                cycle.import_batches.count()
                >= cycle.batch_target
            ):
                active_exists = (
                    AuctionCycle.objects
                    .filter(
                        status__in=[
                            AuctionCycle.Status.VOTING,
                            AuctionCycle.Status.SCHEDULED,
                            AuctionCycle.Status.LIVE,
                        ]
                    )
                    .exclude(pk=cycle.pk)
                    .exists()
                )

                if active_exists:
                    # Do not consume further historical imports yet.
                    #
                    # They'll remain available to the next auction
                    # after this full collecting cycle starts voting.
                    break

                # No active auction exists, so this full collecting
                # cycle can begin voting now.
                start_voting(
                    cycle,
                    at=at,
                )

                opened_voting_count += 1

                # Create the NEXT collecting cycle.
                cycle = get_or_create_collecting_cycle()

                cycle = (
                    AuctionCycle.objects
                    .select_for_update()
                    .get(pk=cycle.pk)
                )

            # -----------------------------------------------------
            # Process this import batch
            # -----------------------------------------------------

            imports = list(
                ImportTank.objects
                .select_related('tank')
                .filter(
                    available_from=batch_available_from
                )
                .order_by('id')
            )

            leftovers = [
                import_tank
                for import_tank in imports
                if not import_tank.is_purchased
            ]

            AuctionImportBatch.objects.create(
                cycle=cycle,

                available_from=(
                    batch_available_from
                ),

                expired_at=(
                    batch_expires_at
                ),

                total_imports=len(imports),
                leftover_imports=len(leftovers),
            )

            for import_tank in leftovers:
                candidate, _ = (
                    AuctionCandidate.objects
                    .get_or_create(
                        cycle=cycle,
                        tank=import_tank.tank,
                    )
                )

                _, source_created = (
                    AuctionCandidateSource.objects
                    .get_or_create(
                        source_import=import_tank,

                        defaults={
                            'candidate': candidate,
                        },
                    )
                )

                if source_created:
                    candidate_source_count += 1

            processed_count += 1

            # -----------------------------------------------------
            # Did this batch make the cycle 8 / 8?
            # -----------------------------------------------------

            batches_collected = (
                cycle.import_batches.count()
            )

            if (
                batches_collected
                >= cycle.batch_target
            ):
                active_exists = (
                    AuctionCycle.objects
                    .filter(
                        status__in=[
                            AuctionCycle.Status.VOTING,
                            AuctionCycle.Status.SCHEDULED,
                            AuctionCycle.Status.LIVE,
                        ]
                    )
                    .exclude(pk=cycle.pk)
                    .exists()
                )

                if not active_exists:
                    start_voting(
                        cycle,
                        at=at,
                    )

                    opened_voting_count += 1

                    # Make the empty next pool immediately.
                    get_or_create_collecting_cycle()

                else:
                    # This cycle remains COLLECTING at 8 / 8.
                    #
                    # It is effectively "ready and waiting".
                    break

    get_or_create_collecting_cycle()

    return {
        'processed_import_batches': (
            processed_count
        ),

        'added_leftover_imports': (
            candidate_source_count
        ),

        'opened_voting_cycles': (
            opened_voting_count
        ),
    }


def build_auction_lots(cycle):
    """
    Turn voting results into individual physical AuctionLot rows.
    """

    # Idempotency.
    if cycle.lots.exists():
        return

    allocation = allocate_auction_copies(
        cycle
    )

    cycle.candidates.update(
        selected_quantity=0
    )

    position = 1

    candidates = (
        cycle.candidates
        .select_related('tank')
        .prefetch_related(
            'sources__source_import'
        )
        .order_by('id')
    )

    for candidate in candidates:
        selected_quantity = allocation.get(
            candidate.id,
            0,
        )

        if selected_quantity <= 0:
            continue

        candidate.selected_quantity = (
            selected_quantity
        )

        candidate.save(
            update_fields=[
                'selected_quantity'
            ]
        )

        # Oldest leftover copies are consumed first.
        sources = list(
            candidate.sources
            .select_related('source_import')
            .order_by(
                'source_import__available_from',
                'source_import_id',
            )[:selected_quantity]
        )

        for source in sources:
            AuctionLot.objects.create(
                cycle=cycle,
                candidate=candidate,
                source=source,

                position=position,

                starting_bid=max(
                    int(candidate.tank.price * 0.30),
                    0,
                ),

                minimum_increment=(
                    cycle.minimum_increment
                ),

                # Every lot begins with the normal
                # one-hour closing deadline.
                ends_at=cycle.auction_ends_at,
            )

            position += 1


def close_due_voting(at=None):
    """
    Find voting cycles whose voting period has ended and create their lots.
    """

    at = at or timezone.now()

    cycle_ids = list(
        AuctionCycle.objects
        .filter(
            status=AuctionCycle.Status.VOTING,
            voting_ends_at__lte=at,
        )
        .values_list('id', flat=True)
    )

    closed = 0

    for cycle_id in cycle_ids:
        with transaction.atomic():
            cycle = (
                AuctionCycle.objects
                .select_for_update()
                .get(pk=cycle_id)
            )

            if cycle.status != AuctionCycle.Status.VOTING:
                continue

            if (
                cycle.voting_ends_at is None
                or cycle.voting_ends_at > at
            ):
                continue

            build_auction_lots(cycle)

            cycle.status = AuctionCycle.Status.SCHEDULED
            cycle.save(
                update_fields=['status']
            )

            closed += 1

    return closed


def mark_live_auctions(at=None):
    """
    This status is mainly for display.

    Bid validation itself always checks timestamps, so auctions still
    open exactly on time even if cron runs a few seconds late.
    """

    at = at or timezone.now()

    return (
        AuctionCycle.objects
        .filter(
            status=AuctionCycle.Status.SCHEDULED,
            auction_starts_at__lte=at,
            auction_ends_at__gt=at,
        )
        .update(
            status=AuctionCycle.Status.LIVE
        )
    )


def place_vote(
    cycle_id,
    candidate_id,
    team,
    user,
):
    """
    Add ONE vote to a tank.

    Rules:
      - maximum 5 votes total per school
      - same tank may receive multiple votes
      - maximum votes from one school to one tank equals
        the number of available copies

    Example:
        3 T-72 copies available
        => one school can vote T-72 at most 3 times
    """

    current_time = timezone.now()

    with transaction.atomic():
        # Serializes actions from multiple commanders
        # belonging to the same school.
        team = (
            Team.objects
            .select_for_update()
            .get(pk=team.pk)
        )

        cycle = (
            AuctionCycle.objects
            .select_for_update()
            .get(pk=cycle_id)
        )

        if cycle.status != AuctionCycle.Status.VOTING:
            raise ValidationError(
                "Voting is not open."
            )

        if not (
            cycle.voting_starts_at
            <= current_time
            < cycle.voting_ends_at
        ):
            raise ValidationError(
                "Voting is not currently open."
            )

        try:
            candidate = (
                AuctionCandidate.objects
                .select_for_update()
                .get(
                    pk=candidate_id,
                    cycle=cycle,
                )
            )
        except AuctionCandidate.DoesNotExist:
            raise ValidationError(
                "This tank is not available in this auction."
            )

        # -------------------------------------------
        # Total school allocation
        # -------------------------------------------

        total_used = (
            AuctionVote.objects
            .filter(
                cycle=cycle,
                team=team,
            )
            .aggregate(
                total=Sum('quantity')
            )['total']
            or 0
        )

        if total_used >= cycle.max_votes_per_team:
            raise ValidationError(
                f"Your school has already used all "
                f"{cycle.max_votes_per_team} votes."
            )

        # -------------------------------------------
        # Allocation to this particular tank
        # -------------------------------------------

        allocation = (
            AuctionVote.objects
            .select_for_update()
            .filter(
                cycle=cycle,
                team=team,
                candidate=candidate,
            )
            .first()
        )

        current_quantity = (
            allocation.quantity
            if allocation
            else 0
        )

        available_copies = (
            candidate.sources.count()
        )

        if current_quantity >= available_copies:
            raise ValidationError(
                f"There are only {available_copies} "
                f"copies of {candidate.tank.name} "
                f"in this auction pool."
            )

        if allocation:
            allocation.quantity += 1
            allocation.user = _user_label(user)

            allocation.save(
                update_fields=[
                    'quantity',
                    'user',
                    'updated_at',
                ]
            )

        else:
            allocation = AuctionVote.objects.create(
                cycle=cycle,
                candidate=candidate,
                team=team,
                quantity=1,
                user=_user_label(user),
            )

        return allocation


def remove_vote(
    cycle_id,
    candidate_id,
    team,
):
    """
    Remove ONE vote from the team's allocation.
    """

    current_time = timezone.now()

    with transaction.atomic():
        team = (
            Team.objects
            .select_for_update()
            .get(pk=team.pk)
        )

        cycle = (
            AuctionCycle.objects
            .select_for_update()
            .get(pk=cycle_id)
        )

        if cycle.status != AuctionCycle.Status.VOTING:
            raise ValidationError(
                "Voting is not open."
            )

        if not (
            cycle.voting_starts_at
            <= current_time
            < cycle.voting_ends_at
        ):
            raise ValidationError(
                "Voting is not currently open."
            )

        allocation = (
            AuctionVote.objects
            .select_for_update()
            .filter(
                cycle=cycle,
                candidate_id=candidate_id,
                team=team,
            )
            .first()
        )

        if not allocation:
            raise ValidationError(
                "Your school has no votes allocated "
                "to this tank."
            )

        if allocation.quantity <= 1:
            allocation.delete()
        else:
            allocation.quantity -= 1

            allocation.save(
                update_fields=[
                    'quantity',
                    'updated_at',
                ]
            )

        return True


def place_bid(
    lot_id,
    team,
    user,
    amount,
):
    current_time = timezone.now()

    try:
        amount = int(amount)
    except (TypeError, ValueError):
        raise ValidationError(
            "Bid must be a valid number."
        )

    if amount <= 0:
        raise ValidationError(
            "Bid must be greater than zero."
        )

    with transaction.atomic():
        try:
            lot = (
                AuctionLot.objects
                .select_for_update()
                .select_related(
                    'cycle',
                    'candidate__tank',
                )
                .get(pk=lot_id)
            )

        except AuctionLot.DoesNotExist:
            raise ValidationError(
                "Auction lot does not exist."
            )

        cycle = lot.cycle

        if lot.finalized_at is not None:
            raise ValidationError(
                "This lot has already finished."
            )

        if cycle.status in [
            AuctionCycle.Status.FINISHED,
            AuctionCycle.Status.CANCELLED,
        ]:
            raise ValidationError(
                "This auction has finished."
            )

        if cycle.auction_starts_at is None:
            raise ValidationError(
                "This auction is not scheduled."
            )

        # --------------------------------------------
        # Start is controlled by the cycle.
        # End is controlled by the individual lot.
        # --------------------------------------------

        if current_time < cycle.auction_starts_at:
            raise ValidationError(
                "This auction has not started yet."
            )

        if current_time >= lot.ends_at:
            raise ValidationError(
                "This auction lot has closed."
            )

        old_bidder_id = (
            lot.current_bidder_id
        )

        previous_bid = (
            lot.current_bid or 0
        )

        team_ids = {
            team.pk
        }

        if old_bidder_id is not None:
            team_ids.add(
                old_bidder_id
            )

        locked_teams = {
            locked_team.pk: locked_team
            for locked_team in (
                Team.objects
                .select_for_update()
                .filter(pk__in=team_ids)
                .order_by('pk')
            )
        }

        bidder = locked_teams[
            team.pk
        ]

        old_bidder = (
            locked_teams.get(
                old_bidder_id
            )
            if old_bidder_id is not None
            else None
        )

        # --------------------------------------------
        # Minimum legal bid
        # --------------------------------------------

        if lot.current_bid is None:
            minimum_bid = (
                lot.starting_bid
            )

        else:
            minimum_bid = (
                lot.current_bid
                + lot.minimum_increment
            )

        if amount < minimum_bid:
            raise ValidationError(
                f"Minimum bid is {minimum_bid}."
            )

        # --------------------------------------------
        # Inventory limit reservation
        # --------------------------------------------

        if old_bidder_id != bidder.pk:
            owned_count = (
                TeamTank.objects
                .filter(
                    team=bidder,
                    tank=lot.candidate.tank,
                )
                .count()
            )

            reserved_count = (
                AuctionLot.objects
                .filter(
                    current_bidder=bidder,
                    candidate__tank=lot.candidate.tank,
                    finalized_at__isnull=True,
                )
                .exclude(
                    pk=lot.pk
                )
                .count()
            )

            if (
                owned_count
                + reserved_count
                >= bidder.MAX_PER_TANK
            ):
                raise ValidationError(
                    f"Tank limit reached for "
                    f"{lot.candidate.tank.name}."
                )

        # ============================================
        # SAME TEAM increasing its own bid
        # ============================================

        if old_bidder_id == bidder.pk:
            additional_hold = (
                amount - previous_bid
            )

            if bidder.balance < additional_hold:
                raise ValidationError(
                    "Insufficient balance."
                )

            previous_balance = (
                bidder.balance
            )

            bidder.balance -= (
                additional_hold
            )

            bidder.save(
                update_fields=[
                    'balance'
                ]
            )

        # ============================================
        # NEW highest bidder
        # ============================================

        else:
            if bidder.balance < amount:
                raise ValidationError(
                    "Insufficient balance."
                )

            bidder_previous_balance = (
                bidder.balance
            )

            bidder.balance -= amount

            bidder.save(
                update_fields=[
                    'balance'
                ]
            )


            # ----------------------------------------
            # Refund previous highest bidder
            # ----------------------------------------

            if old_bidder is not None:
                old_previous_balance = (
                    old_bidder.balance
                )

                old_bidder.balance += (
                    previous_bid
                )

                old_bidder.save(
                    update_fields=[
                        'balance'
                    ]
                )

        # ============================================
        # Record bid
        # ============================================

        AuctionBid.objects.create(
            lot=lot,
            team=bidder,
            user=_user_label(user),
            amount=amount,
        )

        lot.current_bid = amount
        lot.current_bidder = bidder
        lot.last_bid_at = current_time

        # ============================================
        # ANTI-SNIPE
        #
        # NON-STACKING:
        #
        # not:
        #     lot.ends_at += 5 minutes
        #
        # but:
        #     deadline = max(deadline, now + 5m)
        # ============================================

        extension_target = (
            current_time
            + BID_EXTENSION_WINDOW
        )

        if extension_target > lot.ends_at:
            lot.ends_at = (
                extension_target
            )

        lot.save(
            update_fields=[
                'current_bid',
                'current_bidder',
                'last_bid_at',
                'ends_at',
            ]
        )

        # If cron hasn't flipped Scheduled -> Live yet,
        # an accepted bid proves the auction has started.
        if (
            cycle.status
            == AuctionCycle.Status.SCHEDULED
        ):
            cycle.status = (
                AuctionCycle.Status.LIVE
            )

            cycle.save(
                update_fields=[
                    'status'
                ]
            )

        return lot

def finalize_due_auctions(at=None):
    at = at or timezone.now()

    due_lot_ids = list(
        AuctionLot.objects
        .filter(
            cycle__status__in=[
                AuctionCycle.Status.SCHEDULED,
                AuctionCycle.Status.LIVE,
            ],
            finalized_at__isnull=True,
            ends_at__lte=at,
        )
        .values_list(
            'id',
            flat=True,
        )
    )

    touched_cycle_ids = set()

    awarded_tanks = 0
    finalized_lots = 0

    for lot_id in due_lot_ids:
        with transaction.atomic():
            try:
                lot = (
                    AuctionLot.objects
                    .select_for_update()
                    .select_related(
                        'cycle',
                        'candidate__tank',
                    )
                    .get(pk=lot_id)
                )

            except AuctionLot.DoesNotExist:
                continue

            if lot.finalized_at is not None:
                continue

            # It may have been extended since the query
            # above was executed.
            if lot.ends_at > at:
                continue

            cycle = lot.cycle

            touched_cycle_ids.add(
                cycle.id
            )

            lot.finalized_at = at

            if (
                lot.current_bidder_id is not None
                and lot.current_bid is not None
            ):
                winning_team = (
                    Team.objects
                    .select_for_update()
                    .get(
                        pk=lot.current_bidder_id
                    )
                )

                old_total_spent = (
                    winning_team.total_money_spent
                )

                # Money was already removed when
                # the winning bid was placed.
                winning_team.total_money_spent += (
                    lot.current_bid
                )

                winning_team.save(
                    update_fields=[
                        'total_money_spent'
                    ]
                )

                TeamTank.objects.create(
                    team=winning_team,
                    tank=lot.candidate.tank,

                    from_auctions=True,

                    # Store actual auction value.
                    value=lot.current_bid,
                )

                lot.winner = (
                    winning_team
                )

                lot.winning_bid = (
                    lot.current_bid
                )

                TeamLog.objects.create(
                    team=winning_team,
                    user='Auction',

                    field_name='multiple_fields',

                    previous_value={
                        # Balance does not change during finalization because
                        # the money was already escrowed while bidding.
                        'balance': winning_team.balance,

                        'total_money_spent': (
                            old_total_spent
                        ),
                    },

                    new_value={
                        'balance': winning_team.balance,

                        'total_money_spent': (
                            winning_team.total_money_spent
                        ),

                        # Structured auction data for the frontend.
                        'transaction_amount': (
                            -lot.current_bid
                        ),

                        'auction': {
                            'cycle_id': cycle.id,

                            # Database ID, useful for debugging/admin.
                            'lot_id': lot.id,

                            # User-facing lot number.
                            'lot_position': lot.position,

                            'tank': (
                                lot.candidate.tank.name
                            ),

                            'winning_bid': (
                                lot.current_bid
                            ),
                        },
                    },

                    description=(
                        f"Balance Changed by: {-lot.current_bid}\n"
                        f"Auction Won: {lot.candidate.tank.name}\n"
                        f"Auction Cycle: #{cycle.id}\n"
                        f"Lot: #{lot.position}\n"
                        f"Winning Bid: {lot.current_bid}"
                    ),

                    method_name='auction_win',
                )
                awarded_tanks += 1

            lot.save(
                update_fields=[
                    'winner',
                    'winning_bid',
                    'finalized_at',
                ]
            )

            finalized_lots += 1

    # -------------------------------------------------
    # Check whether affected cycles are completely done
    # -------------------------------------------------

    finished_cycles = 0

    for cycle_id in touched_cycle_ids:
        with transaction.atomic():
            cycle = (
                AuctionCycle.objects
                .select_for_update()
                .get(pk=cycle_id)
            )

            has_open_lots = (
                AuctionLot.objects
                .filter(
                    cycle=cycle,
                    finalized_at__isnull=True,
                )
                .exists()
            )

            if not has_open_lots:
                cycle.status = (
                    AuctionCycle.Status.FINISHED
                )

                cycle.finished_at = at

                cycle.save(
                    update_fields=[
                        'status',
                        'finished_at',
                    ]
                )

                finished_cycles += 1

    # Handle cycles that produced zero lots.
    empty_due_cycles = (
        AuctionCycle.objects
        .filter(
            status__in=[
                AuctionCycle.Status.SCHEDULED,
                AuctionCycle.Status.LIVE,
            ],
            auction_ends_at__lte=at,
        )
        .annotate(
            lot_total=Count('lots')
        )
        .filter(
            lot_total=0
        )
    )

    for cycle in empty_due_cycles:
        cycle.status = (
            AuctionCycle.Status.FINISHED
        )

        cycle.finished_at = at

        cycle.save(
            update_fields=[
                'status',
                'finished_at',
            ]
        )

        finished_cycles += 1

    return {
        'finalized_lots': finalized_lots,
        'awarded_tanks': awarded_tanks,
        'finished_cycles': finished_cycles,
    }


def allocate_auction_copies(cycle):
    """
    Determine how many physical copies of each tank qualify.

    Rules:

    1. Auction attempts to fill `cycle.lot_count` physical lots
       (10 by default).

    2. Tanks with votes are allocated first using the existing
       D'Hondt-style multiplicative system:

           effective_score =
               total_votes / (selected_copies + 1)

    3. If multiple tanks have exactly the same effective score,
       the winner of that slot is chosen randomly.

    4. A candidate can never receive more slots than the number
       of physical leftover copies that actually exist.

    5. If voting does not fill all available auction slots,
       the remaining slots are filled randomly from candidates
       that still have unused physical copies.

    Random fallback is by TANK MODEL rather than by physical copy,
    so a tank with 5 leftover copies is not automatically 5x more
    likely to be selected than a tank with 1 leftover copy.

    Duplicate copies may still be selected if there are not enough
    distinct remaining tank models to fill all slots.
    """

    import secrets

    candidates = list(
        cycle.candidates
        .select_related('tank')
        .annotate(
            total_votes=Sum(
                'votes__quantity'
            )
        )
        .order_by('id')
    )

    if not candidates:
        return {}

    # ------------------------------------------------------------
    # Build mutable allocation data for ALL candidates,
    # including candidates with zero votes.
    # ------------------------------------------------------------

    entries = []

    total_available_copies = 0

    for candidate in candidates:
        copies = candidate.sources.count()

        if copies <= 0:
            continue

        votes = candidate.total_votes or 0

        entry = {
            'candidate': candidate,
            'votes': votes,
            'copies': copies,
            'selected': 0,
        }

        entries.append(entry)

        total_available_copies += copies

    if not entries:
        return {}

    # ------------------------------------------------------------
    # Number of physical auction lots.
    #
    # Example:
    #     target = 10
    #     only 8 physical leftover tanks exist
    #     => create 8 lots
    # ------------------------------------------------------------

    slot_count = min(
        cycle.lot_count,
        total_available_copies,
    )

    selected_slots = 0

    # ============================================================
    # PHASE 1:
    # VOTED TANKS
    #
    # Existing multiplicative / D'Hondt-style allocation.
    #
    # Unlike the old implementation, exact score ties are RANDOM.
    # ============================================================

    while selected_slots < slot_count:
        scored_entries = []

        highest_score = None

        for entry in entries:
            # No votes means this candidate does not participate
            # in the voting phase.
            if entry['votes'] <= 0:
                continue

            # No physical copies remain available.
            if entry['selected'] >= entry['copies']:
                continue

            score = Fraction(
                entry['votes'],
                entry['selected'] + 1,
            )

            if (
                highest_score is None
                or score > highest_score
            ):
                highest_score = score

                scored_entries = [
                    entry
                ]

            elif score == highest_score:
                scored_entries.append(
                    entry
                )

        # No more voted tanks can be allocated.
        if not scored_entries:
            break

        # --------------------------------------------------------
        # RANDOM TIE BREAK
        #
        # If one candidate has the clear highest score,
        # this simply selects that candidate.
        #
        # If several candidates are tied, one is randomly chosen.
        # --------------------------------------------------------

        winner = secrets.choice(
            scored_entries
        )

        winner['selected'] += 1
        selected_slots += 1

    # ============================================================
    # PHASE 2:
    # RANDOM FILL
    #
    # If voting didn't fill the target number of lots, randomly
    # select from candidates with remaining physical copies.
    # ============================================================

    while selected_slots < slot_count:
        remaining_candidates = [
            entry
            for entry in entries
            if (
                entry['selected']
                < entry['copies']
            )
        ]

        if not remaining_candidates:
            break

        # --------------------------------------------------------
        # Prefer tank models which have not already received a
        # RANDOM fallback slot in this phase.
        #
        # We intentionally choose by candidate/tank model rather
        # than putting every physical copy into the random pool.
        #
        # That prevents:
        #
        #   T-72 x8
        #   M60  x1
        #
        # from making T-72 eight times more likely on each draw.
        # --------------------------------------------------------

        winner = secrets.choice(
            remaining_candidates
        )

        winner['selected'] += 1
        selected_slots += 1

    # ------------------------------------------------------------
    # Final result:
    #
    # {
    #     candidate_id: selected_quantity,
    # }
    # ------------------------------------------------------------

    return {
        entry['candidate'].id:
            entry['selected']

        for entry in entries

        if entry['selected'] > 0
    }

def add_import_batch_to_cycle(
    cycle,
    batch_available_from,
    batch_expires_at,
):
    """
    Add one already-expired import batch to a specific auction cycle.

    Returns:
        {
            'added_sources': int,
            'total_imports': int,
            'leftover_imports': int,
        }
    """

    imports = list(
        ImportTank.objects
        .select_related('tank')
        .filter(
            available_from=batch_available_from
        )
        .order_by('id')
    )

    leftovers = [
        import_tank
        for import_tank in imports
        if not import_tank.is_purchased
    ]

    AuctionImportBatch.objects.create(
        cycle=cycle,
        available_from=batch_available_from,
        expired_at=batch_expires_at,
        total_imports=len(imports),
        leftover_imports=len(leftovers),
    )

    added_sources = 0

    for import_tank in leftovers:
        candidate, _ = (
            AuctionCandidate.objects
            .get_or_create(
                cycle=cycle,
                tank=import_tank.tank,
            )
        )

        _, created = (
            AuctionCandidateSource.objects
            .get_or_create(
                source_import=import_tank,
                defaults={
                    'candidate': candidate,
                },
            )
        )

        if created:
            added_sources += 1

    return {
        'added_sources': added_sources,
        'total_imports': len(imports),
        'leftover_imports': len(leftovers),
    }

def start_ready_collecting_cycle(at=None):
    """
    If there is no active auction and the collecting cycle already
    has 8/8 batches, immediately open voting.

    This is particularly useful when bootstrapping a historical backlog.
    """

    at = at or timezone.now()

    active_exists = (
        AuctionCycle.objects
        .filter(
            status__in=[
                AuctionCycle.Status.VOTING,
                AuctionCycle.Status.SCHEDULED,
                AuctionCycle.Status.LIVE,
            ]
        )
        .exists()
    )

    if active_exists:
        return 0

    cycle = (
        AuctionCycle.objects
        .filter(
            status=AuctionCycle.Status.COLLECTING
        )
        .order_by('created_at')
        .first()
    )

    if not cycle:
        return 0

    if (
        cycle.import_batches.count()
        < cycle.batch_target
    ):
        return 0

    with transaction.atomic():
        cycle = (
            AuctionCycle.objects
            .select_for_update()
            .get(pk=cycle.pk)
        )

        # Recheck after acquiring lock.
        if (
            cycle.status
            != AuctionCycle.Status.COLLECTING
        ):
            return 0

        if (
            cycle.import_batches.count()
            < cycle.batch_target
        ):
            return 0

        start_voting(
            cycle,
            at=at,
        )

        get_or_create_collecting_cycle()

    return 1

def run_auction_tick(at=None):
    at = at or timezone.now()

    # Finish/open existing auction state first.
    voting_closed = close_due_voting(
        at=at
    )

    live_started = mark_live_auctions(
        at=at
    )

    finish_result = finalize_due_auctions(
        at=at
    )

    # A previously-full waiting cycle may now be allowed
    # to enter voting.
    ready_started = start_ready_collecting_cycle(
        at=at
    )

    # Then consume available historical/current imports.
    import_result = sync_expired_import_batches(
        at=at
    )

    # Deliver only after state transitions have committed. Successful deliveries
    # are recorded so the next minute's tick does not repeat them.
    from .auction_notifications import send_due_auction_announcements
    announcement_result = send_due_auction_announcements(at=at)

    return {
        **import_result,

        'opened_ready_cycle': (
            ready_started
        ),

        'closed_voting_cycles': (
            voting_closed
        ),

        'started_live_cycles': (
            live_started
        ),

        **finish_result,
        **announcement_result,
    }
