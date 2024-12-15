from django.db.models import Avg, Q, Max
from django.utils import timezone
from rest_framework import serializers
from .models import Manufacturer, Team, Tank, UpgradePath, TeamTank, Match, TeamMatch, Substitute, MatchResult, \
    TankLost, TeamResult, TankBox, TeamBox, TeamLog, ImportTank, ImportCriteria


class TankSerializerSlim(serializers.ModelSerializer):
    class Meta:
        model = Tank
        fields = ['id', 'name', 'battle_rating']


class TankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tank
        fields = ['id', 'name', 'battle_rating', 'price', 'rank', 'type']


class TankBoxSerializer(serializers.ModelSerializer):
    tanks = TankSerializerSlim(many=True, read_only=True)

    class Meta:
        model = TankBox
        fields = ['id', 'name', 'price', 'tanks']


class TeamBoxSerializer(serializers.ModelSerializer):
    box_id = serializers.CharField(source='box.id', read_only=True)
    box_name = serializers.CharField(source='box.name', read_only=True)
    amount = serializers.IntegerField()

    class Meta:
        model = TeamBox
        fields = ['box_id', 'box_name', 'amount']


class TankBoxCreateSerializer(serializers.ModelSerializer):
    tanks = serializers.ListField(
        child=serializers.CharField(max_length=50),
        write_only=True
    )

    class Meta:
        model = TankBox
        fields = ['name', 'tanks', 'price']
        read_only_fields = ['price']

    def validate_tanks(self, tank_names):
        tanks = Tank.objects.filter(name__in=tank_names)
        if len(tanks) != len(tank_names):
            missing_tanks = set(tank_names) - set(tanks.values_list('name', flat=True))
            raise serializers.ValidationError(f"Some tanks not found: {', '.join(missing_tanks)}")
        return tanks

    def create(self, validated_data):
        tanks = validated_data.pop('tanks')
        tank_box = TankBox.objects.create(name=validated_data['name'])

        tank_box.tanks.set(tanks)

        mean_price = tanks.aggregate(average_price=Avg('price'))['average_price']
        tank_box.price = int(mean_price)
        tank_box.save()

        return tank_box


class ManufacturerSerializer(serializers.ModelSerializer):
    tanks = TankSerializer(many=True, read_only=True)
    add_tank_names = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    remove_tank_names = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)

    class Meta:
        model = Manufacturer
        fields = ['id', 'name', 'tanks', 'add_tank_names', 'remove_tank_names']

    def update(self, instance, validated_data):
        if 'add_tank_names' in validated_data:
            tank_names = validated_data.pop('add_tank_names')
            tanks_to_add = Tank.objects.filter(name__in=tank_names)
            instance.tanks.add(*tanks_to_add)

        if 'remove_tank_names' in validated_data:
            remove_tank_names = validated_data.pop('remove_tank_names')
            tanks_to_remove = Tank.objects.filter(name__in=remove_tank_names)
            instance.tanks.remove(*tanks_to_remove)

        return super().update(instance, validated_data)


class UpgradePathSerializer(serializers.ModelSerializer):
    from_tank = TankSerializer(read_only=True)
    to_tank = TankSerializer(read_only=True)

    class Meta:
        model = UpgradePath
        fields = ['id', 'from_tank', 'to_tank', 'required_kit_tier', 'cost']


class TeamTankSerializer(serializers.ModelSerializer):
    tank = TankSerializerSlim()
    available = serializers.SerializerMethodField()

    class Meta:
        model = TeamTank
        fields = ['id', 'tank', 'team', 'is_trad', 'available']

    def get_available(self, obj):
        team_tanks = TeamTank.objects.filter(team=obj.team)

        non_trad_tanks = team_tanks.filter(is_trad=False)
        highest_non_trad_rank = non_trad_tanks.aggregate(max_rank=Max('tank__rank', default=0))['max_rank']
        if highest_non_trad_rank is not None and obj.tank.rank <= highest_non_trad_rank:
            return True
        return False


class TeamSerializer(serializers.ModelSerializer):
    manufacturers = ManufacturerSerializer(many=True, read_only=True)
    tanks = TeamTankSerializer(many=True, read_only=True, source='teamtank_set')
    upgrade_kits = serializers.JSONField(required=False)
    tank_boxes = TeamBoxSerializer(many=True, read_only=True, source='teambox_set')

    class Meta:
        model = Team
        fields = ['id', 'name', 'color', 'balance', 'manufacturers', 'tanks', 'upgrade_kits', 'tank_boxes']
        depth = 1


class TeamMatchSerializer(serializers.ModelSerializer):
    team = serializers.SlugRelatedField(slug_field='name', queryset=Team.objects.all())
    tanks = TeamTankSerializer(many=True)

    class Meta:
        model = TeamMatch
        fields = ['team', 'tanks', 'side']

    def validate(self, data):
        team = data.get('team')
        tanks_data = data.get('tanks', [])
        for team_tank_data in tanks_data:
            tank_data = team_tank_data.get('tank')
            if tank_data:
                tank_name = tank_data.get('name')
                try:
                    tank = Tank.objects.get(name=tank_name)
                    if not TeamTank.objects.filter(tank=tank, team=team).exists():
                        raise serializers.ValidationError(
                            f"Tank '{tank_name}' is not associated with team '{team.name}'.")
                except Tank.DoesNotExist:
                    raise serializers.ValidationError(f"Tank '{tank_name}' does not exist.")

        return data

    def create(self, validated_data):
        tanks_data = validated_data.pop('tanks')
        team_match = TeamMatch.objects.create(**validated_data)

        team = validated_data['team']
        for team_tank_data in tanks_data:
            tank_data = team_tank_data.pop('tank')
            tank_name = tank_data.get('name')
            tank = Tank.objects.get(name=tank_name)
            team_tank, created = TeamTank.objects.get_or_create(tank=tank, team=team, **team_tank_data)
            team_match.tanks.add(team_tank)
        return team_match


class MatchSerializer(serializers.ModelSerializer):
    teammatch_set = TeamMatchSerializer(many=True)

    class Meta:
        model = Match
        fields = [
            'id', 'datetime', 'mode', 'gamemode', 'best_of_number',
            'map_selection', 'money_rules', 'special_rules', 'teammatch_set'
        ]

    def validate(self, data):
        team_matches_data = data.get('teammatch_set', [])
        match_date = data.get('datetime', timezone.now()).date()

        existing_team_ids = (
            self.instance.teammatch_set.values_list('team_id', flat=True)
            if self.instance else []
        )

        for team_match_data in team_matches_data:
            team = team_match_data['team']

            if team.id in existing_team_ids:
                continue

            if team.matches_for_week(match_date) >= 6:
                raise serializers.ValidationError(
                    f"Cannot add Team '{team.name}' to this match as it has already reached the limit of 6 matches this week."
                )

        return data

    def create(self, validated_data):
        team_matches_data = validated_data.pop('teammatch_set')
        match = Match.objects.create(**validated_data)

        for team_match_data in team_matches_data:
            tanks_data = team_match_data.pop('tanks', [])
            team_match = TeamMatch.objects.create(match=match, **team_match_data)

            for team_tank_data in tanks_data:
                tank_data = team_tank_data.pop('tank')
                tank, created = Tank.objects.get_or_create(**tank_data)

                team = team_match_data['team']
                if match.mode == 'traditional':
                    team_tank = TeamTank.objects.filter(tank=tank, is_trad=True, team__name=team,
                                                        **team_tank_data).exclude(
                        id__in=team_match.tanks.values_list('id', flat=True)).first()
                else:
                    team_tank = TeamTank.objects.filter(tank=tank, is_trad=False, team__name=team,
                                                        **team_tank_data).exclude(
                        id__in=team_match.tanks.values_list('id', flat=True)).first()

                if not team_match.tanks.filter(id=team_tank.id).exists():
                    team_match.tanks.add(team_tank)

        return match

    def update(self, instance, validated_data):
        team_matches_data = validated_data.pop('teammatch_set', [])

        # Update the match fields
        instance.datetime = validated_data.get('datetime', instance.datetime)
        instance.mode = validated_data.get('mode', instance.mode)
        instance.gamemode = validated_data.get('gamemode', instance.gamemode)
        instance.best_of_number = validated_data.get('best_of_number', instance.best_of_number)
        instance.map_selection = validated_data.get('map_selection', instance.map_selection)
        instance.money_rules = validated_data.get('money_rules', instance.money_rules)
        instance.special_rules = validated_data.get('special_rules', instance.special_rules)
        instance.save()

        # Clear existing team matches
        instance.teammatch_set.all().delete()

        for team_match_data in team_matches_data:
            tanks_data = team_match_data.pop('tanks', [])
            team_match = TeamMatch.objects.create(match=instance, **team_match_data)

            for team_tank_data in tanks_data:
                tank_data = team_tank_data.pop('tank')
                tank, created = Tank.objects.get_or_create(**tank_data)

                team = team_match_data['team']
                if instance.mode == 'traditional':
                    team_tank = TeamTank.objects.filter(tank=tank, is_trad=True, team__name=team, **team_tank_data).exclude(id__in=team_match.tanks.values_list('id', flat=True)).first()
                else:
                    team_tank = TeamTank.objects.filter(tank=tank, is_trad=False, team__name=team, **team_tank_data).exclude(id__in=team_match.tanks.values_list('id', flat=True)).first()


                if not team_match.tanks.filter(id=team_tank.id).exists():
                    team_match.tanks.add(team_tank)

        return instance


class SlimTeamSerializer(serializers.ModelSerializer):

    class Meta:
        model = Team
        fields = ['name', 'color', 'balance']


class SlimTeamSerializerWithTanks(serializers.ModelSerializer):
    tanks = TeamTankSerializer(many=True, read_only=True, source='teamtank_set')

    class Meta:
        model = Team
        fields = ['id', 'name', 'color', 'balance', 'tanks']


class SlimTeamMatchSerializer(serializers.ModelSerializer):
    team = SlimTeamSerializer()

    class Meta:
        model = TeamMatch
        fields = ['team', 'side']


class SlimMatchSerializer(serializers.ModelSerializer):
    teammatch_set = SlimTeamMatchSerializer(many=True, read_only=True)

    class Meta:
        model = Match
        fields = ['id', 'datetime', 'teammatch_set']


class TeamResultSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', write_only=True)
    team = serializers.SlugRelatedField(slug_field='name', read_only=True)

    class Meta:
        model = TeamResult
        fields = ['team', 'team_name', 'bonuses', 'penalties']


class TankLostSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', write_only=True)
    team = serializers.SlugRelatedField(slug_field='name', read_only=True)
    tank_name = serializers.CharField(source='tank.name', write_only=True)
    tank = serializers.SlugRelatedField(slug_field='name', read_only=True)

    class Meta:
        model = TankLost
        fields = ['team', 'team_name', 'tank', 'tank_name', 'quantity']


class SubstituteSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', write_only=True)
    team = serializers.SlugRelatedField(slug_field='name', read_only=True)
    team_played_for_name = serializers.CharField(source='team_played_for.name', write_only=True)
    team_played_for = serializers.SlugRelatedField(slug_field='name', read_only=True)

    class Meta:
        model = Substitute
        fields = ['team', 'team_name', 'activity', 'side', 'team_played_for', 'team_played_for_name']


class MatchResultSerializer(serializers.ModelSerializer):
    team_results = TeamResultSerializer(many=True)
    tanks_lost = TankLostSerializer(many=True)
    substitutes = SubstituteSerializer(many=True)
    judge_name = serializers.CharField(source='judge.name', write_only=True, allow_blank=True)
    judge = serializers.SlugRelatedField(slug_field='name', read_only=True)
    match_id = serializers.IntegerField(source='match.id', write_only=True)
    match = serializers.SlugRelatedField(slug_field='id', read_only=True)

    class Meta:
        model = MatchResult
        fields = ['match', 'match_id', 'winning_side', 'judge', 'judge_name', 'team_results', 'tanks_lost',
                  'substitutes', 'is_calced']
        depth = 1

    def create(self, validated_data):
        print(validated_data)
        match_data = validated_data.pop('match')
        match = Match.objects.get(id=match_data.id)
        judge_data = validated_data.pop('judge')
        if judge_data['name']:
            judge = Team.objects.get(name=judge_data['name'])
        else:
            judge = None

        team_results_data = validated_data.pop('team_results')
        tanks_lost_data = validated_data.pop('tanks_lost')
        substitutes_data = validated_data.pop('substitutes')

        match_result = MatchResult.objects.create(match=match, judge=judge, **validated_data)

        for team_result_data in team_results_data:
            team_name = team_result_data.pop('team')['name']
            team = Team.objects.get(name=team_name)
            TeamResult.objects.create(match_result=match_result, team=team, **team_result_data)

        for tank_lost_data in tanks_lost_data:
            team_name = tank_lost_data.pop('team')['name']
            tank_name = tank_lost_data.pop('tank')['name']
            team = Team.objects.get(name=team_name)
            tank = Tank.objects.get(name=tank_name)
            TankLost.objects.create(match_result=match_result, team=team, tank=tank, **tank_lost_data)

        for substitute_data in substitutes_data:
            team_name = substitute_data.pop('team')['name']
            team_played_for_name = substitute_data.pop('team_played_for')['name']
            team = Team.objects.get(name=team_name)
            team_played_for = Team.objects.get(name=team_played_for_name)
            side = substitute_data.pop('side')
            activity = substitute_data.pop('activity')
            Substitute.objects.create(
                match_result=match_result,
                team=team,
                team_played_for=team_played_for,
                side=side,
                activity=activity,
                **substitute_data
            )
        return match_result


class TeamLogSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = TeamLog
        fields = ['id', 'team', 'team_name', 'method_name', 'description', 'timestamp']
        depth = 0


class ImportTankSerializer(serializers.ModelSerializer):
    tank_name = serializers.CharField(source='tank.name')
    base_discounted_price = serializers.SerializerMethodField()
    criteria_id = serializers.IntegerField(source='criteria.id', read_only=True)

    class Meta:
        model = ImportTank
        fields = ['id', 'tank_name', 'discount', 'available_from', 'available_until', 'is_purchased', 'base_discounted_price', 'criteria_id']

    def get_base_discounted_price(self, obj):
        if not obj.tank or obj.tank.price is None:
            return None
        return max(obj.tank.price - (obj.tank.price * (obj.discount / 100)), 0)


class ImportCriteriaSerializer(serializers.ModelSerializer):
    required_tanks = TankSerializerSlim(many=True, read_only=True)
    class Meta:
        model = ImportCriteria
        fields = [
            'id', 'min_rank', 'max_rank', 'tank_type', 'is_active',
            'required_tanks', 'required_tank_count', 'discount', 'required_tank_discount',
        ]
