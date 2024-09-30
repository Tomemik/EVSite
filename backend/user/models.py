import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from sheets.models import Team


class User(AbstractUser):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(
        max_length=50, unique=True,
    )
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members', null=True, blank=True, default=None)

    class Meta:
        permissions = (
            ("commander_permissions", "Is a team Commander"),
            ("judge_permissions", "Is a judge"),
            ("admin_permissions", "Is an admin"),
        )