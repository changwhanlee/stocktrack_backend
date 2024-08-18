from django.contrib import admin
from .models import Category, CategoryTransaction, CategoryTotal, CategoryUpdateDate

# Register your models here.


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
    )


@admin.register(CategoryTransaction)
class CategoryTransactionsAdmin(admin.ModelAdmin):
    list_display = (
        "category",
        "total_asset",
        "asset_krw",
        "asset_usd",
        "date",
    )

    ordering = ('category', 'date')

@admin.register(CategoryTotal)
class CategoryTotalAdmin(admin.ModelAdmin):
    list_display = (
        "owner",
        "category_krw_total",
        "category_usd_total",
        "usd_rate",
        "total_asset",
        "date",
    )
    ordering = ('date',)

@admin.register(CategoryUpdateDate)
class CategoryUpdateDateAdmin(admin.ModelAdmin):
    list_display = (
        "owner",
        "date",
    )
