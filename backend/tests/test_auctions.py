from datetime import timedelta
from types import SimpleNamespace

from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from sheets.models import (
    Team,
    Tank,
    TeamTank,
    ImportTank,

    AuctionCycle,
    AuctionImportBatch,
    AuctionIgnoredImportBatch,
    AuctionCandidate,
    AuctionCandidateSource,
    AuctionVote,
    AuctionLot,
    AuctionBid,
)

from sheets.services.auctions import (
    add_import_batch_to_cycle,
    allocate_auction_copies,
    build_auction_lots,
    finalize_due_auctions,
    get_or_create_collecting_cycle,
    next_sunday_17utc,
    place_bid,
    place_vote,
    remove_vote,
    start_voting,
    sync_expired_import_batches,
)


class AuctionTestMixin:
    """
    Shared helpers for auction tests.
    """

    def make_team(
        self,
        name,
        balance=1_000_000,
    ):
        return Team.objects.create(
            name=name,
            balance=balance,
        )

    def make_tank(
        self,
        name,
        price=100_000,
        battle_rating=5.0,
        rank=3,
        tank_type="MT",
    ):
        return Tank.objects.create(
            name=name,
            price=price,
            battle_rating=battle_rating,
            rank=rank,
            type=tank_type,
        )

    def make_user(self, username):
        """
        Services only need a username/string representation.
        No real auth user is needed for these domain tests.
        """
        return SimpleNamespace(
            username=username
        )

    def make_expired_import(
        self,
        tank,
        available_from=None,
        purchased=False,
        purchased_by=None,
    ):
        available_from = (
            available_from
            or timezone.now() - timedelta(days=8)
        )

        return ImportTank.objects.create(
            tank=tank,
            discount=0,
            available_from=available_from,
            available_until=(
                available_from
                + timedelta(days=7)
            ),
            is_purchased=purchased,
            purchased_by=purchased_by,
        )

    def make_candidate(
        self,
        cycle,
        tank,
        copies=1,
    ):
        candidate = AuctionCandidate.objects.create(
            cycle=cycle,
            tank=tank,
        )

        base_time = (
            timezone.now()
            - timedelta(days=30)
        )

        for index in range(copies):
            import_tank = self.make_expired_import(
                tank=tank,
                available_from=(
                    base_time
                    + timedelta(days=index)
                ),
            )

            AuctionCandidateSource.objects.create(
                candidate=candidate,
                source_import=import_tank,
            )

        return candidate


# ================================================================
# SCHEDULING
# ================================================================


class AuctionSchedulingTests(
    AuctionTestMixin,
    TestCase,
):
    def test_next_sunday_17utc(self):
        """
        Wednesday -> next Sunday at exactly 17:00 UTC.
        """

        source = timezone.datetime(
            2026,
            9,
            9,
            12,
            0,
            tzinfo=timezone.utc,
        )

        result = next_sunday_17utc(source)

        self.assertEqual(
            result.weekday(),
            6,
        )

        self.assertEqual(
            result.hour,
            17,
        )

        self.assertEqual(
            result.minute,
            0,
        )

    def test_sunday_after_17_moves_to_next_week(self):
        source = timezone.datetime(
            2026,
            9,
            6,
            18,
            0,
            tzinfo=timezone.utc,
        )

        result = next_sunday_17utc(source)

        self.assertEqual(
            result.date(),
            timezone.datetime(
                2026,
                9,
                13,
                tzinfo=timezone.utc,
            ).date(),
        )

        self.assertEqual(
            result.hour,
            17,
        )

    def test_get_or_create_collecting_cycle_is_idempotent(self):
        first = get_or_create_collecting_cycle()
        second = get_or_create_collecting_cycle()

        self.assertEqual(
            first.pk,
            second.pk,
        )

        self.assertEqual(
            AuctionCycle.objects.filter(
                status=AuctionCycle.Status.COLLECTING
            ).count(),
            1,
        )

    def test_start_voting_sets_dates(self):
        cycle = AuctionCycle.objects.create(
            status=AuctionCycle.Status.COLLECTING,
        )

        now = timezone.now()

        start_voting(
            cycle,
            at=now,
        )

        cycle.refresh_from_db()

        self.assertEqual(
            cycle.status,
            AuctionCycle.Status.VOTING,
        )

        self.assertEqual(
            cycle.voting_starts_at,
            now,
        )

        self.assertEqual(
            cycle.voting_ends_at,
            now + timedelta(days=7),
        )

        self.assertEqual(
            cycle.auction_starts_at.weekday(),
            6,
        )

        self.assertEqual(
            cycle.auction_starts_at.hour,
            17,
        )

        self.assertEqual(
            cycle.auction_ends_at,
            cycle.auction_starts_at
            + timedelta(hours=1),
        )


# ================================================================
# IMPORT COLLECTION
# ================================================================


class AuctionImportCollectionTests(
    AuctionTestMixin,
    TestCase,
):
    def test_unpurchased_import_is_added_to_pool(self):
        tank = self.make_tank("T-72")

        available_from = (
            timezone.now()
            - timedelta(days=8)
        )

        import_tank = self.make_expired_import(
            tank=tank,
            available_from=available_from,
        )

        cycle = AuctionCycle.objects.create(
            status=AuctionCycle.Status.COLLECTING,
        )

        result = add_import_batch_to_cycle(
            cycle=cycle,
            batch_available_from=available_from,
            batch_expires_at=import_tank.available_until,
        )

        self.assertEqual(
            result["total_imports"],
            1,
        )

        self.assertEqual(
            result["leftover_imports"],
            1,
        )

        candidate = AuctionCandidate.objects.get(
            cycle=cycle,
            tank=tank,
        )

        self.assertEqual(
            candidate.sources.count(),
            1,
        )

    def test_purchased_import_is_not_added_to_pool(self):
        tank = self.make_tank("M60")
        team = self.make_team("Saunders")

        available_from = (
            timezone.now()
            - timedelta(days=8)
        )

        import_tank = self.make_expired_import(
            tank=tank,
            available_from=available_from,
            purchased=True,
            purchased_by=team,
        )

        cycle = AuctionCycle.objects.create(
            status=AuctionCycle.Status.COLLECTING,
        )

        result = add_import_batch_to_cycle(
            cycle=cycle,
            batch_available_from=available_from,
            batch_expires_at=import_tank.available_until,
        )

        self.assertEqual(
            result["leftover_imports"],
            0,
        )

        self.assertFalse(
            AuctionCandidate.objects.filter(
                cycle=cycle,
                tank=tank,
            ).exists()
        )

    def test_same_tank_from_multiple_batches_becomes_multiple_copies(self):
        tank = self.make_tank("Leopard 1")

        cycle = AuctionCycle.objects.create(
            status=AuctionCycle.Status.COLLECTING,
        )

        first_time = (
            timezone.now()
            - timedelta(days=20)
        )

        second_time = (
            timezone.now()
            - timedelta(days=12)
        )

        first = self.make_expired_import(
            tank,
            available_from=first_time,
        )

        second = self.make_expired_import(
            tank,
            available_from=second_time,
        )

        add_import_batch_to_cycle(
            cycle,
            first_time,
            first.available_until,
        )

        add_import_batch_to_cycle(
            cycle,
            second_time,
            second.available_until,
        )

        candidate = AuctionCandidate.objects.get(
            cycle=cycle,
            tank=tank,
        )

        self.assertEqual(
            candidate.sources.count(),
            2,
        )

    def test_ignored_import_batch_is_not_synced(self):
        tank = self.make_tank("Old Tank")

        available_from = (
            timezone.now()
            - timedelta(days=50)
        )

        self.make_expired_import(
            tank,
            available_from=available_from,
        )

        AuctionIgnoredImportBatch.objects.create(
            available_from=available_from,
            reason="test",
        )

        sync_expired_import_batches()

        self.assertFalse(
            AuctionImportBatch.objects.filter(
                available_from=available_from,
            ).exists()
        )


# ================================================================
# VOTING
# ================================================================


class AuctionVotingTests(
    AuctionTestMixin,
    TestCase,
):
    def setUp(self):
        self.team = self.make_team(
            "Saunders"
        )

        self.user = self.make_user(
            "commander"
        )

        self.cycle = AuctionCycle.objects.create(
            status=AuctionCycle.Status.VOTING,
            voting_starts_at=(
                timezone.now()
                - timedelta(minutes=5)
            ),
            voting_ends_at=(
                timezone.now()
                + timedelta(days=1)
            ),
            max_votes_per_team=5,
        )

        self.tank = self.make_tank(
            "T-72"
        )

        self.candidate = self.make_candidate(
            cycle=self.cycle,
            tank=self.tank,
            copies=3,
        )

    def test_can_vote_same_tank_multiple_times(self):
        place_vote(
            self.cycle.pk,
            self.candidate.pk,
            self.team,
            self.user,
        )

        place_vote(
            self.cycle.pk,
            self.candidate.pk,
            self.team,
            self.user,
        )

        allocation = AuctionVote.objects.get(
            cycle=self.cycle,
            team=self.team,
            candidate=self.candidate,
        )

        self.assertEqual(
            allocation.quantity,
            2,
        )

    def test_cannot_vote_more_than_available_copies(self):
        for _ in range(3):
            place_vote(
                self.cycle.pk,
                self.candidate.pk,
                self.team,
                self.user,
            )

        with self.assertRaises(
            ValidationError
        ):
            place_vote(
                self.cycle.pk,
                self.candidate.pk,
                self.team,
                self.user,
            )

    def test_team_cannot_use_more_than_five_votes_total(self):
        tanks = []

        for index in range(6):
            tank = self.make_tank(
                f"Tank {index}"
            )

            candidate = self.make_candidate(
                cycle=self.cycle,
                tank=tank,
                copies=1,
            )

            tanks.append(candidate)

        for candidate in tanks[:5]:
            place_vote(
                self.cycle.pk,
                candidate.pk,
                self.team,
                self.user,
            )

        with self.assertRaises(
            ValidationError
        ):
            place_vote(
                self.cycle.pk,
                tanks[5].pk,
                self.team,
                self.user,
            )

        total = sum(
            AuctionVote.objects.filter(
                cycle=self.cycle,
                team=self.team,
            ).values_list(
                "quantity",
                flat=True,
            )
        )

        self.assertEqual(
            total,
            5,
        )

    def test_remove_vote_decrements_allocation(self):
        place_vote(
            self.cycle.pk,
            self.candidate.pk,
            self.team,
            self.user,
        )

        place_vote(
            self.cycle.pk,
            self.candidate.pk,
            self.team,
            self.user,
        )

        remove_vote(
            self.cycle.pk,
            self.candidate.pk,
            self.team,
        )

        allocation = AuctionVote.objects.get(
            cycle=self.cycle,
            team=self.team,
            candidate=self.candidate,
        )

        self.assertEqual(
            allocation.quantity,
            1,
        )

    def test_removing_last_vote_deletes_allocation(self):
        place_vote(
            self.cycle.pk,
            self.candidate.pk,
            self.team,
            self.user,
        )

        remove_vote(
            self.cycle.pk,
            self.candidate.pk,
            self.team,
        )

        self.assertFalse(
            AuctionVote.objects.filter(
                cycle=self.cycle,
                team=self.team,
                candidate=self.candidate,
            ).exists()
        )

    def test_vote_rejected_after_voting_closes(self):
        self.cycle.voting_ends_at = (
            timezone.now()
            - timedelta(seconds=1)
        )

        self.cycle.save(
            update_fields=[
                "voting_ends_at"
            ]
        )

        with self.assertRaises(
            ValidationError
        ):
            place_vote(
                self.cycle.pk,
                self.candidate.pk,
                self.team,
                self.user,
            )


# ================================================================
# MULTIPLICATIVE / APPORTIONMENT SELECTION
# ================================================================


class AuctionAllocationTests(
    AuctionTestMixin,
    TestCase,
):
    def setUp(self):
        self.cycle = AuctionCycle.objects.create(
            status=AuctionCycle.Status.VOTING,
            lot_count=3,
        )

        self.team = self.make_team(
            "Saunders"
        )

    def add_votes(
        self,
        candidate,
        quantity,
        team=None,
    ):
        AuctionVote.objects.create(
            cycle=self.cycle,
            candidate=candidate,
            team=team or self.team,
            quantity=quantity,
            user="test",
        )

    def test_eight_vs_five_awards_first_tank_twice(self):
        """
        A = 8 votes, 3 copies
        B = 5 votes, 1 copy
        C = 3 votes, 1 copy

        3 slots:
            A
            B
            A
        """

        tank_a = self.make_tank("A")
        tank_b = self.make_tank("B")
        tank_c = self.make_tank("C")

        candidate_a = self.make_candidate(
            self.cycle,
            tank_a,
            copies=3,
        )

        candidate_b = self.make_candidate(
            self.cycle,
            tank_b,
            copies=1,
        )

        candidate_c = self.make_candidate(
            self.cycle,
            tank_c,
            copies=1,
        )

        self.add_votes(
            candidate_a,
            8,
        )

        other_team = self.make_team(
            "Other"
        )

        self.add_votes(
            candidate_b,
            5,
            team=other_team,
        )

        third_team = self.make_team(
            "Third"
        )

        self.add_votes(
            candidate_c,
            3,
            team=third_team,
        )

        result = allocate_auction_copies(
            self.cycle
        )

        self.assertEqual(
            result[candidate_a.pk],
            2,
        )

        self.assertEqual(
            result[candidate_b.pk],
            1,
        )

        self.assertNotIn(
            candidate_c.pk,
            result,
        )

    def test_cannot_select_more_copies_than_exist(self):
        tank = self.make_tank("Rare")

        candidate = self.make_candidate(
            self.cycle,
            tank,
            copies=1,
        )

        self.add_votes(
            candidate,
            100,
        )

        result = allocate_auction_copies(
            self.cycle
        )

        self.assertEqual(
            result[candidate.pk],
            1,
        )

    def test_zero_vote_candidate_does_not_qualify(self):
        tank = self.make_tank("No Votes")

        candidate = self.make_candidate(
            self.cycle,
            tank,
            copies=2,
        )

        result = allocate_auction_copies(
            self.cycle
        )

        self.assertNotIn(
            candidate.pk,
            result,
        )


# ================================================================
# LOT CREATION
# ================================================================


class AuctionLotCreationTests(
    AuctionTestMixin,
    TestCase,
):
    def test_selected_quantity_creates_individual_lots(self):
        cycle = AuctionCycle.objects.create(
            status=AuctionCycle.Status.VOTING,
            lot_count=2,
            auction_ends_at=(
                timezone.now()
                + timedelta(days=10)
            ),
            minimum_increment=1000,
        )

        team = self.make_team("Saunders")

        tank = self.make_tank(
            "T-72",
            price=150_000,
        )

        candidate = self.make_candidate(
            cycle,
            tank,
            copies=3,
        )

        AuctionVote.objects.create(
            cycle=cycle,
            candidate=candidate,
            team=team,
            quantity=5,
        )

        build_auction_lots(cycle)

        candidate.refresh_from_db()

        self.assertEqual(
            candidate.selected_quantity,
            2,
        )

        self.assertEqual(
            cycle.lots.count(),
            2,
        )

        for lot in cycle.lots.all():
            self.assertEqual(
                lot.starting_bid,
                tank.price,
            )

            self.assertEqual(
                lot.ends_at,
                cycle.auction_ends_at,
            )

    def test_build_lots_is_idempotent(self):
        cycle = AuctionCycle.objects.create(
            status=AuctionCycle.Status.VOTING,
            lot_count=1,
            auction_ends_at=(
                timezone.now()
                + timedelta(days=10)
            ),
        )

        team = self.make_team("Saunders")
        tank = self.make_tank("M60")

        candidate = self.make_candidate(
            cycle,
            tank,
            copies=1,
        )

        AuctionVote.objects.create(
            cycle=cycle,
            candidate=candidate,
            team=team,
            quantity=1,
        )

        build_auction_lots(cycle)
        build_auction_lots(cycle)

        self.assertEqual(
            cycle.lots.count(),
            1,
        )


# ================================================================
# BIDDING
# ================================================================


class AuctionBiddingTests(
    AuctionTestMixin,
    TestCase,
):
    def setUp(self):
        self.now = timezone.now()

        self.team_a = self.make_team(
            "Saunders",
            balance=1_000_000,
        )

        self.team_b = self.make_team(
            "Ooarai",
            balance=1_000_000,
        )

        self.user_a = self.make_user(
            "commander_a"
        )

        self.user_b = self.make_user(
            "commander_b"
        )

        self.tank = self.make_tank(
            "T-72",
            price=100_000,
        )

        self.cycle = AuctionCycle.objects.create(
            status=AuctionCycle.Status.LIVE,
            auction_starts_at=(
                self.now
                - timedelta(minutes=30)
            ),
            auction_ends_at=(
                self.now
                + timedelta(minutes=30)
            ),
        )

        candidate = self.make_candidate(
            self.cycle,
            self.tank,
            copies=1,
        )

        source = candidate.sources.first()

        self.lot = AuctionLot.objects.create(
            cycle=self.cycle,
            candidate=candidate,
            source=source,
            position=1,
            starting_bid=100_000,
            minimum_increment=10_000,
            ends_at=(
                self.now
                + timedelta(minutes=30)
            ),
        )

    def test_first_bid_reserves_full_amount(self):
        place_bid(
            self.lot.pk,
            self.team_a,
            self.user_a,
            100_000,
        )

        self.team_a.refresh_from_db()
        self.lot.refresh_from_db()

        self.assertEqual(
            self.team_a.balance,
            900_000,
        )

        self.assertEqual(
            self.lot.current_bid,
            100_000,
        )

        self.assertEqual(
            self.lot.current_bidder,
            self.team_a,
        )

    def test_outbid_refunds_previous_team(self):
        place_bid(
            self.lot.pk,
            self.team_a,
            self.user_a,
            100_000,
        )

        place_bid(
            self.lot.pk,
            self.team_b,
            self.user_b,
            120_000,
        )

        self.team_a.refresh_from_db()
        self.team_b.refresh_from_db()
        self.lot.refresh_from_db()

        self.assertEqual(
            self.team_a.balance,
            1_000_000,
        )

        self.assertEqual(
            self.team_b.balance,
            880_000,
        )

        self.assertEqual(
            self.lot.current_bidder,
            self.team_b,
        )

        self.assertEqual(
            self.lot.current_bid,
            120_000,
        )

    def test_leading_team_only_pays_bid_difference(self):
        place_bid(
            self.lot.pk,
            self.team_a,
            self.user_a,
            100_000,
        )

        place_bid(
            self.lot.pk,
            self.team_a,
            self.user_a,
            140_000,
        )

        self.team_a.refresh_from_db()

        self.assertEqual(
            self.team_a.balance,
            860_000,
        )

    def test_bid_below_increment_is_rejected(self):
        place_bid(
            self.lot.pk,
            self.team_a,
            self.user_a,
            100_000,
        )

        with self.assertRaises(
            ValidationError
        ):
            place_bid(
                self.lot.pk,
                self.team_b,
                self.user_b,
                105_000,
            )

    def test_insufficient_balance_is_rejected(self):
        poor_team = self.make_team(
            "Poor",
            balance=50_000,
        )

        with self.assertRaises(
            ValidationError
        ):
            place_bid(
                self.lot.pk,
                poor_team,
                self.make_user("poor"),
                100_000,
            )

    def test_bid_after_lot_deadline_is_rejected(self):
        self.lot.ends_at = (
            timezone.now()
            - timedelta(seconds=1)
        )

        self.lot.save(
            update_fields=[
                "ends_at"
            ]
        )

        with self.assertRaises(
            ValidationError
        ):
            place_bid(
                self.lot.pk,
                self.team_a,
                self.user_a,
                100_000,
            )

    def test_bid_is_recorded(self):
        place_bid(
            self.lot.pk,
            self.team_a,
            self.user_a,
            100_000,
        )

        self.assertEqual(
            AuctionBid.objects.filter(
                lot=self.lot
            ).count(),
            1,
        )


# ================================================================
# ANTI-SNIPE
# ================================================================


class AuctionAntiSnipeTests(
    AuctionTestMixin,
    TestCase,
):
    def setUp(self):
        self.now = timezone.now()

        self.team = self.make_team(
            "Saunders"
        )

        self.user = self.make_user(
            "commander"
        )

        self.tank = self.make_tank(
            "T-72"
        )

        self.cycle = AuctionCycle.objects.create(
            status=AuctionCycle.Status.LIVE,
            auction_starts_at=(
                self.now
                - timedelta(minutes=55)
            ),
            auction_ends_at=(
                self.now
                + timedelta(minutes=5)
            ),
        )

        candidate = self.make_candidate(
            self.cycle,
            self.tank,
            copies=1,
        )

        self.lot = AuctionLot.objects.create(
            cycle=self.cycle,
            candidate=candidate,
            source=candidate.sources.first(),
            position=1,
            starting_bid=100_000,
            minimum_increment=10_000,
            ends_at=(
                self.now
                + timedelta(minutes=5)
            ),
        )

    def test_early_bid_does_not_extend_deadline(self):
        """
        Existing deadline is already at least five minutes away.
        """

        old_deadline = self.lot.ends_at

        place_bid(
            self.lot.pk,
            self.team,
            self.user,
            100_000,
        )

        self.lot.refresh_from_db()

        # Allow very small timing differences caused by timezone.now()
        self.assertGreaterEqual(
            self.lot.ends_at,
            old_deadline,
        )

    def test_late_bid_guarantees_about_five_minutes_remaining(self):
        self.lot.ends_at = (
            timezone.now()
            + timedelta(seconds=30)
        )

        self.lot.save(
            update_fields=[
                "ends_at"
            ]
        )

        before = timezone.now()

        place_bid(
            self.lot.pk,
            self.team,
            self.user,
            100_000,
        )

        self.lot.refresh_from_db()

        minimum_expected = (
            before
            + timedelta(minutes=4, seconds=59)
        )

        self.assertGreaterEqual(
            self.lot.ends_at,
            minimum_expected,
        )

    def test_extensions_are_non_stacking(self):
        """
        Deadline becomes approximately NOW + 5m, not OLD + 5m.
        """

        self.lot.ends_at = (
            timezone.now()
            + timedelta(seconds=30)
        )

        self.lot.save(
            update_fields=[
                "ends_at"
            ]
        )

        before = timezone.now()

        place_bid(
            self.lot.pk,
            self.team,
            self.user,
            100_000,
        )

        self.lot.refresh_from_db()

        # If implementation incorrectly did:
        #     old_deadline + 5 minutes
        #
        # we'd get about 5m30s.
        #
        # Correct result should be close to 5m.
        self.assertLess(
            self.lot.ends_at,
            before + timedelta(
                minutes=5,
                seconds=10,
            ),
        )


# ================================================================
# FINALIZATION
# ================================================================


class AuctionFinalizationTests(
    AuctionTestMixin,
    TestCase,
):
    def setUp(self):
        self.team = self.make_team(
            "Saunders",
            balance=900_000,
        )

        self.tank = self.make_tank(
            "T-72",
            price=100_000,
        )

        self.cycle = AuctionCycle.objects.create(
            status=AuctionCycle.Status.LIVE,
            auction_starts_at=(
                timezone.now()
                - timedelta(hours=2)
            ),
            auction_ends_at=(
                timezone.now()
                - timedelta(hours=1)
            ),
        )

        candidate = self.make_candidate(
            self.cycle,
            self.tank,
            copies=1,
        )

        self.lot = AuctionLot.objects.create(
            cycle=self.cycle,
            candidate=candidate,
            source=candidate.sources.first(),
            position=1,
            starting_bid=100_000,
            minimum_increment=10_000,
            current_bid=100_000,
            current_bidder=self.team,
            ends_at=(
                timezone.now()
                - timedelta(seconds=1)
            ),
        )

    def test_winner_receives_team_tank(self):
        finalize_due_auctions()

        owned = TeamTank.objects.get(
            team=self.team,
            tank=self.tank,
        )

        self.assertTrue(
            owned.from_auctions
        )

        self.assertEqual(
            owned.value,
            100_000,
        )

    def test_finalization_does_not_deduct_balance_again(self):
        before = self.team.balance

        finalize_due_auctions()

        self.team.refresh_from_db()

        self.assertEqual(
            self.team.balance,
            before,
        )

    def test_total_money_spent_is_incremented(self):
        previous = (
            self.team.total_money_spent
        )

        finalize_due_auctions()

        self.team.refresh_from_db()

        self.assertEqual(
            self.team.total_money_spent,
            previous + 100_000,
        )

    def test_lot_records_winner_and_winning_bid(self):
        finalize_due_auctions()

        self.lot.refresh_from_db()

        self.assertEqual(
            self.lot.winner,
            self.team,
        )

        self.assertEqual(
            self.lot.winning_bid,
            100_000,
        )

        self.assertIsNotNone(
            self.lot.finalized_at
        )

    def test_finalization_is_idempotent(self):
        finalize_due_auctions()
        finalize_due_auctions()

        self.assertEqual(
            TeamTank.objects.filter(
                team=self.team,
                tank=self.tank,
            ).count(),
            1,
        )

    def test_extended_lot_does_not_finalize_early(self):
        self.lot.ends_at = (
            timezone.now()
            + timedelta(minutes=3)
        )

        self.lot.save(
            update_fields=[
                "ends_at"
            ]
        )

        finalize_due_auctions()

        self.lot.refresh_from_db()

        self.assertIsNone(
            self.lot.finalized_at
        )

        self.assertFalse(
            TeamTank.objects.filter(
                team=self.team,
                tank=self.tank,
            ).exists()
        )


# ================================================================
# MULTIPLE LOT CLOSING TIMES
# ================================================================


class AuctionIndependentLotTests(
    AuctionTestMixin,
    TestCase,
):
    def test_one_lot_can_finalize_while_another_remains_extended(self):
        team = self.make_team(
            "Saunders"
        )

        tank_a = self.make_tank(
            "Tank A"
        )

        tank_b = self.make_tank(
            "Tank B"
        )

        cycle = AuctionCycle.objects.create(
            status=AuctionCycle.Status.LIVE,
            auction_starts_at=(
                timezone.now()
                - timedelta(hours=1)
            ),
            auction_ends_at=timezone.now(),
        )

        candidate_a = self.make_candidate(
            cycle,
            tank_a,
            copies=1,
        )

        candidate_b = self.make_candidate(
            cycle,
            tank_b,
            copies=1,
        )

        closed_lot = AuctionLot.objects.create(
            cycle=cycle,
            candidate=candidate_a,
            source=candidate_a.sources.first(),
            position=1,
            starting_bid=100_000,
            current_bid=100_000,
            current_bidder=team,
            ends_at=(
                timezone.now()
                - timedelta(seconds=1)
            ),
        )

        open_lot = AuctionLot.objects.create(
            cycle=cycle,
            candidate=candidate_b,
            source=candidate_b.sources.first(),
            position=2,
            starting_bid=100_000,
            ends_at=(
                timezone.now()
                + timedelta(minutes=5)
            ),
        )

        finalize_due_auctions()

        closed_lot.refresh_from_db()
        open_lot.refresh_from_db()
        cycle.refresh_from_db()

        self.assertIsNotNone(
            closed_lot.finalized_at
        )

        self.assertIsNone(
            open_lot.finalized_at
        )

        self.assertEqual(
            cycle.status,
            AuctionCycle.Status.LIVE,
        )