from django.urls import path
from . import views

urlpatterns = [
    path("create", views.CreateStock.as_view()),
    path("get/<int:cat>/<int:stock>", views.GetStock.as_view()),
    path("create/stock_transaction", views.PostStockTransaction.as_view()),
    path("modify/stock_transaction/<int:transaction>", views.ModifyStockTransaction.as_view()),
    path("<int:cat>", views.Stocklist.as_view()),
    path("<int:cat>/stockTable", views.CategoryStockTable.as_view()),
    path("<int:cat>/<int:stock>", views.Stockview.as_view()),
    path("<int:cat>/<int:stock>/<int:transaction>", views.StockTransactionDetail.as_view() )
]