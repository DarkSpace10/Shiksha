from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, DonorProfile, StudentProfile, Notification


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_verified', 'is_suspended', 'created_at')
    list_filter = ('role', 'is_verified', 'is_suspended', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    fieldsets = UserAdmin.fieldsets + (
        ('Platform Details', {'fields': ('role', 'phone_number', 'profile_picture', 'is_verified', 'is_suspended')}),
    )


@admin.register(DonorProfile)
class DonorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'state', 'total_donations_count', 'created_at')
    search_fields = ('user__username', 'city', 'state')


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'institution_name', 'course_of_study', 'academic_level', 'verification_status', 'created_at')
    list_filter = ('academic_level', 'verification_status')
    search_fields = ('user__username', 'institution_name', 'student_id_number')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
