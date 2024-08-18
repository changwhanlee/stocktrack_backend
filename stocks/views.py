from django.shortcuts import render
from rest_framework.status import HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import (
    NotFound,
    ParseError,
    PermissionDenied,
    ValidationError,
)
from categories.models import Category, CategoryTransaction, CategoryTotal, CategoryUpdateDate
from .models import StockTransaction, Stock
from .serializers import (
    StockTransactionSerializer,
    StockMakingSerializer,
    StockSerializer,
)
from categories.serializers import CategoryTransactionsSerializer, CategoryTotalSerializer, CategoryUpdateDateSerializer
import pandas as pd
from pandas_datareader import data as pdr
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd

# Create your views here.


class CreateStock(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        category = Category.objects.get(pk=data["categoryPk"])
        if category.owner != request.user:
            raise NotFound
        stock_data = {}
        stock_data["name"] = data["name"]
        stock_data["ticker"] = data["ticker"]
        stock_data["currency"] = data["currency"]
        serializer = StockMakingSerializer(data=stock_data)
        if serializer.is_valid():
            stock_trans_data = {}
            
            date_str = data["date"]
            date = datetime.strptime(date_str, "%Y-%m-%d")
            date_next = date + timedelta(days=1)

            if data["currency"] == "usd" :
                ticker = data["ticker"]
            elif data["currency"] == "krw" :
                ticker = data["ticker"] + ".KS"
            
            market_price = yf.download(
                tickers=ticker, start=date, end=date_next
            )
            if isinstance(market_price, pd.DataFrame) and market_price.empty:
                raise ValidationError("ticker or date is invalid")
            else:
                market_price = market_price.iloc[0]["Adj Close"]
            
            stock_trans_data["amount"] = int(data["amount"])
            stock_trans_data["price"] = float(data["price"])
            stock_trans_data["date"] = data["date"]
            stock_trans_data["total_amount"] = int(data["amount"])
            stock_trans_data["total_average_price"] = float(data["price"])
            stock_trans_data["total_stock_asset"] = int(data["amount"]) * market_price
            stock_trans_data["market_price"] = market_price
            stock_trans_data["realize_money"] = 0

            trans_serializer = StockTransactionSerializer(data=stock_trans_data)
            if trans_serializer.is_valid():
                new_stock = serializer.save(
                    owner=request.user,
                    category=category,
                )
                new_stock_trans = trans_serializer.save(
                    stock=new_stock,
                    owner = request.user,
                )
                update_date = CategoryUpdateDate.objects.filter(date=data["date"], owner=request.user)
                date_lst = update_date.values_list('date', flat=True)
                print('dddddddddddddddddddddddddddddddddddddddddddddddddddd')
                print(update_date)
                print(date_lst)
                if not update_date.exists():
                    print(data["date"])
                    add_date = {"date" : data["date"]}
                    update_serializer = CategoryUpdateDateSerializer(data=add_date)
                    if update_serializer.is_valid():
                        update_date = update_serializer.save(
                            owner=request.user,
                        )

                print(new_stock.category.pk)
                return Response(
                    {
                        "id": new_stock.pk,
                        "category_id": new_stock.category.pk,
                    }
                )
        else:
            print(serializer.errors)
            raise ValidationError("Invalid data")


class GetStock(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, cat, stock):
        print("ddddddddddddddddddddddddddddd")
        category = Category.objects.get(pk=cat)
        stock = Stock.objects.get(pk=stock, category=category)
        serializer = StockSerializer(stock)
        return Response(serializer.data)


class PostStockTransaction(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        print(data)
        print(type(data["amount"]))
        data["amount"] = int(data["amount"])
        data["price"] = float(data["price"])
        category = Category.objects.get(pk=data["categoryPk"])
        stock = Stock.objects.get(pk=data["stockPk"], category=category)
        date_str = data["date"]
        that_transaction = StockTransaction.objects.filter(stock=stock, date=date_str)
        if that_transaction:
            raise ValidationError("same day exists")
        del data["categoryPk"]
        del data["stockPk"]

        """스톡 트랜스액션 등록하기"""

        try:
            previous_stock_transaction = StockTransaction.objects.filter(
                stock=stock, date__lt=date_str
            ).latest("date")
            previous_total_amount = previous_stock_transaction.total_amount
            previous_total_average_price = (
                previous_stock_transaction.total_average_price
            )
            previous_realize_money = previous_stock_transaction.realize_money
        except StockTransaction.DoesNotExist:
            previous_total_amount = 0
            previous_total_average_price = 0
            previous_realize_money = 0

        if previous_total_amount + data["amount"] < 0:
            raise ValidationError("Invalid data")

        date = datetime.strptime(date_str, "%Y-%m-%d")
        date_b = date + timedelta(days=1)
        date_next = date_b.strftime("%Y-%m-%d")
        market_price = yf.download(
            tickers=stock.ticker, start=date_str, end=date_next
        )
        print(market_price)
        if isinstance(market_price, pd.DataFrame) and market_price.empty:
            raise ValidationError("date is invalid")
        else :
            market_price = market_price.iloc[0]["Adj Close"]  


        total_amount = previous_total_amount + data["amount"]
        total_average_price = (
            (previous_total_average_price * previous_total_amount)
            + (data["amount"] * data["price"])
        ) / (previous_total_amount + data["amount"])
        if data["amount"] < 0:
            realize_money = previous_realize_money - (data["amount"] * data["price"])
        elif data["amount"] >= 0:
            realize_money = previous_realize_money
        serializer = StockTransactionSerializer(data=data)
        if serializer.is_valid():
            stock_transaction = serializer.save(
                stock=stock,
                total_amount=total_amount,
                total_average_price=total_average_price,
                total_stock_asset=total_amount * market_price,
                market_price=market_price,
                realize_money=realize_money
            )
            serializer = StockTransactionSerializer(stock_transaction)
            print('dddddddddddddddddddddddddddddddddddddddddd')
            if not CategoryUpdateDate.objects.filter(owner=request.user, date=data["date"]).exists():
                print(data["date"])
                add_date = {"date" : data["date"]}
                add_date_serializer = CategoryUpdateDateSerializer(data=add_date)
                if add_date_serializer.is_valid():
                    add_date_serializer.save(owner=request.user)

            """이후 트랜스액션 업데이트"""
            print(stock_transaction.pk)

            subsequent_transactions = StockTransaction.objects.filter(
                stock=stock_transaction.stock, date__gte=stock_transaction.date
            ).exclude(pk=stock_transaction.pk)

            if subsequent_transactions.exists():
                total_amount= stock_transaction.total_amount
                total_average_price = stock_transaction.total_average_price
                realize_money = stock_transaction.realize_money
                for transaction in subsequent_transactions.order_by("date"):
                    total_average_price = (
                        (
                            (total_average_price * total_amount)
                            + (transaction.amount * transaction.price)
                        )
                        / (total_amount + transaction.amount)
                        if total_amount + transaction.amount != 0
                        else 0
                    )
                    if transaction.amount < 0:
                        realize_money = realize_money - (
                            transaction.amount * transaction.price
                        )
                    transaction.total_amount = total_amount + transaction.amount
                    transaction.total_average_price = total_average_price
                    transaction.total_stock_asset = (total_amount + transaction.amount) * transaction.market_price
                    transaction.realize_money = realize_money
                    transaction.save()
            else:
                print('__________________끝_______________________')
                pass
            return Response({"categoryPk" : category.pk})
        else:
            raise ValidationError(serializer.error_messages)        


class ModifyStockTransaction(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, transaction):
        stock_trans = StockTransaction.objects.get(pk=transaction)
        date = stock_trans.date
        name = stock_trans.stock.name
        amount = stock_trans.amount
        price = stock_trans.price
        return Response({
            "name" : name,
            "date" : date,
            "amount" : amount,
            "price" : price
        })
    
    def put(self, request, transaction):
        data = request.data
        amount = int(data["amount"])
        price = float(data["price"])
        stock_trans = StockTransaction.objects.get(pk=transaction)
        stock = stock_trans.stock
        date = stock_trans.date
        market_price = stock_trans.market_price

        """스톡 트랜스액션 수정하기"""
        try:
            previous_stock_transaction = StockTransaction.objects.filter(
                stock=stock, date__lt=date
            ).latest("date")
            print(previous_stock_transaction.date)
            previous_total_amount = previous_stock_transaction.total_amount
            previous_total_average_price = (
                previous_stock_transaction.total_average_price
            )
            previous_realize_money = previous_stock_transaction.realize_money
        except StockTransaction.DoesNotExist:
            print('-----------------------------------------------')
            previous_total_amount = 0
            previous_total_average_price = 0
            previous_realize_money = 0
        
        if previous_total_amount + amount < 0 :
            raise ValidationError("Invalid Data")
        
        total_amount = previous_total_amount + amount
        total_average_price = (
            (previous_total_average_price * previous_total_amount)
            + (amount * price)
        ) / (previous_total_amount + amount)
        if amount < 0 :
            realize_money = previous_realize_money - (amount * price)
        elif amount >= 0:
            realize_money = previous_realize_money

        modify_data = {}
        modify_data["amount"] = amount
        modify_data["price"] = price
        modify_data["total_amount"] = total_amount
        modify_data["total_average_price"] = total_average_price
        modify_data["total_stock_asset"] = market_price * total_amount
        modify_data["realize_money"] = realize_money

        serializer = StockTransactionSerializer(
            stock_trans,
            data=modify_data,
            partial=True,
        )
        if serializer.is_valid():
            updated_transaction = serializer.save()

            """이후 트랜스액션 업데이트"""

            subsequent_transactions = StockTransaction.objects.filter(
                stock=updated_transaction.stock, date__gte=updated_transaction.date
            ).exclude(pk=updated_transaction.pk)

            if subsequent_transactions.exists():
                total_amount = updated_transaction.total_amount
                total_average_price = updated_transaction.total_average_price
                realize_money = updated_transaction.realize_money
                for transaction in subsequent_transactions.order_by("date"):
                    total_average_price = (
                        (
                            (total_average_price * total_amount)
                            + (transaction.amount * transaction.price)
                        )
                        / (total_amount + transaction.amount)
                        if total_amount + transaction.amount != 0
                        else 0
                    )
                    if transaction.amount < 0:
                        realize_money = realize_money - (
                            transaction.amount * transaction.price
                        )
                    transaction.total_amount = total_amount + transaction.amount
                    transaction.total_average_price = total_average_price
                    transaction.total_stock_asset = (total_amount + transaction.amount) * transaction.market_price
                    transaction.realize_money = realize_money
                    transaction.save()
                else :
                    pass
            return Response({
                "result" : "good"
            })
        else:
            raise ValidationError(serializer.error_messages)




class Stocklist(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, cat):
        category = Category.objects.get(pk=cat)
        if category.owner != request.user:
            raise NotFound
        stocks = category.stocks.all()
        stocks_json = {}
        for stock in stocks:
            stock_latest = stock.transactions.all().order_by("date")
            if stock_latest:
                latest = stock_latest.last()
                serializer = StockTransactionSerializer(stock_latest, many=True)
                stocks_json[latest.stock.name] = serializer.data
        category_trans = category.transaction.all().order_by("date")
        cat_serializer = CategoryTransactionsSerializer(category_trans, many=True)

        return Response(
            {
                "result": stocks_json,
                "category_result" : cat_serializer.data,
            }
        )

    def post(self, request, cat):
        category = Category.objects.get(pk=cat)
        if category.owner != request.user:
            raise PermissionDenied

        data = request.data
        print(data)
        for date_str, stocks_data in data.items():
            date = datetime.strptime(date_str, "%Y-%m-%d")
            for stock_key, stock_data in stocks_data.items():
                if stock_key.startswith("new"):
                    print(stock_data["name"])
                    self.create_stocks(request, stock_data, cat, date)
                    print(stock_data["name"])
                else:
                    print(stock_key)
                    self.update_stock_transaction(cat, stock_key, stock_data, date)
                    print(stock_key)

        return Response({"result": "good"})

    def create_stocks(self, request, stock_data, cat, date):
        category = Category.objects.get(pk=cat)

        date_b = date + timedelta(days=1)
        date_next = date_b.strftime("%Y-%m-%d")
        market_price = yf.download(
            tickers=stock_data["ticker"], start=date, end=date_next
        )
        print(market_price)
        if market_price is None:
            raise ParseError
        market_price = market_price.iloc[0]["Adj Close"]

        ticker = stock_data["ticker"]
        data = {}
        data["name"] = stock_data["name"]
        data["ticker"] = ticker
        data["currency"] = stock_data["currency"]
        serializer = StockMakingSerializer(data=data)
        if serializer.is_valid():
            new_stock = serializer.save(
                owner=request.user,
                category=category,
            )
            self.save_stock_transaction(new_stock, stock_data, date, market_price)

    def save_stock_transaction(self, new_stock, stock_data, date, market_price):
        date_str = date.strftime("%Y-%m-%d")
        data = {
            "amount": stock_data["amount"],
            "price": stock_data["price"],
            "date": date_str,
        }
        serializer = StockTransactionSerializer(data=data)
        print(serializer)
        if serializer.is_valid():
            stock_transaction = serializer.save(
                stock=new_stock,
                total_amount=data["amount"],
                total_average_price=data["price"],
                total_stock_asset=data["amount"] * market_price,
                market_price=market_price,
                realize_money=0,
            )
        else:
            print(serializer.errors)
            raise ValidationError("Invalid data")

    def update_stock_transaction(self, cat, stock_key, stock_data, date):
        date_str = date.strftime("%Y-%m-%d")
        category = Category.objects.get(pk=cat)
        stock = category.stocks.get(ticker=stock_key)
        print("--------------------------------------")
        try:
            previous_stock_transaction = StockTransaction.objects.filter(
                stock=stock, date__lt=date_str
            ).latest("date")
            previous_total_amount = previous_stock_transaction.total_amount
            previous_total_average_price = (
                previous_stock_transaction.total_average_price
            )
            previous_realize_money = previous_stock_transaction.realize_money
        except StockTransaction.DoesNotExist:
            previous_total_amount = 0
            previous_total_average_price = 0
            previous_realize_money = 0

        try:
            print("-------------------start-----------------------")
            stock_transaction = StockTransaction.objects.get(stock=stock, date=date)
            stock_transaction.amount = stock_data["amount"]
            stock_transaction.price = stock_data["price"]
            stock_transaction.total_amount = (
                previous_total_amount + stock_data["amount"]
            )
            stock_transaction.total_average_price = (
                (previous_total_amount * previous_total_average_price)
                + (stock_data["amount"] * stock_data["price"])
            ) / (previous_total_amount + stock_data["amount"])
            stock_transaction.total_stock_asset = stock_transaction.market_price * (
                previous_total_amount + stock_data["amount"]
            )
            if stock_data["amount"] < 0:
                stock_transaction.realize_money = previous_realize_money - (
                    stock_data["amount"] * stock_data["price"]
                )
            elif stock_data["amount"] >= 0:
                stock_transaction.realize_money = previous_realize_money
            stock_transaction.save()
            stock_transaction_pk = stock_transaction.pk
            self.update_subsequent_transactions(stock_transaction_pk)

        except StockTransaction.DoesNotExist:
            print("-------------empty-------------------")
            date_b = date + timedelta(days=1)
            date_next = date_b.strftime("%Y-%m-%d")
            market_price = yf.download(tickers=stock_key, start=date, end=date_next)
            if market_price is None:
                raise ParseError
            market_price = market_price.iloc[0]["Adj Close"]
            data = {
                "amount": stock_data["amount"],
                "price": stock_data["price"],
                "date": date_str,
            }
            if stock_data["amount"] < 0:
                realize_money = previous_realize_money - (
                    stock_data["amount"] * stock_data["price"]
                )
            elif stock_data["amount"] >= 0:
                realize_money = previous_realize_money
            serializer = StockTransactionSerializer(data=data)
            if serializer.is_valid():
                stock_transaction = serializer.save(
                    stock=stock,
                    total_amount=previous_total_amount + data["amount"],
                    total_average_price=(
                        ((previous_total_average_price * previous_total_amount))
                        + (data["amount"] * data["price"])
                    )
                    / (data["amount"] + previous_total_amount),
                    total_stock_asset=(previous_total_amount + data["amount"])
                    * market_price,
                    market_price=market_price,
                    realize_money=realize_money,
                )

    def update_subsequent_transactions(self, stock_transaction_pk):
        stock_transaction = StockTransaction.objects.get(pk=stock_transaction_pk)
        print("update_______________________________________")
        subsequent_transactions = StockTransaction.objects.filter(
            stock=stock_transaction.stock, date__gte=stock_transaction.date
        ).exclude(pk=stock_transaction.pk)

        if subsequent_transactions.exists():
            total_amount = stock_transaction.total_amount
            total_average_price = stock_transaction.total_average_price
            realize_money = stock_transaction.realize_money
            for transaction in subsequent_transactions.order_by("date"):
                total_average_price = (
                    (
                        (total_average_price * total_amount)
                        + (transaction.amount * transaction.price)
                    )
                    / (total_amount + transaction.amount)
                    if total_amount + transaction.amount != 0
                    else 0
                )
                if transaction.amount < 0:
                    realize_money = realize_money - (
                        transaction.amount * transaction.price
                    )
                total_amount = total_amount + transaction.amount
                total_asset_stock = total_amount * transaction.market_price
                transaction.total_amount = total_amount
                transaction.total_average_price = total_average_price
                transaction.total_stock_asset = total_asset_stock
                transaction.save()
        else:
            pass

    def update_category_transaction(self, request, cat):
        category = Category.objects.get(pk=cat)
        if category.owner != request.user:
            raise PermissionDenied
        stocks = Stock.objects.filter(category=category)
        asset_df = pd.DataFrame()
        amount_df = pd.DataFrame()
        realize_money_df = pd.DataFrame()
        for idx, stock in enumerate(stocks):
            stock_trans = StockTransaction.objects.filter(stock=stock)
            serializer = StockTransactionSerializer(stock_trans, many=True)
            df = pd.DataFrame(serializer.data)
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            df_total_stock_asset = df["total_stock_asset"].to_frame()
            df_total_stock_asset.columns = [f"{stock.ticker}"]
            df_total_amount = df["total_amount"].to_frame()
            df_total_amount.columns = [f"{stock.ticker}"]
            df_realize_money = df["realize_money"].to_frame()
            df_realize_money.columns = [f"{stock.ticker}"]
            if idx == 0:
                asset_df = df_total_stock_asset
                amount_df = df_total_amount
                realize_money_df = df_realize_money
            else:
                asset_df = pd.concat(
                    [asset_df, df_total_stock_asset], axis=1, join="outer"
                )
                amount_df = pd.concat(
                    [amount_df, df_total_amount], axis=1, join="outer"
                )
                realize_money_df = pd.concat(
                    [realize_money_df, df_realize_money], axis=1, join="outer"
                )
        for column in amount_df.columns:
            first_valid_index = amount_df[column].first_valid_index()
            amount_df.loc[:first_valid_index, column] = amount_df.loc[
                :first_valid_index, column
            ].fillna(0)
            realize_money_df.loc[:first_valid_index, column] = realize_money_df.loc[
                :first_valid_index, column
            ].fillna(0)

        amount_df.fillna(method="ffill", inplace=True)
        realize_money_df.fillna(method="ffill", inplace=True)
        print(amount_df)

        columns = amount_df.columns
        start_day = amount_df.index[0]
        end_day = amount_df.index[-1]
        end_day_next = end_day + timedelta(days=1)
        end_day_next_str = end_day_next.strftime("%Y-%m-%d")

        for column in columns:
            market_price = yf.download(
                tickers=column, start=start_day, end=end_day_next_str
            )
            price_df = market_price["Adj Close"].to_frame()
            price_df.columns = [f"{column}_price"]
            
            amount_df = pd.concat(
                [amount_df, price_df], axis=1
            ).reindex(amount_df.index)
            amount_df.fillna(method="ffill", inplace=True)
            amount_df[f"{column}_asset"] = amount_df[f"{column}"] * amount_df[f"{column}_price"]
        amount_df["total_asset_krw"] = 0
        amount_df["total_asset_usd"] = 0
        amount_df["total_asset"] = 0
        print(amount_df)

        for column in columns:
            stock_currency = Stock.objects.get(ticker=column, category=category).currency
            print(stock_currency)
            if stock_currency == "usd":
                amount_df["total_asset_usd"] = amount_df["total_asset_usd"] + amount_df[f"{column}_asset"]
            elif stock_currency == "krw":
                amount_df["total_asset_krw"] = amount_df["total_asset_krw"] + amount_df[f"{column}_asset"]
        exchange_rate = yf.download(
                tickers="KRW=X", start=start_day, end=end_day_next_str
            )
        exchange_rate_df = exchange_rate["Adj Close"].to_frame()
        exchange_rate_df.columns = ["usd_rate"]
        amount_df = pd.concat(
            [amount_df, exchange_rate_df], axis=1
        ).reindex(amount_df.index)
        amount_df["total_asset"] = amount_df["total_asset_krw"] + (amount_df["total_asset_usd"] * amount_df["usd_rate"])
        realize_money_df["sum"] = realize_money_df.sum(axis=1)
        print(amount_df)

        for i in range(len(amount_df)):
            date = amount_df.index[i]
            print(i)
            date_str = date.strftime("%Y-%m-%d")
            date_asset_krw = amount_df.loc[date, "total_asset_krw"]
            date_asset_usd = amount_df.loc[date, "total_asset_usd"]
            date_asset_total = amount_df.loc[date, "total_asset"]
            date_usd_rate = amount_df.loc[date, "usd_rate"]
            date_realize_money = realize_money_df.loc[date, "sum"]
            is_category_trans_exist = CategoryTransaction.objects.filter(category=category, date=date_str).exists()
            is_total_trans_exist = CategoryTotal.objects.filter(owner=request.user, date=date_str).exists()
            is_total_trans_first_exist = CategoryTotal.objects.filter(owner=request.user).exists()
            print(is_category_trans_exist)
            print(is_total_trans_exist)
            print(is_total_trans_first_exist)

            if is_category_trans_exist and is_total_trans_exist :
                category_trans = CategoryTransaction.objects.get(
                    category=category, date=date_str
                )
                total_trans = CategoryTotal.objects.get(
                    owner=request.user, date=date_str
                )
                print(i, total_trans)

                if category_trans.total_asset != date_asset_total:
                    total_trans.category_krw_total = total_trans.category_krw_total - category_trans.asset_krw + date_asset_krw
                    total_trans.category_usd_total = total_trans.category_usd_total - category_trans.asset_usd + date_asset_usd
                    total_trans.total_asset = total_trans.total_asset - category_trans.total_asset + date_asset_total
                    category_trans.asset_krw = date_asset_krw
                    category_trans.asset_usd = date_asset_usd
                    category_trans.usd_rate = date_usd_rate
                    category_trans.total_asset = date_asset_total
                    category_trans.realize_money = date_realize_money
                    category_trans.save()
                    total_trans.save()

            elif is_category_trans_exist and not is_total_trans_exist :
                print(i, "ddddddddddddddddddddddddd")
                category_trans = CategoryTransaction.objects.get(
                    category=category, date=date_str
                )

                if category_trans.total_asset != date_asset_total:
                    category_trans.asset_krw = date_asset_krw
                    category_trans.asset_usd = date_asset_usd
                    category_trans.usd_rate = date_usd_rate
                    category_trans.total_asset = date_asset_total
                    category_trans.realize_money = date_realize_money
                    category_trans.save()
            
            elif not is_category_trans_exist and is_total_trans_exist :
                print(i, 'aaaaaaaaaaaaaaaaaaaaaaaaaaaa')
                data = {
                    "asset_krw" : date_asset_krw,
                    "asset_usd" : date_asset_usd,
                    "usd_rate" : date_usd_rate,
                    "total_asset" : date_asset_total,
                    "date" : date_str,
                    "realize_money" : date_realize_money,
                }
                serializer = CategoryTransactionsSerializer(data=data)
                if serializer.is_valid():
                    category_trans = serializer.save(category=category)
                    total_trans = CategoryTotal.objects.get(
                    owner=request.user, date=date_str
                    )
                    total_trans.category_krw_total = total_trans.category_krw_total + date_asset_krw
                    total_trans.category_usd_total = total_trans.category_usd_total + date_asset_usd
                    total_trans.total_asset = total_trans.total_asset + date_asset_total
                    total_trans.save()
                else:
                    raise ValidationError("Invalid data")
            
            elif not is_category_trans_exist and not is_total_trans_exist:
                print(i, 'qqqqqqqqqqqqqqqqqqqqqqqqqqqq')
                data = {
                    "asset_krw" : date_asset_krw,
                    "asset_usd" : date_asset_usd,
                    "usd_rate" : date_usd_rate,
                    "total_asset" : date_asset_total,
                    "date" : date_str,
                    "realize_money" : date_realize_money,
                }
                serializer = CategoryTransactionsSerializer(data=data)
                if serializer.is_valid():
                    category_trans = serializer.save(category=category)
                    total_update_obj = {
                        "category_krw_total" :date_asset_krw,
                        "category_usd_total" : date_asset_usd,
                        "usd_rate" : date_usd_rate,
                        "total_asset" : date_asset_total,
                        "date" : date_str,
                    }
                    total_serializer = CategoryTotalSerializer(data=total_update_obj)
                    if total_serializer.is_valid():
                        total_trans = total_serializer.save(
                            owner=request.user,
                        )
                else:
                    raise ValidationError("Invalid data") 


        

class Stockview(APIView):

    permission_classes = [IsAuthenticated]

    def update_category(self, cat, date, amount, price, market_price):
        category = Category.objects.get(pk=cat)
        try:
            category_trans = CategoryTransaction.objects.filter(category=category)
            print(category_trans)
            category_trans = category_trans.order_by("date")
            if category_trans.get(date=date).exist():
                updating_category = category_trans.get(date=date)
                asset = updating_category.asset + (amount * market_price)
                realize_money = updating_category.realize_money
                if amount < 0:
                    realize_money = updating_category.realize_money - (amount * price)
                updating_category.asset = asset
                updating_category.realize_money = realize_money
                updating_category.save()
            else:
                data = {}
                data["asset"] = amount * market_price
                data["date"] = date
                data["realize_money"] = 0
                serializer = CategoryTransactionsSerializer(data=data)
                if serializer.is_valid():
                    cat_trans = serializer.save(
                        category=category,
                    )

        except CategoryTransaction.DoesNotExist:
            data = {}
            data["asset"] = amount * market_price
            data["date"] = date
            data["realize_money"] = 0
            serializer = CategoryTransactionsSerializer(data=data)
            if serializer.is_valid():
                cat_trans = serializer.save(
                    category=category,
                )

    def get_object(self, stock):
        try:
            stock = Stock.objects.get(pk=stock)
            transactions = stock.transactions.all().order_by("date")
            return transactions
        except:
            raise NotFound

    def get(self, request, cat, stock):
        isMyStock = Stock.objects.get(pk=stock)
        if isMyStock.owner != request.user:
            raise PermissionError

        transactions = self.get_object(stock)
        serializer = StockTransactionSerializer(transactions, many=True)
        return Response(serializer.data)

    def post(self, request, cat, stock):
        data = request.data
        print("11111111111111111111")
        stock = Stock.objects.get(pk=stock)
        print("122222222222222222222")
        ticker = stock.ticker
        date = data["date"]

        date_a = datetime.strptime(date, "%Y-%m-%d")
        date_b = date_a + timedelta(days=1)
        date_next = date_b.strftime("%Y-%m-%d")
        try:
            transactions = stock.transactions.all().order_by("date")
            latest = transactions.last()

            total_amount = latest.total_amount + data["amount"]
            total_average_price = (
                (latest.total_average_price * latest.total_amount)
                + (data["amount"] * data["price"])
            ) / (latest.total_amount + data["amount"])
            market_price = yf.download(ticker, start=date, end=date_next)
            market_price = market_price.iloc[0]["Adj Close"]

            total_stock_asset = total_amount * market_price

            if data["amount"] < 0:
                realize_money = latest.realize_money - (data["amount"] * data["price"])
            elif data["amount"] >= 0:
                realize_money = latest.realize_money

            serializer = StockTransactionSerializer(data=request.data)
            if serializer.is_valid():

                updated_stock = serializer.save(
                    total_amount=total_amount,
                    total_average_price=total_average_price,
                    total_stock_asset=total_stock_asset,
                    market_price=market_price,
                    stock=stock,
                    realize_money=realize_money,
                )
                self.update_category(
                    cat, date, data["amount"], data["price"], market_price
                )

                serializer = StockTransactionSerializer(updated_stock)
                return Response(serializer.data)
            else:
                return Response(serializer.errors)

        except StockTransaction.DoesNotExist:
            total_amount = data["amount"]
            total_average_price = data["price"]
            market_price = yf.download(ticker, start=date, end=date_next)
            market_price = market_price.iloc[0]["Adj Close"]
            total_stock_asset = total_amount * market_price
            realize_money = 0

            serializer = StockTransactionSerializer(data=request.data)
            if serializer.is_valid():
                updated_stock = serializer.save(
                    total_amount=total_amount,
                    total_average_price=total_average_price,
                    total_stock_asset=total_stock_asset,
                    market_price=market_price,
                    stock=stock,
                    realize_money=realize_money,
                )
                serializer = StockTransactionSerializer(updated_stock)
                return Response(serializer.data)
            else:
                return Response(serializer.errors)


class StockTransactionDetail(APIView):

    permission_classes = [IsAuthenticated]

    def get_object(self, stock, transaction):
        try:
            stock_transaction = StockTransaction.objects.get(pk=transaction)
            return stock_transaction
        except:
            raise NotFound

    def update_subsequent_transactions(self, stock_transaction):
        subsequent_transactions = StockTransaction.objects.filter(
            stock=stock_transaction.stock, date__gte=stock_transaction.date
        ).exclude(pk=stock_transaction.pk)

        if subsequent_transactions.exists():
            total_amount = stock_transaction.total_amount
            total_average_price = stock_transaction.total_average_price
            for transaction in subsequent_transactions.order_by("date"):
                total_amount += transaction.amount
                total_average_price = (
                    (total_average_price * total_amount)
                    + (transaction.amount * transaction.price)
                ) / total_amount
                total_asset_stock = total_amount * transaction.market_price
                transaction.total_amount = total_amount
                transaction.total_average_price = total_average_price
                transaction.total_stock_asset = total_asset_stock
                transaction.save()

    def update_delete_transactions(self, delete_transaction):
        past_transactions = StockTransaction.objects.filter(
            stock=delete_transaction.stock, date__lt=delete_transaction.date
        ).order_by("date")
        latest_transaction = past_transactions.last()
        subsequent_transactions = StockTransaction.objects.filter(
            stock=delete_transaction.stock, date__gte=delete_transaction.date
        ).exclude(pk=delete_transaction.pk)

        if subsequent_transactions.exists():
            total_amount = latest_transaction.total_amount
            total_average_price = latest_transaction.total_average_price
            for transaction in subsequent_transactions.order_by("date"):
                total_amount += transaction.amount
                total_average_price = (
                    (total_average_price * total_amount)
                    + (transaction.amount * transaction.price)
                ) / total_amount
                total_asset_stock = total_amount * transaction.market_price
                transaction.total_amount = total_amount
                transaction.total_average_price = total_average_price
                transaction.total_stock_asset = total_asset_stock
                transaction.save()

    def get(self, request, cat, stock, transaction):
        stock = Stock.objects.get(pk=stock)
        if stock.owner != request.user:
            raise ParseError(f"your are not authenticated to look this stock")
        stock_trans = stock.transactions.get(pk=transaction)
        serializer = StockTransactionSerializer(stock_trans)
        return Response(serializer.data)

    def put(self, request, cat, stock, transaction):
        stock = Stock.objects.get(pk=stock)
        stock_trans = stock.transactions.get(pk=transaction)
        serializer = StockTransactionSerializer(
            stock_trans,
            data=request.data,
            partial=True,
        )
        if serializer.is_valid():
            amount = request.data.get("amount", stock_trans.amount)
            price = request.data.get("price", stock_trans.price)
            past_transactions = StockTransaction.objects.filter(
                stock=stock_trans.stock, date__lt=stock_trans.date
            ).order_by("date")
            latest_transaction = past_transactions.last()
            total_amount = latest_transaction.total_amount + amount
            total_average_price = (
                (
                    latest_transaction.total_average_price
                    * latest_transaction.total_amount
                )
                + (amount * price)
            ) / total_amount
            total_stock_asset = total_amount * stock_trans.market_price

            updated_transaction = serializer.save(
                total_amount=total_amount,
                total_average_price=total_average_price,
                total_stock_asset=total_stock_asset,
            )

            self.update_subsequent_transactions(updated_transaction)

            updated_transaction = StockTransactionSerializer(updated_transaction)
            return Response(updated_transaction.data)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    def delete(self, request, cat, stock, transaction):
        stock = Stock.objects.get(pk=stock)
        stock_trans = stock.transactions.get(pk=transaction)

        if stock.owner != request.user:
            raise PermissionDenied

        self.update_delete_transactions(stock_trans)
        stock_trans.delete()
        return Response(status=HTTP_204_NO_CONTENT)
    

class CategoryStockTable(APIView):
    def get(self, request, cat):
        category = Category.objects.get(pk=cat)
        if category.owner != request.user:
            raise NotFound
        category_trans = CategoryTransaction.objects.filter(category=category).order_by("date")
        category_trans_last = category_trans.last()
        last_date = category_trans_last.date
        usd_rate = category_trans_last.usd_rate
        last_date_tomorrow = last_date + timedelta(days=1)
        stocks = category.stocks.all()
        result_data = {}
        for stock in stocks:
            stock_data = {}
        
            try:                
                stock_trans_date = StockTransaction.objects.get(stock=stock, date=last_date)
                date = last_date
                total_amount = stock_trans_date.total_amount
                total_asset = round(stock_trans_date.total_stock_asset, 1)
                total_average = stock_trans_date.total_average_price
                market_price = stock_trans_date.market_price
                if stock.currency == "usd":
                    currency = "usd"
                    total_asset_krw = round(total_asset * category_trans_last.usd_rate, 1)
                elif stock.currency == "krw":
                    currency = "krw"
                    total_asset_krw = total_asset
                total_rate = round((total_asset_krw /category_trans_last.total_asset) * 100, 1)
            except StockTransaction.DoesNotExist:
                stock_trans_last = StockTransaction.objects.filter(stock=stock).order_by("date").last()
                date = stock_trans_last.date
                total_amount = stock_trans_last.total_amount
                market_price_df = yf.download(tickers=stock.ticker, start=last_date, end=last_date_tomorrow)
                market_price = round(market_price_df['Adj Close'].iloc[-1], 1)
                total_asset = round(total_amount * market_price, 1)
                total_average = stock_trans_last.total_average_price
                if stock.currency == "usd":
                    currency = "usd"
                    total_asset_krw = round(total_asset * category_trans_last.usd_rate, 1)
                elif stock.currency == "krw":
                    currency = "krw"
                    total_asset_krw = total_asset
                total_rate = round((total_asset_krw /category_trans_last.total_asset) * 100, 1)
            
            stock_data['total_amount'] = total_amount
            stock_data['total_asset'] = total_asset
            stock_data['total_asset_krw'] = total_asset_krw
            stock_data['total_average'] = total_average
            stock_data['market_price'] = market_price
            stock_data['total_rate'] = total_rate
            stock_data['currency'] = currency
            stock_data['usd_rate'] = usd_rate
            stock_data['date'] = last_date
            
            result_data[stock.name] = stock_data

        print(result_data)

        return Response(
            {"result" : result_data}
        )



