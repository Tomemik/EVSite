import csv
from django.core.management.base import BaseCommand
from ...models import Tank


class Command(BaseCommand):
    help = 'Import internal IDs for tanks from a CSV file as a parsed list without modifying other data'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file to import')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        updated_count = 0
        not_found_count = 0

        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                tank_name = row.get('Tank Name')
                raw_internal_ids = row.get('Internal IDs', '')

                if tank_name:
                    # Parse the '|' separated string into a clean Python list
                    parsed_ids = [
                        tank_id.strip()
                        for tank_id in raw_internal_ids.split('|')
                        if tank_id.strip()
                    ]

                    # .update() ensures we ONLY touch the internal_ids field
                    updated = Tank.objects.filter(name=tank_name).update(internal_ids=parsed_ids)

                    if updated:
                        updated_count += 1
                        self.stdout.write(self.style.SUCCESS(f"Updated: {tank_name} with IDs {parsed_ids}"))
                    else:
                        not_found_count += 1
                        self.stdout.write(self.style.WARNING(f"Tank not found in DB: {tank_name}. Skipped."))

        self.stdout.write(self.style.SUCCESS(f'\nFinished. Updated: {updated_count} | Not found: {not_found_count}'))