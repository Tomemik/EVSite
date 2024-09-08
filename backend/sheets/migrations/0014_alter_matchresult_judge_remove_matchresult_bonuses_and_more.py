# Generated by Django 5.1a1 on 2024-07-31 16:04

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sheets', '0013_alter_matchresult_bonuses_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='matchresult',
            name='judge',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='judged_matches', to='sheets.team'),
        ),
        migrations.RemoveField(
            model_name='matchresult',
            name='bonuses',
        ),
        migrations.RemoveField(
            model_name='matchresult',
            name='penalties',
        ),
        migrations.RemoveField(
            model_name='matchresult',
            name='substitutes',
        ),
        migrations.RemoveField(
            model_name='matchresult',
            name='tanks_lost',
        ),
        migrations.AddField(
            model_name='substitute',
            name='match_result',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sheets.matchresult'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='matchresult',
            name='match',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='sheets.match'),
        ),
        migrations.CreateModel(
            name='TankLost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField()),
                ('match_result', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sheets.matchresult')),
                ('tank', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sheets.tank')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sheets.team')),
            ],
        ),
        migrations.CreateModel(
            name='TeamResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bonuses', models.FloatField(blank=True, null=True)),
                ('penalties', models.FloatField(blank=True, null=True)),
                ('match_result', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='team_results', to='sheets.matchresult')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sheets.team')),
            ],
        ),
        migrations.DeleteModel(
            name='Judge',
        ),
    ]
