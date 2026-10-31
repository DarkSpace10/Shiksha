from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('dashboard/', views.dispatch, name='dispatch'),
    path('donor/dashboard/', views.donor_dashboard, name='donor_dashboard'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('ngo/dashboard/', views.ngo_dashboard, name='ngo_dashboard'),
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/ngo/<uuid:ngo_id>/decision/', views.admin_ngo_decision, name='admin_ngo_decision'),
    path('admin-panel/user/<uuid:user_id>/toggle-suspension/', views.admin_toggle_user_suspension, name='admin_toggle_user_suspension'),
]
