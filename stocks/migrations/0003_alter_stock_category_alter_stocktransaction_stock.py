# Generated by Django 5.0.3 on 2024-03-30 00:55

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0004_alter_categorytransaction_category'),
        ('stocks', '0002_stocktransaction'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stock',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stocks', to='categories.category'),
        ),
        migrations.AlterField(
            model_name='stocktransaction',
            name='stock',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='stocks.stock'),
        ),
    ]
