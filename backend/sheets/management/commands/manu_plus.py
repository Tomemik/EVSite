import csv
import sys
from django.core.management.base import BaseCommand
from sheets.models import Team, Tank
from django.db.models import F


class Command(BaseCommand):
    help = 'Exports Manufacturer+ rosters for all teams to a CSV format.'

    def handle(self, *args, **options):
        filename = "manufacturer_plus_rosters.csv"
        teams = Team.objects.all().prefetch_related('manufacturers')

        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            console_writer = csv.writer(sys.stdout)

            header = ['Team', 'Manufacturers', 'Category', 'BR', 'Tank Name']
            writer.writerow(header)
            console_writer.writerow(header)

            for team in teams:
                team_manufacturers = team.manufacturers.all()
                if not team_manufacturers.exists():
                    continue

                # Joined with ' | ' so it doesn't mess up CSV columns when copy-pasting
                manufacturers_str = " | ".join(m.name for m in team_manufacturers)

                # 1. Base Tanks
                base_tanks = Tank.objects.filter(
                    manufacturers__in=team_manufacturers
                ).distinct().order_by('battle_rating', 'name')

                # 2. +1 Tier (Upgrades FROM a base tank, HIGHER or EQUAL BR)
                plus_1_tanks = Tank.objects.filter(
                    upgrade_to__from_tank__manufacturers__in=team_manufacturers,
                    battle_rating__gte=F('upgrade_to__from_tank__battle_rating'),
                    battle_rating__lte=7.5
                ).exclude(id__in=base_tanks).distinct().order_by('battle_rating', 'name')

                # 3. -1 Tier (Upgrades TO a base tank, LOWER BR)
                minus_1_tanks = Tank.objects.filter(
                    upgrade_from__to_tank__manufacturers__in=team_manufacturers,
                    battle_rating__lt=F('upgrade_from__to_tank__battle_rating'),
                    battle_rating__lte=7.5
                ).exclude(id__in=base_tanks).exclude(id__in=plus_1_tanks).distinct().order_by('battle_rating', 'name')

                for t in base_tanks:
                    row = [team.name, 'Base Tank', f"{t.battle_rating:.1f}", t.name]
                    writer.writerow(row)
                    console_writer.writerow(row)

                for t in plus_1_tanks:
                    row = [team.name, '+1 Tier', f"{t.battle_rating:.1f}", t.name]
                    writer.writerow(row)
                    console_writer.writerow(row)

                for t in minus_1_tanks:
                    row = [team.name, '-1 Tier', f"{t.battle_rating:.1f}", t.name]
                    writer.writerow(row)
                    console_writer.writerow(row)

        self.stdout.write(self.style.SUCCESS(f"\n✅ Data printed above! Also saved to '{filename}'."))