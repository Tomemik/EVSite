# Generated by Django 5.1.2 on 2024-12-14 17:25

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sheets', '0018_importtank_available_from'),
    ]

    operations = [
        migrations.AlterField(
            model_name='importtank',
            name='available_from',
            field=models.DateTimeField(default=datetime.datetime(2024, 12, 14, 17, 25, 19, 889661, tzinfo=datetime.timezone.utc)),
        ),
    ]