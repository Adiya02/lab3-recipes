from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('add/', views.add_recipe, name='add_recipe'),
    path('upload/', views.upload_file, name='upload_file'),
    path('files/', views.files_view, name='files'),
    path('files/<str:filename>/', views.view_file, name='view_file'),
    path('files/<str:filename>/delete/', views.delete_file, name='delete_file'),
]