# Generated by Django 5.0.3 on 2024-04-07 12:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0004_alter_categorytransaction_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='categorytransaction',
            name='realize_money',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='categorytransaction',
            name='asset',
            field=models.FloatField(null=True),
        ),
    ]
