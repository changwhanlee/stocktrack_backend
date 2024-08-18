from django.db import models


# Create your models here.
class Cash(models.Model):

    class cashCurrencyChoices(models.TextChoices):
        KRW = ("krw", "원화")
        USD = ("usd", "달러")

    name = models.CharField(
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
        "categories.Category",
        on_delete=models.CASCADE,
        related_name = "cash"
    )

    def __str__(self) -> str:
        return self.name

class CashTransaction(models.Model):
    cash_name = models.ForeignKey(
        Cash,
        on_delete=models.CASCADE,
        related_name = "transaction"
    )

    money = models.PositiveIntegerField(
        default=0,
    )
    date = models.DateField(null=True)
