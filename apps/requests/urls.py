from django.urls import path
from . import views

app_name = 'requests'

urlpatterns = [
    # Student routes
    path('documents/upload/', views.document_upload, name='document_upload'),
    path('documents/<uuid:doc_id>/delete/', views.document_delete, name='document_delete'),
    path('create/<uuid:copy_id>/', views.request_create, name='request_create'),
    path('my-requests/', views.student_requests_list, name='student_requests_list'),
    path('view/<uuid:request_id>/', views.student_request_detail, name='student_request_detail'),
    path('delivery/<uuid:delivery_id>/confirm/', views.student_confirm_receipt, name='student_confirm_receipt'),

    # NGO Staff routes
    path('ngo/verification-queue/', views.ngo_students_verification_queue, name='ngo_students_verification_queue'),
    path('ngo/verify-student/<uuid:profile_id>/', views.ngo_verify_student, name='ngo_verify_student'),
    path('ngo/queue/', views.ngo_requests_queue, name='ngo_requests_queue'),
    path('ngo/<uuid:request_id>/review/', views.ngo_request_review_detail, name='ngo_request_review_detail'),
    path('ngo/<uuid:request_id>/allocate/', views.ngo_execute_allocation, name='ngo_execute_allocation'),
    path('ngo/<uuid:request_id>/reject/', views.ngo_reject_request, name='ngo_reject_request'),
    path('ngo/<uuid:request_id>/waitlist/', views.ngo_waitlist_request, name='ngo_waitlist_request'),
    path('ngo/deliveries/', views.ngo_deliveries_list, name='ngo_deliveries_list'),
    path('ngo/delivery/<uuid:delivery_id>/dispatch/', views.ngo_delivery_dispatch, name='ngo_delivery_dispatch'),
    path('ngo/delivery/<uuid:delivery_id>/status/', views.ngo_delivery_status_update, name='ngo_delivery_status_update'),
]
