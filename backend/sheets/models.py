import json
import re
from datetime import timedelta
import random

from django.db import models, transaction
from django.db.models import F, Q, Count
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError
import heapq
from functools import wraps
from django.forms.models import model_to_dict
import copy
from collections import Counter, deque

ROUND_POINTS = {
    "1:0": 4,
    "0:0": 3,
    "0:1": 2,
    "2:0": 7,
    "2:1": 6,
    "1:1": 5,
    "1:2": 4,
    "0:2": 3,
    "3:0": 10,
    "3:1": 9,
    "3:2": 8,
    "2:2": 7,
    "2:3": 6,
    "1:3": 5,
    "0:3": 4
}


def log_team_changes(method=None, custom_method_name=None):
    if method is None:
        return lambda method: log_team_changes(method, custom_method_name)

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        user = kwargs.get('user')
        if user is None:
            raise ValueError("User must be provided as a keyword argument to the decorated method.")

        initial_state = model_to_dict(self)

        initial_upgrade_kits = copy.deepcopy(self.upgrade_kits)
        initial_state['upgrade_kits'] = initial_upgrade_kits
        initial_state['manufacturers'] = [str(m) for m in self.manufacturers.all()]
        initial_state['tanks'] = [str(t) for t in self.tanks.all()]

        initial_tanks = [tank.name for tank in self.tanks.all()]

        result = method(self, *args, **kwargs)

        final_state = model_to_dict(self)

        final_upgrade_kits = copy.deepcopy(self.upgrade_kits)
        final_state['upgrade_kits'] = final_upgrade_kits
        final_state['manufacturers'] = [str(m) for m in self.manufacturers.all()]
        final_state['tanks'] = [str(t) for t in self.tanks.all()]

        final_tanks = [tank.name for tank in self.tanks.all()]

        changes = {}

        for field, initial_value in initial_state.items():
            final_value = final_state.get(field)
            if initial_value != final_value:
                changes[field] = {
                    'from': initial_value,
                    'to': final_value
                }

        upgrade_kit_changes = compare_upgrade_kits(initial_upgrade_kits, final_upgrade_kits)
        if upgrade_kit_changes:
            changes['upgrade_kits'] = upgrade_kit_changes

        initial_counter = Counter(initial_tanks)
        final_counter = Counter(final_tanks)

        added_tanks = final_counter - initial_counter
        removed_tanks = initial_counter - final_counter

        if added_tanks or removed_tanks:
            changes['tanks'] = {
                'added': list(added_tanks.elements()),
                'removed': list(removed_tanks.elements())
            }

        if changes:
            readable_changes = parse_changes(changes)
            method_name = custom_method_name if custom_method_name else method.__name__
            TeamLog.objects.create(
                team=self,
                user=user,
                field_name='multiple_fields',
                previous_value=json.dumps(initial_state),
                new_value=json.dumps(final_state),
                description=f"Changes made by method: {method_name}\n{readable_changes}",
                method_name=method_name
            )

        return result

    return wrapper


def compare_upgrade_kits(initial_kits, final_kits):
    changes = []

    for tier, initial_data in initial_kits.items():
        initial_quantity = initial_data.get('quantity', 0)
        final_quantity = final_kits.get(tier, {}).get('quantity', 0)

        if initial_quantity != final_quantity:
            quantity_diff = final_quantity - initial_quantity
            changes.append({
                'tier': tier,
                'diff': quantity_diff
            })

    return changes if changes else None


def parse_changes(changes):
    readable_changes = []

    # Handle upgrade kits changes
    if 'upgrade_kits' in changes:
        for kit_change in changes['upgrade_kits']:
            quantity_diff = kit_change['diff']
            tier = kit_change['tier']
            if quantity_diff > 0:
                readable_changes.append(f"+{quantity_diff} {tier} kit")
            else:
                readable_changes.append(f"{quantity_diff} {tier} kit")

    # Handle tank changes
    if 'tanks' in changes:
        if changes['tanks']['added']:
            readable_changes.append(f"Added Tanks: {', '.join(changes['tanks']['added'])}")
        if changes['tanks']['removed']:
            readable_changes.append(f"Removed Tanks: {', '.join(changes['tanks']['removed'])}")

    # Handle other field changes
    for field, change in changes.items():
        if field not in ['upgrade_kits', 'tanks']:
            readable_changes.append(f"{field.capitalize()} Changed by: {change['to'] - change['from']}")

    return '\n'.join(readable_changes)


def default_upgrade_kits():
    return {
        'T1': {'quantity': 0, 'price': 25000},
        'T2': {'quantity': 0, 'price': 50000},
        'T3': {'quantity': 0, 'price': 100000}
    }


class Manufacturer(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Team(models.Model):

    UPGRADE_KITS = default_upgrade_kits()

    name = models.CharField(max_length=50)
    color = models.CharField(default='#000000', max_length=7)
    balance = models.IntegerField(default=0)
    manufacturers = models.ManyToManyField(Manufacturer, related_name='teams')
    tanks = models.ManyToManyField('Tank', through='TeamTank', related_name='teams')
    upgrade_kits = models.JSONField(default=default_upgrade_kits)
    tank_boxes = models.ManyToManyField('TankBox', through='TeamBox', related_name='teams')
    score = models.IntegerField(default=0)
    total_money_earned = models.IntegerField(default=0)
    total_money_spent = models.IntegerField(default=0)
    discord_role_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name

    @property
    def matches_played(self):
        return MatchResult.objects.filter(
            match__teams=self
        ).count()

    @property
    def matches_won(self):
        return MatchResult.objects.filter(
            models.Q(match__teammatch__team=self) &
            models.Q(winning_side=models.F('match__teammatch__side'))
        ).count()

    @property
    def winrate(self):
        played = self.matches_played
        if played == 0:
            return 0  # Unikamy dzielenia przez 0
        return (self.matches_won / played) * 100


    def split_merge_kit(self, action, kit_type, kit_amount):
        if action not in ['merge', 'split']:
            raise ValueError("Action must be 'merge' or 'split'.")
        if kit_type not in self.upgrade_kits:
            raise ValueError(f"Invalid kit type '{kit_type}'. Valid options are: {list(self.upgrade_kits.keys())}.")

        if action == 'merge':
            if kit_type == 'T1':
                target_kit = 'T2'
            elif kit_type == 'T2':
                target_kit = 'T3'
            else:
                return False

            if self.upgrade_kits[kit_type]['quantity'] < 2:
                return False

            self.upgrade_kits[kit_type]['quantity'] -= 2 * kit_amount
            self.upgrade_kits[target_kit]['quantity'] += 1 * kit_amount

        elif action == 'split':
            if kit_type == 'T3':
                target_kit = 'T2'
            elif kit_type == 'T2':
                target_kit = 'T1'
            else:
                return False

            if self.upgrade_kits[kit_type]['quantity'] < 1:
                return False

            self.upgrade_kits[kit_type]['quantity'] -= 1 * kit_amount
            self.upgrade_kits[target_kit]['quantity'] += 2 * kit_amount

        self.save()
        return True

    def money_transfer(self, from_team, to_team, amount, user):
        if amount <= 0:
            raise ValueError("Amount to transfer must be greater than zero.")

        if amount > 25000:
            taxxed_amount = amount*0.8
        elif amount > 10000:
            taxxed_amount = amount*0.9
        elif amount <= 10000:
            taxxed_amount = amount*0.95

        method_name = 'money_transfer_out'
        opposite_method_name = 'money_transfer_in'

        start_of_week = now() - timedelta(days=now().weekday())
        recent_out_transfer = TeamLog.objects.filter(
            team=from_team,
            method_name=method_name,
            timestamp__gte=start_of_week
        ).exists()
        if recent_out_transfer:
            raise ValueError(f"{from_team.name} has already made a transfer out this week.")

        from_team.balance -= amount
        to_team.balance += taxxed_amount
        from_team.total_money_spent += amount

        from_team.save()
        to_team.save()

        TeamLog.objects.create(
            team=from_team,
            user=user,
            field_name='balance',
            previous_value={'balance': from_team.balance + amount},
            new_value={'balance': from_team.balance},
            description=f"Changes made by method: {method_name}\nMoney Transferred to {to_team.name}\nBalance Changed by: {-amount}",
            method_name=method_name,
        )

        TeamLog.objects.create(
            team=to_team,
            user=user,
            field_name='balance',
            previous_value={'balance': to_team.balance - taxxed_amount},
            new_value={'balance': to_team.balance},
            description=f"Changes made by method: {opposite_method_name}\nMoney received from {from_team.name}\nBalance Changed by: {taxxed_amount}",
            method_name=opposite_method_name,
        )

    def matches_for_week(self, date):
        start_of_week = date - timedelta(days=date.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        return Match.objects.filter(
            teammatch__team=self,
            datetime__date__gte=start_of_week,
            datetime__date__lte=end_of_week
        ).count()

    def trad_dom_matches_for_week(self, date):
        start_of_week = date - timedelta(days=date.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        return Match.objects.filter(
            teammatch__team=self,
            datetime__date__gte=start_of_week,
            datetime__date__lte=end_of_week,
            was_played=True,
        ).filter(Q(mode="traditional") | Q(gamemode="domination")).count()

    @log_team_changes
    def purchase_tank(self, tank, *, user):
        if tank.price > self.balance:
            raise ValidationError("Insufficient balance to purchase this tank.")
        if not self.manufacturers.filter(id__in=tank.manufacturers.all()).exists():
            raise ValidationError("This tank is not available from your manufacturers.")
        self.balance -= tank.price
        self.total_money_spent += tank.price
        self.save()
        TeamTank.objects.create(team=self, tank=tank)
        return f"Tank {tank.name} purchased successfully. Remaining balance: {self.balance}"

    @log_team_changes
    def sell_teamtank(self, teamtank, *, user):
        active_matches = Match.objects.filter(
            teammatch__tanks=teamtank,
            was_played=False
        )

        if active_matches.exists():
            match_info = ", ".join([f"ID {m.id} ({m.datetime.date()})" for m in active_matches])
            raise ValidationError(
                f"Cannot sell {teamtank.tank.name}. It is currently assigned to upcoming matches: {match_info}. "
                "Please remove it from the match lineup first."
            )

        if teamtank.value != 0:
            price = teamtank.value
        else:
            price = Tank.objects.get(name=teamtank.tank.name).price

        tank_name = teamtank.tank.name

        teamtank.delete()

        self.balance += price * 0.6
        self.save()
        return f"Tank {tank_name} sold successfully. New balance: {self.balance}"

    def sell_tank(self, tank, *, user):
        candidates = TeamTank.objects.filter(
            team=self,
            tank=tank,
            is_trad=False,
            from_auctions=False
        )

        if not candidates.exists():
            raise ValidationError("You do not own this tank.")

        busy_tank_ids = TeamMatch.objects.filter(
            match__was_played=False,
            tanks__in=candidates
        ).values_list('tanks__id', flat=True)

        free_tank = candidates.exclude(id__in=busy_tank_ids).first()

        if not free_tank:
            if candidates.exists():
                raise ValidationError(
                    f"Cannot sell {tank.name}. All copies of this tank are currently assigned to upcoming matches. "
                    "Remove one from a match lineup to proceed."
                )
            else:
                raise ValidationError("You do not own this tank.")

        return self.sell_teamtank(free_tank, user=user)

    @log_team_changes
    def add_upgrade_kit(self, tier, quantity=1, *, user,):
        if tier in self.UPGRADE_KITS:
            if tier in self.upgrade_kits:
                self.upgrade_kits[tier]['quantity'] += quantity
            self.save()
            return f"Added {quantity} Upgrade Kit(s) of tier {tier} to {self.name}."
        else:
            return "Invalid upgrade kit tier."

    @log_team_changes
    def add_tank_boxes(self, tank_box_ids, amounts, *, user,):
        if len(tank_box_ids) != len(amounts):
            raise ValueError("The length of tank_box_ids and amounts must be the same.")

        for box_id, amount in zip(tank_box_ids, amounts):
            if amount <= 0:
                raise ValueError(f"Amount for TankBox ID {box_id} must be positive.")

            team_box, created = TeamBox.objects.update_or_create(
                team=self,
                box_id=box_id,
                defaults={'amount': amount}
            )

            if not created:
                pass

    def get_upgrade_kit_discount(self, tier):
        return self.upgrade_kits.get(tier, {"price": 0})["price"]

    @log_team_changes
    def upgrade_or_downgrade_tank(self, tank, to_tank, extra_upgrade_kit_tiers=[], *, user, ):
        from_tank = tank.tank
        if not tank.is_upgradable:
            raise ValidationError(f"The team does not own the tank or its not upgradable: {from_tank.name}.")

        active_matches = Match.objects.filter(
            teammatch__tanks=tank,
            was_played=False
        )

        if active_matches.exists():
            match_info = ", ".join([f"ID {m.id}" for m in active_matches])
            raise ValidationError(
                f"Cannot upgrade {from_tank.name}. It is assigned to upcoming matches: {match_info}. "
                "Remove it from the match lineup to proceed."
            )

        possible_upgrades = self.get_possible_upgrades(tank)
        upgrade_path = next((path for path in possible_upgrades if path['to_tank'] == to_tank.name), None)

        if not upgrade_path:
            raise ValidationError(f"No valid upgrade path from {from_tank.name} to {to_tank.name}.")

        if self.manufacturers.filter(id__in=to_tank.manufacturers.all()).exists():
            cost = upgrade_path['manu_cost']
        else:
            cost = upgrade_path['total_cost']

        required_kits = upgrade_path['required_kits'] if not self.manufacturers.filter(
            id__in=to_tank.manufacturers.all()).exists() else (
            {
                'T1': 0, 'T2': 0, 'T3': 0
            })

        total_extra_discount = sum(
            self.get_upgrade_kit_discount(tier) for tier in extra_upgrade_kit_tiers if tier in self.UPGRADE_KITS
        )
        total_cost = (cost - total_extra_discount) if (cost - total_extra_discount) > 0 else 0

        for kit in extra_upgrade_kit_tiers:
            if kit in required_kits:
                required_kits[kit] += 1

        missing_kits = [tier for tier, count in required_kits.items() if
                        self.upgrade_kits.get(tier, {}).get('quantity', 0) < count]
        if missing_kits:
            raise ValidationError(f"Missing upgrade kits: {', '.join(missing_kits)}")

        if total_cost > self.balance:
            raise ValidationError("Insufficient balance for this upgrade.")

        self.balance -= total_cost

        for tier, count in required_kits.items():
            self.upgrade_kits[tier]['quantity'] -= count

        self.tanks.through.objects.filter(team=self, id=tank.id, is_upgradable=True).delete()

        self.tanks.through.objects.create(team=self, tank=to_tank)

        self.save()

        return f"Tank {from_tank.name} upgraded to {to_tank.name}. Total cost: {total_cost}. Remaining balance: {self.balance}"

    @log_team_changes(custom_method_name="upgrade_or_downgrade_tank")
    def do_direct_upgrade(self, tank, to_tank, extra_upgrade_kit_tiers=[], *, user,):
        from_tank = tank.tank
        if not tank.is_upgradable:
            raise ValidationError(f"The team does not own the tank or its not upgradable: {from_tank.name}.")

        possible_upgrades = self.get_direct_upgrades(tank)

        upgrade_path = next((path for path in possible_upgrades if path['to_tank'] == to_tank.name), None)

        if not upgrade_path:
            raise ValidationError(f"No valid upgrade path from {from_tank.name} to {to_tank.name}.")

        if self.manufacturers.filter(id__in=to_tank.manufacturers.all()).exists():
            cost = upgrade_path['manu_cost']
        else:
            cost = upgrade_path['total_cost']

        required_kits = upgrade_path['required_kits'] if not self.manufacturers.filter(id__in=to_tank.manufacturers.all()).exists() else (
        {
            'T1': 0,
            'T2': 0,
            'T3': 0
        })

        total_extra_discount = sum(
            self.get_upgrade_kit_discount(tier) for tier in extra_upgrade_kit_tiers if tier in self.UPGRADE_KITS
        )
        total_cost = (cost - total_extra_discount) if (cost - total_extra_discount) > 0 else 0

        for kit in extra_upgrade_kit_tiers:
            if kit in required_kits:
                required_kits[kit] += 1

        missing_kits = [tier for tier, count in required_kits.items() if
                        self.upgrade_kits.get(tier, {}).get('quantity', 0) < count]
        if missing_kits:
            raise ValidationError(f"Missing upgrade kits: {', '.join(missing_kits)}")

        if total_cost > self.balance:
            raise ValidationError("Insufficient balance for this upgrade.")

        self.balance -= total_cost

        for tier, count in required_kits.items():
            self.upgrade_kits[tier]['quantity'] -= count

        active_matches = Match.objects.filter(
            teammatch__tanks=tank,
            was_played=False
        )

        self.tanks.through.objects.create(team=self, tank=to_tank)

        if active_matches.exists():
            tank.save()
        else:
            self.tanks.through.objects.filter(team=self, id=tank.id, is_upgradable=True).delete()

        self.save()

        return f"Tank {from_tank.name} upgraded to {to_tank.name}. Total cost: {total_cost}. Remaining balance: {self.balance}"

    def get_direct_upgrades(self, tank):
        from_tank = tank.tank
        if not tank.is_upgradable:
            raise ValidationError(f"The team does not own the tank or its not upgradable: {from_tank.name}.")

        direct_upgrade_paths = UpgradePath.objects.filter(from_tank=from_tank)
        direct_upgrades = []

        for upgrade_path in direct_upgrade_paths:
            to_tank = upgrade_path.to_tank
            if tank.from_auctions:
                base_cost = abs(tank.value - to_tank.price)
            else:
                base_cost = upgrade_path.cost
            required_kit_tier = upgrade_path.required_kit_tier
            kit_discount = self.get_upgrade_kit_discount(required_kit_tier) if required_kit_tier else 0

            effective_cost = max(base_cost - kit_discount, 0)

            required_kits = {
                'T1': 0,
                'T2': 0,
                'T3': 0
            }
            if required_kit_tier:
                required_kits[required_kit_tier] += 1

            available_in_manufacturer = self.manufacturers.filter(id__in=to_tank.manufacturers.all()).exists()

            direct_upgrades.append({
                'from_tank': from_tank.name,
                'to_tank': to_tank.name,
                'manu_cost': base_cost,
                'kit_discount': kit_discount,
                'required_kit_tier': required_kit_tier,
                'total_cost': effective_cost,
                'available_in_manufacturer': available_in_manufacturer,
                'required_kits': required_kits,
                'to_tank_br': to_tank.battle_rating,
            })

        return direct_upgrades

    def get_possible_upgrades(self, tank, minimize_kits=True):
        from_tank = tank.tank
        if not tank.is_upgradable:
            raise ValidationError(f"The team does not own the tank or its not upgradable: {from_tank.name}.")

        best_upgrade_paths = {}
        priority_queue = []
        required_kits = {
            'T1': 0,
            'T2': 0,
            'T3': 0
        }
        heapq.heappush(priority_queue, (0, 0, from_tank.id, required_kits.copy()))

        while priority_queue:
            kits, current_cost, current_tank_id, accumulated_kits = heapq.heappop(priority_queue)

            current_tank = Tank.objects.get(id=current_tank_id)

            upgrade_paths = UpgradePath.objects.filter(from_tank=current_tank)

            for upgrade_path in upgrade_paths:
                to_tank = upgrade_path.to_tank
                base_cost = upgrade_path.cost

                required_kit_tier = upgrade_path.required_kit_tier
                kit_discount = self.get_upgrade_kit_discount(required_kit_tier) if required_kit_tier else 0

                step_total_cost = base_cost - kit_discount
                step_total_cost = max(step_total_cost, 0)
                total_cost = current_cost + step_total_cost


                new_required_kits = accumulated_kits.copy()

                if required_kit_tier:
                    new_required_kits[required_kit_tier] += 1

                if minimize_kits:
                    if to_tank.id != from_tank.id:
                        if (to_tank.id not in best_upgrade_paths or
                                self.is_path_requirements_less(new_required_kits, best_upgrade_paths[to_tank.id]['required_kits'])):

                            available_in_manufacturer = self.manufacturers.filter(
                                id__in=to_tank.manufacturers.all()).exists()
                            manu_cost = None
                            if available_in_manufacturer:
                                manu_cost = abs(
                                    to_tank.price - from_tank.price) if to_tank.price >= from_tank.price else abs(
                                    to_tank.price - from_tank.price) / 2

                            kits = self.calculate_total_kits(new_required_kits)
                            effective_cost = total_cost

                            best_upgrade_paths[to_tank.id] = {
                                'from_tank': current_tank.name,
                                'to_tank': to_tank.name,
                                'base_cost': base_cost,
                                'kit_discount': kit_discount,
                                'required_kit_tier': required_kit_tier,
                                'total_cost': total_cost,
                                'available_in_manufacturer': available_in_manufacturer,
                                'manu_cost': manu_cost,
                                'required_kits': new_required_kits,
                                'to_tank_br': to_tank.battle_rating,
                            }

                            heapq.heappush(priority_queue, (kits, effective_cost, to_tank.id, new_required_kits))
                else:
                    if to_tank.id != from_tank.id:
                        if (to_tank.id not in best_upgrade_paths or total_cost < best_upgrade_paths[to_tank.id][
                            'total_cost']):

                            available_in_manufacturer = self.manufacturers.filter(
                                id__in=to_tank.manufacturers.all()).exists()
                            manu_cost = None
                            if available_in_manufacturer:
                                manu_cost = abs(
                                    to_tank.price - from_tank.price) if to_tank.price >= from_tank.price else abs(
                                    to_tank.price - from_tank.price) / 2

                            kits = self.calculate_total_kits(new_required_kits)
                            effective_cost = total_cost

                            best_upgrade_paths[to_tank.id] = {
                                'from_tank': current_tank.name,
                                'to_tank': to_tank.name,
                                'base_cost': base_cost,
                                'kit_discount': kit_discount,
                                'required_kit_tier': required_kit_tier,
                                'total_cost': total_cost,
                                'available_in_manufacturer': available_in_manufacturer,
                                'manu_cost': manu_cost,
                                'required_kits': new_required_kits,
                                'to_tank_br': to_tank.battle_rating,
                            }

                            heapq.heappush(priority_queue, (kits, effective_cost, to_tank.id, new_required_kits))

        final_upgrade_paths = [path for path in best_upgrade_paths.values() if path['to_tank'] != from_tank.name]

        return final_upgrade_paths

    def calculate_total_kits(self, required_kits):
        weights = {
            'T1': 1,
            'T2': 2,
            'T3': 4
        }

        total_kits = 0

        for kit_type, count in required_kits.items():
            total_kits += weights[kit_type] * count

        return total_kits

    def is_path_requirements_less(self, path_a_kits, path_b_kits):
        total_kits_a = self.calculate_total_kits(path_a_kits)
        total_kits_b = self.calculate_total_kits(path_b_kits)

        return total_kits_a < total_kits_b

    def reverse_change(self, log_entry):
        previous_state = json.loads(log_entry.previous_value)
        if log_entry.method_name == 'calc_rewards':
            self.balance = int(previous_state['balance'])
            self.save()

        else:
            self.balance = int(previous_state['balance'])
            self.upgrade_kits = previous_state['upgrade_kits']

            added_tanks_match = re.search(r'Added Tanks: ([\w\s,]+)', log_entry.description)
            removed_tanks_match = re.search(r'Removed Tanks: ([\w\s,]+)', log_entry.description)

            added_tanks = []
            removed_tanks = []

            if added_tanks_match:
                added_tanks = [tank.strip() for tank in added_tanks_match.group(1).split(',')]
            if removed_tanks_match:
                removed_tanks = [tank.strip() for tank in removed_tanks_match.group(1).split(',')]

            current_tanks = [tank.name for tank in self.tanks.all()]

            for tank_name in removed_tanks:
                if tank_name in current_tanks:
                    self.tanks.through.objects.filter(team=self, tank__name=tank_name).delete()

            for tank_name in added_tanks:
                if tank_name not in current_tanks:
                    tank_to_add = Tank.objects.get(name=tank_name)
                    self.tanks.through.objects.create(team=self, tank=tank_to_add)

            self.save()


class Booster(models.Model):
    name = models.CharField(max_length=50)
    multiplier = models.FloatField(default=1.0)
    expires_at = models.DateTimeField(null=True, blank=True)
    match_limited = models.BooleanField(default=False)
    matches_left = models.IntegerField(null=True, blank=True)
    active = models.BooleanField(default=True)
    team = models.OneToOneField(Team, related_name='booster', on_delete=models.CASCADE, null=True, blank=True)


class Tank(models.Model):

    name = models.CharField(max_length=50)
    battle_rating = models.FloatField(default=1.0)
    price = models.IntegerField(default=0)
    rank = models.IntegerField(default=1)
    type = models.CharField(max_length=50, default='MT')
    upgrades = models.ManyToManyField('self', through='UpgradePath', symmetrical=False, related_name='downgrades')
    manufacturers = models.ManyToManyField(Manufacturer, related_name='tanks', blank=True)

    def __str__(self):
        return f"{self.name}"

    def save(self, *args, **kwargs):
        if self.pk:
            old_price = Tank.objects.get(pk=self.pk).price
        else:
            old_price = None

        super().save(*args, **kwargs)

        if old_price is not None and old_price != self.price:
            for upgrade_path in UpgradePath.objects.filter(from_tank=self):
                upgrade_path.cost = upgrade_path.calculate_cost()
                upgrade_path.save()
            for upgrade_path in UpgradePath.objects.filter(to_tank=self):
                upgrade_path.cost = upgrade_path.calculate_cost()
                upgrade_path.save()


class TankBox(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=50)
    price = models.IntegerField(default=0)
    tier = models.IntegerField(default=1)
    tanks = models.ManyToManyField(Tank, blank=True)
    is_national = models.BooleanField(default=True)

    def __str__(self):
        return self.name + str(self.tier)

    def save(self, *args, **kwargs):
        self.calculate_cost()
        super().save(*args, **kwargs)

    def calculate_cost(self):
        tank_prices = self.tanks.all().values_list('price', flat=True)

        if tank_prices:
            mean_price = sum(tank_prices) / len(tank_prices)
        else:
            mean_price = 0

        if self.is_national:
            self.price = int(mean_price * 1.30)
        else:
            self.price = int(mean_price)

    def purchase(self, team, user):
        if team.balance < self.price:
            raise ValueError(f"Team '{team.name}' does not have enough balance to purchase '{self.name}'.")

        team.balance -= self.price
        team.total_money_spent += self.price
        team.save()

        box = TeamBox.objects.create(team=team, box=self)

        TeamLog.objects.create(
            team=team,
            user=user,
            field_name='balance',
            previous_value={'balance': team.balance + self.price},
            new_value={'balance': team.balance},
            description=f"Changes made by method: purchase_box\nBalance Changed by: {-self.price}\nBox Purchased: {self.name} T{self.tier}",
            method_name='purchase_box',
        )

        return {
            'team': team.name,
            'box': self.name,
            'new_balance': team.balance,
            'id': box.id,
        }


class TeamBox(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    box = models.ForeignKey(TankBox, on_delete=models.CASCADE)

    @transaction.atomic
    def open_box(self, user):
        tank_box = self.box

        available_tanks = list(tank_box.tanks.all())
        if not available_tanks:
            raise ValueError(f"TankBox '{tank_box.name}' has no tanks to open.")

        selected_tank = random.choice(available_tanks)

        TeamTank.objects.create(team=self.team, tank=selected_tank)
        self.delete()

        TeamLog.objects.create(
            team=self.team,
            user=user,
            field_name='balance',
            previous_value={'balance': self.team.balance},
            new_value={'balance': self.team.balance},
            description=f"Changes made by method: open_tank_box\nBalance Changed by: 0\nBox Opened: {tank_box.name} T{tank_box.tier}\nTanks Added: {str(selected_tank)}",
            method_name='open_tank_box',
        )

        return selected_tank.name


class UpgradePath(models.Model):
    from_tank = models.ForeignKey(Tank, related_name='upgrade_from', on_delete=models.CASCADE)
    to_tank = models.ForeignKey(Tank, related_name='upgrade_to', on_delete=models.CASCADE)
    required_kit_tier = models.CharField(max_length=50, blank=True, null=True)
    cost = models.IntegerField(default=0)
    in_graph = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.calculate_cost()
        super().save(*args, **kwargs)

    def calculate_cost(self):
        price_difference = self.to_tank.price - self.from_tank.price
        if self.from_tank.price > self.to_tank.price:
            self.cost = abs(price_difference / 2)
        else:
            self.cost = abs(price_difference)
        if price_difference == 0:
            rank = self.to_tank.rank
            rank_based_costs = {
                1: 3500,
                2: 7500,
                3: 10000,
                4: 15000,
                5: 20000
            }
            self.cost = rank_based_costs.get(rank, 0)

    def __str__(self):
        return f"From {self.from_tank} to {self.to_tank} using {self.required_kit_tier} for {self.cost}"

def get_upgrade_tree(start_tank_name):

    visited = set()
    upgrade_paths = []
    queue = deque()

    try:
        start_tank = Tank.objects.get(name=start_tank_name)
    except Tank.DoesNotExist:
        return []

    queue.append(start_tank)

    while queue:
        current_tank = queue.popleft()
        if current_tank.id in visited:
            continue
        visited.add(current_tank.id)

        direct_upgrades = UpgradePath.objects.filter(from_tank=current_tank).select_related('from_tank', 'to_tank')

        for path in direct_upgrades:
            upgrade_paths.append(path)
            if path.to_tank.id not in visited:
                queue.append(path.to_tank)

    return upgrade_paths


class TeamTank(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    tank = models.ForeignKey(Tank, on_delete=models.CASCADE)
    is_trad = models.BooleanField(default=False)
    is_upgradable = models.BooleanField(default=True)
    value = models.IntegerField(default=0)
    from_auctions = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.pk and self.value == 0:
            self.value = self.tank.price
        super().save(*args, **kwargs)

    def __str__(self):
        return self.tank.name


class Match(models.Model):
    MODE_CHOICES = [
        ('traditional', 'Traditional'),
        ('advanced', 'Advanced'),
        ('evolved', 'Evolved'),
    ]

    GAMEMODE_CHOICES = [
        ('annihilation', 'Annihilation'),
        ('domination', 'Domination'),
        ('flag_tank', 'Flag Tank'),
    ]

    MONEY_RULES = [
        ('none', 'None'),
        ('money_rule', 'Money Rule'),
        ('even_split', 'Even Split'),
    ]

    datetime = models.DateTimeField(db_index=True)
    mode = models.CharField(max_length=50, choices=MODE_CHOICES)
    gamemode = models.CharField(max_length=50, choices=GAMEMODE_CHOICES)
    best_of_number = models.IntegerField()
    map_selection = models.CharField(max_length=255)
    money_rules = models.CharField(max_length=50, choices=MONEY_RULES)
    special_rules = models.TextField(blank=True, null=True)
    teams = models.ManyToManyField(Team, through='TeamMatch', related_name='matches')
    was_played = models.BooleanField(default=False)
    webhook_id_schedule = models.CharField(max_length=255, blank=True, null=True)
    webhook_id_result = models.CharField(max_length=255, blank=True, null=True)
    webhook_id_calc = models.CharField(max_length=255, blank=True, null=True)
    channel_id_schedule = models.CharField(max_length=255, blank=True, null=True)
    channel_id_result = models.CharField(max_length=255, blank=True, null=True)
    channel_id_calc = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        teams_by_side = {
            'team_1': [],
            'team_2': [],
        }
        team_matches = TeamMatch.objects.filter(match=self)
        for team_match in team_matches:
            teams_by_side[team_match.side].append(team_match.team.name)

        side_1_teams = ", ".join(teams_by_side['team_1'])
        side_2_teams = ", ".join(teams_by_side['team_2'])
        return f"{self.datetime} - {self.mode} - {self.gamemode}\n {side_1_teams} vs {side_2_teams}"


class TeamMatch(models.Model):
    SIDE_CHOICES = [
        ('team_1', 'Team 1'),
        ('team_2', 'Team 2'),
    ]

    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    tanks = models.ManyToManyField('TeamTank', related_name='team_matches')
    side = models.CharField(max_length=10, choices=SIDE_CHOICES, default='team_1')

    def __str__(self):
        return f"{self.team.name} in {self.match} with: \n {self.tanks.all()}"


class MatchResult(models.Model):
    match = models.OneToOneField(Match, on_delete=models.SET_NULL, null=True, related_name='match_result')
    winning_side = models.CharField(max_length=10, choices=TeamMatch.SIDE_CHOICES)
    judge = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='judged_matches')
    is_calced = models.BooleanField(default=False)
    round_score = models.CharField(max_length=5, null=True, blank=True, help_text="Enter the score as 'X:Y' (e.g., 2:1)")

    def calculate_average_rank(self):
        tanks_lost = TankLost.objects.filter(match_result__match=self.match)
        tanks = Tank.objects.filter(id__in=tanks_lost.values_list('tank_id', flat=True))

        total_rank_br = sum(tank.rank * tank.battle_rating for tank in tanks)
        total_br = sum(tank.battle_rating for tank in tanks)

        if total_br > 0:
            average_rank = total_rank_br / total_br
        else:
            average_rank = 0

        return round(average_rank)

    def calculate_base_reward(self, average_rank):

        advanced_rewards = [
            {"rank": 1, "winner": 20000, "loser": 15000},
            {"rank": 2, "winner": 40000, "loser": 30000},
            {"rank": 3, "winner": 60000, "loser": 45000},
            {"rank": 4, "winner": 80000, "loser": 60000},
            {"rank": 5, "winner": 100000, "loser": 75000},
        ]

        flag_rewards = [
            {"rank": 1, "winner": 35000, "loser": 15000},
            {"rank": 2, "winner": 60000, "loser": 25000},
            {"rank": 3, "winner": 85000, "loser": 40000},
            {"rank": 4, "winner": 110000, "loser": 50000},
            {"rank": 5, "winner": 150000, "loser": 70000},
        ]

        trad_bo5_rewards = [
            {"rank": 1, "winner": 20000, "loser": 15000},
            {"rank": 2, "winner": 40000, "loser": 30000},
            {"rank": 3, "winner": 55000, "loser": 40000},
            {"rank": 4, "winner": 75000, "loser": 55000},
            {"rank": 5, "winner": 95000, "loser": 70000},
        ]

        trad_bo3_rewards = [
            {"rank": 1, "winner": 15000, "loser": 12000},
            {"rank": 2, "winner": 30000, "loser": 23000},
            {"rank": 3, "winner": 45000, "loser": 34000},
            {"rank": 4, "winner": 60000, "loser": 45000},
            {"rank": 5, "winner": 75000, "loser": 56000},
        ]

        mode = self.match.mode
        game_mode = self.match.gamemode
        best_of = self.match.best_of_number

        if mode == "traditional":
            if best_of == 5:
                return trad_bo5_rewards[min(int(round(average_rank)-1), 4)]["winner"], \
                    trad_bo5_rewards[min(int(round(average_rank)-1), 4)]["loser"]
            else:
                return trad_bo3_rewards[min(int(round(average_rank) - 1), 4)]["winner"], \
                    trad_bo3_rewards[min(int(round(average_rank) - 1), 4)]["loser"]
        elif mode == "advanced" or mode == "evolved":
            if game_mode == "flag_tank":
                return flag_rewards[min(int(round(average_rank)-1), 4)]["winner"], \
                    flag_rewards[min(int(round(average_rank)-1), 4)]["loser"]
            else:
                return advanced_rewards[min(int(round(average_rank)-1), 4)]["winner"], \
                    advanced_rewards[min(int(round(average_rank)-1), 4)]["loser"]

        return 0, 0

    def calculate_rewards(self, user):
        average_rank = self.calculate_average_rank()
        winner_base_reward, loser_base_reward = self.calculate_base_reward(average_rank)

        participating_teams = set(
            TeamMatch.objects.filter(match=self.match).values_list('team_id', flat=True)
        )
        playing_teams = set(
            TeamMatch.objects.filter(match=self.match).values_list('team_id', flat=True)
        )
        participating_teams.update(substitute.team.id for substitute in self.substitutes.all())
        if self.judge:
            participating_teams.add(self.judge.id)

        team_rewards = {team_id: 0 for team_id in participating_teams}

        teams_on_side = {
            'team_1': list(TeamMatch.objects.filter(match=self.match, side='team_1').values_list('team_id', flat=True)),
            'team_2': list(TeamMatch.objects.filter(match=self.match, side='team_2').values_list('team_id', flat=True)),
        }

        num_teams_on_side = {
            'team_1': len(teams_on_side['team_1']),
            'team_2': len(teams_on_side['team_2']),
        }

        substitutes_rewards = {
            'team_1': 0,
            'team_2': 0,
        }

        for team_result in self.team_results.all():
            team = team_result.team
            team_id = team.id
            side = 'team_1' if team_id in teams_on_side['team_1'] else 'team_2'
            other_side = 'team_2' if side == 'team_1' else 'team_1'

            if not team_result.was_present:
                if len(teams_on_side[side]) > 1:
                    TeamLog.objects.create(
                        team=team,
                        user=user,
                        field_name='balance',
                        previous_value={'balance': team.balance},
                        new_value={'balance': team.balance},
                        description=f"Balance Changed by: {0}\n"
                                    f"No Show\n"
                                    f"Match: {self.match.__str__()}\n"
                                    f"Match ID: {self.match.id}",
                        method_name="calc_rewards"
                    )
                    participating_teams.remove(team_id)
                    playing_teams.remove(team_id)
                else:
                    initial_balance = team.balance
                    team.balance -= 20000

                    TeamLog.objects.create(
                        team=team,
                        user=user,
                        field_name='balance',
                        previous_value={'balance': initial_balance},
                        new_value={'balance': team.balance},
                        description=f"Balance Changed by: {-20000}\n"
                                    f"No Show\n"
                                    f"Match: {self.match.__str__()}\n"
                                    f"Match ID: {self.match.id}",
                        method_name="calc_rewards"
                    )
                    team.save()

                    for other_team in teams_on_side[other_side]:
                        team = Team.objects.get(id=other_team)
                        initial_balance = team.balance
                        team.balance += 20000

                        TeamLog.objects.create(
                            team=team,
                            user=user,
                            field_name='balance',
                            previous_value={'balance': initial_balance},
                            new_value={'balance': team.balance},
                            description=f"Balance Changed by: {20000}\n"
                                        f"Enemy No Show\n"
                                        f"Match: {self.match.__str__()}\n"
                                        f"Match ID: {self.match.id}",
                            method_name="calc_rewards"
                        )
                        team.save()

                    self.is_calced = True
                    self.save()
                    return



        if self.winning_side == 'team_1':
            winner_base_reward -= substitutes_rewards['team_1']
            loser_base_reward -= substitutes_rewards['team_2']
        else:
            winner_base_reward -= substitutes_rewards['team_2']
            loser_base_reward -= substitutes_rewards['team_1']

        winning_teams = teams_on_side[self.winning_side]
        losing_teams = teams_on_side['team_1' if self.winning_side == 'team_2' else 'team_2']

        tank_counts = TeamMatch.objects.filter(match=self.match).values('side').annotate(total_tanks=Count('tanks'))
        team_1_tanks = next((t['total_tanks'] for t in tank_counts if t['side'] == 'team_1'), 0)
        team_2_tanks = next((t['total_tanks'] for t in tank_counts if t['side'] == 'team_2'), 0)

        if self.match.mode == "traditional" or self.match.gamemode == "flag_tank":
            for team in winning_teams:
                team_rewards[team] += winner_base_reward

            for team in losing_teams:
                team_rewards[team] += loser_base_reward
        else:
            total_loss_penalty_team_1 = 0
            total_gain_reward_team_1 = 0
            total_loss_penalty_team_2 = 0
            total_gain_reward_team_2 = 0

            for tank_lost in self.tanks_lost.all():
                team_id = tank_lost.team.id
                tank_price = tank_lost.tank.price
                quantity = tank_lost.quantity
                side = 'team_1' if team_id in teams_on_side['team_1'] else 'team_2'
                other_side = 'team_2' if side == 'team_1' else 'team_1'

                if self.match.money_rules == 'even_split':
                    loss_penalty = tank_price * 0 * quantity
                    gain_reward = tank_price * 0.0045 * quantity
                elif self.match.money_rules == 'money_rule':
                    loss_penalty = tank_price * 0 * quantity
                    gain_reward = tank_price * 0.01 * quantity
                else:
                    loss_penalty = tank_price * 0.02 * quantity
                    gain_reward = tank_price * 0.032 * quantity

                if side == 'team_1':
                    total_loss_penalty_team_1 += loss_penalty
                    total_gain_reward_team_2 += gain_reward
                else:
                    total_gain_reward_team_1 += gain_reward
                    total_loss_penalty_team_2 += loss_penalty

                if team_1_tanks == 1 and team_2_tanks == 1:
                    total_gain_reward_team_2 = 0
                    total_gain_reward_team_1 = 0

            if self.winning_side == 'team_1':
                winner_base_reward += total_gain_reward_team_1 - total_loss_penalty_team_1
                loser_base_reward += total_gain_reward_team_2 - total_loss_penalty_team_2
            else:
                winner_base_reward += total_gain_reward_team_2 - total_loss_penalty_team_2
                loser_base_reward += total_gain_reward_team_1 - total_loss_penalty_team_1

            winner_total_reward = winner_base_reward
            loser_total_reward = loser_base_reward

            if self.match.money_rules == "even_split":
                winner_total_reward = (winner_base_reward + loser_base_reward) / 2
                loser_total_reward = (winner_base_reward + loser_base_reward) / 2

            for team in winning_teams:
                team_rewards[team] += winner_total_reward / len(winning_teams)

            for team in losing_teams:
                team_rewards[team] += loser_total_reward / len(losing_teams)



        used_boosters = {}

        for team in winning_teams:
            try:
                booster = Booster.objects.get(team=team)
            except Booster.DoesNotExist:
                continue

            if booster and booster.active:
                if booster.expires_at and booster.expires_at < now():
                    booster.delete()
                elif booster.match_limited and (booster.matches_left is None or booster.matches_left <= 0):
                    booster.delete()
                else:
                    team_rewards[team] *= booster.multiplier
                    if booster.match_limited and booster.matches_left is not None:
                        used_boosters[team] = {
                            "team_id": team,
                            "booster_id": booster.id,
                            "matches_left_before": booster.matches_left,
                            "matches_left_after": booster.matches_left - 1
                        }
                        booster.matches_left -= 1
                    booster.save()

        for team in losing_teams:
            try:
                booster = Booster.objects.get(team=team)
            except Booster.DoesNotExist:
                continue

            if booster and booster.active:
                if booster.expires_at and booster.expires_at < now():
                    booster.delete()
                elif booster.match_limited and (booster.matches_left is None or booster.matches_left <= 0):
                    booster.delete()
                else:
                    team_rewards[team] *= booster.multiplier
                    if booster.match_limited and booster.matches_left is not None:
                        used_boosters[team] = {
                            "team_id": team,
                            "booster_id": booster.id,
                            "matches_left_before": booster.matches_left,
                            "matches_left_after": booster.matches_left - 1
                        }
                        booster.matches_left -= 1
                    booster.save()

        for team_result in self.team_results.all():
            team_id = team_result.team.id
            if team_result.bonuses:
                team_rewards[team_id] += 10000 * team_result.bonuses

        if self.match.money_rules == "money_rule":
            for team_id in playing_teams:
                reward = team_rewards.get(team_id, 0)

                if reward < 0:
                    deficit = abs(reward)
                    team_rewards[team_id] = 0

                    winning_side_teams = teams_on_side[self.winning_side]
                    if winning_side_teams:
                        per_team_deduction = deficit / len(winning_side_teams)

                        for winner_id in winning_side_teams:
                            team_rewards[winner_id] -= per_team_deduction

                            if team_rewards[winner_id] < 0:
                                deficit += abs(team_rewards[winner_id])
                                team_rewards[winner_id] = 0

                                remaining_winners = [
                                    t for t in winning_side_teams if team_rewards[t] > 0
                                ]
                                if remaining_winners:
                                    per_team_deduction = deficit / len(remaining_winners)

        for team_result in self.team_results.all():
            team_id = team_result.team.id
            if team_result.penalties:
                team_rewards[team_id] -= 10000 * average_rank * team_result.penalties

        for team in winning_teams:
            for sub in self.substitutes.all():
                if sub.team_played_for.id == team:
                    team_rewards[sub.team.id] += team_rewards[team] * (sub.activity * 0.05) if team_rewards[team] > 0 else 0
                    team_rewards[team] -= team_rewards[team] * (sub.activity * 0.05) if team_rewards[team] > 0 else 0
        for team in losing_teams:
            for sub in self.substitutes.all():
                if sub.team_played_for.id == team:
                    team_rewards[sub.team.id] += team_rewards[team] * (sub.activity * 0.05) if team_rewards[team] > 0 else 0
                    team_rewards[team] -= team_rewards[team] * (sub.activity * 0.05) if team_rewards[team] > 0 else 0

        combined_rewards = winner_base_reward + loser_base_reward
        if self.tanks_lost.all().count() >= 12:
            judge_reward = 0.075 * combined_rewards
        else:
            judge_reward = 0.05 * combined_rewards
        if self.match.mode == "bo5":
            judge_reward = max(judge_reward, 7500)
        else:
            judge_reward = max(judge_reward, 5000)

        if self.judge:
            team_rewards[self.judge.id] += judge_reward

        winning_teams = teams_on_side[self.winning_side]
        losing_teams = teams_on_side['team_1' if self.winning_side == 'team_2' else 'team_2']

        for team in winning_teams:
            points = ROUND_POINTS.get(self.round_score, 0)
            num_rounds = sum(map(int, self.round_score.split(':')))
            win_percentage = int(self.round_score.split(':')[0]) / num_rounds if num_rounds > 0 else 0
            total_points = points * (1 + win_percentage)
            team_rewards[team] += total_points

        reversed_score = ":".join(self.round_score.split(':')[::-1])
        for team in losing_teams:
            points = ROUND_POINTS.get(reversed_score, 0)
            num_rounds = sum(map(int, reversed_score.split(':')))
            win_percentage = int(reversed_score.split(':')[0]) / num_rounds if num_rounds > 0 else 0
            total_points = points * (1 + win_percentage)
            team_rewards[team] += total_points

        a = TeamLog.objects.filter(
            Q(description__contains=f'Reverted rewards calculation for Match ID: {self.match.id}')
        ).delete()

        today = now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        for team_id, reward in team_rewards.items():
            reversed_score = ":".join(self.round_score.split(':')[::-1])
            if team_id in winning_teams:
                points = ROUND_POINTS.get(self.round_score, 0)
                num_rounds = sum(map(int, self.round_score.split(':')))
                win_percentage = int(self.round_score.split(':')[0]) / num_rounds if num_rounds > 0 else 0
                total_points = points * (1 + win_percentage)
            elif team_id in losing_teams:
                points = ROUND_POINTS.get(reversed_score, 0)
                num_rounds = sum(map(int, self.round_score.split(':')))
                win_percentage = int(self.round_score.split(':')[0]) / num_rounds if num_rounds > 0 else 0
                total_points = points * (1 + win_percentage)
            else:
                total_points = 0

            team = Team.objects.get(id=team_id)
            initial_balance = team.balance
            initial_points = team.score

            team.balance += reward
            team.score += total_points
            team.total_money_earned += reward
            kits = copy.deepcopy(team.upgrade_kits)
            if (
                    (self.match.mode == "traditional" or self.match.gamemode == 'domination') and
                    team_1_tanks >= 3 and
                    team_2_tanks >= 3 and
                    team.trad_dom_matches_for_week(self.match.datetime) <= 2
            ):
                team.upgrade_kits['T1']['quantity'] += 1
            team.save()

            if team_id in playing_teams:
                log_method = "calc_rewards"
            elif self.judge and team_id == self.judge.id and any(sub.team.id == team_id for sub in self.substitutes.all()):
                log_method = "judge_and_sub_rewards"
            elif any(sub.team.id == team_id for sub in self.substitutes.all()):
                log_method = "sub_rewards"
            else:
                log_method = "judge_rewards"

            booster_log_data = used_boosters.get(team.id)
            if booster_log_data:
                previous_booster = {
                    "booster_id": booster_log_data["booster_id"],
                    "matches_left": booster_log_data["matches_left_before"]
                }
                new_booster = {
                    "booster_id": booster_log_data["booster_id"],
                    "matches_left": booster_log_data["matches_left_after"]
                }
            else:
                previous_booster = None
                new_booster = None

            if log_method == 'calc_rewards':
                TeamLog.objects.create(
                    team=team,
                    user=user,
                    field_name='balance',
                    previous_value={
                        'balance': initial_balance,
                        'upgrade_kits': kits,
                        'score': initial_points,
                        'booster': previous_booster
                    },
                    new_value={
                        'balance': team.balance,
                        'upgrade_kits': team.upgrade_kits,
                        'score': team.score,
                        'booster': new_booster
                    },
                    description=f"Balance Changed by: {reward}\n"
                                f"Kits changed by: {compare_upgrade_kits(kits, team.upgrade_kits)}\n"
                                f"Match: {self.match.__str__()}\n"
                                f"Match ID: {self.match.id}\n"
                                f"Booster: {booster_log_data if booster_log_data else 'None'}",
                    method_name=log_method
                )
            else:
                TeamLog.objects.create(
                    team=team,
                    user=user,
                    field_name='balance',
                    previous_value={
                        'balance': initial_balance,
                        'booster': previous_booster
                    },
                    new_value={
                        'balance': team.balance,
                        'booster': new_booster
                    },
                    description=f"Balance Changed by: {reward}\n"
                                f"Match: {self.match.__str__()}\n"
                                f"Match ID: {self.match.id}\n"
                                f"Booster: {booster_log_data if booster_log_data else 'None'}",
                    method_name=log_method
                )

        self.is_calced = True
        self.save()

        rewards_summary = {
            "winning_teams": {},
            "losing_teams": {},
            "substitutes": {},
            "judge": {},
            "total_rewards": 0,
            "kits": {},
        }

        for team_id in playing_teams:
            team = Team.objects.get(id=team_id)
            team_data = {
                "reward": int(team_rewards.get(team_id, 0)),
                "new_balance": team.balance,
                "new_score": team.score,
            }

            if team_id in winning_teams:
                rewards_summary["winning_teams"][team.name] = team_data
            else:
                rewards_summary["losing_teams"][team.name] = team_data

            if (
                    (self.match.mode == "traditional" or self.match.gamemode == 'domination') and
                    team_1_tanks >= 3 and
                    team_2_tanks >= 3 and
                    team.trad_dom_matches_for_week(self.match.datetime) <= 2
            ):
                if team_id in TeamMatch.objects.filter(match=self.match).values_list('team_id', flat=True):
                    rewards_summary["kits"][team.name] = {
                        "T1_kits_received": 1
                    }

        for sub in self.substitutes.all():
            sub_team_name = sub.team.name
            sub_reward = int(team_rewards.get(sub.team.id, 0))
            if sub_team_name not in rewards_summary["substitutes"]:
                rewards_summary["substitutes"][sub_team_name] = {"reward": 0}
            rewards_summary["substitutes"][sub_team_name]["reward"] += sub_reward

        if self.judge:
            judge_team = self.judge
            rewards_summary["judge"] = {
                "name": judge_team.name,
                "reward": int(team_rewards.get(judge_team.id, 0)),
                "new_balance": judge_team.balance,
            }

        rewards_summary["total_rewards"] = sum(team_rewards.values())

        return rewards_summary


    def revert_rewards(self):
        if not self.is_calced:
            raise ValueError("Rewards have not been calculated yet, cannot revert.")

        team_logs = TeamLog.objects.filter(
            description__icontains=f"Match ID: {self.match.id}"
        )

        for log in team_logs:
            team = log.team
            current_balance = team.balance
            current_kits = team.upgrade_kits
            current_score = team.score

            calc_difference = log.new_value['balance'] - log.previous_value['balance']
            revert_balance = current_balance - calc_difference

            previous_kits = log.previous_value.get('upgrade_kits', {})
            new_kits = log.new_value.get('upgrade_kits', {})

            calc_score_difference = log.new_value.get('score', 0) - log.previous_value.get('score', 0)
            revert_score = current_score - calc_score_difference

#            kits_difference = {
#                kit: new_kits.get([kit, {}]).get('quantity', 0) - previous_kits.get(kit, {}).get('quantity', 0)
#                for kit in new_kits
#            }
#            for kit, diff in kits_difference.items():
#                current_kits[kit]['quantity'] -= diff

            prev_booster = log.previous_value.get('booster')
            new_booster = log.new_value.get('booster')
            if prev_booster and new_booster:
                try:
                    booster = Booster.objects.get(id=prev_booster['booster_id'], team=team)
                    booster.matches_left = prev_booster['matches_left']
                    booster.save()
                except Booster.DoesNotExist:
                    pass

            team.balance = revert_balance
            team.upgrade_kits = current_kits
            team.score = revert_score
            team.total_money_earned -= calc_difference
            team.save()

            log.previous_value = {'balance': 0, 'score': 0}
            log.new_value = {'balance': 0, 'score': 0}
            log.description = f"Balance Changed by: 0\n" \
                              f"\nReverted rewards calculation for Match ID: {self.match.id}."
            log.method_name = 'revert_rewards'
            log.save()

        self.is_calced = False
        self.save()


class TeamResult(models.Model):
    match_result = models.ForeignKey(MatchResult, on_delete=models.CASCADE, related_name='team_results')
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    bonuses = models.FloatField(blank=True, null=True)
    penalties = models.FloatField(blank=True, null=True)
    was_present = models.BooleanField(default=True)

class TankLost(models.Model):
    match_result = models.ForeignKey(MatchResult, on_delete=models.CASCADE, related_name='tanks_lost')
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    tank = models.ForeignKey(Tank, on_delete=models.CASCADE)
    quantity = models.IntegerField()


class Substitute(models.Model):
    SIDE_CHOICES = [
        ('team_1', 'Team 1'),
        ('team_2', 'Team 2'),
    ]

    match_result = models.ForeignKey(MatchResult, on_delete=models.CASCADE, related_name='substitutes')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='substitute_teams')
    activity = models.IntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    side = models.CharField(max_length=10, choices=SIDE_CHOICES, default='team_1')
    team_played_for = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='assisted_by_substitutes', blank=True, null=True)

    def __str__(self):
        return f"Substitute from {self.team.name} on {self.side} with activity level {self.activity}"


class TeamLog(models.Model):
    team = models.ForeignKey('Team', on_delete=models.CASCADE)
    user = models.CharField(max_length=255, blank=True, null=True)
    field_name = models.CharField(max_length=255)
    previous_value = models.JSONField()
    new_value = models.JSONField()
    description = models.TextField()
    method_name = models.CharField(max_length=255, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.method_name} for {self.team.name}"


def default_expiry_date():
    return now() + timedelta(days=7)


class ImportTank(models.Model):
    tank = models.ForeignKey(Tank, on_delete=models.CASCADE, related_name='import_tanks')
    discount = models.IntegerField()
    available_from = models.DateTimeField(default=now)
    available_until = models.DateTimeField(default=default_expiry_date)
    is_purchased = models.BooleanField(default=False)
    criteria = models.ForeignKey(
        'ImportCriteria',
        on_delete=models.SET_NULL,
        related_name='import_tanks',
        null=True,
        blank=True
    )

    def __str__(self):
        status = "Expired" if self.available_until <= now() else "Active"
        return f"Import {self.tank.name} ({status})"

    @transaction.atomic
    def purchase_from_imports(self, team, user):
        import_tank = ImportTank.objects.select_for_update().get(pk=self.pk)
        team = Team.objects.select_for_update().get(pk=team.pk)

        if import_tank.is_purchased:
            raise ValidationError("This tank has already been purchased.")

        if now() < import_tank.available_from or now() > import_tank.available_until:
            raise ValidationError("This import is not open.")

        tank_price = max(import_tank.tank.price - import_tank.tank.price * (import_tank.discount / 100), 0)

        if team.manufacturers.filter(id__in=import_tank.tank.manufacturers.all()).exists():
            if import_tank.tank.battle_rating <= 3.7:
                tank_price = 0.8 * tank_price
            else:
                tank_price = 0.9 * tank_price
        else:
            if import_tank.tank.battle_rating <= 3.7:
                tank_price = 1.25 * tank_price
            else:
                tank_price = 1.35 * tank_price

        if tank_price > team.balance:
            raise ValidationError("Insufficient balance to purchase this tank.")

        team.balance -= tank_price
        team.total_money_spent += tank_price
        import_tank.is_purchased = True
        import_tank.save()
        team.save()

        TeamTank.objects.create(team=team, tank=import_tank.tank)

        TeamLog.objects.create(
            team=team,
            user=user,
            field_name='balance',
            previous_value={'balance': team.balance + tank_price},
            new_value={'balance': team.balance},
            description=f"Changes made by method: imports_purchase\nBalance Changed by: {tank_price}\nTanks Added: {str(import_tank.tank)}",
            method_name='imports_purchase',
        )

        return f"Tank {import_tank.tank.name} purchased from imports successfully. Remaining balance: {team.balance}"


class ImportCriteria(models.Model):
    name = models.CharField(default='', max_length=255, null=True, blank=True)
    min_rank = models.IntegerField(default=0, null=True, blank=True, help_text="Minimum rank of tanks to include.")
    max_rank = models.IntegerField(default=6, null=True, blank=True, help_text="Maximum rank of tanks to include.")
    tank_type = models.CharField(max_length=50, null=True, blank=True, help_text="Filter by tank type (e.g., MT, HT).")
    is_active = models.BooleanField(default=True, help_text="Activate this criteria for offer generation.")
    required_tanks = models.ManyToManyField(
        'Tank', blank=True, related_name="criteria",
        help_text="List of specific tanks to always include in offers."
    )
    required_tank_count = models.IntegerField(
        null=True, blank=True, default=0,
        help_text="Minimum number of tanks from the required list to include."
    )
    discount = models.IntegerField(
        default=0, help_text="Discount to apply to tanks matching the criteria (0-100%)."
    )
    required_tank_discount = models.IntegerField(
        default=0, help_text="Additional discount for required tanks (0-100%)."
    )

    def __str__(self):
        return self.name

    def get_filters(self):
        """Generate a dictionary of filters based on the criteria fields."""
        filters = {}
        if self.min_rank is not None:
            filters['rank__gte'] = self.min_rank
        if self.max_rank is not None:
            filters['rank__lte'] = self.max_rank
        if self.tank_type:
            filters['type'] = self.tank_type
        return filters


class UpgradeTree(models.Model):
    label = models.CharField(max_length=100)
    value = models.ForeignKey(Tank, related_name='TreeTank', on_delete=models.CASCADE)

    def __str__(self):
        return self.label


class InterchangeGroup(models.Model):
    label = models.CharField(max_length=100)
    root_tank = models.ForeignKey(Tank, related_name='interchange_group_root', on_delete=models.CASCADE)

    def __str__(self):
        return self.label

class Interchange(models.Model):
    from_tank = models.ForeignKey(Tank, related_name='interchanges_from', on_delete=models.CASCADE)
    to_tank = models.ForeignKey(Tank, related_name='interchanges_to', on_delete=models.CASCADE)
    is_bidirectional = models.BooleanField(default=True)

    def __str__(self):
        arrow = "<->" if self.is_bidirectional else "->"
        return f"{self.from_tank} {arrow} {self.to_tank}"


def get_interchange_graph(start_tank_name):
    try:
        start_tank = Tank.objects.get(name=start_tank_name)
    except Tank.DoesNotExist:
        return []

    visited_tank_ids = set()
    collected_edges = set()
    results = []

    queue = deque([start_tank])
    visited_tank_ids.add(start_tank.id)

    while queue:
        current_tank = queue.popleft()

        outgoing = Interchange.objects.filter(from_tank=current_tank)
        incoming = Interchange.objects.filter(to_tank=current_tank)

        for edge in outgoing:
            if edge.id not in collected_edges:
                collected_edges.add(edge.id)
                results.append(edge)

            if edge.to_tank.id not in visited_tank_ids:
                visited_tank_ids.add(edge.to_tank.id)
                queue.append(edge.to_tank)

        for edge in incoming:
            if edge.id not in collected_edges:
                collected_edges.add(edge.id)
                results.append(edge)

            if edge.from_tank.id not in visited_tank_ids:
                visited_tank_ids.add(edge.from_tank.id)
                queue.append(edge.from_tank)

    return results