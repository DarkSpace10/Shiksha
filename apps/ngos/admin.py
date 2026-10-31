from django.contrib import admin
from .models import NGO, NGOMembership, NGOServiceArea


@admin.register(NGO)
class NGOAdmin(admin.ModelAdmin):
    list_display = ('name', 'registration_number', 'city', 'state', 'status', 'created_at')
    list_filter = ('status', 'state')
    search_fields = ('name', 'registration_number', 'city')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(NGOMembership)
class NGOMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'ngo', 'role', 'is_active', 'joined_at')
    list_filter = ('role', 'is_active', 'ngo')
    search_fields = ('user__username', 'ngo__name')


@admin.register(NGOServiceArea)
class NGOServiceAreaAdmin(admin.ModelAdmin):
    list_display = ('ngo', 'city', 'state', 'postal_code', 'is_active')
    list_filter = ('state', 'is_active', 'ngo')
