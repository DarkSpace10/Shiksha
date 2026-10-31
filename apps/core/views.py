from django.shortcuts import render
from apps.inventory.models import InventoryCopy, InventoryStatus
from apps.ngos.models import NGO, NGOStatus
from apps.donations.models import DonationListing
from apps.accounts.models import User, UserRole
from apps.requests.models import Allocation, AllocationStatus


def home(request):
    """Modern public homepage with platform impact metrics and featured textbooks."""
    featured_books = InventoryCopy.objects.filter(
        status=InventoryStatus.AVAILABLE,
        is_published=True
    ).select_related('ngo')[:6]

    verified_ngos = NGO.objects.filter(status=NGOStatus.APPROVED).prefetch_related('service_areas')[:4]

    impact_stats = {
        'total_books_donated': DonationListing.objects.count(),
        'active_partner_ngos': NGO.objects.filter(status=NGOStatus.APPROVED).count(),
        'students_supported': Allocation.objects.filter(status=AllocationStatus.FULFILLED).count(),
        'available_in_inventory': InventoryCopy.objects.filter(status=InventoryStatus.AVAILABLE).count(),
    }

    return render(request, 'core/home.html', {
        'featured_books': featured_books,
        'verified_ngos': verified_ngos,
        'stats': impact_stats,
    })


def how_it_works(request):
    """Detailed visual guide to the multi-NGO verification and distribution pipeline."""
    return render(request, 'core/how_it_works.html')


def about(request):
    """About BookBridge: Mission, Security, and Non-Profit Accountability."""
    return render(request, 'core/about.html')
