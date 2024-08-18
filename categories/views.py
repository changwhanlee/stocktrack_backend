from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ParseError
from .models import Category, CategoryTransaction, CategoryTotal, CategoryUpdateDate
from .serializers import (
    CategoryTransactionsSerializer, 
    CategoryFullSerializer, 
    CategorySerializer, 
    CategoryTotalSerializer,
    CategoryUpdateDateSerializer)
from datetime import datetime, timedelta
import yfinance as yf
from stocks.models import StockTransaction, Stock
from stocks.serializers import StockTransactionSerializer
from cashes.models import Cash, CashTransaction
from cashes.serializers import CashTransactionSerialzer, CashMakingSerializer
import pandas as pd
from pandas_datareader import data as pdr
from datetime import datetime, timedelta
import yfinance as yf
from rest_framework.exceptions import (
    NotFound,
    ParseError,
    PermissionDenied,
    ValidationError,
)
# Create your views here.

class CategoriesName(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        categories_name = Category.objects.filter(owner=request.user)
        serializer = CategorySerializer(categories_name, many=True)
        return Response(serializer.data)


class CategoriesList(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        categories = Category.objects.filter(owner=request.user)
        categories_json = {}
        for category in categories :
            name = category.name
            transactions = category.transaction.all().order_by('date')
            serializer = CategoryTransactionsSerializer(transactions, many=True)
            categories_json[name] = serializer.data

        return Response(
            {
                "result" : categories_json
            }
        )
    
    def post(self, request):
        serializer = CategoryFullSerializer(data=request.data)
        if serializer.is_valid():
            create_category = serializer.save(
                owner = request.user
            )
            serializer = CategoryFullSerializer(create_category)
            cat_id = create_category.pk
            return Response(
                { "result" : cat_id }
            )
        else:
            return Response(serializer.errors)


class CategoryView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, cat):
        isMyCat = Category.objects.get(pk=cat)
        if isMyCat.owner != request.user:
            raise PermissionError
        
        transactions = isMyCat.transaction.all().order_by("date")
        serializer = CategoryTransactionsSerializer(transactions, many=True)
        return Response(serializer.data)

class UpdateDate(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        update_date_list =  CategoryUpdateDate.objects.filter(owner=request.user).order_by("date")
        if not update_date_list.exists():
            total_trans = CategoryTotal.objects.filter(owner=request.user).order_by("date")
            total_serializer = CategoryTotalSerializer(total_trans, many=True)
            return Response(total_serializer.data)
        
        date_array = [update_date.date for update_date in update_date_list]

        today = datetime.today()
        tomorrow = today +timedelta(days=1)
        one_week_ago = today - timedelta(days=7)
        today_str = today.strftime('%Y-%m-%d')
        tomorrow_str = tomorrow.strftime('%Y-%m-%d')
        one_week_ago_str = one_week_ago.strftime('%Y-%m-%d')

        """미국, 한국주식 공통의 최신날짜 찾기"""
        SPY = yf.download('SPY', start=one_week_ago_str, end=tomorrow_str)
        KOSPI = yf.download('^KS200', start=one_week_ago_str, end=tomorrow_str)
        common_dates = SPY.index.intersection(KOSPI.index)
        latest_common_date = common_dates.max().date()

        if latest_common_date in date_array:
            total_trans = CategoryTotal.objects.filter(owner=request.user).order_by("date")
            total_serializer = CategoryTotalSerializer(total_trans, many=True)
            return Response(total_serializer.data)
        
        else :
            date_array.append(latest_common_date)
            add_date = {"date" : latest_common_date}
            date_serializer = CategoryUpdateDateSerializer(data=add_date)
            if date_serializer.is_valid():
                date_serializer.save(owner=request.user)
            
        start_day = date_array[0]
        end_day = date_array[-1] + timedelta(days=1)
        total_asset_df = pd.DataFrame(index=date_array)
        exchange_rate = yf.download('KRW=X', start=start_day, end=end_day)
        exchange_rate.index = exchange_rate.index.date
        exchange_rate = exchange_rate.reindex(total_asset_df.index)
        total_asset_df["usd_rate"] = exchange_rate["Adj Close"]
        total_asset_df["category_krw_total"] = 0
        total_asset_df["category_usd_total"] = 0
        total_asset_df["total_asset"] = 0

        categories = Category.objects.filter(owner=request.user)
        for category in categories:
            category_total_df = pd.DataFrame(index=date_array)
            category_total_df["asset_krw"] = 0
            category_total_df["asset_usd"] = 0
            category_total_df["usd_rate"] = total_asset_df["usd_rate"]
            category_total_df["total_asset"] = 0
            category_total_df["realize_money"] = 0

            if category.classification == "stock":
                stocks = Stock.objects.filter(category=category)
                for stock in stocks:
                    stock_trans = StockTransaction.objects.filter(stock=stock)
                    if stock_trans.exists():
                        serializer = StockTransactionSerializer(stock_trans, many=True)
                        df = pd.DataFrame(serializer.data)
                        df["date"] = pd.to_datetime(df["date"])
                        df.set_index("date", inplace=True)
                        df.index = df.index.date
                        df[f'{stock.name}_amount'] = df["total_amount"]
                        df[f'{stock.name}_realize_money'] = df["realize_money"]
                        stock_price = yf.download(stock.ticker, start=start_day, end=end_day)
                        stock_price.index = stock_price.index.date
                        stock_price = stock_price.reindex(category_total_df.index)
                        stock_price[f'{stock.name}_price'] = stock_price["Adj Close"]

                        category_total_df = pd.concat(
                            [category_total_df, df[f'{stock.name}_amount']], axis=1, join="outer"
                        )
                        category_total_df = pd.concat(
                            [category_total_df, df[f'{stock.name}_realize_money']], axis=1, join="outer"
                        )
                        category_total_df = pd.concat(
                            [category_total_df, stock_price[f'{stock.name}_price']], axis=1, join="outer"
                        )
                    else :
                        pass

                stock_name_list = [stock.name for stock in stocks]
                for stock_name in stock_name_list:
                    first_valid_index = category_total_df[f'{stock_name}_amount'].first_valid_index()
                    category_total_df.loc[:first_valid_index, f'{stock_name}_amount'] = category_total_df.loc[
                        :first_valid_index, f'{stock_name}_amount'
                    ].fillna(0)
                    category_total_df.loc[:first_valid_index, f'{stock_name}_realize_money'] = category_total_df.loc[
                        :first_valid_index, f'{stock_name}_realize_money'
                    ].fillna(0)
                category_total_df.fillna(method="ffill", inplace=True)

                for stock in stocks:
                    if stock.currency == "usd":
                        category_total_df["asset_usd"] = category_total_df["asset_usd"] + \
                        (category_total_df[f'{stock.name}_amount'] * category_total_df[f'{stock.name}_price'])
                        category_total_df["realize_money"] = category_total_df["realize_money"] + \
                        (category_total_df[f'{stock.name}_realize_money'] * category_total_df["usd_rate"])
                    if stock.currency == "krw":
                        category_total_df["asset_krw"] = category_total_df["asset_krw"] + \
                        (category_total_df[f'{stock.name}_amount'] * category_total_df[f'{stock.name}_price'])
                        category_total_df["realize_money"] = category_total_df["realize_money"] + \
                        (category_total_df[f'{stock.name}_realize_money'])

                category_total_df["total_asset"] = category_total_df["asset_krw"] + \
                (category_total_df["asset_usd"]*category_total_df["usd_rate"]) 
            
            elif category.classification == "bank":
                banks = Cash.objects.filter(category=category)
                for bank in banks:
                    bank_trans = CashTransaction.objects.filter(cash_name=bank)
                    serializer = CashTransactionSerialzer(bank_trans, many=True)
                    df = pd.DataFrame(serializer.data)
                    df["date"] = pd.to_datetime(df["date"])
                    df.set_index("date", inplace=True)
                    df.index = df.index.date
                    df[f'{bank.name}_total_asset'] = df["money"]

                    category_total_df = pd.concat(
                        [category_total_df, df[f'{bank.name}_total_asset']], axis=1, join="outer"
                    )
                
                bank_name_list = [bank.name for bank in banks]
                for bank.name in bank_name_list:
                    first_valid_index = category_total_df[f'{bank.name}_total_asset'].first_valid_index()
                    category_total_df.loc[:first_valid_index, f'{bank.name}_total_asset'] = category_total_df.loc[
                        :first_valid_index, f'{bank.name}_total_asset'
                    ].fillna(0)
                category_total_df.fillna(method="ffill", inplace=True)

                for bank in banks:
                    if bank.currency == "usd":
                        category_total_df["asset_usd"] = category_total_df["asset_usd"] + \
                            category_total_df[f'{bank.name}_total_asset']
                    if bank.currency == "krw":
                        category_total_df["asset_krw"] = category_total_df["asset_krw"] + \
                            category_total_df[f'{bank.name}_total_asset']
                
                category_total_df["total_asset"] = category_total_df["asset_krw"] +\
                    (category_total_df["asset_usd"] * category_total_df["usd_rate"])
                
            for i in range(len(category_total_df)):
                date = category_total_df.index[i]
                date_asset_krw = category_total_df.loc[date, "asset_krw"]
                date_asset_usd = category_total_df.loc[date, "asset_usd"]
                date_asset_total = category_total_df.loc[date, "total_asset"]
                date_usd_rate = category_total_df.loc[date, "usd_rate"]
                date_realize_money = category_total_df.loc[date, "realize_money"]
                is_category_trans_exist = CategoryTransaction.objects.filter(category=category, date=date).exists()

                if is_category_trans_exist:
                    category_trans = CategoryTransaction.objects.get(
                        category=category, date=date
                    )
                    if category_trans.total_asset != date_asset_total:
                        category_trans.asset_krw = date_asset_krw
                        category_trans.asset_usd = date_asset_usd
                        category_trans.usd_rate = date_usd_rate
                        category_trans.total_asset = date_asset_total
                        category_trans.realize_money = date_realize_money
                        category_trans.save()
                elif not is_category_trans_exist :
                    data = {
                        "asset_krw" : date_asset_krw,
                        "asset_usd" : date_asset_usd,
                        "usd_rate" : date_usd_rate,
                        "total_asset" : date_asset_total,
                        "date" : date,
                        "realize_money" : date_realize_money,
                    }
                    serializer = CategoryTransactionsSerializer(data=data)
                    if serializer.is_valid():
                        category_trans = serializer.save(category=category)
                    else:
                        raise ValidationError("Invalid data")
        

            total_asset_df["category_krw_total"] = total_asset_df["category_krw_total"] + category_total_df["asset_krw"]
            total_asset_df["category_usd_total"] = total_asset_df["category_usd_total"] + category_total_df["asset_usd"]
            total_asset_df["total_asset"] = total_asset_df["total_asset"] + category_total_df["total_asset"]
        
        for i in range(len(total_asset_df)):
            date = total_asset_df.index[i]
            date_krw_total = total_asset_df.loc[date, "category_krw_total"]
            date_usd_total = total_asset_df.loc[date, "category_usd_total"]
            date_usd_rate = total_asset_df.loc[date, "usd_rate"]
            date_total = total_asset_df.loc[date, "total_asset"]
            is_category_total_exist = CategoryTotal.objects.filter(owner=request.user, date=date)

            if is_category_total_exist:
                category_total = CategoryTotal.objects.get(owner=request.user, date=date)
                if category_total.total_asset != date_total:
                    category_total.category_krw_total = date_krw_total
                    category_total.category_usd_total = date_usd_total
                    category_total.total_asset = date_total
                    category_total.usd_rate = date_usd_rate
                    category_total.save()
            elif not is_category_total_exist:
                data = {
                    "category_krw_total" : date_krw_total,
                    "category_usd_total" : date_usd_total,
                    "usd_rate" : date_usd_rate,
                    "total_asset" : date_total,
                    "date" : date,
                }
                serializer = CategoryTotalSerializer(data=data)
                if serializer.is_valid():
                    category_total_trans = serializer.save(owner=request.user)
                else:
                    raise ValidationError("Invalid data")
        
        total_trans = CategoryTotal.objects.filter(owner=request.user).order_by("date")
        total_serializer = CategoryTotalSerializer(total_trans, many=True)
        return Response(total_serializer.data)


        """
        category_total = CategoryTotal.objects.filter(owner=request.user).order_by("date")
        if not category_total.exists():
            return Response({"result" : "Category Total doesn't exsit"})
        category_last_date = datetime.combine(category_total.last().date, datetime.min.time())
        print(category_last_date)
        print(day_update)
        if day_update == category_last_date:
            total_trans = CategoryTotal.objects.filter(owner=request.user)
            total_serializer = CategoryTotalSerializer(total_trans, many=True)
            return Response(total_serializer.data)
        
        
        exchange_rate = yf.download('KRW=X', start=day_update_past, end=day_update_tomorrow)
        exchange_rate = exchange_rate['Adj Close'].iloc[-1]

        total_update_obj = {
            "category_krw_total" : 0,
            "category_usd_total" : 0,
            "usd_rate" : exchange_rate,
            "total_asset" : 0,
            "date" : day_update.strftime('%Y-%m-%d'),
        }

        categories = Category.objects.filter(owner=request.user)
        for category in categories:
            category_trans = category.transaction.all().order_by("date").last()
            if category_trans is None:
                print('----------------category_trans empty------------')
                continue

            if category.classification == "stock":
                category_update_obj = {
                    "asset_krw" : 0,
                    "asset_usd" : 0,
                    "usd_rate" : exchange_rate,
                    "total_asset" : 0,
                    "date" : day_update.strftime('%Y-%m-%d'),
                    "realize_money" : category_trans.realize_money,
                }
                print(category_update_obj)
                print(category.name)
                
                stocks = category.stocks.all()
                print(stocks)
            
                for stock in stocks:
                    try :
                        stock_last = stock.transactions.all().order_by("date").last()
                        stock_currency = stock.currency
                        stock_ticker = stock.ticker
                        total_amount = stock_last.total_amount
                        market_price = yf.download(stock_ticker, start=day_update_past, end=day_update_tomorrow)
                        market_price = market_price['Adj Close'].iloc[-1]
                        total_stock_asset = total_amount * market_price
                        if stock_currency == "usd":
                            category_update_obj["asset_usd"] = category_update_obj["asset_usd"] + total_stock_asset 
                        elif stock_currency == "krw":
                            category_update_obj["asset_krw"] = category_update_obj["asset_krw"] + total_stock_asset
                    except AttributeError:
                        print("no transaction")
                        continue
                
                category_update_obj["total_asset"] = category_update_obj['asset_krw'] \
                    + (category_update_obj["asset_usd"] * category_update_obj["usd_rate"])
                serializer = CategoryTransactionsSerializer(data=category_update_obj)
                if serializer.is_valid():
                    category_transaction = serializer.save(
                        category=category,
                    )
                
            elif category.classification == "bank":
                category_update_obj = {
                    "asset_krw" : category_trans.asset_krw,
                    "asset_usd" : category_trans.asset_usd,
                    "usd_rate" : exchange_rate,
                    "total_asset" : category_trans.asset_krw + \
                        (category_trans.asset_usd * exchange_rate),
                    "date" : day_update.strftime('%Y-%m-%d'),
                    "realize_money" : 0,
                }
                serializer = CategoryTransactionsSerializer(data=category_update_obj)
                if serializer.is_valid():
                    category_trans = serializer.save(
                        category=category
                    )
            
            total_update_obj["category_krw_total"] = total_update_obj["category_krw_total"] + category_update_obj["asset_krw"]
            total_update_obj["category_usd_total"] = total_update_obj["category_usd_total"] + category_update_obj["asset_usd"]
            total_update_obj["total_asset"] = total_update_obj["total_asset"] + category_update_obj["total_asset"]

        serializer = CategoryTotalSerializer(data=total_update_obj)
        if serializer.is_valid():
            category_total_update = serializer.save(
                owner = request.user,
            )
        total_trans = CategoryTotal.objects.filter(owner=request.user).order_by("date")
        total_serializer = CategoryTotalSerializer(total_trans, many=True)


        total_asset = CategoryTotal.objects.filter(owner=request.user).order_by("date")
        return Response(total_serializer.data)"""
        
class UpdateTrans(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        update_date_list =  CategoryUpdateDate.objects.filter(owner=request.user).order_by("date")
        date_array = [update_date.date for update_date in update_date_list]
        print(date_array)

        """미국, 한국주식 공통의 최신 날짜 찾기"""
        today = datetime.today()
        tomorrow = today + timedelta(days=1)
        tomorrow_str = tomorrow.strftime('%Y-%m-%d')
        one_week_ago = today - timedelta(days=7)
        today_str = today.strftime('%Y-%m-%d')
        one_week_ago_str = one_week_ago.strftime('%Y-%m-%d')
        SPY = yf.download('SPY', start=one_week_ago_str, end=tomorrow_str)
        KOSPI = yf.download('^KS200', start=one_week_ago_str, end=tomorrow_str)
        common_dates = SPY.index.intersection(KOSPI.index)
        latest_common_date = common_dates.max().date()

        """공통의 최신 날짜가 categoryUpdateDate에 있는지 확인"""
        if latest_common_date not in date_array:
            date_array.append(latest_common_date)
            add_date = {"date" : latest_common_date}
            serializer = CategoryUpdateDateSerializer(data=add_date)
            if serializer.is_valid():
                serializer.save(owner=request.user)
            
        
        start_day = date_array[0]
        end_day = date_array[-1] + timedelta(days=1)

        total_asset_df = pd.DataFrame(index=date_array)
        exchange_rate = yf.download('KRW=X', start=start_day, end=end_day)
        exchange_rate.index = exchange_rate.index.date
        exchange_rate = exchange_rate.reindex(total_asset_df.index)
        total_asset_df["usd_rate"] = exchange_rate["Adj Close"]
        total_asset_df["category_krw_total"] = 0
        total_asset_df["category_usd_total"] = 0
        total_asset_df["total_asset"] = 0

        categories = Category.objects.filter(owner=request.user)
        category_stocks_total = {}
        for category in categories:
            category_total_df = pd.DataFrame(index=date_array)
            category_total_df["asset_krw"] = 0
            category_total_df["asset_usd"] = 0
            category_total_df["usd_rate"] = total_asset_df["usd_rate"]
            category_total_df["total_asset"] = 0
            category_total_df["realize_money"] = 0
            
            if category.classification == "stock":
                stocks = Stock.objects.filter(category=category)
                for stock in stocks:
                    stock_trans = StockTransaction.objects.filter(stock=stock)
                    if stock_trans.exists():
                        serializer = StockTransactionSerializer(stock_trans, many=True)
                        df = pd.DataFrame(serializer.data)
                        df["date"] = pd.to_datetime(df["date"])
                        df.set_index("date", inplace=True)
                        df.index = df.index.date
                        df[f'{stock.name}_amount'] = df["total_amount"]
                        df[f'{stock.name}_realize_money'] = df["realize_money"]
                        stock_price = yf.download(stock.ticker, start=start_day, end=end_day)
                        stock_price.index = stock_price.index.date
                        stock_price = stock_price.reindex(category_total_df.index)
                        stock_price[f'{stock.name}_price'] = stock_price["Adj Close"]

                        category_total_df = pd.concat(
                            [category_total_df, df[f'{stock.name}_amount']], axis=1, join="outer"
                        )
                        category_total_df = pd.concat(
                            [category_total_df, df[f'{stock.name}_realize_money']], axis=1, join="outer"
                        )
                        category_total_df = pd.concat(
                            [category_total_df, stock_price[f'{stock.name}_price']], axis=1, join="outer"
                        )
                    else :
                        pass

                stock_name_list = [stock.name for stock in stocks]
                for stock_name in stock_name_list:
                    first_valid_index = category_total_df[f'{stock_name}_amount'].first_valid_index()
                    category_total_df.loc[:first_valid_index, f'{stock_name}_amount'] = category_total_df.loc[
                        :first_valid_index, f'{stock_name}_amount'
                    ].fillna(0)
                    category_total_df.loc[:first_valid_index, f'{stock_name}_realize_money'] = category_total_df.loc[
                        :first_valid_index, f'{stock_name}_realize_money'
                    ].fillna(0)
                category_total_df.fillna(method="ffill", inplace=True)

                
                

                for stock in stocks:
                    if stock.currency == "usd":
                        category_total_df["asset_usd"] = category_total_df["asset_usd"] + \
                            (category_total_df[f'{stock.name}_amount'] * category_total_df[f'{stock.name}_price'])
                        category_total_df["realize_money"] = category_total_df["realize_money"] + \
                            (category_total_df[f'{stock.name}_realize_money'] * category_total_df["usd_rate"])
                        category_total_df[f'{stock.name}_total'] = category_total_df[f'{stock.name}_amount'] * \
                            category_total_df[f'{stock.name}_price'] * category_total_df["usd_rate"]
                        
                    elif stock.currency == "krw":
                        category_total_df["asset_krw"] = category_total_df["asset_krw"] + \
                            (category_total_df[f'{stock.name}_amount'] * category_total_df[f'{stock.name}_price'])
                        category_total_df["realize_money"] = category_total_df["realize_money"] + \
                            (category_total_df[f'{stock.name}_realize_money'])
                        category_total_df[f'{stock.name}_total'] = category_total_df[f'{stock.name}_amount'] * \
                            category_total_df[f'{stock.name}_price']

                category_total_df["total_asset"] = category_total_df["asset_krw"] + \
                (category_total_df["asset_usd"]*category_total_df["usd_rate"]) 

                data_list = []
                for idx, row in category_total_df.iterrows():
                    data_obj = {}
                    data_obj["date"] = idx
                    for stock in stocks:
                        data_obj[f'{stock.name}'] = row[f'{stock.name}_total']
                    data_obj["total_asset"] = row['total_asset']
                    data_list.append(data_obj)

                category_stocks_total[f'{category.name}'] = data_list
                print(category_stocks_total)


                      
                
                
            

            elif category.classification == "bank":
                banks = Cash.objects.filter(category=category)
                for bank in banks:
                    bank_trans = CashTransaction.objects.filter(cash_name=bank)
                    serializer = CashTransactionSerialzer(bank_trans, many=True)
                    df = pd.DataFrame(serializer.data)
                    df["date"] = pd.to_datetime(df["date"])
                    df.set_index("date", inplace=True)
                    df.index = df.index.date
                    df[f'{bank.name}_total_asset'] = df["money"]

                    category_total_df = pd.concat(
                        [category_total_df, df[f'{bank.name}_total_asset']], axis=1, join="outer"
                    )
                
                bank_name_list = [bank.name for bank in banks]
                for bank.name in bank_name_list:
                    first_valid_index = category_total_df[f'{bank.name}_total_asset'].first_valid_index()
                    category_total_df.loc[:first_valid_index, f'{bank.name}_total_asset'] = category_total_df.loc[
                        :first_valid_index, f'{bank.name}_total_asset'
                    ].fillna(0)
                category_total_df.fillna(method="ffill", inplace=True)

                for bank in banks:
                    if bank.currency == "usd":
                        category_total_df["asset_usd"] = category_total_df["asset_usd"] + \
                            category_total_df[f'{bank.name}_total_asset']
                    if bank.currency == "krw":
                        category_total_df["asset_krw"] = category_total_df["asset_krw"] + \
                            category_total_df[f'{bank.name}_total_asset']
                
                category_total_df["total_asset"] = category_total_df["asset_krw"] +\
                    (category_total_df["asset_usd"] * category_total_df["usd_rate"])
            

                
            for i in range(len(category_total_df)):
                date = category_total_df.index[i]
                date_asset_krw = category_total_df.loc[date, "asset_krw"]
                date_asset_usd = category_total_df.loc[date, "asset_usd"]
                date_asset_total = category_total_df.loc[date, "total_asset"]
                date_usd_rate = category_total_df.loc[date, "usd_rate"]
                date_realize_money = category_total_df.loc[date, "realize_money"]
                is_category_trans_exist = CategoryTransaction.objects.filter(category=category, date=date).exists()

                if is_category_trans_exist:
                    category_trans = CategoryTransaction.objects.get(
                        category=category, date=date
                    )
                    if category_trans.total_asset != date_asset_total:
                        category_trans.asset_krw = date_asset_krw
                        category_trans.asset_usd = date_asset_usd
                        category_trans.usd_rate = date_usd_rate
                        category_trans.total_asset = date_asset_total
                        category_trans.realize_money = date_realize_money
                        category_trans.save()
                elif not is_category_trans_exist :
                    data = {
                        "asset_krw" : date_asset_krw,
                        "asset_usd" : date_asset_usd,
                        "usd_rate" : date_usd_rate,
                        "total_asset" : date_asset_total,
                        "date" : date,
                        "realize_money" : date_realize_money,
                    }
                    serializer = CategoryTransactionsSerializer(data=data)
                    if serializer.is_valid():
                        category_trans = serializer.save(category=category)
                    else:
                        raise ValidationError("Invalid data")
        

            total_asset_df["category_krw_total"] = total_asset_df["category_krw_total"] + category_total_df["asset_krw"]
            total_asset_df["category_usd_total"] = total_asset_df["category_usd_total"] + category_total_df["asset_usd"]
            total_asset_df["total_asset"] = total_asset_df["total_asset"] + category_total_df["total_asset"]
        
        for i in range(len(total_asset_df)):
            date = total_asset_df.index[i]
            date_krw_total = total_asset_df.loc[date, "category_krw_total"]
            date_usd_total = total_asset_df.loc[date, "category_usd_total"]
            date_usd_rate = total_asset_df.loc[date, "usd_rate"]
            date_total = total_asset_df.loc[date, "total_asset"]
            is_category_total_exist = CategoryTotal.objects.filter(owner=request.user, date=date)

            if is_category_total_exist:
                category_total = CategoryTotal.objects.get(owner=request.user, date=date)
                if category_total.total_asset != date_total:
                    category_total.category_krw_total = date_krw_total
                    category_total.category_usd_total = date_usd_total
                    category_total.total_asset = date_total
                    category_total.usd_rate = date_usd_rate
                    category_total.save()
            elif not is_category_total_exist:
                data = {
                    "category_krw_total" : date_krw_total,
                    "category_usd_total" : date_usd_total,
                    "usd_rate" : date_usd_rate,
                    "total_asset" : date_total,
                    "date" : date,
                }
                serializer = CategoryTotalSerializer(data=data)
                if serializer.is_valid():
                    category_total_trans = serializer.save(owner=request.user)
                else:
                    raise ValidationError("Invalid data")
        
        total_trans = CategoryTotal.objects.filter(owner=request.user).order_by("date")
        total_serializer = CategoryTotalSerializer(total_trans, many=True)

        return Response({
            "total_trans" : total_serializer.data,
            "stock_data" : category_stocks_total,
            })

class CategoryStockHave(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = {}
        categories = Category.objects.filter(owner=request.user)
        print(categories)
        for category in categories:
            name = category.name
            print(name)
            print(category.classification)
            if category.classification == 'bank':
                print(name)
                result[name] = 0
            elif category.classification == 'stock':
                print(name)
                stocks = Stock.objects.filter(owner=request.user, category=category)
                stock_count = stocks.count()
                result[name] = stock_count
        return Response(
            {
                "count" : result
            }
        )




