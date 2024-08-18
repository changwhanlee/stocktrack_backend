from django.urls import path
from . import views

urlpatterns = [
    path("update_date", views.UpdateDate.as_view()),
    path("update_trans", views.UpdateTrans.as_view()),
    path("categories_name", views.CategoriesName.as_view()),
    path("categories_list", views.CategoriesList.as_view()),
    path("category_count", views.CategoryStockHave.as_view()),
    path("categories_list/<int:cat>", views.CategoryView.as_view()),
]
