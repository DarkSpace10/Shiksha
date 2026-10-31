from django.contrib import admin
from .models import DonationListing, DonationImage, DonationReview, PickupJob


class DonationImageInline(admin.TabularInline):
    model = DonationImage
    extra = 1


@admin.register(DonationListing)
class DonationListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'donor', 'ngo', 'category', 'declared_condition', 'status', 'created_at')
    list_filter = ('status', 'category', 'ngo')
    search_fields = ('title', 'author', 'donor__username', 'ngo__name')
    inlines = [DonationImageInline]


@admin.register(DonationReview)
class DonationReviewAdmin(admin.ModelAdmin):
    list_display = ('donation', 'reviewer', 'decision', 'created_at')
    list_filter = ('decision',)


@admin.register(PickupJob)
class PickupJobAdmin(admin.ModelAdmin):
    list_display = ('donation', 'ngo', 'scheduled_date', 'time_slot', 'assigned_agent_name', 'status')
    list_filter = ('status', 'time_slot', 'ngo')
