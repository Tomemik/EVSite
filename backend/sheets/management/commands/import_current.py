import csv
from django.core.management.base import BaseCommand
from ...models import Team, TeamTank, Tank

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
                        name=row['Name']
                    )

                    tank_entries = [tank.strip() for tank in row['Tanks'].split(',')]
                    for tank_entry in tank_entries:
                        if 'x' in tank_entry:
                            count, tank_name = tank_entry.split('x')
                            count = count.strip()
                            tank_name = tank_name.strip()

                            print(tank_name)
                            tank_model = Tank.objects.get(name=tank_name)

                            for _ in range(int(count)):
                                tank = TeamTank.objects.create(
                                    team=team,
                                    tank=tank_model,
                                    is_trad=False,
                                    is_upgradable=True,
                                )
                        else:
                            tank_name = tank_entry.strip()
                            print(tank_name)
                            tank_model = Tank.objects.get(name=tank_name)
                            tank = TeamTank.objects.create(
                                team=team,
                                tank=tank_model,
                                is_trad=False,
                                is_upgradable=True,
                            )


        self.stdout.write(self.style.SUCCESS('Successfully imported current Tanks'))