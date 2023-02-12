# Generated by Django 4.1.2 on 2023-02-11 16:42

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0012_alter_promocode_options_orderitem_flag_static_price_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='orderitem',
            name='flag_static_price',
        ),
        migrations.AddField(
            model_name='order',
            name='flag_set_static_price',
            field=models.BooleanField(default=False, verbose_name='Статичная цена для orderitem установлена'),
        ),
        migrations.AlterField(
            model_name='promocode',
            name='valid_to',
            field=models.DateTimeField(default=datetime.datetime(2023, 2, 18, 16, 42, 15, 513942, tzinfo=datetime.timezone.utc), verbose_name='Действует до'),
        ),
    ]