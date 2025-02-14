# Generated by Django 5.1.2 on 2024-12-15 13:49

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sheets', '0019_alter_importtank_available_from'),
    ]

    operations = [
        migrations.AddField(
            model_name='importcriteria',
            name='discount',
            field=models.IntegerField(default=0, help_text='Discount to apply to tanks matching the criteria (0-100%).'),
        ),
        migrations.AddField(
            model_name='importcriteria',
            name='required_tank_discount',
            field=models.IntegerField(default=0, help_text='Additional discount for required tanks (0-100%).'),
        ),
        migrations.AlterField(
            model_name='importtank',
            name='available_from',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
