from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('add/', views.add_recipe, name='add_recipe'),
    path('upload/', views.upload_file, name='upload_file'),
    path('files/', views.files_view, name='files'),
    path('files/<str:filename>/', views.view_file, name='view_file'),
    path('files/<str:filename>/delete/', views.delete_file, name='delete_file'),
    path('db/', views.db_view, name='db'),
    path('ajax/search/', views.search_recipes_ajax, name='search_recipes_ajax'),
    path('ajax/edit/<int:pk>/', views.edit_recipe_ajax, name='edit_recipe_ajax'),
    path('ajax/delete/<int:pk>/', views.delete_recipe_ajax, name='delete_recipe_ajax'),
]