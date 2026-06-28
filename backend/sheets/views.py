import copy
import json
import math
import os
import re
import tempfile
from collections import deque, defaultdict
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.shortcuts import render, get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from django.contrib.auth.mixins import PermissionRequiredMixin
import requests
from django.db.models import F, Window
from django.db.models.functions import RowNumber

from .discord import format_match_message, format_match_result_message, format_match_calc_message, send_transaction_log
from .filters import TeamLogFilter, MatchFilter
from .models import Team, Manufacturer, Tank, Match, MatchResult, TankBox, TeamMatch, TeamLog, ImportTank, \
    ImportCriteria, TeamBox, TeamTank, UpgradePath, get_upgrade_tree, UpgradeTree, InterchangeGroup, \
    get_interchange_graph, Interchange, Alliance, MatchKill, MatchRound, ReplayFile, MatchCrit
from .serializers import TeamSerializer, ManufacturerSerializer, TankSerializer, MatchSerializer, SlimMatchSerializer, \
    MatchResultSerializer, TankBoxSerializer, TankBoxCreateSerializer, SlimTeamSerializer, TeamMatchSerializer, \
    TeamLogSerializer, SlimTeamSerializerWithTanks, ImportTankSerializer, ImportCriteriaSerializer, \
    UpgradePathSerializer, UpgradeTreeSerializer, InterchangeGroupSerializer, InterchangeSerializer, AllianceSerializer, \
    MatchRoundSerializer, VerifyRoundPayloadSerializer, MatchKillSerializer
from .services.replay_parser import execute_safe_worker
from .services.stats import StatsService

MAPS_DIR = Path(__file__).resolve().parent.parent / '_vendor' / 'maps'

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
            team.add_tank_boxes(tank_box_ids, box_amounts, user=request.user)
        if upgrade_kit and kit_amount:
            team.add_upgrade_kit(upgrade_kit, kit_amount, user=request.user)
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

        try:
            team = Team.objects.get(name=team_name)
            initial_balance = team.balance

            purchased_names = []
            for tank_name in tanks:
                tank = Tank.objects.get(name=tank_name)
                team.purchase_tank(tank, user=request.user)
                purchased_names.append(tank.name)

            team.refresh_from_db()
            cost = initial_balance - team.balance

            if cost > 0:
                details = f"**Purchased {len(purchased_names)} Tank(s):**\n" + ", ".join(purchased_names)
                send_transaction_log(team.name, 'Purchase', details, cost, team.balance)

            return Response(
                data={'new_balance': team.balance, 'new_tanks': tanks},
                status=status.HTTP_200_OK
            )

        except ValidationError as e:
            error_msg = e.detail[0] if hasattr(e, 'detail') and isinstance(e.detail, list) else str(e)
            return Response({'error': str(error_msg)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


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

        try:
            team = Team.objects.get(name=team_name)
            initial_balance = team.balance
            sold_names = []

            for tank_id in tanks:
                t = TeamTank.objects.get(pk=tank_id)
                sold_names.append(t.tank.name)
                team.sell_teamtank(t, user=request.user)

            # Calculate gain and log
            team.refresh_from_db()
            gain = team.balance - initial_balance  # Positive number

            if gain > 0:
                details = f"**Sold {len(sold_names)} Tank(s):**\n" + ", ".join(sold_names)
                # Pass negative amount to indicate gain in our helper
                send_transaction_log(team.name, 'Sale', details, -gain, team.balance)

            return Response(
                data={'new_balance': team.balance, 'sold_tanks': sold_names},
                status=status.HTTP_200_OK
            )

        except ValidationError as e:
            error_msg = e.detail[0] if hasattr(e, 'detail') and isinstance(e.detail, list) else str(e)
            return Response({'error': str(error_msg)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class SellTanksView(APIView):
    def post(self, request):
        user = request.user
        team_name = request.data['team']
        if not (
            user.has_perm('user.admin_permissions') or
            (user.has_perm('user.commander_permissions') and user.team and user.team.name == team_name)
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            tanks = request.data.get('tanks', [])
            team = Team.objects.get(name=team_name)
            initial_balance = team.balance
            sold_summary = []

            for tank in tanks:
                for i in range(tank['quantity']):
                    tanka = Tank.objects.get(name=tank['name'])
                    team.sell_tank(tanka, user=request.user)
                sold_summary.append(f"{tank['quantity']}x {tank['name']}")

            team.refresh_from_db()
            gain = team.balance - initial_balance

            if gain > 0:
                details = "**Bulk Sale:**\n" + "\n".join(sold_summary)
                send_transaction_log(team.name, 'Sale', details, -gain, team.balance)
            return Response(data={'new_balance': team.balance, 'sold_tanks': [tank for tank in tanks]}, status=status.HTTP_200_OK)
        except ValidationError as e:
            error_msg = e.detail[0] if hasattr(e, 'detail') and isinstance(e.detail, list) else str(e)
            return Response({'error': str(error_msg)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class TransferMoneyView(APIView):
    def post(self, request):
        user = request.user
        team_name = request.data['team']
        if not (
            user.has_perm('user.admin_permissions') or
            (user.has_perm('user.commander_permissions') and user.team and user.team.name == team_name)
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        to_team_name = request.data['to_team']
        amount = request.data['amount']

        from_team = Team.objects.get(name=team_name)
        to_team = Team.objects.get(name=to_team_name)
        from_team.money_transfer(from_team, to_team, amount, request.user)
        return Response(data={'new_balance': from_team.balance}, status=status.HTTP_200_OK)


class AllianceTransferKitView(APIView):
    def post(self, request):
        user = request.user
        team_name = request.data.get('team')

        if not (
                user.has_perm('user.admin_permissions') or
                (user.has_perm('user.commander_permissions') and user.team and user.team.name == team_name)
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        target_team_name = request.data.get('target_team')
        amount = request.data.get('amount', 1)

        try:
            sender = Team.objects.get(name=team_name)
            receiver = Team.objects.get(name=target_team_name)

            sender.transfer_alliance_kit(receiver, amount, user.username)

            return Response({
                'status': 'success',
                'new_balance': sender.upgrade_kits
            }, status=status.HTTP_200_OK)

        except Team.DoesNotExist:
            return Response({'error': 'Team not found'}, status=status.HTTP_404_NOT_FOUND)

        except ValidationError as e:
            if hasattr(e, 'detail'):
                if isinstance(e.detail, list) and e.detail:
                    error_msg = str(e.detail[0])
                elif isinstance(e.detail, dict) and e.detail:
                    key = next(iter(e.detail))
                    val = e.detail[key]
                    error_msg = str(val[0]) if isinstance(val, list) else str(val)
                else:
                    error_msg = str(e.detail)
            else:
                error_msg = str(e)

            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


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

        try:
            team = Team.objects.get(name=team_name)
            team.split_merge_kit(action=action, kit_type=kit_type, kit_amount=kit_amount)
            return Response(status=status.HTTP_200_OK)

        except ValidationError as e:
            error_msg = e.detail[0] if hasattr(e, 'detail') and isinstance(e.detail, list) else str(e)
            return Response({'error': str(error_msg)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AllUpgradesView(APIView):
    def get(self, request):
        team_name = request.headers['team']
        tank = request.headers['tank']
        team = Team.objects.get(name=team_name)
        tank = TeamTank.objects.get(pk=tank)

        all_upgrades = team.get_possible_upgrades(tank)

        return Response(all_upgrades, status=status.HTTP_200_OK)


class UpgradeTreeView(APIView):
    def get(self, request):
        tank = request.headers['tank']
        all_upgrades = get_upgrade_tree(start_tank_name=tank)
        serializer = UpgradePathSerializer(all_upgrades, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AllDirectUpgradesView(APIView):
    def get(self, request):
        team_name = request.headers['team']
        tank = request.headers['tank']
        team = Team.objects.get(name=team_name)
        tank = TeamTank.objects.get(pk=tank)

        all_upgrades = team.get_direct_upgrades(tank)

        return Response(all_upgrades, status=status.HTTP_200_OK)


class DirectUpgradeTankView(APIView):
    def post(self, request):
        user = request.user
        team_name = request.data.get('team', None)
        if not (
                user.has_perm('user.admin_permissions') or
                (user.has_perm('user.commander_permissions') and user.team and user.team.name == team_name)
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        team_name = request.data.get('team', None)
        from_tank_id = request.data.get('from_tank', None)
        to_tank_name = request.data.get('to_tank', None)
        kits = request.data.get('kits', [])

        try:
            team = Team.objects.get(name=team_name)
            initial_balance = team.balance
            # Capture initial kit state
            initial_kits = copy.deepcopy(team.upgrade_kits)

            from_tank = TeamTank.objects.get(id=from_tank_id)
            from_tank_name = from_tank.tank.name
            to_tank = Tank.objects.get(name=to_tank_name)

            extra_kits = []
            for key, val in kits.items():
                if val > 0:
                    if key == 'T1': extra_kits += ['T1'] * val
                    if key == 'T2': extra_kits += ['T2'] * val
                    if key == 'T3': extra_kits += ['T3'] * val

            team.do_direct_upgrade(from_tank, to_tank, extra_kits, user=request.user)

            team.refresh_from_db()
            cost = initial_balance - team.balance

            used_kits_summary = []
            for tier in ['T1', 'T2', 'T3']:
                start_qty = int(initial_kits.get(tier, {}).get('quantity', 0))
                end_qty = int(team.upgrade_kits.get(tier, {}).get('quantity', 0))
                diff = start_qty - end_qty

                if diff > 0:
                    used_kits_summary.append(f"{diff}x {tier}")

            details = f"**{from_tank_name}** ➡ **{to_tank.name}**"
            if used_kits_summary:
                details += f"\nKits Used: {', '.join(used_kits_summary)}"

            send_transaction_log(team.name, 'Upgrade', details, cost, team.balance)

            return Response(data={'new_balance': team.balance, 'new_kits': team.upgrade_kits},
                            status=status.HTTP_200_OK)

        except ValidationError as e:
            error_msg = e.detail[0] if hasattr(e, 'detail') and isinstance(e.detail, list) else str(e)
            return Response({'error': str(error_msg)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UpgradeTankView(APIView):
    def post(self, request):
        user = request.user
        team_name = request.data.get('team', None)
        if not (
                user.has_perm('user.admin_permissions') or
                (user.has_perm('user.commander_permissions') and user.team and user.team.name == team_name)
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        team_name = request.data.get('team', None)
        from_tank_id = request.data.get('from_tank', None)
        to_tank_name = request.data.get('to_tank', None)
        kits = request.data.get('kits', [])

        try:
            team = Team.objects.get(name=team_name)
            initial_balance = team.balance
            # Capture initial kit state to compare later
            initial_kits = copy.deepcopy(team.upgrade_kits)

            from_tank = TeamTank.objects.get(id=from_tank_id)
            from_tank_name = from_tank.tank.name
            to_tank = Tank.objects.get(name=to_tank_name)

            extra_kits = []
            for key, val in kits.items():
                if val > 0:
                    if key == 'T1': extra_kits += ['T1'] * val
                    if key == 'T2': extra_kits += ['T2'] * val
                    if key == 'T3': extra_kits += ['T3'] * val

            team.upgrade_or_downgrade_tank(from_tank, to_tank, extra_kits, user=request.user)

            team.refresh_from_db()
            cost = initial_balance - team.balance

            used_kits_summary = []
            for tier in ['T1', 'T2', 'T3']:
                start_qty = int(initial_kits.get(tier, {}).get('quantity', 0))
                end_qty = int(team.upgrade_kits.get(tier, {}).get('quantity', 0))
                diff = start_qty - end_qty

                if diff > 0:
                    used_kits_summary.append(f"{diff}x {tier}")

            details = f"**{from_tank_name}** ➡ **{to_tank.name}**"
            if used_kits_summary:
                details += f"\nKits Used: {', '.join(used_kits_summary)}"

            send_transaction_log(team.name, 'Upgrade', details, cost, team.balance)

            return Response(data={'new_balance': team.balance, 'new_kits': team.upgrade_kits},
                            status=status.HTTP_200_OK)

        except ValidationError as e:
            error_msg = e.detail[0] if hasattr(e, 'detail') and isinstance(e.detail, list) else str(e)
            return Response({'error': str(error_msg)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PurchaseBoxView(APIView):
    def post(self, request):
        user = request.user
        team_name = request.data['team']
        if not (
            user.has_perm('user.admin_permissions') or
            (user.has_perm('user.commander_permissions') and user.team and user.team.name == team_name)
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        box_id = request.data.get('box_id', None)
        team = Team.objects.get(name=team_name)
        if box_id is not None:
            box = TankBox.objects.get(id=box_id)
            result = box.purchase(team, request.user)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(data=result, status=status.HTTP_200_OK)


class PurchaseAndOpenBoxView(APIView):
    def post(self, request):
        user = request.user
        team_name = request.data['team']
        if not (
                user.has_perm('user.admin_permissions') or
                (user.has_perm('user.commander_permissions') and user.team and user.team.name == team_name)
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        box_id = request.data.get('box_id', None)
        if box_id is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            team = Team.objects.get(name=team_name)
            initial_balance = team.balance

            # 1. Purchase the box template (TankBox)
            tank_box = TankBox.objects.get(id=box_id)
            result = tank_box.purchase(team, request.user)

            # 2. Get the newly generated inventory box (TeamBox) and open it
            new_team_box = TeamBox.objects.get(id=result['id'])
            result_tank_name = new_team_box.open_box(request.user)

            # 3. Refresh team to calculate the cost dynamically
            team.refresh_from_db()
            cost = initial_balance - team.balance

            # 4. Log to Discord (tank_box has .name, NOT .box.name)
            details = f"Bought & Opened **{tank_box.name} (Tier {tank_box.tier})**\nObtained: **{result_tank_name}**"
            send_transaction_log(team.name, 'Lootbox', details, cost, team.balance)

            # Return the resulting tank name back to Vue for the alert popup
            return Response(data=result_tank_name, status=status.HTTP_200_OK)

        except Exception as e:
            # Catch errors so the frontend gets a readable message instead of crashing
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OpenBoxView(APIView):
    def post(self, request):
        # ... [Permissions Check] ...
        user = request.user
        team_name = request.data['team']
        if not (
                user.has_perm('user.admin_permissions') or
                (user.has_perm('user.commander_permissions') and user.team and user.team.name == team_name)
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        box_id = request.data.get('box_id', None)

        try:
            team = Team.objects.get(name=team_name)
            if box_id is not None:
                box = TeamBox.objects.get(id=box_id)
                box_name = box.box.name
                box_tier = box.box.tier

                result_tank_name = box.open_box(request.user)

                team.refresh_from_db()
                details = f"Opened **{box_name} (Tier {box_tier})**\nObtained: **{result_tank_name}**"
                send_transaction_log(team.name, 'Lootbox', details, 0, team.balance)

                return Response(data=result_tank_name, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


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
            match = serializer.save()

            self.send_discord_notification(match)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(
                {"detail": e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )

    def send_discord_notification(self, match):
        webhook_url = settings.DISCORD_WEBHOOK_URL_SCHEDULE + '?wait=true'
        if not webhook_url:
            return

        message = format_match_message(match)

        try:
            response = requests.post(webhook_url, json={"content": message})
            response_data = response.json()
            match.webhook_id_schedule = response_data.get("id")
            match.channel_id_schedule = response_data.get("channel_id")
            match.save()

        except Exception as e:
            print(f"Error sending Discord webhook: {e}")


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

            self.edit_discord_notification(match)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(
                {"detail": e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )

    def delete(self, request, pk):
        user = request.user
        if not any([user.has_perm('user.admin_permissions'), user.has_perm('user.commander_permissions'), user.has_perm('user.judge_permissions')]):
            return Response(status=status.HTTP_403_FORBIDDEN)

        match = Match.objects.get(pk=pk)

        self.delete_discord_notification(match)

        match.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def edit_discord_notification(self, match):
        webhook_url = settings.DISCORD_WEBHOOK_URL_SCHEDULE
        if not webhook_url or not match.webhook_id_schedule:
            return

        message_url = f"{webhook_url}/messages/{match.webhook_id_schedule}"
        message = format_match_message(match)

        try:
            response = requests.patch(message_url, json={"content": message})
            if response.status_code not in [200, 204]:
                print(f"Error editing Discord webhook: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error editing Discord webhook: {e}")

    def delete_discord_notification(self, match):

        webhook_url = settings.DISCORD_WEBHOOK_URL_SCHEDULE
        if not webhook_url or not match.webhook_id_schedule:
            return

        message_url = f"{webhook_url}/messages/{match.webhook_id_schedule}"

        try:
            response = requests.delete(message_url)
            if response.status_code not in [200, 204]:
                print(f"Error deleting Discord webhook: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error deleting Discord webhook: {e}")


class MatchResultsView(APIView):
    def get(self, request, pk):
        try:
            # Attempt to fetch the result
            matchResult = MatchResult.objects.get(match__pk=pk)
            serializer = MatchResultSerializer(matchResult)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except MatchResult.DoesNotExist:
            # If no result exists yet (new match), return a clean 404 instead of a 500 crash
            return Response({"detail": "Match result not found."}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, pk):
        user = request.user
        if not any([user.has_perm('user.admin_permissions'), user.has_perm('user.judge_permissions')]):
            if user.has_perm('user.commander_permissions'):
                team_matches = request.data.get('team_results', [])
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
            if match.webhook_id_result:
                self.edit_discord_notification(match)
            else:
                self.send_discord_notification(match)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
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
            self.edit_discord_notification(match)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def send_discord_notification(self, match):
        webhook_url = settings.DISCORD_WEBHOOK_URL_RESULT + '?wait=true'
        if not webhook_url:
            return

        message = format_match_result_message(match)

        try:
            response = requests.post(webhook_url, json={"content": message})
            response_data = response.json()
            match.webhook_id_result = response_data.get("id")
            match.channel_id_result = response_data.get("channel_id")
            match.save()

        except Exception as e:
            print(f"Error sending Discord webhook: {e}")


    def edit_discord_notification(self, match):
        webhook_url = settings.DISCORD_WEBHOOK_URL_RESULT
        if not webhook_url or not match.webhook_id_result:
            return

        message_url = f"{webhook_url}/messages/{match.webhook_id_result}"
        message = format_match_result_message(match)

        try:
            response = requests.patch(message_url, json={"content": message})
            if response.status_code not in [200, 204]:
                print(f"Error editing Discord webhook: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error editing Discord webhook: {e}")

class CalcTestView(APIView):
    def post(self, request, pk):
        user = request.user
        if not any([user.has_perm('user.admin_permissions'), user.has_perm('user.judge_permissions'), user.has_perm('user.commander_permissions')]):
            return Response(status=status.HTTP_403_FORBIDDEN)
        match_result = MatchResult.objects.get(match__pk=pk)
        if not match_result.is_calced:
            rewards = match_result.calculate_rewards(request.user)
            try:
                if match_result.match.webhook_id_calc:
                    self.edit_discord_notification(match_result.match, rewards)
                else:
                    self.send_discord_notification(match_result.match, rewards)
            except Exception as e:
                pass
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    def send_discord_notification(self, match, rewards):
        webhook_url = settings.DISCORD_WEBHOOK_URL_CALC + '?wait=true'
        if not webhook_url:
            return

        message = format_match_calc_message(match, rewards)

        try:
            response = requests.post(webhook_url, json={"content": message})
            response_data = response.json()
            match.webhook_id_calc = response_data.get("id")
            match.channel_id_calc = response_data.get("channel_id")
            match.save()

        except Exception as e:
            print(f"Error sending Discord webhook: {e}")


    def edit_discord_notification(self, match, rewards):
        webhook_url = settings.DISCORD_WEBHOOK_URL_CALC
        if not webhook_url or not match.webhook_id_calc:
            return

        message_url = f"{webhook_url}/messages/{match.webhook_id_calc}"
        message = format_match_calc_message(match, rewards)

        try:
            response = requests.patch(message_url, json={"content": message})
            if response.status_code not in [200, 204]:
                print(f"Error editing Discord webhook: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error editing Discord webhook: {e}")


class CalcRevertView(APIView):
    def post(self, request, pk):
        user = request.user
        if not any([user.has_perm('user.admin_permissions'), user.has_perm('user.judge_permissions'), user.has_perm('user.commander_permissions')]):
            return Response(status=status.HTTP_403_FORBIDDEN)
        match_result = MatchResult.objects.get(match__pk=pk)
        if match_result.is_calced:
            match_result.revert_rewards()
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

class TeamLogFilteredView(ListAPIView):
    queryset = TeamLog.objects.all()
    serializer_class = TeamLogSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TeamLogFilter

    def get_queryset(self):
        return TeamLog.objects.annotate(
            row_number=Window(
                expression=RowNumber(),
                partition_by=[F('team')],
                order_by=F('timestamp').desc()
            )
        ).filter(row_number__lte=100)


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

        try:
            team = Team.objects.get(name=team_name)
            initial_balance = team.balance

            if import_id is not None:
                tank = ImportTank.objects.get(pk=import_id)
                tank_name = tank.tank.name

                tank.purchase_from_imports(team, request.user)

                team.refresh_from_db()
                cost = initial_balance - team.balance

                details = f"Imported **{tank_name}**"
                send_transaction_log(team.name, 'Import', details, cost, team.balance)

                return Response(data={'new_balance': team.balance, 'new_tanks': [tank.tank.name]},
                                status=status.HTTP_200_OK)
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            error_msg = e.detail[0] if hasattr(e, 'detail') and isinstance(e.detail, list) else str(e)
            return Response({'error': str(error_msg)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UpgradeTreeListView(APIView):
    def get(self, request):
        trees = UpgradeTree.objects.all()
        serializer = UpgradeTreeSerializer(trees, many=True)
        return Response(serializer.data)


class InterchangeListView(APIView):
    def get(self, request):
        groups = InterchangeGroup.objects.all()
        serializer = InterchangeGroupSerializer(groups, many=True)
        return Response(serializer.data)


class InterchangeDetailView(APIView):
    def get(self, request):
        tank_name = request.headers.get('tank')

        if tank_name:
            graph_edges = get_interchange_graph(start_tank_name=tank_name)
        else:
            graph_edges = Interchange.objects.all()

        serializer = InterchangeSerializer(graph_edges, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AllianceListView(APIView):
    def get(self, request):
        alliances = Alliance.objects.all()
        serializer = AllianceSerializer(alliances, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


def sanitize_filename(name):
    """Replaces spaces and invalid filesystem characters with underscores."""
    return re.sub(r'(?u)[^-\w.]', '_', name.strip())


class UploadReplayRoundView(APIView):
    def post(self, request, pk):
        user = request.user
        if not any([user.has_perm('user.admin_permissions'), user.has_perm('user.judge_permissions')]):
            return Response(status=status.HTTP_403_FORBIDDEN)

        round_number = request.data.get('round_number')
        start_time_str = request.data.get('start_time', '5:00')
        replay_files = request.FILES.getlist('replay_files')

        if not round_number or not replay_files:
            return Response({"error": "round_number and at least one replay_file are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        match = get_object_or_404(Match, id=pk)
        match_round, created = MatchRound.objects.get_or_create(match=match, round_number=int(round_number))

        try:
            parts = str(start_time_str).split(':')
            if len(parts) == 2:
                start_s = int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 1:
                start_s = int(parts[0])
            else:
                start_s = 300
        except ValueError:
            start_s = 300

        match_round.start_time_s = start_s

        # --- FILENAME GENERATION ---
        team_1_names = [sanitize_filename(tm.team.name) for tm in match.teammatch_set.filter(side='team_1')]
        team_2_names = [sanitize_filename(tm.team.name) for tm in match.teammatch_set.filter(side='team_2')]

        t1_str = "_".join(team_1_names) if team_1_names else "Team1"
        t2_str = "_".join(team_2_names) if team_2_names else "Team2"
        date_str = match.datetime.strftime("%Y-%m-%d")

        base_filename = f"{t1_str}_vs_{t2_str}_{date_str}_round_{round_number}"
        existing_file_count = match_round.replay_files.count()
        saved_file_paths = []

        for idx, f_obj in enumerate(replay_files, start=1):
            part_number = existing_file_count + idx
            new_name = f"{base_filename}_part_{part_number}.wrpl"
            f_obj.name = new_name

            replay_record = ReplayFile.objects.create(match_round=match_round, file=f_obj)
            saved_file_paths.append(replay_record.file.path)

        # Parse files
        res = execute_safe_worker(saved_file_paths, start_time_str=start_time_str)
        if res["status"] != "success":
            return Response({"error": res["error"]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        data = res["data"]

        match_round.map_areas = data.get("areas", [])
        match_round.capture_zones = data.get("zones", [])
        raw_chat = data.get("chat", {})
        match_round.chat_log = sorted(list(raw_chat.values()), key=lambda x: x["time"])

        # --- MULTI-VARIANT RESOLUTION GRAPH ---
        internal_id_to_tanks = defaultdict(list)
        for tank in Tank.objects.all():
            for int_id in tank.internal_ids:
                internal_id_to_tanks[int_id].append(tank.name)

        adj = defaultdict(list)
        for edge in Interchange.objects.all():
            adj[edge.from_tank.name].append(edge.to_tank.name)
            if edge.is_bidirectional:
                adj[edge.to_tank.name].append(edge.from_tank.name)

        team_1_allowed = set(tt.tank.name for tm in match.teammatch_set.filter(side='team_1') for tt in tm.tanks.all())
        team_2_allowed = set(tt.tank.name for tm in match.teammatch_set.filter(side='team_2') for tt in tm.tanks.all())

        def resolve_vehicle(parsed_name, allowed_names):
            if parsed_name in allowed_names:
                return parsed_name
            start_names = internal_id_to_tanks.get(parsed_name, [parsed_name])
            for name in start_names:
                if name in allowed_names:
                    return name
            queue = deque(start_names)
            visited = set(start_names)
            while queue:
                curr = queue.popleft()
                if curr in allowed_names:
                    return curr
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            return start_names[0]

        # --- PROCESS METADATA & FILTERING ---
        if not match_round.map_name or match_round.map_name == "unknown":
            match_round.map_name = data.get("map_context", {}).get("level_name", "unknown")

        raw_level_name = data.get("map_context", {}).get("level_name", "unknown")
        postfix = data.get("map_context", {}).get("postfix", "")
        loc_name = data.get("map_context", {}).get("loc_name", "")

        # --- MAP VARIANT ALIASING ---
        # Intercept _02 locNames and remap the internal .bin name to the correct JSON file
        if "_02" in loc_name:
            map_aliases = {
                "avg_egypt_sinai": "avg_sands_of_sinai",
                "avg_poland": "avg_fields_of_poland",
                "avg_poland_snow": "avg_fields_of_poland_snow",
                "avg_normandy": "avg_fields_of_normandy",
                "avg_eastern_europe": "avg_european_province",
                "avg_volokolamsk": "avg_surroundings_of_volokolamsk",
                "avg_arctic": "avg_arctic_02"
            }
            # Swap the raw_level_name to target the correct JSON
            raw_level_name = map_aliases.get(raw_level_name, f"{raw_level_name}_02")

        if "_01" in loc_name:
            map_aliases = {
                "avg_arctic": "avg_arctic_01"
            }
            # Swap the raw_level_name to target the correct JSON
            raw_level_name = map_aliases.get(raw_level_name, f"{raw_level_name}_01")

        map_details = {
            "internal_name": raw_level_name,
            "postfix": postfix,
            "mode": "Unknown",
        }
        human_map_name = raw_level_name

        if raw_level_name != "unknown":
            map_json_path = MAPS_DIR / f"{raw_level_name}.json"
            if map_json_path.exists():
                try:
                    import json
                    with open(map_json_path, 'r', encoding='utf-8') as f:
                        map_info = json.load(f)
                        human_map_name = map_info.get("map_name", raw_level_name)

                        variant_data = map_info.get("variants", {}).get(postfix, {})
                        map_details.update({
                            "human_name": human_map_name,
                            "texture": map_info.get("texture", ""),
                            "variant_data": variant_data,
                            "mode": variant_data.get("mode", "Unknown")
                        })
                except Exception as e:
                    print(f"Error loading map JSON for {raw_level_name}: {e}")

        match_round.map_name = human_map_name
        match_round.map_details = map_details

        current_rosters = match_round.team_rosters

        # 1. Map who actually spawned a valid vehicle
        spawned_players = set()
        for p_name, vehicles in data.get("spawns", {}).items():
            if p_name.lower() != "unknown" and vehicles:
                if vehicles[-1].lower() != "unknown":
                    spawned_players.add(p_name)

        # 2. Filter Rosters: Only append if they actually spawned
        for team_id, players in data.get("teams", {}).items():
            if str(team_id) not in current_rosters:
                current_rosters[str(team_id)] = []
            for p in players:
                if p in spawned_players and p not in current_rosters[str(team_id)]:
                    current_rosters[str(team_id)].append(p)

        match_round.team_rosters = current_rosters

        formatted_spawns = {"team_1": [], "team_2": []}
        team_1_roster = current_rosters.get("1", []) + current_rosters.get("team_1", [])
        team_2_roster = current_rosters.get("2", []) + current_rosters.get("team_2", [])

        # --- PROCESS SPAWNS WITH RESOLVER ---
        player_to_resolved_veh = {}
        player_to_side = {}

        for p_name, vehicles in data.get("spawns", {}).items():
            if p_name not in spawned_players:
                continue

            v_name = vehicles[-1]

            # Determine side and resolve vehicle
            if p_name in team_2_roster:
                resolved_veh = resolve_vehicle(v_name, team_2_allowed)
                formatted_spawns["team_2"].append({"player": p_name, "vehicle": resolved_veh})
                side = 'team_2'
            else:
                resolved_veh = resolve_vehicle(v_name, team_1_allowed)
                formatted_spawns["team_1"].append({"player": p_name, "vehicle": resolved_veh})
                side = 'team_1'

            # Clean name for robust dictionary matching (lowercase & stripped)
            clean_name = p_name.strip().lower()
            player_to_resolved_veh[clean_name] = resolved_veh
            player_to_side[clean_name] = side

        match_round.player_spawns = formatted_spawns

        # Process Telemetry
        current_telemetry = match_round.telemetry_data

        for p_name, veh_data in data.get("movement", {}).items():
            clean_name = p_name.strip().lower()

            # 1. Filter: Only process players who were confirmed to have spawned
            if clean_name not in player_to_resolved_veh:
                continue

            # 2. Identify the target vehicle this player actually spawned (Ground Truth)
            target_veh = player_to_resolved_veh[clean_name]

            # Determine side for resolution context
            side = player_to_side.get(clean_name, 'team_1')
            allowed_names = team_1_allowed if side == 'team_1' else team_2_allowed

            if p_name not in current_telemetry:
                current_telemetry[p_name] = {}

            # 3. Process each vehicle in telemetry
            for v_name, points in veh_data.items():
                # Map the telemetry vehicle name to DB name
                resolved_veh = resolve_vehicle(v_name, allowed_names)

                # Filter: Only keep telemetry if it matches the player's actual spawn vehicle
                if resolved_veh == target_veh:
                    current_telemetry[p_name][resolved_veh] = points

        match_round.telemetry_data = current_telemetry

        # --- AUTO-CALCULATE ANNIHILATION ---
        team_1_players = set(p['player'] for p in formatted_spawns['team_1'])
        team_2_players = set(p['player'] for p in formatted_spawns['team_2'])
        team_1_deaths = set()
        team_2_deaths = set()

        for k in data.get("kills", []):
            victim = k["victim"]
            if victim in team_1_players:
                team_1_deaths.add(victim)
            elif victim in team_2_players:
                team_2_deaths.add(victim)

        if team_1_players and len(team_1_deaths) >= len(team_1_players):
            match_round.winning_team = 'team_2'
            match_round.win_reason = 'Annihilation'
        elif team_2_players and len(team_2_deaths) >= len(team_2_players):
            match_round.winning_team = 'team_1'
            match_round.win_reason = 'Annihilation'

        match_round.save()

        # --- PROCESS KILLS WITH FUZZY RESOLVER ---
        # Helper function to bypass clan tags and suffixes if a direct match fails
        def fuzzy_lookup(mapping, raw_name, default_val):
            clean = raw_name.strip().lower()
            if clean in mapping: return mapping[clean]

            # Try removing Clan Tags (e.g., "[-XYZ-] playername" -> "playername")
            no_tag = re.sub(r'^\[.*?\]\s*|^=.*?=\s*', '', clean).strip()
            if no_tag in mapping: return mapping[no_tag]

            # Try removing platform suffixes (e.g., "playername@live" -> "playername")
            no_suffix = clean.split('@')[0].strip()
            if no_suffix in mapping: return mapping[no_suffix]

            return default_val

        # --- PROCESS CRITS WITH FUZZY RESOLVER ---
        resolved_crits = []
        crit_data = data.get("crits", [])

        # If your worker returns a dict (instead of a list), use .values()
        if isinstance(crit_data, dict):
            crit_data = crit_data.values()

        for c in crit_data:
            # Now 'c' is the dictionary containing "attacker", "victim", etc.
            raw_atk = c.get("attacker")
            raw_vic = c.get("victim")

            # Guard for ghost entities
            if not raw_atk or not raw_vic or raw_atk.lower() == "unknown" or raw_vic.lower() == "unknown":
                continue

            # Fuzzy match side
            atk_side = fuzzy_lookup(player_to_side, raw_atk, 'team_1')
            vic_side = fuzzy_lookup(player_to_side, raw_vic, 'team_2')

            atk_allowed = team_1_allowed if atk_side == 'team_1' else team_2_allowed
            vic_allowed = team_1_allowed if vic_side == 'team_1' else team_2_allowed

            # Resolve Vehicles
            fallback_atk = resolve_vehicle(c["attacker_veh"], atk_allowed)
            fallback_vic = resolve_vehicle(c["victim_veh"], vic_allowed)

            final_atk_veh = fuzzy_lookup(player_to_resolved_veh, raw_atk, fallback_atk)
            final_vic_veh = fuzzy_lookup(player_to_resolved_veh, raw_vic, fallback_vic)

            resolved_crits.append(MatchCrit(
                match_round=match_round,
                time_s=c["time"],
                attacker=raw_atk,
                attacker_veh=final_atk_veh,
                victim=raw_vic,
                victim_veh=final_vic_veh,
                is_fire=c["is_fire"],
            ))

        MatchCrit.objects.bulk_create(resolved_crits, ignore_conflicts=True)

        resolved_kills = []
        for k in data.get("kills", []):
            raw_atk = k["attacker"]
            raw_vic = k["victim"]

            # Guard to drop bugged ghost entity kills
            if raw_atk.lower() == "unknown" or raw_vic.lower() == "unknown":
                continue

            # Fuzzy match side
            atk_side = fuzzy_lookup(player_to_side, raw_atk, 'team_1')
            vic_side = fuzzy_lookup(player_to_side, raw_vic, 'team_2')

            atk_allowed = team_1_allowed if atk_side == 'team_1' else team_2_allowed
            vic_allowed = team_1_allowed if vic_side == 'team_1' else team_2_allowed

            # Fuzzy match EXACT resolved spawn vehicle
            fallback_atk = resolve_vehicle(k["attacker_veh"], atk_allowed)
            fallback_vic = resolve_vehicle(k["victim_veh"], vic_allowed)

            final_atk_veh = fuzzy_lookup(player_to_resolved_veh, raw_atk, fallback_atk)
            final_vic_veh = fuzzy_lookup(player_to_resolved_veh, raw_vic, fallback_vic)

            resolved_kills.append(MatchKill(
                match_round=match_round,
                time_s=k["time"],
                attacker=raw_atk,
                attacker_veh=final_atk_veh,
                weapon=k["weapon"],
                victim=raw_vic,
                victim_veh=final_vic_veh
            ))

        MatchKill.objects.bulk_create(resolved_kills, ignore_conflicts=True)

        if resolved_kills:
            import math
            last_kill_time = max(k.time_s for k in resolved_kills)
            match_round.end_time_s = int(math.ceil(last_kill_time))
            match_round.save()

        serializer = MatchRoundSerializer(match_round)
        return Response({
            "message": f"Round {round_number} parsed. Merged and saved {len(saved_file_paths)} replays.",
            "saved_filenames": [os.path.basename(path) for path in saved_file_paths],
            "round_data": serializer.data
        }, status=status.HTTP_201_CREATED)


class VerifyRoundView(APIView):
    def post(self, request, pk, round_number):
        user = request.user
        if not any([user.has_perm('user.admin_permissions'), user.has_perm('user.judge_permissions')]):
            return Response(status=status.HTTP_403_FORBIDDEN)

        match_round = get_object_or_404(MatchRound, match_id=pk, round_number=round_number)

        serializer = VerifyRoundPayloadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": "Invalid payload format.", "details": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        corrected_kills = validated_data.get('kills', [])
        corrected_spawns = validated_data.get('spawns', {})

        # Extract the new fields
        winning_team = validated_data.get('winning_team')
        win_reason = validated_data.get('win_reason')

        with transaction.atomic():
            # 1. Update Spawns & Winner
            match_round.player_spawns = corrected_spawns
            match_round.winning_team = winning_team
            match_round.win_reason = win_reason
            match_round.is_verified = True
            match_round.save()

            # 2. Overwrite Kills (Safest way is to wipe and rewrite for this specific round)
            match_round.kills.all().delete()

            new_kill_objects = [
                MatchKill(
                    match_round=match_round,
                    time_s=k.get("time_s", 0),
                    attacker=k.get("attacker", ""),
                    attacker_veh=k.get("attacker_veh", ""),
                    weapon=k.get("weapon", ""),
                    victim=k.get("victim", ""),
                    victim_veh=k.get("victim_veh", "")
                ) for k in corrected_kills
            ]
            MatchKill.objects.bulk_create(new_kill_objects)

        return Response({"message": f"Round {round_number} verified and saved."}, status=status.HTTP_200_OK)


class MatchRoundListView(ListAPIView):
    serializer_class = MatchRoundSerializer

    def get_queryset(self):
        match_id = self.kwargs['pk']
        return MatchRound.objects.filter(match_id=match_id).order_by('round_number')


class RoundTelemetryView(APIView):
    def get(self, request, pk, round_number):
        match_round = get_object_or_404(MatchRound, match_id=pk, round_number=round_number)

        serializer = MatchRoundSerializer(match_round)

        return Response(serializer.data, status=status.HTTP_200_OK)


class ParseTemporaryReplayView(APIView):
    def post(self, request):
        user = request.user
        if not any([user.has_perm('user.admin_permissions'), user.has_perm('user.judge_permissions')]):
            return Response(status=status.HTTP_403_FORBIDDEN)

        start_time_str = request.data.get('start_time', '5:00')
        replay_files = request.FILES.getlist('replay_files')

        if not replay_files:
            return Response({"error": "At least one replay_file is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        with tempfile.TemporaryDirectory() as tmp_dir:
            saved_file_paths = []

            for f_obj in replay_files:
                temp_path = os.path.join(tmp_dir, f_obj.name)
                with open(temp_path, 'wb+') as dest:
                    for chunk in f_obj.chunks():
                        dest.write(chunk)
            saved_file_paths.append(temp_path)

            # --- 1. PARSE FILES ---
            res = execute_safe_worker(saved_file_paths, start_time_str=start_time_str)
            if res["status"] != "success":
                return Response({"error": res["error"]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            data = res["data"]

            # --- 2. MAP METADATA RESOLUTION ---
            raw_level_name = data.get("map_context", {}).get("level_name", "unknown")
            postfix = data.get("map_context", {}).get("postfix", "")
            loc_name = data.get("map_context", {}).get("loc_name", "")

            if "_02" in loc_name:
                map_aliases = {
                    "avg_egypt_sinai": "avg_sands_of_sinai",
                    "avg_poland": "avg_fields_of_poland",
                    "avg_normandy": "avg_fields_of_normandy",
                    "avg_eastern_europe": "avg_european_province",
                    "avg_volokolamsk": "avg_surroundings_of_volokolamsk"
                }
                raw_level_name = map_aliases.get(raw_level_name, f"{raw_level_name}_02")

            map_details = {
                "internal_name": raw_level_name,
                "postfix": postfix,
                "mode": "Unknown",
            }

            if raw_level_name != "unknown":
                map_json_path = MAPS_DIR / f"{raw_level_name}.json"
                if map_json_path.exists():
                    try:
                        with open(map_json_path, 'r', encoding='utf-8') as f:
                            map_info = json.load(f)
                            variant_data = map_info.get("variants", {}).get(postfix, {})
                            map_details.update({
                                "human_name": map_info.get("map_name", raw_level_name),
                                "texture": map_info.get("texture", ""),
                                "variant_data": variant_data,
                                "mode": variant_data.get("mode", "Unknown")
                            })
                    except Exception as e:
                        print(f"Error loading map JSON for {raw_level_name}: {e}")
                else:
                    print(f"WARNING: Map JSON not found at {map_json_path}")

            # --- 3. DATABASE VEHICLE RESOLUTION ---
            internal_id_to_tanks = defaultdict(list)
            for tank in Tank.objects.all():
                for int_id in tank.internal_ids:
                    internal_id_to_tanks[int_id].append(tank.name)

            def resolve_vehicle(parsed_name):
                # Temporary parses have no predefined roster limits, so we grab the first match
                start_names = internal_id_to_tanks.get(parsed_name, [])
                if start_names:
                    return start_names[0]
                return parsed_name

            # --- 4. FILTER SPAWNS & METADATA CACHING ---
            spawned_players = set()
            for p_name, vehicles in data.get("spawns", {}).items():
                if p_name.lower() != "unknown" and vehicles and vehicles[-1].lower() != "unknown":
                    spawned_players.add(p_name)

            player_spawns = {"team_1": [], "team_2": []}
            player_to_resolved_veh = {}
            player_to_side = {}

            for team_id in ["1", "2"]:
                target_key = "team_1" if team_id == "1" else "team_2"
                for p in data.get("teams", {}).get(team_id, []):
                    if p in spawned_players:
                        raw_veh = data["spawns"][p][-1]
                        resolved_veh = resolve_vehicle(raw_veh)

                        player_spawns[target_key].append({"player": p, "vehicle": resolved_veh})

                        clean_name = p.strip().lower()
                        player_to_resolved_veh[clean_name] = resolved_veh
                        player_to_side[clean_name] = target_key

            # --- 5. PROCESS TELEMETRY (Cleaned against active spawn) ---
            telemetry_data = {}
            for p_name, veh_data in data.get("movement", {}).items():
                clean_name = p_name.strip().lower()
                if clean_name not in player_to_resolved_veh:
                    continue

                target_veh = player_to_resolved_veh[clean_name]
                telemetry_data[p_name] = {}

                for v_name, points in veh_data.items():
                    resolved_veh = resolve_vehicle(v_name)
                    if resolved_veh == target_veh:
                        telemetry_data[p_name][resolved_veh] = points

            # --- 6. PROCESS CHAT ---
            raw_chat = data.get("chat", {})
            chat_log = sorted(list(raw_chat.values()), key=lambda x: x["time"])

            # --- 7. FUZZY RESOLVER HELPER ---
            def fuzzy_lookup(mapping, raw_name, default_val):
                clean = raw_name.strip().lower()
                if clean in mapping: return mapping[clean]
                no_tag = re.sub(r'^\[.*?\]\s*|^=.*?=\s*', '', clean).strip()
                if no_tag in mapping: return mapping[no_tag]
                no_suffix = clean.split('@')[0].strip()
                if no_suffix in mapping: return mapping[no_suffix]
                return default_val

            # --- 8. PROCESS KILLS & CRITS ---
            kills = []
            for k in data.get("kills", []):
                raw_atk = k["attacker"]
                raw_vic = k["victim"]

                if raw_atk.lower() == "unknown" or raw_vic.lower() == "unknown":
                    continue

                fallback_atk = resolve_vehicle(k.get("attacker_veh", ""))
                fallback_vic = resolve_vehicle(k.get("victim_veh", ""))

                final_atk_veh = fuzzy_lookup(player_to_resolved_veh, raw_atk, fallback_atk)
                final_vic_veh = fuzzy_lookup(player_to_resolved_veh, raw_vic, fallback_vic)

                kills.append({
                    "attacker": raw_atk,
                    "attacker_veh": final_atk_veh,
                    "victim": raw_vic,
                    "victim_veh": final_vic_veh,
                    "weapon": k.get("weapon", "Unknown"),
                    "time_s": k["time"]
                })

            crits = []
            crit_data = data.get("crits", [])
            if isinstance(crit_data, dict):
                crit_data = crit_data.values()

            for c in crit_data:
                raw_atk = c.get("attacker", "")
                raw_vic = c.get("victim", "")

                if not raw_atk or not raw_vic or raw_atk.lower() == "unknown" or raw_vic.lower() == "unknown":
                    continue

                fallback_atk = resolve_vehicle(c.get("attacker_veh", ""))
                fallback_vic = resolve_vehicle(c.get("victim_veh", ""))

                final_atk_veh = fuzzy_lookup(player_to_resolved_veh, raw_atk, fallback_atk)
                final_vic_veh = fuzzy_lookup(player_to_resolved_veh, raw_vic, fallback_vic)

                crits.append({
                    "attacker": raw_atk,
                    "attacker_veh": final_atk_veh,
                    "victim": raw_vic,
                    "victim_veh": final_vic_veh,
                    "is_fire": c.get("is_fire", False),
                    "time_s": c["time"]
                })

            # --- 9. CALCULATE TIMELINE ENDPOINTS ---
            try:
                parts = str(start_time_str).split(':')
                if len(parts) == 2:
                    start_s = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 1:
                    start_s = int(parts[0])
                else:
                    start_s = 300
            except ValueError:
                start_s = 300

            end_s = start_s + 1200
            if kills:
                end_s = int(math.ceil(max(k["time_s"] for k in kills)))

            # --- 10. COMPILE FINAL PAYLOAD ---
            frontend_payload = {
                "map_details": map_details,
                "telemetry_data": telemetry_data,
                "player_spawns": player_spawns,
                "chat_log": chat_log,
                "kills": kills,
                "crits": crits,
                "map_areas": data.get("areas", []),
                "capture_zones": data.get("zones", []),
                "start_time_s": start_s,
                "end_time_s": end_s,
            }

            return Response({
                "message": "Temporary replays parsed successfully.",
                "parsed_telemetry": frontend_payload
            }, status=status.HTTP_200_OK)


from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.cache import cache


class ComprehensiveStatsView(APIView):
    def get(self, request):
        # Pagination & Query Params
        tab = request.query_params.get('tab', 'vehicles')
        page = int(request.query_params.get('page', 1))
        limit = int(request.query_params.get('itemsPerPage', 25))
        search = request.query_params.get('search', '').lower()

        # Sorting Params
        sort_key = request.query_params.get('sortBy', None)
        sort_order = request.query_params.get('sortOrder', 'asc')

        # Drill-down Dialog Params
        filter_players = request.query_params.get('players', None)
        filter_vehicle = request.query_params.get('vehicle', None)

        # 1. Fetch or Generate Raw Data (Cached)
        cache_key = "stats_comprehensive_raw_v1"
        stats_data = cache.get(cache_key)

        if not stats_data:
            service = StatsService()
            stats_data = service.get_filtered_stats()
            cache.set(cache_key, stats_data, timeout=300)

        # 2. Select the targeted dataset and convert dict to list
        dataset = stats_data.get(tab, {})

        if tab == 'combos':
            items = [{'combo_id': k, **v} for k, v in dataset.items()]
        else:
            items = [{'name': k, **v} for k, v in dataset.items()]

        # 3. Apply Drill-down Filters (Used by the Vehicle Dialog)
        if filter_players:
            player_list = filter_players.split(',')
            if tab == 'combos':
                items = [i for i in items if i.get('player') in player_list]
            else:
                items = [i for i in items if i.get('name') in player_list]

        if filter_vehicle:
            if tab == 'combos':
                items = [i for i in items if i.get('vehicle') == filter_vehicle]
            else:
                items = [i for i in items if i.get('name') == filter_vehicle]

        # 4. Apply Global Search
        if search:
            items = [
                item for item in items
                if search in str(item.get('name', '')).lower()
                   or search in str(item.get('player', '')).lower()
                   or search in str(item.get('vehicle', '')).lower()
            ]

        # 5. Apply Sorting
        if sort_key:
            reverse = (sort_order == 'desc')
            items.sort(
                key=lambda x: x.get(sort_key, 0) if x.get(sort_key) is not None else 0,
                reverse=reverse
            )

        # 6. Apply Pagination
        total_items = len(items)
        if limit > 0:  # -1 is passed when we want to fetch "All" for the dialog
            start = (page - 1) * limit
            end = start + limit
            paginated_items = items[start:end]
        else:
            paginated_items = items

        return Response({
            'items': paginated_items,
            'total': total_items,
        })