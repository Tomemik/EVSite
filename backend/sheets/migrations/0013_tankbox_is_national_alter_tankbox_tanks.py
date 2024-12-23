# Generated by Django 5.1.2 on 2024-12-04 17:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sheets', '0012_alter_match_datetime_alter_teamlog_method_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tankbox',
            name='is_national',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='tankbox',
            name='tanks',
            field=models.ManyToManyField(blank=True, to='sheets.tank'),
        ),
    ]
