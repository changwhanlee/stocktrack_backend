from django.db import models


# Create your models here.
class Stock(models.Model):

    class cashCurrencyChoices(models.TextChoices):
        KRW = ("krw", "원화")
        USD = ("usd", "달러")

    name = models.CharField(
        max_length=80,
    )

    ticker = models.CharField(
        max_length=80,
    )

    currency = models.CharField(
        max_length=20, choices=cashCurrencyChoices, default="krw"
    )

    owner = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
    )

    category = models.ForeignKey(
        "categories.Category", on_delete=models.CASCADE, related_name="stocks"
    )

    def __str__(self) -> str:
        return self.name


class StockTransaction(models.Model):

    owner = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="stocktrnas",
        null=True
    )

    stock = models.ForeignKey(
        Stock, on_delete=models.CASCADE, related_name="transactions"
    )

    amount = models.IntegerField(
        default=0,
    )

    price = models.FloatField(
        default=0,
    )

    date = models.DateField(null=True)

    total_amount = models.IntegerField(
        default=0,
    )

    total_average_price = models.FloatField(
        default=0,
    )

    total_stock_asset = models.FloatField(
        default=0,
    )

    market_price = models.FloatField(
        default=0,
    )

    realize_money = models.FloatField(
        default=0
    )
