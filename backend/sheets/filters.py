from django_filters import rest_framework as filters
from .models import TeamLog


class TeamLogFilter(filters.FilterSet):
    method_name = filters.MultipleChoiceFilter(
        field_name="method_name",
        lookup_expr="iexact",
        choices=[
            ('calc_rewards', 'Calc Rewards'),
            ('purchase_tank', 'Purchase Tank'),
            ('sell_tank', 'Sell Tank'),
            ('upgrade_or_downgrade_tank', 'Upgrade or Downgrade Tank'),
        ],
    )
    from_date = filters.DateTimeFilter(field_name="timestamp", lookup_expr="gte")
    to_date = filters.DateTimeFilter(field_name="timestamp", lookup_expr="lte")