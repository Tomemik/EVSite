from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from django.db import transaction
from django.db.models import Count, Max
from django.utils import timezone

from sheets.models import (
    ImportTank,
    AuctionCycle,
    AuctionImportBatch,
    AuctionIgnoredImportBatch,
)

from sheets.services.auctions import (
    add_import_batch_to_cycle,
    start_voting,
)


class Command(BaseCommand):
    help = (
        "Bootstrap the Auctions system from an existing imports backlog. "
        "Older auction periods are ignored, the second-newest period is "
        "opened for voting, and the newest period becomes collecting."
    )

    def handle(self, *args, **options):
        now = timezone.now()

        # ---------------------------------------------------------
        # Safety check
        # ---------------------------------------------------------

        if AuctionImportBatch.objects.exists():
            raise CommandError(
                "Auction import batches already exist. "
                "Bootstrap is intended to run once before normal "
                "auction processing starts."
            )

        if AuctionCycle.objects.exists():
            raise CommandError(
                "Auction cycles already exist. "
                "Delete the empty/test cycles first before bootstrapping."
            )

        # ---------------------------------------------------------
        # Fetch every fully expired import batch in chronological order.
        #
        # One unique available_from = one import batch, matching your
        # existing Imports behaviour.
        # ---------------------------------------------------------

        expired_batches = list(
            ImportTank.objects
            .values('available_from')
            .annotate(
                batch_expires_at=Max('available_until'),
                total_imports=Count('id'),
            )
            .filter(
                batch_expires_at__lte=now
            )
            .order_by('available_from')
        )

        if len(expired_batches) < 9:
            raise CommandError(
                "At least 9 expired import batches are required "
                "to have both a previous auction period and a "
                "new collecting period."
            )

        # ---------------------------------------------------------
        # Divide history into groups of 8, beginning with the oldest.
        #
        # Example: 21 expired batches
        #
        #   Period 1:  1-8
        #   Period 2:  9-16    <- second newest -> voting
        #   Period 3: 17-21    <- newest -> collecting
        #
        # Period 1 gets ignored.
        # ---------------------------------------------------------

        periods = [
            expired_batches[index:index + 8]
            for index in range(
                0,
                len(expired_batches),
                8,
            )
        ]

        if len(periods) < 2:
            raise CommandError(
                "Could not determine both a second-newest "
                "and newest auction period."
            )

        voting_period = periods[-2]
        collecting_period = periods[-1]

        older_periods = periods[:-2]

        older_batches = [
            batch
            for period in older_periods
            for batch in period
        ]

        self.stdout.write(
            f"Expired import batches found: "
            f"{len(expired_batches)}"
        )

        self.stdout.write(
            f"Historical batches to ignore: "
            f"{len(older_batches)}"
        )

        self.stdout.write(
            f"Voting-period batches: "
            f"{len(voting_period)}"
        )

        self.stdout.write(
            f"Collecting-period batches: "
            f"{len(collecting_period)}"
        )

        # ---------------------------------------------------------
        # Do the complete operation transactionally.
        # ---------------------------------------------------------

        with transaction.atomic():

            # =====================================================
            # 1. IGNORE OLD HISTORY
            # =====================================================

            for batch in older_batches:
                AuctionIgnoredImportBatch.objects.create(
                    available_from=(
                        batch['available_from']
                    ),
                    reason=(
                        "Historical import ignored during "
                        "initial Auctions bootstrap"
                    ),
                )

            # =====================================================
            # 2. SECOND-NEWEST PERIOD -> VOTING
            # =====================================================

            voting_cycle = AuctionCycle.objects.create(
                status=AuctionCycle.Status.COLLECTING,
                batch_target=8,
            )

            voting_sources = 0

            for batch in voting_period:
                result = add_import_batch_to_cycle(
                    cycle=voting_cycle,

                    batch_available_from=(
                        batch['available_from']
                    ),

                    batch_expires_at=(
                        batch['batch_expires_at']
                    ),
                )

                voting_sources += (
                    result['added_sources']
                )

            # Open it immediately.
            start_voting(
                voting_cycle,
                at=now,
            )

            # =====================================================
            # 3. NEWEST PERIOD -> COLLECTING
            # =====================================================

            collecting_cycle = AuctionCycle.objects.create(
                status=AuctionCycle.Status.COLLECTING,
                batch_target=8,
            )

            collecting_sources = 0

            for batch in collecting_period:
                result = add_import_batch_to_cycle(
                    cycle=collecting_cycle,

                    batch_available_from=(
                        batch['available_from']
                    ),

                    batch_expires_at=(
                        batch['batch_expires_at']
                    ),
                )

                collecting_sources += (
                    result['added_sources']
                )

        # ---------------------------------------------------------
        # Report
        # ---------------------------------------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Auction bootstrap completed."
            )
        )

        self.stdout.write(
            f"Voting cycle: #{voting_cycle.id}"
        )

        self.stdout.write(
            f"  batches: "
            f"{voting_cycle.import_batches.count()}/8"
        )

        self.stdout.write(
            f"  leftover tank copies: "
            f"{voting_sources}"
        )

        self.stdout.write(
            f"  status: {voting_cycle.status}"
        )

        self.stdout.write("")
        self.stdout.write(
            f"Collecting cycle: #{collecting_cycle.id}"
        )

        self.stdout.write(
            f"  batches: "
            f"{collecting_cycle.import_batches.count()}/8"
        )

        self.stdout.write(
            f"  leftover tank copies: "
            f"{collecting_sources}"
        )

        self.stdout.write(
            f"  status: {collecting_cycle.status}"
        )

        self.stdout.write("")
        self.stdout.write(
            f"Ignored historical batches: "
            f"{len(older_batches)}"
        )