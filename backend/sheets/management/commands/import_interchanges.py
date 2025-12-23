import csv
from django.core.management.base import BaseCommand
from ...models import Tank, Interchange

class Command(BaseCommand):
    help = 'Import tank interchanges (chains) from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file to import')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        with open(csv_file, newline='') as file:
            reader = csv.DictReader(file)

            count_created = 0
            count_updated = 0

            for row in reader:
                if row:
                    print(row)
                    try:
                        from_tank = Tank.objects.get(name=row['From Tank'].strip())
                        print(from_tank)
                    except Tank.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f'Skipping row: Tank "{row["From Tank"]}" does not exist'))
                        continue

                    try:
                        to_tank = Tank.objects.get(name=row['To Tank'].strip())
                    except Tank.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f'Skipping row: Tank "{row["To Tank"]}" does not exist'))
                        continue

                    print(from_tank, to_tank)

                    raw_bi = row.get('Bidirectional', 'true').lower().strip()
                    is_bidirectional = raw_bi in ['true', '1', 'yes', 't', 'y']

                    interchange, created = Interchange.objects.update_or_create(
                        from_tank=from_tank,
                        to_tank=to_tank,
                        defaults={
                            'is_bidirectional': is_bidirectional
                        }
                    )

                    if created:
                        count_created += 1
                    else:
                        count_updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Successfully processed Interchanges: {count_created} created, {count_updated} updated.'
        ))