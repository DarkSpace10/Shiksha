from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/donor/', views.register_donor, name='register_donor'),
    path('register/student/', views.register_student, name='register_student'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),
]
