from django.shortcuts import render, get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from django.contrib.auth.mixins import PermissionRequiredMixin

from .filters import TeamLogFilter, MatchFilter
from .models import Team, Manufacturer, Tank, Match, MatchResult, TankBox, TeamMatch, TeamLog, ImportTank, \
    ImportCriteria
from .serializers import TeamSerializer, ManufacturerSerializer, TankSerializer, MatchSerializer, SlimMatchSerializer, \
    MatchResultSerializer, TankBoxSerializer, TankBoxCreateSerializer, SlimTeamSerializer, TeamMatchSerializer, \
    TeamLogSerializer, SlimTeamSerializerWithTanks, ImportTankSerializer, ImportCriteriaSerializer


class AllTeamsView(APIView):
    def get(self, request):
        teams = Team.objects.all()
        serializer = SlimTeamSerializer(teams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if not request.user.has_perm('user.admin_permissions'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = TeamSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
        print(serializer.errors)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AllTeamsWithTanksView(APIView):
    def get(self, request):
        teams = Team.objects.all()
        serializer = SlimTeamSerializerWithTanks(teams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TeamDetailView(APIView):
    def get(self, request, name):
        team = Team.objects.get(name=name)
        serializer = TeamSerializer(team)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, name):
        if not request.user.has_perm('user.admin_permissions'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        upgrade_kit = request.data.get('upgrade_kits', [])
        kit_amount = request.data.get('kit_amounts', [])
        tank_box_ids = request.data.get('tank_box_ids', [])
        box_amounts = request.data.get('amounts', [])
        team = Team.objects.get(name=name)

        if tank_box_ids and box_amounts:
            team.add_tank_boxes(tank_box_ids, box_amounts)
        if upgrade_kit and kit_amount:
            team.add_upgrade_kit(upgrade_kit, kit_amount)
        team.save()

        serializer = TeamSerializer(team, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class AllTanksView(APIView):
    def get(self, request):
        tanks = Tank.objects.all()
        serializer = TankSerializer(tanks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if not request.user.has_perm('user.admin_permissions'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = TankSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        if not request.user.has_perm('user.admin_permissions'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        ids = request.data.get('to_delete', [])
        tanks = Tank.objects.filter(id__in=ids)
        tanks.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TankDetailView(APIView):
    def get(self, request, name):
        tank = Tank.objects.get(name=name)
        serializer = TankSerializer(tank)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, name):
        if not request.user.has_perm('user.admin_permissions'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        tank = Tank.objects.get(name=name)
        serializer = TankSerializer(tank, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PurchaseTankView(APIView):
    def post(self, request):
        user = request.user
        team_name = request.data['team']
        if not (
            user.has_perm('user.admin_permissions') or
            (user.has_perm('user.commander_permissions') and user.team and user.team.name == team_name)
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        tanks = request.data.get('tanks', [])
        team = Team.objects.get(name=team_name)
        for tank in tanks:
            tank = Tank.objects.get(name=tank)
            team.purchase_tank(tank)
        return Response(data={'new_balance': team.balance, 'new_tanks': [tank for tank in tanks]}, status=status.HTTP_200_OK)


class SellTankView(APIView):
    def post(self, request):
        user = request.user
        team_name = request.data['team']
        if not (
            user.has_perm('user.admin_permissions') or
            (user.has_perm('user.commander_permissions') and user.team and user.team.name == team_name)
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        tanks = request.data.get('tanks', [])
        team = Team.objects.get(name=team_name)
        for tank in tanks:
            tank = Tank.objects.get(name=tank['name'])
            team.sell_tank(tank)
        return Response(data={'new_balance': team.balance, 'sold_tanks': [tank for tank in tanks]}, status=status.HTTP_200_OK)


class TransferMoneyView(APIView):
    def post(self, request):
        user = request.user
        team_name = request.data['team']
        print(user)
        print(team_name)
        if not (
            user.has_perm('user.admin_permissions') or
            (user.has_perm('user.commander_permissions') and user.team and user.team.name == team_name)
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        to_team_name = request.data['to_team']
        amount = request.data['amount']

        from_team = Team.objects.get(name=team_name)
        to_team = Team.objects.get(name=to_team_name)
        from_team.money_transfer(from_team, to_team, amount)
        return Response(data={'new_balance': from_team.balance}, status=status.HTTP_200_OK)


class MergeSplitKitView(APIView):
    def post(self, request):
        user = request.user
        team_name = request.data['team']
        if not (
            user.has_perm('user.admin_permissions') or
            (user.has_perm('user.commander_permissions') and user.team and user.team.name == team_name)
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        action = request.data.get('action')
        kit_type = request.data.get('kit_type')
        kit_amount = request.data.get('kit_amount')
        if action not in ['merge', 'split']:
            return Response({'success': False, 'message': "Invalid action. Use 'merge' or 'split'."}, status=status.HTTP_400_BAD_REQUEST)
        if kit_type not in ['T1', 'T2', 'T3']:
            return Response({'success': False, 'message': "Invalid kit type. Use 'T1', 'T2', or 'T3'."}, status=status.HTTP_400_BAD_REQUEST)
        team = Team.objects.get(name=team_name)
        success = team.split_merge_kit(action=action, kit_type=kit_type, kit_amount=kit_amount)
        if success:
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class AllUpgradesView(APIView):
    def get(self, request):
        team_name = request.headers['team']
        tank = request.headers['tank']
        team = Team.objects.get(name=team_name)
        tank = Tank.objects.get(name=tank)

        all_upgrades = team.get_possible_upgrades(tank)

        return Response(all_upgrades, status=status.HTTP_200_OK)


class AllDirectUpgradesView(APIView):
    def get(self, request):
        team_name = request.headers['team']
        tank = request.headers['tank']
        team = Team.objects.get(name=team_name)
        tank = Tank.objects.get(name=tank)

        all_upgrades = team.get_direct_upgrades(tank)

        return Response(all_upgrades, status=status.HTTP_200_OK)


class DirectUpgradeTankView(APIView):
    def post(self, request):
        user = request.user
        team = request.data.get('team', None)
        if not (
            user.has_perm('user.admin_permissions') or
            (user.has_perm('user.commander_permissions') and user.team and user.team.name == team)
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        team = request.data.get('team', None)
        from_tank = request.data.get('from_tank', None)
        to_tank = request.data.get('to_tank', None)
        kits = request.data.get('kits', [])

        team = Team.objects.get(name=team)
        from_tank = Tank.objects.get(name=from_tank)
        to_tank = Tank.objects.get(name=to_tank)
        extra_kits = []
        for key, val in kits.items():
            if key == 'T1':
                extra_kits += ['T1'] * val
            if key == 'T2':
                extra_kits += ['T2'] * val
            if key == 'T3':
                extra_kits += ['T3'] * val

        all_upgrades = team.do_direct_upgrade(from_tank, to_tank, extra_kits)

        return Response(data={'new_balance': team.balance, 'new_kits': team.upgrade_kits}, status=status.HTTP_200_OK)


class UpgradeTankView(APIView):
    def post(self, request):
        user = request.user
        team = request.data.get('team', None)
        if not (
            user.has_perm('user.admin_permissions') or
            (user.has_perm('user.commander_permissions') and user.team and user.team.name == team)
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        team = request.data.get('team', None)
        from_tank = request.data.get('from_tank', None)
        to_tank = request.data.get('to_tank', None)
        kits = request.data.get('kits', [])

        team = Team.objects.get(name=team)
        from_tank = Tank.objects.get(name=from_tank)
        to_tank = Tank.objects.get(name=to_tank)
        extra_kits = []
        for key, val in kits.items():
            if key == 'T1':
                extra_kits += ['T1'] * val
            if key == 'T2':
                extra_kits += ['T2'] * val
            if key == 'T3':
                extra_kits += ['T3'] * val

        all_upgrades = team.upgrade_or_downgrade_tank(from_tank, to_tank, extra_kits)

        return Response(data={'new_balance': team.balance, 'new_kits': team.upgrade_kits}, status=status.HTTP_200_OK)


class ManufacturerDetailView(APIView):
    def get(self, request, pk):
        manufacturer = Manufacturer.objects.get(pk=pk)
        serializer = ManufacturerSerializer(manufacturer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        if not request.user.has_perm('user.admin_permissions'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        manufacturer = get_object_or_404(Manufacturer, pk=pk)
        serializer = ManufacturerSerializer(manufacturer, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ManufacturerListView(APIView):
    def get(self, request):
        team_name = request.query_params.get('team_name', None)

        if team_name:
            team = get_object_or_404(Team, name=team_name)
            manufacturers = team.manufacturers.all()
        else:
            manufacturers = Manufacturer.objects.all()

        serializer = ManufacturerSerializer(manufacturers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if not request.user.has_perm('user.admin_permissions'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = ManufacturerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TankBoxView(APIView):
    def get(self, request):
        box = TankBox.objects.all()
        serializer = TankBoxSerializer(box, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if not request.user.has_perm('user.admin_permissions'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = TankBoxCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AllMatchesViewSlim(APIView):
    def get(self, request):
        matches = Match.objects.filter(was_played=False)
        serializer = SlimMatchSerializer(matches, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AllMatchesView(APIView):
    def get(self, request):
        matches = Match.objects.filter(was_played=False)
        serializer = MatchSerializer(matches, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        if not user.has_perm('user.admin_permissions'):
            if not user.has_perm('user.commander_permissions'):
                return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = MatchSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(
                {"detail": e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )


class ArchivedAllMatchesView(APIView):
    def get(self, request):
        matches = Match.objects.all()
        serializer = MatchSerializer(matches, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = MatchSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MatchFilteredView(ListAPIView):
    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = MatchFilter


class MatchView(APIView):
    def get(self, request, pk):
        match = Match.objects.get(pk=pk)
        serializer = MatchSerializer(match)
        print(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        user = request.user
        if not any([user.has_perm('user.admin_permissions'), user.has_perm('user.commander_permissions'), user.has_perm('user.judge_permissions')]):
            return Response(status=status.HTTP_403_FORBIDDEN)
        match = Match.objects.get(pk=pk)
        serializer = MatchSerializer(match, data=request.data, partial=True)
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(
                {"detail": e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )

class MatchResultsView(APIView):
    def get(self, request, pk):
        match = Match.objects.get(pk=pk)
        matchResult = MatchResult.objects.get(match__pk=pk)
        serializer = MatchResultSerializer(matchResult)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, pk):
        user = request.user
        if not any([user.has_perm('user.admin_permissions'), user.has_perm('user.judge_permissions')]):
            if user.has_perm('user.commander_permissions'):
                print(request.data)
                team_matches = request.data.get('team_results', [])
                print(team_matches)
                user_team_name = user.team.name if user.team else None
                team_found = any(match['team_name'] == user_team_name for match in team_matches)
                if not team_found:
                    return Response(status=status.HTTP_403_FORBIDDEN)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

        match = Match.objects.get(pk=pk)
        try:
            matchResult = MatchResult.objects.get(match__pk=pk)
            matchResult.delete()
        except MatchResult.DoesNotExist:
            pass
        serializer = MatchResultSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(match=match)
            match.was_played = True
            match.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        user = request.user
        if not any([user.has_perm('user.admin_permissions'), user.has_perm('user.judge_permissions')]):
            if user.has_perm('user.commander_permissions'):
                team_matches = request.data.get('teammatch_set', [])
                user_team_name = user.team.name if user.team else None
                team_found = any(match['team'] == user_team_name for match in team_matches)
                if not team_found:
                    return Response(status=status.HTTP_403_FORBIDDEN)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

        match = Match.objects.get(pk=pk)
        serializer = MatchResultSerializer(match, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(match=match)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CalcTestView(APIView):
    def post(self, request, pk):
        user = request.user
        if not any([user.has_perm('user.admin_permissions'), user.has_perm('user.judge_permissions')]):
            return Response(status=status.HTTP_403_FORBIDDEN)
        match_result = MatchResult.objects.get(match__pk=pk)
        if not match_result.is_calced:
            match_result.calculate_rewards()
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class TeamLogFilteredView(ListAPIView):
    queryset = TeamLog.objects.all()
    serializer_class = TeamLogSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TeamLogFilter

    def get_queryset(self):
        teams = TeamLog.objects.values_list('team', flat=True).distinct()

        latest_logs = TeamLog.objects.none()
        for team in teams:
            team_logs = TeamLog.objects.filter(team=team).order_by('-timestamp')[:100]
            latest_logs = latest_logs | team_logs

        return latest_logs


class ActiveImportCriteriaView(APIView):
    def get(self, request, *args, **kwargs):
        active_criteria = ImportCriteria.objects.filter(is_active=True).first()

        serializer = ImportCriteriaSerializer(active_criteria)
        return Response(serializer.data)


class GroupedImportTankView(APIView):
    def get(self, request):
        imports = ImportTank.objects.all().order_by('available_from')

        grouped_imports = {}
        for import_tank in imports:
            date_key = import_tank.available_from.date()
            if date_key not in grouped_imports:
                grouped_imports[date_key] = {
                    'criteria': import_tank.criteria,
                    'tanks': []
                }
            grouped_imports[date_key]['tanks'].append(import_tank)
        response_data = {
            str(date): {
                'criteria': ImportCriteriaSerializer(grouped_imports[date]['criteria']).data,
                'tanks': ImportTankSerializer(grouped_imports[date]['tanks'], many=True).data
            }
            for date in grouped_imports
        }

        return Response(response_data)


class PurchaseImportTankView(APIView):
    def post(self, request):
        user = request.user
        team_name = user.team.name
        if not (
            user.has_perm('user.admin_permissions') or
            (user.has_perm('user.commander_permissions'))
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        import_id = request.data.get('import_id', None)
        team = Team.objects.get(name=team_name)

        if import_id is not None:
            tank = ImportTank.objects.get(pk=import_id)
            tank.purchase_from_imports(team)
            return Response(data={'new_balance': team.balance, 'new_tanks': [tank.tank.name]}, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_400_BAD_REQUEST)