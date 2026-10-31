from django.contrib import admin
from .models import BookRequest, RequestReview, Allocation, DeliveryJob, StudentVerification, VerificationDocument


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_title', 'student_profile', 'document_type', 'is_verified', 'uploaded_at')
    list_filter = ('document_type', 'is_verified')


@admin.register(StudentVerification)
class StudentVerificationAdmin(admin.ModelAdmin):
    list_display = ('student_profile', 'ngo', 'status', 'verified_by', 'verified_at')
    list_filter = ('status', 'ngo')


@admin.register(BookRequest)
class BookRequestAdmin(admin.ModelAdmin):
    list_display = ('inventory_copy', 'student', 'ngo', 'status', 'urgent_need', 'created_at')
    list_filter = ('status', 'urgent_need', 'ngo')
    search_fields = ('inventory_copy__book_title', 'student__username', 'ngo__name')


@admin.register(Allocation)
class AllocationAdmin(admin.ModelAdmin):
    list_display = ('inventory_copy', 'book_request', 'ngo', 'allocated_by', 'status', 'allocated_at')
    list_filter = ('status', 'ngo')


@admin.register(DeliveryJob)
class DeliveryJobAdmin(admin.ModelAdmin):
    list_display = ('tracking_number', 'recipient_student', 'courier_name', 'status', 'student_confirmed', 'created_at')
    list_filter = ('status', 'student_confirmed', 'ngo')
    search_fields = ('tracking_number', 'recipient_student__username')
