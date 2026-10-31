from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('catalogue/', views.catalogue, name='catalogue'),
    path('catalogue/<uuid:copy_id>/', views.book_detail, name='book_detail'),
    path('ngo/inventory/', views.ngo_inventory_list, name='ngo_inventory_list'),
    path('ngo/inventory/<uuid:copy_id>/toggle-publish/', views.inventory_toggle_publish, name='inventory_toggle_publish'),
]
