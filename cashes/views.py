from django.shortcuts import render
from rest_framework.status import HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ParseError, PermissionDenied
from .models import Cash, CashTransaction
from .serializers import (
    CashTransactionSerialzer, 
    CashMakingSerializer,
    TinyCashSerializer
    )
from categories.models import Category, CategoryTransaction, CategoryUpdateDate
from categories.serializers import (
    CategoryTransactionsSerializer,
    CategorySerializer, 
    CategoryUpdateDateSerializer,
    )
import pandas as pd
import json
from rest_framework.exceptions import (
    NotFound,
    ParseError,
    PermissionDenied,
    ValidationError,
)


# Create your views here.

class BankList(APIView):
    
    def get(self, request):

        cash_categories = Category.objects.filter(classification="bank", owner=request.user)
        cash_total = []
        cash_json = {}
        for category in cash_categories:
            bank_latest = CategoryTransaction.objects.filter(category=category).order_by("date")
            if bank_latest.exists():
                serializer = CategoryTransactionsSerializer(bank_latest, many=True)
                data = serializer.data

                start_index = 0
                for i, entry in enumerate(data):
                    if entry["total_asset"] > 0:
                        start_index = i
                        break
                
                filterd_data = data[start_index:]
                cash_json[category.name] = filterd_data
        
        update_date_list = CategoryUpdateDate.objects.filter(owner=request.user).order_by("date")
        date_array = [update_date.date for update_date in update_date_list]

        total_asset_df = pd.DataFrame(index=date_array)
        total_asset_df["asset_krw"] = 0
        total_asset_df["asset_usd"] = 0
        total_asset_df["usd_rate"] = 0
        total_asset_df["total_asset"] = 0

        for category in cash_categories:
            bank_total = CategoryTransaction.objects.filter(category=category).order_by("date")
            try :
                bank = Cash.objects.get(category=category)
                print(bank.name)
                serializer = CategoryTransactionsSerializer(bank_total, many=True)
                df = pd.DataFrame(serializer.data)
                df["date"] = pd.to_datetime(df["date"])
                df.set_index("date", inplace=True)
                df.index = df.index.date
                df[f'{bank.name}_asset_krw'] = df["asset_krw"]
                df[f'{bank.name}_asset_usd'] = df["asset_usd"]
                df[f'{bank.name}_total_asset'] = df["total_asset"]

                total_asset_df = pd.concat(
                    [total_asset_df, df[f'{bank.name}_asset_krw']], axis=1, join="outer"
                )
                total_asset_df = pd.concat(
                    [total_asset_df, df[f'{bank.name}_asset_usd']], axis=1, join="outer"
                )
                total_asset_df = pd.concat(
                    [total_asset_df, df[f'{bank.name}_total_asset']], axis=1, join="outer"
                )

                total_asset_df["asset_krw"] = total_asset_df["asset_krw"] + total_asset_df[f'{bank.name}_asset_krw']
                total_asset_df["asset_usd"] = total_asset_df["asset_usd"] + total_asset_df[f'{bank.name}_asset_usd']
                total_asset_df["total_asset"] = total_asset_df["total_asset"] + total_asset_df[f'{bank.name}_total_asset']

            except Cash.DoesNotExist :
                pass

        total_asset_df.index.name = "date"

        total_asset_df.reset_index(inplace=True)
        total_asset_df['date'] = pd.to_datetime(total_asset_df['date']).dt.strftime('%Y-%m-%d')

        total_asset_df = total_asset_df[total_asset_df["total_asset"] != 0]
        print(total_asset_df)
      

        total_data = total_asset_df[["date", "asset_krw", "asset_usd", "total_asset"]].to_dict(orient='records')

        return Response({
            "bank_result" : cash_json,
            "total_result" : total_data,
            })

class CreateBank(APIView):
    permission_classes = [IsAuthenticated]   

    def post(self, request):
        data = request.data
        bank_category = {}
        bank_category["name"] = data["name"]
        bank_category["classification"] = "bank"
        category_serializer = CategorySerializer(data=bank_category)
        if category_serializer.is_valid():
            bank = {}
            bank["name"] = data["name"]
            bank["currency"] = data["currency"]
            bank_serializer = CashMakingSerializer(data=bank)
            if bank_serializer.is_valid():
                bank_trans = {}
                bank_trans["money"] = data["money"]
                bank_trans["date"] = data["date"]
                bank_trans_serializer = CashTransactionSerialzer(data=bank_trans)
                if bank_trans_serializer.is_valid():            
                    new_category = category_serializer.save(
                    owner=request.user
                    )
                    new_bank = bank_serializer.save(
                        owner=request.user,
                        category=new_category
                    )
                    new_bank_trans = bank_trans_serializer.save(
                        cash_name=new_bank
                    )
                    update_date = CategoryUpdateDate.objects.filter(date=data["date"])
                    if not update_date.exists():
                        add_date = {"date" : data["date"]}
                        update_serializer = CategoryUpdateDateSerializer(data=add_date)
                        if update_serializer.is_valid():
                            update_date = update_serializer.save(
                                owner=request.user,
                            )


                    return Response({"result : good"})
                else:
                    raise ValidationError("Invalid Data")
            else :
                raise ValidationError("Invalid Data")
        else :
            raise ValidationError("Invalid Data")
        
class getBank(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        category = Category.objects.get(pk=pk)
        bank = Cash.objects.get(category=category)
        serializer = TinyCashSerializer(bank)
        return Response(serializer.data)
    
    def post(self, request, pk):
        data = request.data
        category = Category.objects.get(pk=pk)
        bank = Cash.objects.get(category=category)
        add_trans = {
            "date" : data["date"],
            "money" : data["money"]
        }
        serializer = CashTransactionSerialzer(data=add_trans)
        if serializer.is_valid():
            updated_trans = serializer.save(
                cash_name = bank
            )
            update_date = CategoryUpdateDate.objects.filter(date=data["date"])
            if not update_date.exists():
                add_date = {"date" : data["date"]}
                update_serializer = CategoryUpdateDateSerializer(data=add_date)
                if update_serializer.is_valid():
                    update_date = update_serializer.save(
                        owner=request.user,
                    )
            return Response({"result" : "good"})
        else : 
            raise ValidationError("Invalid Data")
    



class BankDetail(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk) :
        category = Category.objects.get(pk=pk)
        bank = Cash.objects.get(category=category)
        bank_transaction = bank.transaction.all().order_by("date")
        serializer = CashTransactionSerialzer(bank_transaction, many=True)
        return Response(serializer.data)


class ModifyBankTransaction(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        bank_trans = CashTransaction.objects.get(pk=pk)
        date = bank_trans.date
        money = bank_trans.money
        name = bank_trans.cash_name.name
        return Response({
            "name" : name,
            "date" : date,
            "money" : money,
        })
    
    def put(self, request, pk):
        data = request.data
        money = float(data["money"])
        modify_data = {"money" : money}
        bank_trans = CashTransaction.objects.get(pk=pk)
        cash = bank_trans.cash_name
        serializer = CashTransactionSerialzer(
            bank_trans,
            data= modify_data,
            partial = True,
        )
        if serializer.is_valid():
            updated_transaciont = serializer.save()
        
        return Response({
            "result" : "good"
        })
    






class CashList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, cash):

        cash_category = Category.objects.get(pk=cash)
        if cash_category.owner != request.user:
            raise PermissionDenied
        cashes = cash_category.cash.all()
        cashes_json = {}
        for cash in cashes:
            name = cash.name
            transactions = cash.transaction.all().order_by("date")
            serializer = CashTransactionSerialzer(transactions, many=True)
            cashes_json[name] = serializer.data
        return Response({"result": cashes_json})

    def post(self, request, cash):
        category = Category.objects.get(pk=cash)
        if category.owner != request.user:
            raise PermissionDenied
        serializer = CashMakingSerializer(data=request.data)
        if serializer.is_valid():
            made_cash = serializer.save(
                owner=request.user,
                category=category,
            )
            serializer = CashMakingSerializer(made_cash)
            return Response(serializer.data)


class CashDetial(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, cash, bank):
        bank = Cash.objects.get(pk=bank)
        if bank.owner != request.user:
            raise PermissionDenied
        transactions = bank.transaction.all().order_by("date")
        serializer = CashTransactionSerialzer(transactions, many=True)
        return Response(serializer.data)

    def post(self, request, cash, bank):
        bank = Cash.objects.get(pk=bank)
        data = request.data
        date = data["date"]

        try:
            existing_transaction = bank.transaction.get(date=date)
            raise ParseError(f"{date} is arleady exist")
        except CashTransaction.DoesNotExist:
            serializer = CashTransactionSerialzer(data=request.data)
            if serializer.is_valid():
                updated_bank = serializer.save(
                    cash_name=bank,
                )
                serializer = CashTransactionSerialzer(updated_bank)
                return Response(serializer.data)
            else:
                return Response(serializer.errors)
