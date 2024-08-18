from django.contrib import admin
from .models import Stock, StockTransaction
# Register your models here.

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
        "category",
    )

@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "stock",
        "amount",
        "price",
        "date",
    )
