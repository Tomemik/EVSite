# Generated by Django 5.1.2 on 2024-10-26 11:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sheets', '0010_alter_teamlog_new_value_alter_teamlog_previous_value'),
    ]

    operations = [
        migrations.AddField(
            model_name='teamtank',
            name='is_trad',
            field=models.BooleanField(default=False),
        ),
    ]