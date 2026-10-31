from django.contrib import admin
from .models import InventoryCopy


@admin.register(InventoryCopy)
class InventoryCopyAdmin(admin.ModelAdmin):
    list_display = ('tracking_code', 'book_title', 'author', 'ngo', 'category', 'condition_grade', 'status', 'is_published')
    list_filter = ('status', 'is_published', 'category', 'ngo')
    search_fields = ('tracking_code', 'book_title', 'author', 'location_shelf')
