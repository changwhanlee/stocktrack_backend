from rest_framework import serializers
from .models import CategoryTransaction, Category, CategoryTotal, CategoryUpdateDate
from users.serializers import TinyUserSerializer




class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("pk", "name", "classification")

class CategoryTransactionsSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    class Meta:
        model = CategoryTransaction
        fields = "__all__"

class CategoryFullSerializer(serializers.ModelSerializer):
    owner = TinyUserSerializer(read_only=True)

    class Meta:
        model = Category
        fields = "__all__"


class CategoryTotalSerializer(serializers.ModelSerializer):
    owner = TinyUserSerializer(read_only=True)

    class Meta:
        model = CategoryTotal
        fields = "__all__"

class CategoryUpdateDateSerializer(serializers.ModelSerializer):
    owner = TinyUserSerializer(read_only=True)

    class Meta:
        model = CategoryUpdateDate
        fields = "__all__"
