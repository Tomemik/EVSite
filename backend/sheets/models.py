import json
import re
from datetime import timedelta
from random import random

from django.db import models, transaction
from django.db.models import F, Q
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError
import heapq
from functools import wraps
from django.forms.models import model_to_dict
import copy
from collections import Counter


def log_team_changes(method=None, custom_method_name=None):
    if method is None:
        return lambda method: log_team_changes(method, custom_method_name)

    @wraps(method)
    def wrapper(self, *args, **kwargs):
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
            print(method_name)
            TeamLog.objects.create(
                team=self,
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

    def __str__(self):
        return self.name

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

    def money_transfer(self, from_team, to_team, amount):
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

        from_team.save()
        to_team.save()

        TeamLog.objects.create(
            team=from_team,
            field_name='balance',
            previous_value={'balance': from_team.balance + amount},
            new_value={'balance': from_team.balance},
            description=f"Changes made by method: {method_name}\nMoney Transferred to {to_team.name}\nBalance Changed by: {-amount}",
            method_name=method_name,
        )

        TeamLog.objects.create(
            team=to_team,
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

    @log_team_changes
    def purchase_tank(self, tank):
        if tank.price > self.balance:
            raise ValidationError("Insufficient balance to purchase this tank.")
        if not self.manufacturers.filter(id__in=tank.manufacturers.all()).exists():
            raise ValidationError("This tank is not available from your manufacturers.")
        self.balance -= tank.price
        self.save()
        TeamTank.objects.create(team=self, tank=tank)
        return f"Tank {tank.name} purchased successfully. Remaining balance: {self.balance}"

    @log_team_changes
    def sell_tank(self, tank):
        try:
            teamtank = TeamTank.objects.filter(team=self, tank=tank, is_trad=False).first()
        except TeamTank.DoesNotExist:
            raise ValidationError("You do not own this tank.")

        teamtank.delete()
        self.balance += tank.price * 0.6
        self.save()
        return f"Tank {tank.name} sold successfully. New balance: {self.balance}"

    @log_team_changes
    def add_upgrade_kit(self, tier, quantity=1):
        if tier in self.UPGRADE_KITS:
            if tier in self.upgrade_kits:
                self.upgrade_kits[tier]['quantity'] += quantity
            self.save()
            return f"Added {quantity} Upgrade Kit(s) of tier {tier} to {self.name}."
        else:
            return "Invalid upgrade kit tier."

    @log_team_changes
    def add_tank_boxes(self, tank_box_ids, amounts):
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
    def upgrade_or_downgrade_tank(self, from_tank, to_tank, extra_upgrade_kit_tiers=[]):
        team_tank_entry = TeamTank.objects.filter(team=self, tank=from_tank, is_upgradable=True)
        if not team_tank_entry:
            raise ValidationError(f"The team does not own the tank or its not upgradable: {from_tank.name}.")

        possible_upgrades = self.get_possible_upgrades(from_tank)

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

        self.tanks.through.objects.filter(team=self, tank=from_tank, is_upgradable=True).first().delete()
        self.tanks.through.objects.create(team=self, tank=to_tank)
        self.save()

        return f"Tank {from_tank.name} upgraded to {to_tank.name}. Total cost: {total_cost}. Remaining balance: {self.balance}"

    @log_team_changes(custom_method_name="upgrade_or_downgrade_tank")
    def do_direct_upgrade(self, from_tank, to_tank, extra_upgrade_kit_tiers=[]):
        team_tank_entry = TeamTank.objects.filter(team=self, tank=from_tank, is_upgradable=True)
        if not team_tank_entry:
            raise ValidationError(f"The team does not own the tank or its not upgradable: {from_tank.name}.")

        possible_upgrades = self.get_direct_upgrades(from_tank)

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

        self.tanks.through.objects.filter(team=self, tank=from_tank, is_upgradable=True).first().delete()
        self.tanks.through.objects.create(team=self, tank=to_tank)
        self.save()

        return f"Tank {from_tank.name} upgraded to {to_tank.name}. Total cost: {total_cost}. Remaining balance: {self.balance}"

    def get_direct_upgrades(self, from_tank):
        team_tank_entry = TeamTank.objects.filter(team=self, tank=from_tank, is_upgradable=True)
        if not team_tank_entry:
            raise ValidationError(f"The team does not own the tank or it is not upgradable: {from_tank.name}.")

        direct_upgrade_paths = UpgradePath.objects.filter(from_tank=from_tank)
        direct_upgrades = []

        for upgrade_path in direct_upgrade_paths:
            to_tank = upgrade_path.to_tank
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

    def get_possible_upgrades(self, from_tank, minimize_kits=True):
        team_tank_entry = TeamTank.objects.filter(team=self, tank=from_tank, is_upgradable=True)
        if not team_tank_entry:
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


class Tank(models.Model):

    name = models.CharField(max_length=50)
    battle_rating = models.FloatField(default=1.0)
    price = models.IntegerField(default=0)
    rank = models.IntegerField(default=1)
    type = models.CharField(max_length=50, default='MT')
    upgrades = models.ManyToManyField('self', through='UpgradePath', symmetrical=False, related_name='downgrades')
    manufacturers = models.ManyToManyField(Manufacturer, related_name='tanks', blank=True)

    def __str__(self):
        return self.name

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
    name = models.CharField(max_length=50)
    price = models.IntegerField(default=0)
    tanks = models.ManyToManyField(Tank, blank=True)
    is_national = models.BooleanField(default=True)

    def __str__(self):
        return self.name

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


class TeamBox(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    box = models.ForeignKey(TankBox, on_delete=models.CASCADE)

    @transaction.atomic
    def open_box(self):
        tank_box = self.box

        available_tanks = list(tank_box.tanks.all())
        if not available_tanks:
            raise ValueError(f"TankBox '{tank_box.name}' has no tanks to open.")

        selected_tank = random.choice(available_tanks)

        self.team.tanks.add(selected_tank)
        self.delete()

        return selected_tank


class UpgradePath(models.Model):
    from_tank = models.ForeignKey(Tank, related_name='upgrade_from', on_delete=models.CASCADE)
    to_tank = models.ForeignKey(Tank, related_name='upgrade_to', on_delete=models.CASCADE)
    required_kit_tier = models.CharField(max_length=50, blank=True, null=True)
    cost = models.IntegerField(default=0)

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


class TeamTank(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    tank = models.ForeignKey(Tank, on_delete=models.CASCADE)
    is_trad = models.BooleanField(default=False)
    is_upgradable = models.BooleanField(default=True)

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

    def __str__(self):
        return f"Match on {self.datetime} - {self.mode} - {self.gamemode}"


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
    match = models.OneToOneField(Match, on_delete=models.SET_NULL, null=True)
    winning_side = models.CharField(max_length=10, choices=TeamMatch.SIDE_CHOICES)
    judge = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='judged_matches')
    is_calced = models.BooleanField(default=False)

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
            {"rank": 4, "winner": 11000, "loser": 50000},
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
            if game_mode == "flag":
                return flag_rewards[min(int(round(average_rank)-1), 4)]["winner"], \
                    flag_rewards[min(int(round(average_rank)-1), 4)]["loser"]
            else:
                return advanced_rewards[min(int(round(average_rank)-1), 4)]["winner"], \
                    advanced_rewards[min(int(round(average_rank)-1), 4)]["loser"]

        return 0, 0

    def calculate_rewards(self):
        average_rank = self.calculate_average_rank()
        winner_base_reward, loser_base_reward = self.calculate_base_reward(average_rank)

        participating_teams = set(
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

        if self.winning_side == 'team_1':
            winner_base_reward -= substitutes_rewards['team_1']
            loser_base_reward -= substitutes_rewards['team_2']
        else:
            winner_base_reward -= substitutes_rewards['team_2']
            loser_base_reward -= substitutes_rewards['team_1']

        winning_teams = teams_on_side[self.winning_side]
        losing_teams = teams_on_side['team_1' if self.winning_side == 'team_2' else 'team_2']

        if self.match.mode in ["traditional", "flag"]:
            for team in winning_teams:
                team_rewards[team] += winner_base_reward
                for sub in self.substitutes.all():
                    if sub.team_played_for.id == team:
                        team_rewards[sub.team.id] += team_rewards[team] * (sub.activity * 0.05)
                        team_rewards[team] -= team_rewards[team] * (sub.activity * 0.05)
            for team in losing_teams:
                team_rewards[team] += loser_base_reward
                for sub in self.substitutes.all():
                    if sub.team_played_for.id == team:
                        team_rewards[sub.team.id] += team_rewards[team] * (sub.activity * 0.05)
                        team_rewards[team] -= team_rewards[team] * (sub.activity * 0.05)
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

                loss_penalty = tank_price * 0.02 * quantity
                gain_reward = tank_price * 0.03 * quantity

                if side == 'team_1':
                    total_loss_penalty_team_1 += loss_penalty
                    total_gain_reward_team_2 += gain_reward
                else:
                    total_gain_reward_team_1 += gain_reward
                    total_loss_penalty_team_2 += loss_penalty

            if self.winning_side == 'team_1':
                winner_base_reward += total_gain_reward_team_1 - total_loss_penalty_team_1
                loser_base_reward += total_gain_reward_team_2 - total_loss_penalty_team_2
            else:
                winner_base_reward += total_gain_reward_team_2 - total_loss_penalty_team_2
                loser_base_reward += total_gain_reward_team_1 - total_loss_penalty_team_1

            winner_total_reward = winner_base_reward
            loser_total_reward = loser_base_reward

            for team in winning_teams:
                team_rewards[team] += winner_total_reward / len(winning_teams)
                for sub in self.substitutes.all():
                    if sub.team_played_for == team:
                        team_rewards[sub.team.id] += team_rewards[team] * (sub.activity * 0.05)
                        team_rewards[team] -= team_rewards[team] * (sub.activity * 0.05)
            for team in losing_teams:
                team_rewards[team] += loser_total_reward / len(losing_teams)
                for sub in self.substitutes.all():
                    if sub.team_played_for.id == team:
                        team_rewards[sub.team.id] += team_rewards[team] * (sub.activity * 0.05)
                        team_rewards[team] -= team_rewards[team] * (sub.activity * 0.05)

        for team_result in self.team_results.all():
            team_id = team_result.team.id
            if team_result.bonuses:
                team_rewards[team_id] += 10000 * team_result.bonuses
            if team_result.penalties:
                team_rewards[team_id] -= 10000 * average_rank * team_result.penalties

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


        for team_id, reward in team_rewards.items():
            team = Team.objects.get(id=team_id)
            initial_balance = team.balance
            team.balance += reward
            kits = {}
            if self.match.mode in ["traditional", "domination"] and team_id in TeamMatch.objects.filter(match=self.match).values_list('team_id', flat=True):
                kits = copy.deepcopy(team.upgrade_kits)
                team.upgrade_kits['T1']['quantity'] += 1
            team.save()

            TeamLog.objects.create(
                team=team,
                field_name='balance',
                previous_value={'balance': initial_balance, 'upgrade_kits': kits},
                new_value={'balance': team.balance, 'upgrade_kits': team.upgrade_kits},
                description=f"Balance Changed by: {reward}"
                            f"\n"
                            f"Kits changed by: {compare_upgrade_kits(kits, team.upgrade_kits)}",
                method_name='calc_rewards',
            )

        self.is_calced = True
        self.save()


class TeamResult(models.Model):
    match_result = models.ForeignKey(MatchResult, on_delete=models.CASCADE, related_name='team_results')
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    bonuses = models.FloatField(blank=True, null=True)
    penalties = models.FloatField(blank=True, null=True)


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
    field_name = models.CharField(max_length=255)
    previous_value = models.JSONField()
    new_value = models.JSONField()
    description = models.TextField()
    method_name = models.CharField(max_length=255, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"Change in {self.field_name} for {self.team.name}"


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
    def purchase_from_imports(self, team):
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
        import_tank.is_purchased = True
        import_tank.save()
        team.save()

        TeamTank.objects.create(team=team, tank=import_tank.tank)

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