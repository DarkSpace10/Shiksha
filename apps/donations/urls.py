from django.urls import path
from . import views

app_name = 'donations'

urlpatterns = [
    # Donor routes
    path('create/', views.donation_create, name='donation_create'),
    path('my/', views.my_donations, name='my_donations'),
    path('<uuid:donation_id>/', views.donation_detail, name='donation_detail'),
    path('<uuid:donation_id>/cancel/', views.donation_cancel, name='donation_cancel'),

    # NGO Staff routes
    path('ngo/queue/', views.ngo_donations_list, name='ngo_donations_list'),
    path('ngo/<uuid:donation_id>/review/', views.ngo_donation_review, name='ngo_donation_review'),
    path('ngo/<uuid:donation_id>/pickup-schedule/', views.ngo_pickup_schedule, name='ngo_pickup_schedule'),
    path('ngo/pickup/<uuid:pickup_id>/status/', views.ngo_pickup_status_update, name='ngo_pickup_status_update'),
    path('ngo/<uuid:donation_id>/inspect/', views.ngo_physical_inspection, name='ngo_physical_inspection'),
]
