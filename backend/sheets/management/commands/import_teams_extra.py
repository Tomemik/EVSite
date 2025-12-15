import csv
from django.core.management.base import BaseCommand
from ...models import Team, Manufacturer

class Command(BaseCommand):
    help = 'Import tanks from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file to import')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        with open(csv_file, newline='') as file:
            reader = csv.DictReader(file)

            for row in reader:
                if row:
                    team, created = Team.objects.get_or_create(
                        name=row['Name'],
                        color=row['Color']
                    )

                manufacturer_names = [name.strip() for name in row['Manufacturers'].split(',')]
                for manu_name in manufacturer_names:
                    manu = Manufacturer.objects.filter(name=manu_name).first()
                    if manu:
                        team.manufacturers.add(manu)
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"Manufacturer '{manu_name}' not found for team '{team.name}'."
                        ))

                team.balance = row['Balance']
                team.total_money_earned = row['Total money earned']
                team.total_money_spent = row['Total money spent']
                team.score = row['Score']
                team.upgrade_kits = {
                    'T1': {'quantity': row['Kits'], 'price': 25000},
                    'T2': {'quantity': 0, 'price': 50000},
                    'T3': {'quantity': 0, 'price': 100000}
                }
                team.save()


        self.stdout.write(self.style.SUCCESS('Successfully imported Teams'))