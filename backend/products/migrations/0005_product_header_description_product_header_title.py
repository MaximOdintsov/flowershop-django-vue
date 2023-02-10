# Generated by Django 4.1.2 on 2023-02-03 12:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0004_alter_product_slug_alter_productcomponent_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='header_description',
            field=models.TextField(blank=True, null=True, verbose_name='Описание продукта'),
        ),
        migrations.AddField(
            model_name='product',
            name='header_title',
            field=models.TextField(blank=True, null=True, verbose_name='Название заголовка'),
        ),
    ]