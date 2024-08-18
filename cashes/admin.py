from django.contrib import admin
from .models import Cash, CashTransaction

# Register your models here.
@admin.register(Cash)
class CashAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
        "category"
    )

    fields = ("name", "currency", "owner","category")


@admin.register(CashTransaction)
class CashTransactionAdmin(admin.ModelAdmin):
    list_display = ("cash_name", "money", "date")