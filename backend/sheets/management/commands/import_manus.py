import csv
from django.core.management.base import BaseCommand
from ...models import Tank, Manufacturer

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
                    manu, created = Manufacturer.objects.get_or_create(
                        name=row['Manu'],
                    )
                    print(row)
                    tank = Tank.objects.get(name=row['Tank'])
                    print(tank)
                    tank.manufacturers.add(manu)


        self.stdout.write(self.style.SUCCESS('Successfully imported manufacturers'))