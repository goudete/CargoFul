# Generated by Django 3.0.4 on 2020-05-04 02:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trucker', '0002_truck_company_docs_uploaded'),
    ]

    operations = [
        migrations.AddField(
            model_name='truck_company',
            name='num_units',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
