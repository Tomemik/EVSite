from django.db.models import Q
from django_filters import rest_framework as filters
from .models import TeamLog, Match


class SafeMultipleChoiceFilter(filters.BaseInFilter, filters.CharFilter):

    def filter(self, qs, value):
        if not value:
            return qs

        if isinstance(value, str):
            value = [value]

        valid_values = set(qs.values_list(self.field_name, flat=True))

        valid_input = set(val for val in value if val in valid_values)

        if valid_input:
            return qs.filter(**{f"{self.field_name}__in": valid_input}).distinct()

        return qs


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


class MatchFilter(filters.FilterSet):
    from_date = filters.DateTimeFilter(field_name="datetime", lookup_expr="gte")
    to_date = filters.DateTimeFilter(field_name="datetime", lookup_expr="lte")
    team = SafeMultipleChoiceFilter(field_name="teams__name")
    played = filters.BooleanFilter(method='filter_played')

    class Meta:
        model = Match
        fields = ['team', 'was_played']

    def filter_played(self, queryset, name, value):
        if value:
            return queryset
        else:
            return queryset.filter(was_played=False)

