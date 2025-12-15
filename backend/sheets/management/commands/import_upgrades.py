import csv
from django.core.management.base import BaseCommand
from ...models import Tank, UpgradePath

class Command(BaseCommand):
    help = 'Import tank upgrades from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file to import')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        with open(csv_file, newline='') as file:
            reader = csv.DictReader(file)

            for row in reader:
                if row:
                    try:
                        from_tank = Tank.objects.get(name=row['From Tank'])
                    except Tank.DoesNotExist:
                        print(f'Tank {row["From Tank"]} does not exist')
                    try:
                        to_tank = Tank.objects.get(name=row['To Tank'])
                    except Tank.DoesNotExist:
                        print(f'Tank {row["To Tank"]} does not exist')
                    kit = row['Kit']
                    In_graph = True if row['In_graph'] == 'true' else False

                    path, created = UpgradePath.objects.get_or_create(
                        from_tank=from_tank,
                        to_tank=to_tank,
                        in_graph=In_graph,
                        defaults={
                            'required_kit_tier': kit if kit != 'P' else '',
                        }
                    )
                    if not created:
                        path.required_kit_tier = kit if kit != 'P' else ''
                        path.save()


                    #print(path, created)


        self.stdout.write(self.style.SUCCESS('Successfully imported Upgrades'))