import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from ...models import UpgradeTree, Tank

class Command(BaseCommand):
    help = "Import upgrade trees from CSV"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file to import')

    @transaction.atomic
    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        with open(csv_file, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            count = 0
            for row in reader:
                label = row['label'].strip()
                tank_value = row['value'].strip()

                try:
                    tank = Tank.objects.get(name=tank_value)  # adjust field name if needed
                except Tank.DoesNotExist:
                    self.stderr.write(self.style.ERROR(
                        f"Tank '{tank_value}' not found, skipping '{label}'"
                    ))
                    continue

                UpgradeTree.objects.update_or_create(
                    label=label,
                    defaults={'value': tank}
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {count} upgrade trees."))