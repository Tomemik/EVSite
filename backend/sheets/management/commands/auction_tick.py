from django.core.management.base import BaseCommand

from ...services.auctions import run_auction_tick


class Command(BaseCommand):
    help = (
        "Processes expired imports, auction voting, "
        "auction starts, and auction finalization."
    )

    def handle(self, *args, **options):
        result = run_auction_tick()

        self.stdout.write(
            self.style.SUCCESS(
                "Auction tick completed: "
                f"{result}"
            )
        )