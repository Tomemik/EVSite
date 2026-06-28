import csv
from django.core.management.base import BaseCommand
from ...models import Tank


class Command(BaseCommand):
    help = 'Import tanks and their internal IDs from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file to import')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                tank_name = row.get('Tank Name')

                if tank_name:
                    print(tank_name)

                    raw_internal_ids = row.get('Internal IDs', '')
                    parsed_ids = [
                        tank_id.strip()
                        for tank_id in raw_internal_ids.split('|')
                        if tank_id.strip()
                    ]

                    tank, created = Tank.objects.get_or_create(
                        name=tank_name,
                        defaults={
                            'battle_rating': float(row['Actual BR']),
                            'price': int(row['Cost']),
                            'rank': int(row['Rank']),
                            'type': row['Type'],
                            'internal_ids': parsed_ids,
                        }
                    )

                    if not created:
                        tank.battle_rating = float(row['Actual BR'])
                        tank.price = int(row['Cost'])
                        tank.rank = int(row['Rank'])
                        tank.type = row['Type']
                        tank.internal_ids = parsed_ids
                        tank.save()

        self.stdout.write(self.style.SUCCESS('Successfully imported tanks'))