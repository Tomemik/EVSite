import csv
from django.core.management.base import BaseCommand
from ...models import Tank, TankBox


class Command(BaseCommand):
    help = 'Import tank boxes and tanks from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file to import')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        with open(csv_file, newline='') as file:
            reader = csv.DictReader(file)

            current_tank_box = None
            current_id = 0

            for row in reader:
                current_id += 1
                tank_box_name = row['Name']
                if tank_box_name is not None:
                    print(tank_box_name)

                    tank_box = TankBox.objects.create(
                        name=tank_box_name,
                        id=current_id,
                        tier=int(row['Tier']),
                        price=0,
                        is_national=True if row['National'] == 'True' else False,
                    )

                    tank_names = row['Tanks'].split(',')

                    for tank_name in tank_names:
                        print(tank_name)
                        tank_name = tank_name.strip()
                        tank, created = Tank.objects.get_or_create(
                            name=tank_name,
                        )
                        tank_box.tanks.add(tank)

                    tank_box.save()

        self.stdout.write(self.style.SUCCESS('Successfully imported tank boxes and tanks'))