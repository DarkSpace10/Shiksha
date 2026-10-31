import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from .models import (
    DonationListing, DonationImage, DonationReview, PickupJob,
    DonationStatus, PickupStatus, ReviewDecision, ConditionGrade
)
from .forms import DonationCreateForm, DonationReviewForm, PickupScheduleForm, PhysicalInspectionForm
from apps.inventory.models import InventoryCopy, InventoryStatus
from apps.ngos.permissions import require_role, require_ngo_staff
from apps.accounts.models import UserRole, Notification, NotificationType
from apps.audit.utils import log_audit


@login_required
@require_role(UserRole.DONOR)
def donation_create(request):
    """Donor lists a new book donation with multiple images."""
    donor_profile = getattr(request.user, 'donor_profile', None)
    initial_data = {}
    if donor_profile:
        initial_data = {
            'pickup_address': donor_profile.address_line1,
            'pickup_city': donor_profile.city,
            'pickup_state': donor_profile.state,
            'pickup_postal_code': donor_profile.postal_code,
            'donor_contact_phone': request.user.phone_number or '',
            'preferred_pickup_time': donor_profile.preferred_pickup_instructions,
        }

    if request.method == 'POST':
        form = DonationCreateForm(request.POST, initial=initial_data)
        images = request.FILES.getlist('images')

        if form.is_valid():
            with transaction.atomic():
                donation = form.save(commit=False)
                donation.donor = request.user
                donation.status = DonationStatus.SUBMITTED
                donation.save()

                # Process multiple uploaded images
                for i, img_file in enumerate(images):
                    DonationImage.objects.create(
                        donation=donation,
                        image=img_file,
                        caption=f"Image {i + 1}",
                        is_primary=(i == 0)
                    )

                # Update donor profile stats
                if donor_profile:
                    donor_profile.total_donations_count += 1
                    donor_profile.save()

                # Notify donor
                Notification.objects.create(
                    user=request.user,
                    title="Book Donation Submitted",
                    message=f"Your donation for '{donation.title}' has been submitted to {donation.ngo.name} for verification.",
                    notification_type=NotificationType.SUCCESS,
                    link_url=f"/donations/{donation.id}/"
                )

                # Notify NGO staff members who have review permissions
                ngo_staff_memberships = donation.ngo.memberships.filter(is_active=True, can_review_donations=True)
                for m in ngo_staff_memberships:
                    Notification.objects.create(
                        user=m.user,
                        title=f"New Donation Received: {donation.title}",
                        message=f"Donor {request.user.full_name} has submitted '{donation.title}' for review.",
                        notification_type=NotificationType.INFO,
                        link_url=f"/donations/{donation.id}/"
                    )

                log_audit(
                    request,
                    action="DONATION_SUBMIT",
                    entity=donation,
                    organization=donation.ngo,
                    details={"title": donation.title, "ngo": donation.ngo.name}
                )

                messages.success(request, f"Book donation '{donation.title}' submitted! The NGO will review it shortly.")
                return redirect('donations:donation_detail', donation_id=donation.id)
    else:
        form = DonationCreateForm(initial=initial_data)

    return render(request, 'donations/donation_create.html', {'form': form})


@login_required
def my_donations(request):
    """List of all book donations created by the logged-in donor."""
    if not (request.user.is_donor or request.user.is_platform_admin):
        return redirect('dashboard:dispatch')

    status_filter = request.GET.get('status', '').strip()
    search_query = request.GET.get('q', '').strip()

    donations_qs = DonationListing.objects.filter(donor=request.user).select_related('ngo').prefetch_related('images')

    if status_filter:
        donations_qs = donations_qs.filter(status=status_filter)

    if search_query:
        donations_qs = donations_qs.filter(
            Q(title__icontains=search_query) |
            Q(author__icontains=search_query) |
            Q(subject__icontains=search_query)
        )

    paginator = Paginator(donations_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'donations/my_donations.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'DonationStatus': DonationStatus,
    })


@login_required
def donation_detail(request, donation_id):
    """View complete details and life-cycle timeline of a donation."""
    donation = get_object_or_404(
        DonationListing.objects.select_related('donor', 'ngo', 'inspected_by').prefetch_related('images', 'reviews__reviewer'),
        id=donation_id
    )

    # Access control: Donor, assigned NGO staff, or platform admin
    has_access = False
    if request.user.is_platform_admin:
        has_access = True
    elif request.user == donation.donor:
        has_access = True
    elif request.user.is_ngo_staff:
        membership = request.user.ngo_memberships.filter(ngo=donation.ngo, is_active=True).first()
        if membership:
            has_access = True

    if not has_access:
        messages.error(request, "You are not authorized to view this donation record.")
        return redirect('dashboard:dispatch')

    pickup_job = getattr(donation, 'pickup_job', None)
    inventory_copy = donation.inventory_copies.first()

    return render(request, 'donations/donation_detail.html', {
        'donation': donation,
        'pickup_job': pickup_job,
        'inventory_copy': inventory_copy,
        'is_ngo_staff_viewer': request.user.is_ngo_staff and request.user.ngo_memberships.filter(ngo=donation.ngo, is_active=True).exists(),
    })


@login_required
@require_role(UserRole.DONOR)
def donation_cancel(request, donation_id):
    donation = get_object_or_404(DonationListing, id=donation_id, donor=request.user)

    cancellable_states = [
        DonationStatus.SUBMITTED,
        DonationStatus.UNDER_REVIEW,
        DonationStatus.CORRECTION_REQUESTED,
        DonationStatus.APPROVED,
        DonationStatus.PICKUP_SCHEDULED,
        DonationStatus.FAILED_PICKUP
    ]

    if donation.status not in cancellable_states:
        messages.error(request, "This donation cannot be cancelled at its current stage.")
        return redirect('donations:donation_detail', donation_id=donation.id)

    with transaction.atomic():
        donation.status = DonationStatus.CANCELLED
        donation.save()

        # Cancel any scheduled pickup job
        if hasattr(donation, 'pickup_job'):
            pickup = donation.pickup_job
            pickup.status = PickupStatus.CANCELLED
            pickup.notes += " [Cancelled by Donor]"
            pickup.save()

        log_audit(request, action="DONATION_CANCEL", entity=donation, organization=donation.ngo)
        messages.info(request, f"Donation for '{donation.title}' has been cancelled.")

    return redirect('donations:my_donations')


# ==============================================================================
# NGO STAFF WORKFLOW VIEWS (Strict Organization Isolation)
# ==============================================================================

@require_ngo_staff()
def ngo_donations_list(request):
    """NGO staff review and operations queue for donations received by their organization."""
    tab = request.GET.get('tab', 'pending')
    search_query = request.GET.get('q', '').strip()

    qs = DonationListing.objects.filter(ngo=request.ngo).select_related('donor').prefetch_related('images')

    if tab == 'pending':
        qs = qs.filter(status__in=[DonationStatus.SUBMITTED, DonationStatus.UNDER_REVIEW, DonationStatus.CORRECTION_REQUESTED])
    elif tab == 'pickups':
        qs = qs.filter(status__in=[DonationStatus.APPROVED, DonationStatus.PICKUP_SCHEDULED, DonationStatus.FAILED_PICKUP])
    elif tab == 'inspection':
        qs = qs.filter(status__in=[DonationStatus.COLLECTED, DonationStatus.INSPECTION_FAILED])
    elif tab == 'completed':
        qs = qs.filter(status=DonationStatus.INVENTORIED)
    elif tab == 'rejected':
        qs = qs.filter(status__in=[DonationStatus.REJECTED, DonationStatus.CANCELLED])

    if search_query:
        qs = qs.filter(
            Q(title__icontains=search_query) |
            Q(author__icontains=search_query) |
            Q(donor__username__icontains=search_query) |
            Q(pickup_city__icontains=search_query)
        )

    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Counts for tab badges
    counts = {
        'pending': DonationListing.objects.filter(ngo=request.ngo, status__in=[DonationStatus.SUBMITTED, DonationStatus.UNDER_REVIEW, DonationStatus.CORRECTION_REQUESTED]).count(),
        'pickups': DonationListing.objects.filter(ngo=request.ngo, status__in=[DonationStatus.APPROVED, DonationStatus.PICKUP_SCHEDULED, DonationStatus.FAILED_PICKUP]).count(),
        'inspection': DonationListing.objects.filter(ngo=request.ngo, status__in=[DonationStatus.COLLECTED, DonationStatus.INSPECTION_FAILED]).count(),
        'completed': DonationListing.objects.filter(ngo=request.ngo, status=DonationStatus.INVENTORIED).count(),
        'all': DonationListing.objects.filter(ngo=request.ngo).count(),
    }

    return render(request, 'donations/ngo_donations_list.html', {
        'ngo': request.ngo,
        'page_obj': page_obj,
        'tab': tab,
        'search_query': search_query,
        'counts': counts,
    })


@require_ngo_staff('can_review_donations')
def ngo_donation_review(request, donation_id):
    """Review donation details and images, then Approve, Reject, or Request Corrections."""
    donation = get_object_or_404(DonationListing, id=donation_id, ngo=request.ngo)

    if request.method == 'POST':
        form = DonationReviewForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data['decision']
            comments = form.cleaned_data['comments']

            with transaction.atomic():
                # Record review log
                DonationReview.objects.create(
                    donation=donation,
                    reviewer=request.user,
                    decision=decision,
                    comments=comments
                )

                if decision == ReviewDecision.APPROVED:
                    donation.status = DonationStatus.APPROVED
                    donation.rejection_reason = ""
                    notif_title = f"Donation Approved: {donation.title}"
                    notif_msg = f"{request.ngo.name} has approved your book! A pickup will be scheduled soon. Note: {comments}"
                    notif_type = NotificationType.SUCCESS
                elif decision == ReviewDecision.REJECTED:
                    donation.status = DonationStatus.REJECTED
                    donation.rejection_reason = comments
                    notif_title = f"Donation Not Accepted: {donation.title}"
                    notif_msg = f"{request.ngo.name} could not accept this donation. Reason: {comments}"
                    notif_type = NotificationType.DANGER
                else:  # CORRECTION_REQUESTED
                    donation.status = DonationStatus.CORRECTION_REQUESTED
                    donation.correction_notes = comments
                    notif_title = f"Correction Requested: {donation.title}"
                    notif_msg = f"{request.ngo.name} requested more information or clearer photos. Feedback: {comments}"
                    notif_type = NotificationType.WARNING

                donation.save()

                # Send notification to donor
                Notification.objects.create(
                    user=donation.donor,
                    title=notif_title,
                    message=notif_msg,
                    notification_type=notif_type,
                    link_url=f"/donations/{donation.id}/"
                )

                log_audit(
                    request,
                    action=f"DONATION_REVIEW_{decision}",
                    entity=donation,
                    organization=request.ngo,
                    details={"decision": decision, "comments": comments}
                )

                messages.success(request, f"Donation review recorded: {decision}")
                return redirect('donations:ngo_donations_list')
    else:
        form = DonationReviewForm()

    return render(request, 'donations/ngo_donation_review.html', {
        'donation': donation,
        'form': form,
        'ngo': request.ngo,
    })


@require_ngo_staff('can_schedule_pickups')
def ngo_pickup_schedule(request, donation_id):
    """Schedule physical book collection from donor address."""
    donation = get_object_or_404(DonationListing, id=donation_id, ngo=request.ngo)

    pickup_job = getattr(donation, 'pickup_job', None)

    if request.method == 'POST':
        form = PickupScheduleForm(request.POST, instance=pickup_job)
        if form.is_valid():
            with transaction.atomic():
                pickup = form.save(commit=False)
                pickup.donation = donation
                pickup.ngo = request.ngo
                pickup.status = PickupStatus.SCHEDULED
                pickup.save()

                donation.status = DonationStatus.PICKUP_SCHEDULED
                donation.save()

                Notification.objects.create(
                    user=donation.donor,
                    title=f"Pickup Scheduled: {donation.title}",
                    message=f"{request.ngo.name} has scheduled pickup on {pickup.scheduled_date} ({pickup.get_time_slot_display()}). Assigned Agent: {pickup.assigned_agent_name} ({pickup.assigned_agent_phone}).",
                    notification_type=NotificationType.INFO,
                    link_url=f"/donations/{donation.id}/"
                )

                log_audit(
                    request,
                    action="PICKUP_SCHEDULE",
                    entity=pickup,
                    organization=request.ngo,
                    details={"date": str(pickup.scheduled_date), "slot": pickup.time_slot, "agent": pickup.assigned_agent_name}
                )

                messages.success(request, f"Pickup scheduled for {pickup.scheduled_date}.")
                return redirect('donations:ngo_donations_list')
    else:
        form = PickupScheduleForm(instance=pickup_job)

    return render(request, 'donations/ngo_pickup_schedule.html', {
        'donation': donation,
        'form': form,
        'ngo': request.ngo,
    })


@require_ngo_staff('can_schedule_pickups')
def ngo_pickup_status_update(request, pickup_id):
    """Mark pickup as Collected or Failed."""
    pickup = get_object_or_404(PickupJob, id=pickup_id, ngo=request.ngo)
    donation = pickup.donation

    new_status = request.POST.get('status')
    notes = request.POST.get('notes', '').strip()

    if new_status == 'COLLECTED':
        with transaction.atomic():
            pickup.status = PickupStatus.COMPLETED
            pickup.completed_at = timezone.now()
            if notes:
                pickup.notes += f"\n[Collection Notes]: {notes}"
            pickup.save()

            donation.status = DonationStatus.COLLECTED
            donation.save()

            Notification.objects.create(
                user=donation.donor,
                title=f"Book Collected: {donation.title}",
                message=f"Your donated book '{donation.title}' has been successfully collected and received at {request.ngo.name}'s facility. Next step: Physical Quality Inspection.",
                notification_type=NotificationType.SUCCESS,
                link_url=f"/donations/{donation.id}/"
            )

            log_audit(request, action="PICKUP_COLLECTED", entity=pickup, organization=request.ngo)
            messages.success(request, f"Donation '{donation.title}' marked as COLLECTED. Ready for physical inspection.")

    elif new_status == 'FAILED':
        with transaction.atomic():
            pickup.status = PickupStatus.FAILED
            pickup.failure_reason = notes or "Donor unavailable / address issue."
            pickup.save()

            donation.status = DonationStatus.FAILED_PICKUP
            donation.save()

            Notification.objects.create(
                user=donation.donor,
                title=f"Pickup Attempt Failed: {donation.title}",
                message=f"Our agent was unable to collect the book. Reason: {pickup.failure_reason}. We will contact you to reschedule.",
                notification_type=NotificationType.WARNING,
                link_url=f"/donations/{donation.id}/"
            )

            log_audit(request, action="PICKUP_FAILED", entity=pickup, organization=request.ngo, details={"reason": pickup.failure_reason})
            messages.warning(request, f"Pickup recorded as FAILED for '{donation.title}'.")

    return redirect('donations:ngo_donations_list')


@require_ngo_staff('can_inspect_books')
def ngo_physical_inspection(request, donation_id):
    """
    NGO staff conducts rigorous physical quality inspection on collected book.
    If Passed:
      - Generates inventory tracking code / SKU
      - Creates InventoryCopy record in warehouse shelf
      - Publishes book into student searchable catalogue
      - Marks donation as INVENTORIED
    If Failed:
      - Marks donation as INSPECTION_FAILED with explanatory notes
    """
    donation = get_object_or_404(DonationListing, id=donation_id, ngo=request.ngo)

    if request.method == 'POST':
        form = PhysicalInspectionForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data['decision']
            verified_condition = form.cleaned_data['verified_condition']
            location_shelf = form.cleaned_data['location_shelf']
            inspection_notes = form.cleaned_data['inspection_notes']

            with transaction.atomic():
                donation.inspected_by = request.user
                donation.inspected_at = timezone.now()
                donation.verified_condition = verified_condition
                donation.inspection_notes = inspection_notes

                if decision == 'PASSED':
                    donation.status = DonationStatus.INVENTORIED
                    donation.save()

                    # Generate standardized unique SKU / Tracking Code
                    # Format: BB-{NGO_SLUG[:6]}-{YEAR}-{RANDOM_HEX}
                    year = timezone.now().year
                    unique_suffix = uuid.uuid4().hex[:6].upper()
                    ngo_prefix = (donation.ngo.slug[:6] or "NGO").upper()
                    tracking_code = f"BB-{ngo_prefix}-{year}-{unique_suffix}"

                    # Primary cover image from donation photos if any
                    cover_img = None
                    primary_img_obj = donation.images.filter(is_primary=True).first() or donation.images.first()
                    if primary_img_obj:
                        cover_img = primary_img_obj.image

                    inventory_copy = InventoryCopy.objects.create(
                        ngo=request.ngo,
                        donation_listing=donation,
                        tracking_code=tracking_code,
                        book_title=donation.title,
                        author=donation.author,
                        isbn=donation.isbn,
                        publisher=donation.publisher,
                        publication_year=donation.publication_year,
                        edition=donation.edition,
                        category=donation.category,
                        academic_level=donation.academic_level,
                        subject=donation.subject,
                        condition_grade=verified_condition,
                        location_shelf=location_shelf,
                        status=InventoryStatus.AVAILABLE,
                        is_published=True,
                        cover_image=cover_img,
                        notes=f"Physical inspection passed by {request.user.full_name}. {inspection_notes}"
                    )

                    Notification.objects.create(
                        user=donation.donor,
                        title=f"Book Published & Catalogued: {donation.title}",
                        message=f"Great news! Your donated book passed quality inspection and is now catalogued with SKU [{tracking_code}] for needy students to request. Thank you for your impact!",
                        notification_type=NotificationType.SUCCESS,
                        link_url=f"/catalogue/{inventory_copy.id}/"
                    )

                    log_audit(
                        request,
                        action="INSPECTION_PASSED_INVENTORIED",
                        entity=inventory_copy,
                        organization=request.ngo,
                        details={"tracking_code": tracking_code, "condition": verified_condition, "shelf": location_shelf}
                    )

                    messages.success(request, f"Book successfully inspected, catalogued with SKU [{tracking_code}], and published to catalogue!")
                    return redirect('inventory:ngo_inventory_list')

                else:  # FAILED
                    donation.status = DonationStatus.INSPECTION_FAILED
                    donation.save()

                    Notification.objects.create(
                        user=donation.donor,
                        title=f"Inspection Update: {donation.title}",
                        message=f"Unfortunately, upon physical inspection at our facility, the book did not meet minimum educational preservation standards. Details: {inspection_notes}",
                        notification_type=NotificationType.WARNING,
                        link_url=f"/donations/{donation.id}/"
                    )

                    log_audit(
                        request,
                        action="INSPECTION_FAILED",
                        entity=donation,
                        organization=request.ngo,
                        details={"notes": inspection_notes}
                    )

                    messages.warning(request, f"Book marked as INSPECTION FAILED. Record updated.")
                    return redirect('donations:ngo_donations_list')
    else:
        form = PhysicalInspectionForm(initial={
            'verified_condition': donation.declared_condition,
            'location_shelf': 'Shelf A-1',
        })

    return render(request, 'donations/ngo_physical_inspection.html', {
        'donation': donation,
        'form': form,
        'ngo': request.ngo,
    })
