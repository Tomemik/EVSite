# Generated by Django 5.1.2 on 2024-12-15 14:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sheets', '0020_importcriteria_discount_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='importtank',
            name='criteria',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='import_tanks', to='sheets.importcriteria'),
        ),
    ]