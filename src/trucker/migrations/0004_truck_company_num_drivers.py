# Generated by Django 3.0.4 on 2020-05-06 00:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trucker', '0003_truck_company_num_units'),
    ]

    operations = [
        migrations.AddField(
            model_name='truck_company',
            name='num_drivers',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
