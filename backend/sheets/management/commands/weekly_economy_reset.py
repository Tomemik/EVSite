from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db import transaction
from ...models import Team, WeeklyEconomySettings, TeamLog


class Command(BaseCommand):
    help = "Distributes under-cap payouts and updates the global dynamic cap for the new week."

    def add_arguments(self, parser):
        # Add optional dry-run argument
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run the calculation and print payouts without modifying the database.',
        )

    def handle(self, *args, **options):
        is_dry_run = options['dry_run']
        settings = WeeklyEconomySettings.load()
        teams = Team.objects.all()

        # Wrap in an atomic transaction so we can roll it back if it's a dry run
        with transaction.atomic():
            for team in teams:
                earnings = team.get_weekly_match_earnings()

                if 0 < earnings < settings.current_cap:
                    deficit = settings.current_cap - earnings
                    payout = int(deficit * settings.under_cap_payout_ratio)

                    if payout > 0:
                        if is_dry_run:
                            self.stdout.write(self.style.WARNING(f"[DRY RUN] {team.name} would receive +{payout:,}"))
                        else:
                            initial_balance = team.balance
                            team.balance += payout
                            team.total_money_earned += payout
                            team.save()

                            TeamLog.objects.create(
                                team=team,
                                user="System",
                                field_name="balance",
                                previous_value={'balance': initial_balance},
                                new_value={'balance': team.balance},
                                description=(
                                    f"Weekly Catch-up Bonus: +{payout:,}\n"
                                    f"(Earned {earnings:,} vs {settings.current_cap:,} global cap)"
                                ),
                                method_name="weekly_under_cap_bonus"
                            )
                            self.stdout.write(self.style.SUCCESS(f"Paid {team.name} +{payout:,}"))

            new_cap = settings.update_dynamic_cap()

            if is_dry_run:
                self.stdout.write(self.style.WARNING(f"[DRY RUN] New Global Cap would be: {new_cap:,}"))
                # Rollback all database changes made during the loop
                transaction.set_rollback(True)
            else:
                self.stdout.write(self.style.SUCCESS(f"Weekly economy reset complete. New Global Cap: {new_cap:,}"))