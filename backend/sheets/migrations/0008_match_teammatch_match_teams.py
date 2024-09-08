# Generated by Django 5.1a1 on 2024-07-28 11:34

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sheets', '0007_tank_rank_tank_type_alter_tank_battle_rating_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Match',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime', models.DateTimeField()),
                ('mode', models.CharField(choices=[('traditional', 'Traditional'), ('advanced', 'Advanced'), ('evolved', 'Evolved')], max_length=50)),
                ('gamemode', models.CharField(choices=[('annihilation', 'Annihilation'), ('domination', 'Domination'), ('flag_tank', 'Flag Tank')], max_length=50)),
                ('best_of_number', models.IntegerField()),
                ('map_selection', models.CharField(max_length=255)),
                ('money_rules', models.CharField(choices=[('money_rule', 'Money Rule'), ('even_split', 'Even Split')], max_length=50)),
                ('special_rules', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='TeamMatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('match', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sheets.match')),
                ('tanks', models.ManyToManyField(related_name='team_matches', to='sheets.tank')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sheets.team')),
            ],
        ),
        migrations.AddField(
            model_name='match',
            name='teams',
            field=models.ManyToManyField(related_name='matches', through='sheets.TeamMatch', to='sheets.team'),
        ),
    ]
