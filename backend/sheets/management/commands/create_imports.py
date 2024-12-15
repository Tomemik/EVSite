from datetime import timedelta
import random

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q

from ...models import Tank, ImportTank, ImportCriteria

class Command(BaseCommand):
    help = 'Generate import tanks'

    def handle(self, *args, **kwargs):

        self.stdout.write(self.style.SUCCESS('Started import job'))
        current_time = timezone.now()
        current_week_start = current_time - timedelta(days=current_time.weekday())
        thursday_utc = current_week_start + timedelta(days=3)
        thursday_utc = thursday_utc.replace(hour=17, minute=0, second=0, microsecond=0)
        next_thursday_utc = thursday_utc + timedelta(days=7)

        criteria = ImportCriteria.objects.get(is_active=True)
        filters = criteria.get_filters()
        available_tanks = Tank.objects.filter(**filters)

        one_week_ago = timezone.now() - timedelta(days=7)
        recent_tank_ids = ImportTank.objects.filter(
            Q(available_until__gte=one_week_ago)
        ).values_list('tank_id', flat=True)
        available_tanks = available_tanks.exclude(id__in=recent_tank_ids)

        required_tanks = list(criteria.required_tanks.all())
        required_count = min(criteria.required_tank_count or 0, len(required_tanks))

        selected_required_tanks = random.sample(required_tanks, required_count)

        remaining_count = 10 - required_count
        available_tanks = available_tanks.exclude(pk__in=[tank.pk for tank in selected_required_tanks])

        selected_remaining_tanks = random.sample(list(available_tanks), remaining_count)

        selected_tanks = selected_required_tanks + selected_remaining_tanks

        for tank in selected_tanks:
            discount = criteria.discount

            if tank in selected_required_tanks:
                discount += criteria.required_tank_discount

            discount = min(discount, 100)

            ImportTank.objects.create(
                tank=tank,
                discount=discount,
                available_from=thursday_utc,
                available_until=next_thursday_utc,
                criteria=criteria,
            )
        self.stdout.write(self.style.SUCCESS('Finished import job'))