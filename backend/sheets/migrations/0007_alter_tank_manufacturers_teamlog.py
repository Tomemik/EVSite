# Generated by Django 5.1a1 on 2024-10-06 11:47

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sheets', '0006_remove_team_members'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tank',
            name='manufacturers',
            field=models.ManyToManyField(blank=True, null=True, related_name='tanks', to='sheets.manufacturer'),
        ),
        migrations.CreateModel(
            name='TeamLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_name', models.CharField(max_length=50)),
                ('previous_value', models.TextField(blank=True, null=True)),
                ('new_value', models.TextField(blank=True, null=True)),
                ('change_timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='sheets.team')),
            ],
        ),
    ]