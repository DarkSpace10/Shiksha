from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from django.core.paginator import Paginator

from apps.accounts.models import User, UserRole, StudentProfile, StudentVerificationStatus, Notification, NotificationType
from apps.ngos.models import NGO, NGOMembership, NGOStatus
from apps.donations.models import DonationListing, DonationStatus, PickupJob, PickupStatus
from apps.inventory.models import InventoryCopy, InventoryStatus
from apps.requests.models import BookRequest, RequestStatus, Allocation, DeliveryJob, DeliveryStatus
from apps.audit.models import AuditLog
from apps.audit.utils import log_audit
from apps.ngos.permissions import require_role, require_ngo_staff


@login_required
def dispatch(request):
    """Route user automatically to their dedicated role dashboard."""
    user = request.user
    if user.is_platform_admin:
        return redirect('dashboard:admin_dashboard')
    elif user.is_ngo_staff:
        return redirect('dashboard:ngo_dashboard')
    elif user.is_student:
        return redirect('dashboard:student_dashboard')
    else:
        return redirect('dashboard:donor_dashboard')


@login_required
@require_role(UserRole.DONOR)
def donor_dashboard(request):
    user = request.user
    donations_qs = DonationListing.objects.filter(donor=user).select_related('ngo').order_by('-created_at')

    # Aggregated KPI metrics
    stats = {
        'total': donations_qs.count(),
        'in_review': donations_qs.filter(status__in=[DonationStatus.SUBMITTED, DonationStatus.UNDER_REVIEW]).count(),
        'pickups': donations_qs.filter(status__in=[DonationStatus.APPROVED, DonationStatus.PICKUP_SCHEDULED]).count(),
        'collected': donations_qs.filter(status__in=[DonationStatus.COLLECTED, DonationStatus.INVENTORIED]).count(),
    }

    recent_donations = donations_qs[:6]
    recent_notifs = Notification.objects.filter(user=user)[:5]

    return render(request, 'dashboard/donor_dashboard.html', {
        'stats': stats,
        'recent_donations': recent_donations,
        'recent_notifs': recent_notifs,
        'DonationStatus': DonationStatus,
    })


@login_required
@require_role(UserRole.STUDENT)
def student_dashboard(request):
    user = request.user
    student_profile = getattr(user, 'student_profile', None)

    requests_qs = BookRequest.objects.filter(
        student=user
    ).select_related('inventory_copy__ngo', 'allocation__delivery_job').order_by('-created_at')

    stats = {
        'total_requests': requests_qs.count(),
        'in_progress': requests_qs.filter(status__in=[RequestStatus.PENDING, RequestStatus.UNDER_REVIEW, RequestStatus.APPROVED]).count(),
        'in_transit': requests_qs.filter(status=RequestStatus.ALLOCATED).count(),
        'delivered': requests_qs.filter(status=RequestStatus.COMPLETED).count(),
    }

    recent_requests = requests_qs[:6]
    available_books = InventoryCopy.objects.filter(status=InventoryStatus.AVAILABLE, is_published=True)[:4]

    return render(request, 'dashboard/student_dashboard.html', {
        'student_profile': student_profile,
        'stats': stats,
        'recent_requests': recent_requests,
        'available_books': available_books,
        'RequestStatus': RequestStatus,
        'StudentVerificationStatus': StudentVerificationStatus,
    })


@require_ngo_staff()
def ngo_dashboard(request):
    """Comprehensive operational dashboard for authorized NGO staff."""
    ngo = request.ngo

    # NGO specific isolated stats
    stats = {
        'pending_donations': DonationListing.objects.filter(
            ngo=ngo,
            status__in=[DonationStatus.SUBMITTED, DonationStatus.UNDER_REVIEW, DonationStatus.CORRECTION_REQUESTED]
        ).count(),
        'scheduled_pickups': PickupJob.objects.filter(
            ngo=ngo,
            status__in=[PickupStatus.SCHEDULED, PickupStatus.RESCHEDULED, PickupStatus.IN_PROGRESS]
        ).count(),
        'inspection_needed': DonationListing.objects.filter(
            ngo=ngo,
            status=DonationStatus.COLLECTED
        ).count(),
        'inventory_available': InventoryCopy.objects.filter(
            ngo=ngo,
            status=InventoryStatus.AVAILABLE
        ).count(),
        'pending_requests': BookRequest.objects.filter(
            ngo=ngo,
            status__in=[RequestStatus.PENDING, RequestStatus.UNDER_REVIEW]
        ).count(),
        'active_deliveries': DeliveryJob.objects.filter(
            ngo=ngo,
            status__in=[DeliveryStatus.PREPARING, DeliveryStatus.DISPATCHED, DeliveryStatus.OUT_FOR_DELIVERY]
        ).count(),
        'total_fulfilled': Allocation.objects.filter(
            ngo=ngo,
            status=AllocationStatus.FULFILLED
        ).count(),
        'staff_count': NGOMembership.objects.filter(ngo=ngo, is_active=True).count(),
    }

    recent_donations = DonationListing.objects.filter(ngo=ngo).select_related('donor').order_by('-created_at')[:5]
    recent_requests = BookRequest.objects.filter(ngo=ngo).select_related('student', 'inventory_copy').order_by('-created_at')[:5]

    return render(request, 'dashboard/ngo_dashboard.html', {
        'ngo': ngo,
        'membership': request.membership,
        'stats': stats,
        'recent_donations': recent_donations,
        'recent_requests': recent_requests,
    })


# ==============================================================================
# PLATFORM ADMINISTRATOR VIEWS
# ==============================================================================

@login_required
@require_role(UserRole.PLATFORM_ADMIN)
def admin_dashboard(request):
    """Platform administrator oversight, NGO application approvals, and audit trail."""
    tab = request.GET.get('tab', 'overview')

    # Aggregated Platform Metrics
    metrics = {
        'total_ngos': NGO.objects.count(),
        'approved_ngos': NGO.objects.filter(status=NGOStatus.APPROVED).count(),
        'pending_ngos': NGO.objects.filter(status=NGOStatus.PENDING_APPROVAL).count(),
        'total_donors': User.objects.filter(role=UserRole.DONOR).count(),
        'total_students': User.objects.filter(role=UserRole.STUDENT).count(),
        'total_donations': DonationListing.objects.count(),
        'total_inventory': InventoryCopy.objects.count(),
        'total_delivered': Allocation.objects.filter(status=AllocationStatus.FULFILLED).count(),
    }

    pending_ngos = NGO.objects.filter(status=NGOStatus.PENDING_APPROVAL).order_by('-created_at')
    all_ngos = NGO.objects.all().order_by('name')

    # User Management Tab
    role_filter = request.GET.get('role', '')
    user_search = request.GET.get('u_search', '')
    users_qs = User.objects.all().order_by('-created_at')
    if role_filter:
        users_qs = users_qs.filter(role=role_filter)
    if user_search:
        users_qs = users_qs.filter(
            Q(username__icontains=user_search) |
            Q(email__icontains=user_search) |
            Q(first_name__icontains=user_search) |
            Q(last_name__icontains=user_search)
        )
    users_paginator = Paginator(users_qs, 15)
    users_page = users_paginator.get_page(request.GET.get('u_page'))

    # Audit Logs Tab
    action_filter = request.GET.get('action', '')
    audit_search = request.GET.get('a_search', '')
    audit_qs = AuditLog.objects.select_related('user', 'organization').order_by('-timestamp')
    if action_filter:
        audit_qs = audit_qs.filter(action=action_filter)
    if audit_search:
        audit_qs = audit_qs.filter(
            Q(action__icontains=audit_search) |
            Q(entity_type__icontains=audit_search) |
            Q(user__username__icontains=audit_search) |
            Q(organization__name__icontains=audit_search)
        )
    audit_paginator = Paginator(audit_qs, 20)
    audit_page = audit_paginator.get_page(request.GET.get('a_page'))

    return render(request, 'dashboard/admin_dashboard.html', {
        'metrics': metrics,
        'tab': tab,
        'pending_ngos': pending_ngos,
        'all_ngos': all_ngos,
        'users_page': users_page,
        'audit_page': audit_page,
        'role_filter': role_filter,
        'user_search': user_search,
        'action_filter': action_filter,
        'audit_search': audit_search,
        'UserRole': UserRole,
        'NGOStatus': NGOStatus,
    })


@login_required
@require_role(UserRole.PLATFORM_ADMIN)
def admin_ngo_decision(request, ngo_id):
    """Platform administrator approves, rejects, or suspends an NGO."""
    ngo = get_object_or_404(NGO, id=ngo_id)
    action = request.POST.get('action')
    reason = request.POST.get('reason', '').strip()

    if action == 'APPROVE':
        ngo.status = NGOStatus.APPROVED
        ngo.approved_by = request.user
        ngo.approved_at = timezone.now()
        ngo.rejection_reason = ""
        ngo.save()

        # Notify NGO staff
        for m in ngo.memberships.all():
            Notification.objects.create(
                user=m.user,
                title=f"NGO Application Approved: {ngo.name}",
                message=f"Congratulations! {ngo.name} has been verified and approved by BookBridge Administration. Your staff team can now access operations.",
                notification_type=NotificationType.SUCCESS,
                link_url="/ngo/dashboard/"
            )

        log_audit(request, action="ADMIN_APPROVE_NGO", entity=ngo, organization=ngo)
        messages.success(request, f"NGO '{ngo.name}' has been APPROVED and activated.")

    elif action == 'REJECT':
        ngo.status = NGOStatus.REJECTED
        ngo.rejection_reason = reason or "Documentation criteria not met."
        ngo.save()

        for m in ngo.memberships.all():
            Notification.objects.create(
                user=m.user,
                title=f"NGO Application Update: {ngo.name}",
                message=f"Your NGO application was not approved. Feedback: {ngo.rejection_reason}",
                notification_type=NotificationType.DANGER
            )

        log_audit(request, action="ADMIN_REJECT_NGO", entity=ngo, organization=ngo, details={"reason": reason})
        messages.warning(request, f"NGO '{ngo.name}' has been REJECTED.")

    elif action == 'SUSPEND':
        ngo.status = NGOStatus.SUSPENDED
        ngo.rejection_reason = reason or "Temporarily suspended pending compliance review."
        ngo.save()

        log_audit(request, action="ADMIN_SUSPEND_NGO", entity=ngo, organization=ngo, details={"reason": reason})
        messages.warning(request, f"NGO '{ngo.name}' has been SUSPENDED.")

    elif action == 'REACTIVATE':
        ngo.status = NGOStatus.APPROVED
        ngo.save()

        log_audit(request, action="ADMIN_REACTIVATE_NGO", entity=ngo, organization=ngo)
        messages.success(request, f"NGO '{ngo.name}' has been REACTIVATED.")

    return redirect('/admin-panel/?tab=ngos')


@login_required
@require_role(UserRole.PLATFORM_ADMIN)
def admin_toggle_user_suspension(request, user_id):
    """Platform administrator suspends or activates a user account."""
    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, "You cannot suspend your own administrative account.")
        return redirect('/admin-panel/?tab=users')

    target_user.is_suspended = not target_user.is_suspended
    target_user.save()

    status_str = "SUSPENDED" if target_user.is_suspended else "ACTIVATED"
    log_audit(
        request,
        action=f"ADMIN_USER_{status_str}",
        entity=target_user,
        details={"target_username": target_user.username, "role": target_user.role}
    )
    messages.info(request, f"User account '{target_user.username}' is now {status_str}.")
    return redirect('/admin-panel/?tab=users')
