# Generated by Django 5.1a1 on 2024-07-28 11:50

import sheets.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sheets', '0009_teammatch_side'),
    ]

    operations = [
        migrations.AlterField(
            model_name='team',
            name='upgrade_kits',
            field=models.JSONField(default=sheets.models.default_upgrade_kits),
        ),
    ]
