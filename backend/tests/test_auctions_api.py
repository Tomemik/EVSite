from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient

from sheets.models import (
    Team,
    Tank,
    ImportTank,
    AuctionCycle,
    AuctionCandidate,
    AuctionCandidateSource,
)


User = get_user_model()


class AuctionAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.team = Team.objects.create(
            name="Saunders",
            balance=1_000_000,
        )

        self.tank = Tank.objects.create(
            name="T-72",
            price=100_000,
            battle_rating=5.0,
            rank=3,
            type="MT",
        )

        self.user = User.objects.create_user(
            username="commander",
            password="test-password",
        )

        # Adapt only this assignment if your user/team relationship
        # uses a different field.
        self.user.team = self.team
        self.user.save()

        self.client.force_authenticate(
            user=self.user
        )

    def create_candidate(
        self,
        cycle,
        copies=1,
    ):
        candidate = (
            AuctionCandidate.objects.create(
                cycle=cycle,
                tank=self.tank,
            )
        )

        for index in range(copies):
            available_from = (
                timezone.now()
                - timedelta(
                    days=20 + index
                )
            )

            import_tank = (
                ImportTank.objects.create(
                    tank=self.tank,
                    discount=0,
                    available_from=available_from,
                    available_until=(
                        available_from
                        + timedelta(days=7)
                    ),
                )
            )

            AuctionCandidateSource.objects.create(
                candidate=candidate,
                source_import=import_tank,
            )

        return candidate

    def test_overview_returns_active_and_collecting_cycle(self):
        AuctionCycle.objects.create(
            status=AuctionCycle.Status.COLLECTING,
        )

        AuctionCycle.objects.create(
            status=AuctionCycle.Status.VOTING,
            voting_starts_at=timezone.now(),
            voting_ends_at=(
                timezone.now()
                + timedelta(days=7)
            ),
        )

        response = self.client.get(
            "/api/league/auctions/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "active_cycle",
            response.data,
        )

        self.assertIn(
            "collecting_cycle",
            response.data,
        )

        self.assertIn(
            "server_time",
            response.data,
        )

    def test_cycle_detail(self):
        cycle = AuctionCycle.objects.create(
            status=AuctionCycle.Status.COLLECTING,
        )

        response = self.client.get(
            f"/api/league/auctions/{cycle.pk}/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["id"],
            cycle.pk,
        )

    def test_unknown_cycle_returns_404(self):
        response = self.client.get(
            "/api/league/auctions/999999/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )