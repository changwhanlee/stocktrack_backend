# Generated by Django 5.0.3 on 2024-03-30 03:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stocks', '0004_stocktransaction_total_amount_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='stocktransaction',
            name='market_price',
            field=models.FloatField(default=0),
        ),
    ]
