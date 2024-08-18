from django.db import models

# Create your models here.


class Category(models.Model):

    class CategoryChoices(models.TextChoices):
        STOCK = "stock", "주식"
        BANK = "bank", "예금"

    name = models.CharField(
        max_length=80,
    )

    owner = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
    )

    classification = models.CharField(
        max_length=10, choices=CategoryChoices.choices, default=CategoryChoices.STOCK
    )

    def __str__(self) -> str:
        return self.name


class CategoryTransaction(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='transaction'
    )

    asset_krw = models.FloatField(default=0)
    asset_usd = models.FloatField(default=0)
    usd_rate = models.FloatField(default=0)
    total_asset = models.FloatField(null=True)
    date = models.DateField(null=True)
    realize_money = models.FloatField(
        default=0
    )

class CategoryTotal(models.Model):
    owner = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
    )

    category_krw_total = models.FloatField(null=True)
    category_usd_total = models.FloatField(null=True)
    usd_rate = models.FloatField(null=True)
    total_asset = models.FloatField(null=True)
    date = models.DateField(null=True)

class CategoryUpdateDate(models.Model):
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
    )

    date = models.DateField(null=True)



