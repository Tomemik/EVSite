from django.test import TestCase
from django.utils.timezone import now
from sheets.models import (
    Team, Match, MatchResult, TeamMatch, WeeklyEconomySettings, TeamLog
)
from io import StringIO
from django.core.management import call_command
import json


class MatchRewardsTestCase(TestCase):
    def setUp(self):
        # 1. Setup Economy Settings
        self.economy = WeeklyEconomySettings.load()
        self.economy.current_cap = 300000
        self.economy.over_cap_penalty_scaling = 1.0
        self.economy.min_reward_floor = 0.1
        self.economy.save()

        # 2. Setup Teams
        self.team1 = Team.objects.create(name="Team Alpha", balance=100000, score=0)
        self.team2 = Team.objects.create(name="Team Beta", balance=100000, score=0)

        # 3. Setup a Match
        self.match = Match.objects.create(
            datetime=now(),
            mode="traditional",
            gamemode="domination",
            best_of_number=3,
            money_rules="none"
        )
        TeamMatch.objects.create(match=self.match, team=self.team1, side="team_1")
        TeamMatch.objects.create(match=self.match, team=self.team2, side="team_2")

        # 4. Setup Match Result (Team 1 Wins)
        self.match_result = MatchResult.objects.create(
            match=self.match,
            winning_side="team_1",
            round_score="2:1"
        )

    def test_standard_rewards_under_cap(self):
        """Test that normal rewards are paid out fully when under the soft cap"""
        print("\n" + "=" * 50)
        print("TEST: test_standard_rewards_under_cap")
        print("=" * 50)

        initial_balance = self.team1.balance
        print(f"[BEFORE] {self.team1.name} Balance: {initial_balance:,}")

        # Calculate!
        summary = self.match_result.calculate_rewards(user="test_admin")
        print(f"[ACTION] Calculated rewards. Summary:\n{json.dumps(summary['winning_teams']['Team Alpha'], indent=2)}")

        self.team1.refresh_from_db()
        print(
            f"[AFTER] {self.team1.name} Balance: {self.team1.balance:,} (Gained: {self.team1.balance - initial_balance:,})")

        self.assertTrue(self.team1.balance > initial_balance)
        self.assertTrue(self.match_result.is_calced)

    def test_soft_cap_penalty_applied(self):
        """Test that the reward is reduced if the team is over the weekly soft cap"""
        print("\n" + "=" * 50)
        print("TEST: test_soft_cap_penalty_applied")
        print("=" * 50)

        # Force Team 1 to be over the cap by creating a dummy TeamLog
        TeamLog.objects.create(
            team=self.team1,
            user="system",
            field_name="balance",
            previous_value={"balance": 0},
            new_value={"balance": 400000},  # 400k earned
            description="Fake past earnings",
            method_name="calc_rewards"
        )
        print(
            f"[BEFORE] Simulated past earnings of 400,000 for {self.team1.name} (Global Cap is {self.economy.current_cap:,})")

        # Calculate standard reward to compare against
        # We can bypass the database save to just see what the math *would* be
        average_rank = self.match_result.calculate_average_rank()
        winner_base_reward, _ = self.match_result.calculate_base_reward(average_rank)
        print(f"[EXPECTED] Base Winner Reward (Without Cap Penalty): {winner_base_reward:,}")

        # Now actually calculate and apply it
        summary = self.match_result.calculate_rewards(user="test_admin")

        # Look at the reward actually given to Team Alpha
        actual_reward = summary["winning_teams"]["Team Alpha"]["reward"]
        print(f"[ACTUAL] Scaled Reward Applied: {actual_reward:,}")

        # Because they are over the 300k cap, the actual reward should be LESS than the base reward
        self.assertTrue(actual_reward < winner_base_reward,
                        f"Reward {actual_reward} was not scaled down from {winner_base_reward}")


class WeeklyPayoutCommandTest(TestCase):
    def setUp(self):
        # 1. Setup Economy Settings (Cap = 300k, Payout Ratio = 50%)
        self.economy = WeeklyEconomySettings.load()
        self.economy.current_cap = 300000
        self.economy.under_cap_payout_ratio = 0.5
        self.economy.save()

        # 2. Setup 3 Teams with a base balance of 50k
        self.team_under = Team.objects.create(name="Team Under", balance=50000, total_money_earned=0)
        self.team_over = Team.objects.create(name="Team Over", balance=50000, total_money_earned=0)
        self.team_inactive = Team.objects.create(name="Team Inactive", balance=50000, total_money_earned=0)

        # 3. Simulate Earnings via TeamLogs
        # (Your get_weekly_match_earnings() method looks for 'calc_rewards' logs)

        # Team Under earned 100k
        TeamLog.objects.create(
            team=self.team_under, user="System", field_name="balance",
            previous_value={"balance": 0}, new_value={"balance": 100000},
            description="Match Reward", method_name="calc_rewards"
        )

        # Team Over earned 400k
        TeamLog.objects.create(
            team=self.team_over, user="System", field_name="balance",
            previous_value={"balance": 0}, new_value={"balance": 400000},
            description="Match Reward", method_name="calc_rewards"
        )

        # Team Inactive gets no logs, so earnings remain 0.

    def test_payout_command_execution(self):
        """Tests that active under-cap teams get paid, over-cap get 0, and inactive get 0."""
        print("\n" + "=" * 50)
        print("TEST: test_payout_command_execution (Weekly Reset Command)")
        print("=" * 50)
        print("[BEFORE] Balances & Earnings:")
        print(f"  - {self.team_under.name}: Balance {self.team_under.balance:,} | Past Earnings 100,000")
        print(f"  - {self.team_over.name}: Balance {self.team_over.balance:,} | Past Earnings 400,000")
        print(f"  - {self.team_inactive.name}: Balance {self.team_inactive.balance:,} | Past Earnings 0")

        # Capture the stdout to verify the success print statement at the end
        out = StringIO()

        # Replace 'your_command_name' with the actual name of your file (e.g., 'process_weekly_payouts')
        print("\n[ACTION] Executing 'weekly_economy_reset' command...")
        call_command('weekly_economy_reset', stdout=out)

        print("\n[COMMAND OUTPUT]")
        print("-" * 30)
        print(out.getvalue().strip())
        print("-" * 30)

        # Refresh teams from DB to get updated balances
        self.team_under.refresh_from_db()
        self.team_over.refresh_from_db()
        self.team_inactive.refresh_from_db()

        print("\n[AFTER] Final Balances:")
        print(f"  - {self.team_under.name}: {self.team_under.balance:,} (Expected: 150,000)")
        print(f"  - {self.team_over.name}: {self.team_over.balance:,} (Expected: 50,000)")
        print(f"  - {self.team_inactive.name}: {self.team_inactive.balance:,} (Expected: 50,000)")

        # --- Assertions ---

        # 1. Under Cap Team: Earned 100k. Deficit = 200k. 50% payout = 100k bonus.
        # Starting balance 50k + 100k bonus = 150k final balance.
        self.assertEqual(self.team_under.balance, 150000)
        self.assertEqual(self.team_under.total_money_earned, 100000)

        # 2. Over Cap Team: Earned 400k. (400k > 300k, fails the 0 < earnings < cap check)
        # Starting balance remains 50k.
        self.assertEqual(self.team_over.balance, 50000)

        # 3. Inactive Team: Earned 0. (fails the 0 < earnings check)
        # Starting balance remains 50k.
        self.assertEqual(self.team_inactive.balance, 50000)

        # Verify the script completed and printed the new global cap
        self.assertIn("Weekly economy reset complete", out.getvalue())