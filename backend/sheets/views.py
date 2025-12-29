import copy

from django.conf import settings
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
    get_interchange_graph, Interchange, Alliance
from .serializers import TeamSerializer, ManufacturerSerializer, TankSerializer, MatchSerializer, SlimMatchSerializer, \
    MatchResultSerializer, TankBoxSerializer, TankBoxCreateSerializer, SlimTeamSerializer, TeamMatchSerializer, \
    TeamLogSerializer, SlimTeamSerializerWithTanks, ImportTankSerializer, ImportCriteriaSerializer, \
    UpgradePathSerializer, UpgradeTreeSerializer, InterchangeGroupSerializer, InterchangeSerializer, AllianceSerializer


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
        team = Team.objects.get(name=team_name)
        if box_id is not None:
            box = TankBox.objects.get(id=box_id)
            result = box.purchase(team, request.user)
            new_box = TeamBox.objects.get(id=result['id'])
            tank = new_box.open_box(request.user)
            box_name = box.box.name
            box_tier = box.box.tier

            result_tank_name = box.open_box(request.user)

            team.refresh_from_db()
            details = f"Opened **{box_name} (Tier {box_tier})**\nObtained: **{result_tank_name}**"
            send_transaction_log(team.name, 'Lootbox', details, 0, team.balance)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(data=str(tank), status=status.HTTP_200_OK)


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
        match = Match.objects.get(pk=pk)
        matchResult = MatchResult.objects.get(match__pk=pk)
        serializer = MatchResultSerializer(matchResult)
        return Response(serializer.data, status=status.HTTP_200_OK)

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