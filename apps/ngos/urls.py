from django.urls import path
from . import views

app_name = 'ngos'

urlpatterns = [
    path('register/', views.register_ngo, name='register_ngo'),
    path('status/<uuid:ngo_id>/', views.ngo_status_page, name='ngo_status_page'),
    path('directory/', views.public_directory, name='public_directory'),
    path('view/<slug:slug>/', views.ngo_detail, name='ngo_detail'),
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/create/', views.staff_create, name='staff_create'),
    path('staff/<uuid:membership_id>/toggle/', views.staff_toggle_status, name='staff_toggle_status'),
    path('service-areas/', views.service_areas_list, name='service_areas'),
    path('service-areas/create/', views.service_area_create, name='service_area_create'),
    path('service-areas/<uuid:area_id>/delete/', views.service_area_delete, name='service_area_delete'),
]
