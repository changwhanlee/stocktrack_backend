from rest_framework import serializers
from .models import Cash, CashTransaction
from categories.serializers import CategorySerializer
from users.serializers import TinyUserSerializer


class TinyCashSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cash
        fields = ("name", "currency")

class CashTransactionSerialzer(serializers.ModelSerializer):

    cash_name = TinyCashSerializer(read_only=True)

    class Meta:
        model = CashTransaction
        fields = "__all__"

class CashMakingSerializer(serializers.ModelSerializer):

    category = CategorySerializer(read_only = True)
    owner = TinyUserSerializer(read_only=True)

    class Meta:
        model = Cash
        fields = "__all__"