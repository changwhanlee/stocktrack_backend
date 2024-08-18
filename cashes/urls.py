from django.urls import path
from . import views

urlpatterns = [
    path("", views.BankList.as_view()),
    path("create", views.CreateBank.as_view()),
    path("get/<int:pk>", views.getBank.as_view()),
    path("modify/<int:pk>", views.ModifyBankTransaction.as_view()),
    path("<int:pk>", views.BankDetail.as_view()),
    path("<int:cash>/<int:bank>", views.CashDetial.as_view())
]
