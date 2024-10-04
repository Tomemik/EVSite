from django.shortcuts import render, get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.mixins import PermissionRequiredMixin

from .models import Team, Manufacturer, Tank, Match, MatchResult, TankBox, TeamMatch
from .serializers import TeamSerializer, ManufacturerSerializer, TankSerializer, MatchSerializer, SlimMatchSerializer, \
    MatchResultSerializer, TankBoxSerializer, TankBoxCreateSerializer, SlimTeamSerializer, TeamMatchSerializer


class AllTeamsView(APIView):
    def get(self, request):
        teams = Team.objects.all()
        serializer = SlimTeamSerializer(teams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if not request.user.has_perm('admin_permissions'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = TeamSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
        print(serializer.errors)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TeamDetailView(APIView):
    def get(self, request, name):
        team = Team.objects.get(name=name)
        serializer = TeamSerializer(team)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, name):
        if not request.user.has_perm('admin_permissions'):
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
        if not request.user.has_perm('admin_permissions'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = TankSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        if not request.user.has_perm('admin_permissions'):
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
        print(request.user)
        if not request.user.has_perm('admin_permissions'):
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
        if not user.has_perm('admin_permissions'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        elif not user.has_perm('commander_permissions'):
            user_team_name = user.team.name if user.team else None
            if not team_name == user_team_name:
                return Response(status=status.HTTP_403_FORBIDDEN)
        tanks = request.data.get('tanks', [])
        team = Team.objects.get(name=team_name)
        for tank in tanks:
            tank = Tank.objects.get(name=tank)
            team.purchase_tank(tank)
        return Response(status=status.HTTP_200_OK)


class SellTankView(APIView):
    def post(self, request):
        user = request.user
        team_name = request.data['team']
        if not user.has_perm('admin_permissions'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        elif not user.has_perm('commander_permissions'):
            user_team_name = user.team.name if user.team else None
            if not team_name == user_team_name:
                return Response(status=status.HTTP_403_FORBIDDEN)
        tanks = request.data.get('tanks', [])
        team = Team.objects.get(name=team_name)
        for tank in tanks:
            tank = Tank.objects.get(name=tank['name'])
            team.sell_tank(tank)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AllUpgradesView(APIView):
    def get(self, request):
        team_name = request.headers['team']
        tank = request.headers['tank']
        team = Team.objects.get(name=team_name)
        tank = Tank.objects.get(name=tank)

        all_upgrades = team.get_possible_upgrades(tank)

        return Response(all_upgrades, status=status.HTTP_200_OK)


class UpgradeTankView(APIView):
    def post(self, request):
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

        return Response(all_upgrades, status=status.HTTP_200_OK)


class ManufacturerDetailView(APIView):
    def get(self, request, pk):
        manufacturer = Manufacturer.objects.get(pk=pk)
        serializer = ManufacturerSerializer(manufacturer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        if not request.user.has_perm('admin_permissions'):
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
        if not request.user.has_perm('admin_permissions'):
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
        if not request.user.has_perm('admin_permissions'):
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
        if not any([user.has_perm('admin_permissions'), user.has_perm('commander_permissions')]):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = MatchSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
        print(serializer.errors)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


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


class MatchView(APIView):
    def get(self, request, pk):
        match = Match.objects.get(pk=pk)
        serializer = MatchSerializer(match)
        print(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        user = request.user
        if not any([user.has_perm('admin_permissions'), user.has_perm('commander_permissions'), user.has_perm('judge_permissions')]):
            return Response(status=status.HTTP_403_FORBIDDEN)
        match = Match.objects.get(pk=pk)
        serializer = MatchSerializer(match, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
        print(serializer.errors)
        return Response(serializer.data, status=status.HTTP_200_OK)

class MatchResultsView(APIView):
    def get(self, request, pk):
        match = Match.objects.get(pk=pk)
        matchResult = MatchResult.objects.get(match__pk=pk)
        serializer = MatchResultSerializer(matchResult)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, pk):
        user = request.user
        print(user)
        if not any([user.has_perm('admin_permissions'), user.has_perm('judge_permissions')]):
            return Response(status=status.HTTP_403_FORBIDDEN)
        elif not user.has_perm('commander_permissions'):
            team_matches = request.data.get('teammatch_set', [])
            user_team_name = user_team.name if user_team else None
            team_found = any(match['team'] == user_team_name for match in team_matches)
            if not team_found:
                return Response(status=status.HTTP_403_FORBIDDEN)

        match = Match.objects.get(pk=pk)
        serializer = MatchResultSerializer(data=request.data)
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
        if not any([user.has_perm('admin_permissions'), user.has_perm('judge_permissions')]):
            return Response(status=status.HTTP_403_FORBIDDEN)
        elif not user.has_perm('commander_permissions'):
            team_matches = request.data.get('teammatch_set', [])
            user_team_name = user.team.name if user.team else None
            team_found = any(match['team'] == user_team_name for match in team_matches)
            if not team_found:
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
    def get(self, request, pk):
        matchResult = MatchResult.objects.get(match__pk=pk)
        if not matchResult.is_calced:
            matchResult.calculate_rewards()
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
