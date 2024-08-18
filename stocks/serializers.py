from rest_framework import serializers
from .models import StockTransaction, Stock
from categories.serializers import CategorySerializer
from users.serializers import TinyUserSerializer


class StockSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Stock
        fields = ("pk", "name", "ticker", "category", "currency")


class StockTransactionSerializer(serializers.ModelSerializer):
    stock = StockSerializer(read_only = True)

    class Meta:
        model = StockTransaction
        fields = "__all__"

class StockMakingSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    owner = TinyUserSerializer(read_only=True)
    
    class Meta:
        model = Stock
        fields = "__all__"    

