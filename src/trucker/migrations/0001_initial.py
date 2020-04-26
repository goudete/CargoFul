# Generated by Django 3.0.4 on 2020-04-24 21:04

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('shipper', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='driver',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_approved', models.BooleanField(default=False)),
                ('fname', models.CharField(max_length=30)),
                ('lname', models.CharField(max_length=50)),
                ('orders_completed', models.PositiveIntegerField(default=0)),
                ('rating', models.PositiveIntegerField(default=0, validators=[django.core.validators.MaxValueValidator(5)])),
            ],
        ),
        migrations.CreateModel(
            name='truck_company',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number_of_active_orders', models.IntegerField(default=0)),
                ('completed_orders', models.PositiveIntegerField(default=0)),
                ('incomplete_orders', models.PositiveIntegerField(default=0)),
                ('rating', models.PositiveIntegerField(default=0, validators=[django.core.validators.MaxValueValidator(5)])),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='trucks',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('licence_plate', models.CharField(max_length=15)),
                ('truck_type', models.CharField(choices=[('Low Boy', 'Low Boy'), ('Caja Seca 48 pies', 'Caja Seca 48 pies'), ('Refrigerado 48 pies', 'Refrigerado 48 pies'), ('Plataforma 48 pies', 'Plataforma 48 pies'), ('Caja Seca 53 pies', 'Caja Seca 53 pies'), ('Refrigerado 53 pies', 'Refrigerado 53 pies'), ('Plataforma 53 pies', 'Plataforma 53 pies'), ('Full', 'Full'), ('Plataforma Full', 'Plataforma Full'), ('Torton Caja Seca', 'Torton Caja Seca'), ('Torton Refrigerado', 'Torton Refrigerado'), ('Troton Plataforma', 'Troton Plataforma'), ('Rabon Caja Seca', 'Rabon Caja Seca'), ('Rabon Refrigerado', 'Rabon Refrigerado'), ('Rabon Plataforma', 'Rabon Plataforma'), ('Camioneta 5.5 tons', 'Camioneta 5.5 tons'), ('Camioneta 3.5 tons', 'Camioneta 3.5 tons'), ('Camioneta 3.5 tons Plataforma', 'Camioneta 3.5 tons Plataforma'), ('Camioneta 1.5 tons', 'Camioneta 1.5 tons'), ('Camioneta 3.5 tons Redilla', 'Camioneta 3.5 tons Redilla')], default='LB', max_length=40)),
                ('year', models.PositiveIntegerField(default=0)),
                ('available_capacity', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('driver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trucker.driver')),
                ('truck_company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trucker.truck_company')),
            ],
        ),
        migrations.AddField(
            model_name='driver',
            name='truck_company',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trucker.truck_company'),
        ),
        migrations.AddField(
            model_name='driver',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='counter_offer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('counter_price', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.PositiveIntegerField(default=0, validators=[django.core.validators.MaxValueValidator(3)])),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='shipper.order')),
                ('trucker_user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='trucker.truck_company')),
            ],
        ),
    ]
