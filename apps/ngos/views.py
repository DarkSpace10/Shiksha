from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q

from .models import NGO, NGOMembership, NGOMemberRole, NGOServiceArea, NGOStatus
from .forms import NGORegistrationForm, NGOStaffCreateForm, NGOServiceAreaForm
from .permissions import require_ngo_staff
from apps.accounts.models import User, UserRole, Notification, NotificationType
from apps.audit.utils import log_audit


def register_ngo(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dispatch')

    if request.method == 'POST':
        form = NGORegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                ngo = form.save(commit=False)
                ngo.status = NGOStatus.PENDING_APPROVAL
                ngo.save()

                # Create NGO Admin user
                admin_user = User.objects.create_user(
                    username=form.cleaned_data['admin_username'],
                    email=form.cleaned_data['admin_email'],
                    password=form.cleaned_data['admin_password'],
                    first_name=form.cleaned_data['admin_first_name'],
                    last_name=form.cleaned_data['admin_last_name'],
                    phone_number=form.cleaned_data['admin_phone'],
                    role=UserRole.NGO_STAFF,
                    is_verified=True
                )

                # Create NGO Admin Membership
                membership = NGOMembership.objects.create(
                    user=admin_user,
                    ngo=ngo,
                    role=NGOMemberRole.NGO_ADMIN,
                    can_manage_staff=True,
                    can_review_donations=True,
                    can_schedule_pickups=True,
                    can_inspect_books=True,
                    can_manage_inventory=True,
                    can_verify_students=True,
                    can_review_requests=True,
                    can_manage_deliveries=True
                )

                # Create initial service area
                NGOServiceArea.objects.create(
                    ngo=ngo,
                    city=form.cleaned_data['primary_service_city'],
                    state=form.cleaned_data['primary_service_state'],
                    is_active=True
                )

                # Send in-app notification
                Notification.objects.create(
                    user=admin_user,
                    title="NGO Application Received",
                    message=f"Thank you for registering '{ngo.name}'. Our platform administrators are reviewing your trust credentials. You will receive an update shortly.",
                    notification_type=NotificationType.INFO
                )

                log_audit(
                    request,
                    action="NGO_REGISTER_APPLICATION",
                    entity=ngo,
                    organization=ngo,
                    user=admin_user,
                    details={"ngo_name": ngo.name, "reg_no": ngo.registration_number}
                )

                login(request, admin_user)
                messages.info(
                    request,
                    f"Application for '{ngo.name}' submitted successfully! It is currently awaiting platform administrator verification."
                )
                return redirect('ngos:ngo_status_page', ngo_id=ngo.id)
    else:
        form = NGORegistrationForm()

    return render(request, 'ngos/register_ngo.html', {'form': form})


@login_required
def ngo_status_page(request, ngo_id):
    ngo = get_object_or_404(NGO, id=ngo_id)
    # Check that user belongs to this NGO or is platform admin
    if not request.user.is_platform_admin:
        if not NGOMembership.objects.filter(user=request.user, ngo=ngo).exists():
            messages.error(request, "Access denied.")
            return redirect('core:home')

    return render(request, 'ngos/status_page.html', {'ngo': ngo})


def public_directory(request):
    """Public listing of all verified and approved partner NGOs."""
    search_query = request.GET.get('q', '').strip()
    city_filter = request.GET.get('city', '').strip()

    ngos_qs = NGO.objects.filter(status=NGOStatus.APPROVED).prefetch_related('service_areas').annotate(
        books_count=Count('inventory_copies', filter=Q(inventory_copies__status='AVAILABLE', inventory_copies__is_published=True))
    )

    if search_query:
        ngos_qs = ngos_qs.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(city__icontains=search_query)
        )

    if city_filter:
        ngos_qs = ngos_qs.filter(
            Q(city__icontains=city_filter) |
            Q(service_areas__city__icontains=city_filter)
        ).distinct()

    # Get distinct cities for filter dropdown
    available_cities = NGOServiceArea.objects.filter(
        ngo__status=NGOStatus.APPROVED,
        is_active=True
    ).values_list('city', flat=True).distinct().order_by('city')

    return render(request, 'ngos/public_directory.html', {
        'ngos': ngos_qs,
        'search_query': search_query,
        'city_filter': city_filter,
        'available_cities': available_cities,
    })


def ngo_detail(request, slug):
    ngo = get_object_or_404(NGO, slug=slug, status=NGOStatus.APPROVED)
    service_areas = ngo.service_areas.filter(is_active=True)
    available_books = ngo.inventory_copies.filter(status='AVAILABLE', is_published=True)[:8]
    total_distributed = ngo.allocations.filter(status='FULFILLED').count()

    return render(request, 'ngos/ngo_detail.html', {
        'ngo': ngo,
        'service_areas': service_areas,
        'available_books': available_books,
        'total_distributed': total_distributed,
    })


@require_ngo_staff('can_manage_staff')
def staff_list(request):
    """Manage NGO Staff members with strict organization isolation."""
    memberships = NGOMembership.objects.filter(ngo=request.ngo).select_related('user').order_by('-joined_at')
    return render(request, 'ngos/staff_list.html', {
        'ngo': request.ngo,
        'memberships': memberships,
    })


@require_ngo_staff('can_manage_staff')
def staff_create(request):
    """Invite/Create a new staff member within the current NGO."""
    if request.method == 'POST':
        form = NGOStaffCreateForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                staff_user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    phone_number=form.cleaned_data.get('phone_number', ''),
                    role=UserRole.NGO_STAFF,
                    is_verified=True
                )
                NGOMembership.objects.create(
                    user=staff_user,
                    ngo=request.ngo,
                    role=form.cleaned_data['role'],
                    can_review_donations=form.cleaned_data['can_review_donations'],
                    can_schedule_pickups=form.cleaned_data['can_schedule_pickups'],
                    can_inspect_books=form.cleaned_data['can_inspect_books'],
                    can_manage_inventory=form.cleaned_data['can_manage_inventory'],
                    can_verify_students=form.cleaned_data['can_verify_students'],
                    can_review_requests=form.cleaned_data['can_review_requests'],
                    can_manage_deliveries=form.cleaned_data['can_manage_deliveries'],
                    can_manage_staff=form.cleaned_data['can_manage_staff']
                )
                Notification.objects.create(
                    user=staff_user,
                    title=f"Welcome to {request.ngo.name} Staff Team",
                    message=f"You have been added as an operational team member ({form.cleaned_data['role']}). You can now access your organization's dashboard.",
                    notification_type=NotificationType.SUCCESS
                )
                log_audit(
                    request,
                    action="STAFF_MEMBER_CREATE",
                    entity=staff_user,
                    organization=request.ngo,
                    details={"staff_username": staff_user.username, "role": form.cleaned_data['role']}
                )
                messages.success(request, f"Staff member '{staff_user.username}' added successfully.")
                return redirect('ngos:staff_list')
    else:
        form = NGOStaffCreateForm()

    return render(request, 'ngos/staff_create.html', {'form': form, 'ngo': request.ngo})


@require_ngo_staff('can_manage_staff')
def staff_toggle_status(request, membership_id):
    membership = get_object_or_404(NGOMembership, id=membership_id, ngo=request.ngo)
    if membership.user == request.user:
        messages.error(request, "You cannot deactivate your own staff membership.")
        return redirect('ngos:staff_list')

    membership.is_active = not membership.is_active
    membership.save()
    status_str = "activated" if membership.is_active else "deactivated"
    log_audit(
        request,
        action="STAFF_MEMBER_TOGGLE_STATUS",
        entity=membership.user,
        organization=request.ngo,
        details={"status": status_str}
    )
    messages.info(request, f"Staff member {membership.user.username} has been {status_str}.")
    return redirect('ngos:staff_list')


@require_ngo_staff()
def service_areas_list(request):
    areas = NGOServiceArea.objects.filter(ngo=request.ngo).order_by('state', 'city')
    form = NGOServiceAreaForm()
    return render(request, 'ngos/service_areas.html', {'areas': areas, 'form': form, 'ngo': request.ngo})


@require_ngo_staff()
def service_area_create(request):
    if request.method == 'POST':
        form = NGOServiceAreaForm(request.POST)
        if form.is_valid():
            area = form.save(commit=False)
            area.ngo = request.ngo
            area.save()
            log_audit(request, action="SERVICE_AREA_ADD", entity=area, organization=request.ngo)
            messages.success(request, f"Service coverage area for {area.city}, {area.state} added.")
    return redirect('ngos:service_areas')


@require_ngo_staff()
def service_area_delete(request, area_id):
    area = get_object_or_404(NGOServiceArea, id=area_id, ngo=request.ngo)
    city_name = area.city
    area.delete()
    log_audit(request, action="SERVICE_AREA_REMOVE", entity=None, organization=request.ngo, details={"city": city_name})
    messages.info(request, f"Service area '{city_name}' removed.")
    return redirect('ngos:service_areas')
