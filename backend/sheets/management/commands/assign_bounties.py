from django.core.management.base import BaseCommand
from django.db import transaction
from ...models import Team, Bounty, BountyTier


class Command(BaseCommand):
    help = 'Assigns bounties to the top 4 teams based on BountyTier configuration'

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            Bounty.objects.filter(is_active=True).update(is_active=False)

            top_teams = Team.objects.order_by('-total_money_earned')[:4]

            if not top_teams:
                self.stdout.write(self.style.WARNING("No teams found."))
                return

            self.stdout.write(self.style.SUCCESS("Assigning New Bounties:"))

            for index, team in enumerate(top_teams):
                rank = index + 1

                try:
                    tier_config = BountyTier.objects.get(rank=rank)
                    amount = tier_config.bounty_value
                except BountyTier.DoesNotExist:
                    amount = 50000
                    self.stdout.write(self.style.WARNING(f"No config found for Rank {rank}, using default {amount}"))

                Bounty.objects.create(team=team, value=amount)

                self.stdout.write(f" - Rank {rank}: {team.name} gets bounty of ${amount:,}")

            self.stdout.write(self.style.SUCCESS('Done.'))