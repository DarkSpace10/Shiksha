from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import InventoryCopy, InventoryStatus
from apps.donations.models import BookCategory, ConditionGrade
from apps.accounts.models import AcademicLevel, UserRole
from apps.ngos.models import NGO, NGOStatus
from apps.ngos.permissions import require_ngo_staff
from apps.audit.utils import log_audit


def catalogue(request):
    """
    Public and student-accessible searchable inventory catalogue.
    Displays verified educational books available across partner NGOs.
    """
    search_query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()
    level_filter = request.GET.get('level', '').strip()
    condition_filter = request.GET.get('condition', '').strip()
    ngo_filter = request.GET.get('ngo', '').strip()
    show_all = request.GET.get('all', '0') == '1'

    qs = InventoryCopy.objects.filter(is_published=True).select_related('ngo', 'donation_listing')

    if not show_all:
        qs = qs.filter(status=InventoryStatus.AVAILABLE)

    if search_query:
        qs = qs.filter(
            Q(book_title__icontains=search_query) |
            Q(author__icontains=search_query) |
            Q(subject__icontains=search_query) |
            Q(isbn__icontains=search_query) |
            Q(tracking_code__icontains=search_query)
        )

    if category_filter:
        qs = qs.filter(category=category_filter)

    if level_filter:
        qs = qs.filter(academic_level=level_filter)

    if condition_filter:
        qs = qs.filter(condition_grade=condition_filter)

    if ngo_filter:
        qs = qs.filter(ngo_id=ngo_filter)

    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    active_ngos = NGO.objects.filter(status=NGOStatus.APPROVED).order_by('name')

    return render(request, 'inventory/catalogue.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'category_filter': category_filter,
        'level_filter': level_filter,
        'condition_filter': condition_filter,
        'ngo_filter': ngo_filter,
        'show_all': show_all,
        'categories': BookCategory.choices,
        'academic_levels': AcademicLevel.choices,
        'condition_grades': ConditionGrade.choices,
        'active_ngos': active_ngos,
    })


def book_detail(request, copy_id):
    """Public details view for an inventory copy with request call-to-action."""
    copy = get_object_or_404(
        InventoryCopy.objects.select_related('ngo', 'donation_listing'),
        id=copy_id
    )

    donation_images = []
    if copy.donation_listing:
        donation_images = copy.donation_listing.images.all()

    student_profile = None
    has_active_request = False
    if request.user.is_authenticated and request.user.is_student:
        student_profile = getattr(request.user, 'student_profile', None)
        has_active_request = copy.requests.filter(
            student=request.user,
            status__in=['PENDING', 'UNDER_REVIEW', 'APPROVED', 'ALLOCATED']
        ).exists()

    return render(request, 'inventory/book_detail.html', {
        'copy': copy,
        'donation_images': donation_images,
        'student_profile': student_profile,
        'has_active_request': has_active_request,
    })


@require_ngo_staff('can_manage_inventory')
def ngo_inventory_list(request):
    """NGO staff inventory management for their specific physical facility."""
    status_filter = request.GET.get('status', '').strip()
    search_query = request.GET.get('q', '').strip()

    qs = InventoryCopy.objects.filter(ngo=request.ngo).order_by('-created_at')

    if status_filter:
        qs = qs.filter(status=status_filter)

    if search_query:
        qs = qs.filter(
            Q(book_title__icontains=search_query) |
            Q(author__icontains=search_query) |
            Q(tracking_code__icontains=search_query) |
            Q(location_shelf__icontains=search_query)
        )

    paginator = Paginator(qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    counts = {
        'available': InventoryCopy.objects.filter(ngo=request.ngo, status=InventoryStatus.AVAILABLE).count(),
        'reserved': InventoryCopy.objects.filter(ngo=request.ngo, status=InventoryStatus.RESERVED).count(),
        'allocated': InventoryCopy.objects.filter(ngo=request.ngo, status=InventoryStatus.ALLOCATED).count(),
        'delivered': InventoryCopy.objects.filter(ngo=request.ngo, status=InventoryStatus.DELIVERED).count(),
        'total': InventoryCopy.objects.filter(ngo=request.ngo).count(),
    }

    return render(request, 'inventory/ngo_inventory_list.html', {
        'ngo': request.ngo,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'counts': counts,
        'InventoryStatus': InventoryStatus,
    })


@require_ngo_staff('can_manage_inventory')
def inventory_toggle_publish(request, copy_id):
    """Toggle whether an inventory copy appears in public search catalogue."""
    copy = get_object_or_404(InventoryCopy, id=copy_id, ngo=request.ngo)
    copy.is_published = not copy.is_published
    copy.save()

    status_str = "Published to" if copy.is_published else "Hidden from"
    log_audit(
        request,
        action="INVENTORY_TOGGLE_PUBLISH",
        entity=copy,
        organization=request.ngo,
        details={"is_published": copy.is_published}
    )
    messages.info(request, f"Book '{copy.book_title}' is now {status_str} the public catalogue.")
    return redirect('inventory:ngo_inventory_list')
