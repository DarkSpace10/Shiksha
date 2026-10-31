import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q

from .models import (
    BookRequest, RequestStatus, RequestReview, Allocation, AllocationStatus,
    DeliveryJob, DeliveryStatus, StudentVerification, VerificationDecision,
    VerificationDocument
)
from .forms import (
    BookRequestCreateForm, VerificationDocumentUploadForm,
    StudentVerificationForm, DeliveryDispatchForm, StudentConfirmReceiptForm
)
from apps.inventory.models import InventoryCopy, InventoryStatus
from apps.accounts.models import StudentProfile, StudentVerificationStatus, UserRole, Notification, NotificationType
from apps.ngos.permissions import require_role, require_ngo_staff
from apps.audit.utils import log_audit


# ==============================================================================
# STUDENT WORKFLOW VIEWS
# ==============================================================================

@login_required
@require_role(UserRole.STUDENT)
def document_upload(request):
    """Student uploads academic identity / enrollment proofs for verification."""
    student_profile = request.user.student_profile

    if request.method == 'POST':
        form = VerificationDocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.student_profile = student_profile
            doc.save()

            # Set profile status to PENDING if previously rejected/needs update
            if student_profile.verification_status != StudentVerificationStatus.VERIFIED:
                student_profile.verification_status = StudentVerificationStatus.PENDING
                student_profile.save()

            log_audit(
                request,
                action="STUDENT_DOC_UPLOAD",
                entity=doc,
                details={"doc_type": doc.document_type, "title": doc.document_title}
            )
            messages.success(request, f"Document '{doc.document_title}' uploaded successfully.")
            return redirect('requests:document_upload')
    else:
        form = VerificationDocumentUploadForm()

    documents = student_profile.documents.all()

    return render(request, 'requests/document_upload.html', {
        'form': form,
        'student_profile': student_profile,
        'documents': documents,
    })


@login_required
@require_role(UserRole.STUDENT)
def document_delete(request, doc_id):
    student_profile = request.user.student_profile
    doc = get_object_or_404(VerificationDocument, id=doc_id, student_profile=student_profile)
    title = doc.document_title
    doc.delete()
    log_audit(request, action="STUDENT_DOC_DELETE", details={"title": title})
    messages.info(request, f"Document '{title}' removed.")
    return redirect('requests:document_upload')


@login_required
@require_role(UserRole.STUDENT)
def request_create(request, copy_id):
    """
    Student requests an available book from the inventory.
    Requires genuine educational purpose and delivery address.
    """
    copy = get_object_or_404(InventoryCopy.objects.select_related('ngo'), id=copy_id, is_published=True)
    student_profile = request.user.student_profile

    # Check if student already has a pending or active request for this book copy
    existing_active = BookRequest.objects.filter(
        student=request.user,
        inventory_copy=copy,
        status__in=[RequestStatus.PENDING, RequestStatus.UNDER_REVIEW, RequestStatus.APPROVED, RequestStatus.ALLOCATED]
    ).exists()

    if existing_active:
        messages.warning(request, "You already have an active request in progress for this book copy.")
        return redirect('inventory:book_detail', copy_id=copy.id)

    initial_data = {
        'delivery_address': student_profile.delivery_address,
        'delivery_city': student_profile.delivery_city,
        'delivery_state': student_profile.delivery_state,
        'delivery_postal_code': student_profile.delivery_postal_code,
        'contact_phone': request.user.phone_number or '',
    }

    if request.method == 'POST':
        form = BookRequestCreateForm(request.POST, initial=initial_data)
        if form.is_valid():
            with transaction.atomic():
                book_req = form.save(commit=False)
                book_req.student = request.user
                book_req.inventory_copy = copy
                book_req.ngo = copy.ngo
                book_req.status = RequestStatus.PENDING
                book_req.save()

                # Notify student
                Notification.objects.create(
                    user=request.user,
                    title="Book Request Submitted",
                    message=f"Your request for '{copy.book_title}' has been sent to {copy.ngo.name}. Their verification specialist will review your educational details.",
                    notification_type=NotificationType.INFO,
                    link_url=f"/student/requests/{book_req.id}/"
                )

                # Notify NGO review team
                for membership in copy.ngo.memberships.filter(is_active=True, can_review_requests=True):
                    Notification.objects.create(
                        user=membership.user,
                        title=f"New Book Request: {copy.book_title}",
                        message=f"Student {request.user.full_name} ({student_profile.institution_name}) requested '{copy.book_title}'.",
                        notification_type=NotificationType.INFO,
                        link_url=f"/ngo/requests/{book_req.id}/review/"
                    )

                log_audit(
                    request,
                    action="BOOK_REQUEST_SUBMIT",
                    entity=book_req,
                    organization=copy.ngo,
                    details={"book_title": copy.book_title, "sku": copy.tracking_code}
                )

                messages.success(request, f"Your request for '{copy.book_title}' has been submitted to {copy.ngo.name}!")
                return redirect('requests:student_requests_list')
    else:
        form = BookRequestCreateForm(initial=initial_data)

    return render(request, 'requests/request_create.html', {
        'form': form,
        'copy': copy,
        'student_profile': student_profile,
    })


@login_required
@require_role(UserRole.STUDENT)
def student_requests_list(request):
    """Student tracks all their book requests and delivery statuses."""
    status_filter = request.GET.get('status', '').strip()
    requests_qs = BookRequest.objects.filter(
        student=request.user
    ).select_related('inventory_copy', 'ngo', 'allocation__delivery_job').order_by('-created_at')

    if status_filter:
        requests_qs = requests_qs.filter(status=status_filter)

    paginator = Paginator(requests_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'requests/student_requests_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'RequestStatus': RequestStatus,
    })


@login_required
def student_request_detail(request, request_id):
    """Detailed tracker and delivery timeline for a book request."""
    book_request = get_object_or_404(
        BookRequest.objects.select_related('student__student_profile', 'inventory_copy__ngo', 'allocation__delivery_job'),
        id=request_id
    )

    # Access control
    if not request.user.is_platform_admin and request.user != book_request.student:
        if not (request.user.is_ngo_staff and request.user.ngo_memberships.filter(ngo=book_request.ngo, is_active=True).exists()):
            messages.error(request, "Unauthorized access.")
            return redirect('dashboard:dispatch')

    delivery_job = None
    if hasattr(book_request, 'allocation') and hasattr(book_request.allocation, 'delivery_job'):
        delivery_job = book_request.allocation.delivery_job

    receipt_form = StudentConfirmReceiptForm()

    return render(request, 'requests/request_detail.html', {
        'book_request': book_request,
        'delivery_job': delivery_job,
        'receipt_form': receipt_form,
        'is_student_viewer': (request.user == book_request.student),
    })


@login_required
@require_role(UserRole.STUDENT)
def student_confirm_receipt(request, delivery_id):
    """
    Student confirms they have physically received the allocated book.
    Closes the entire donation-to-delivery lifecycle!
    """
    delivery = get_object_or_404(
        DeliveryJob.objects.select_related('allocation__book_request__inventory_copy', 'ngo'),
        id=delivery_id,
        recipient_student=request.user
    )

    if request.method == 'POST':
        form = StudentConfirmReceiptForm(request.POST)
        feedback = ""
        if form.is_valid():
            feedback = form.cleaned_data.get('student_feedback', '')

        with transaction.atomic():
            now = timezone.now()
            delivery.student_confirmed = True
            delivery.student_confirmed_at = now
            delivery.status = DeliveryStatus.DELIVERED
            delivery.delivered_at = now
            delivery.student_feedback = feedback
            delivery.save()

            allocation = delivery.allocation
            allocation.status = AllocationStatus.FULFILLED
            allocation.save()

            book_req = allocation.book_request
            book_req.status = RequestStatus.COMPLETED
            book_req.save()

            copy = allocation.inventory_copy
            copy.status = InventoryStatus.DELIVERED
            copy.save()

            # If tied to donor listing, notify original book donor of fulfilled mission!
            if copy.donation_listing:
                Notification.objects.create(
                    user=copy.donation_listing.donor,
                    title="Your Donated Book Reached a Student!",
                    message=f"Student {request.user.first_name} has confirmed safe receipt of your donated book '{copy.book_title}'. Thank you for bridging educational opportunity!",
                    notification_type=NotificationType.SUCCESS,
                    link_url=f"/donations/{copy.donation_listing.id}/"
                )

            # Notify NGO team
            for m in delivery.ngo.memberships.filter(is_active=True):
                Notification.objects.create(
                    user=m.user,
                    title=f"Delivery Confirmed: {copy.book_title}",
                    message=f"Student {request.user.full_name} confirmed receipt of [{copy.tracking_code}].",
                    notification_type=NotificationType.SUCCESS
                )

            log_audit(
                request,
                action="STUDENT_CONFIRM_RECEIPT",
                entity=delivery,
                organization=delivery.ngo,
                details={"feedback": feedback, "book_title": copy.book_title}
            )

            messages.success(request, f"Thank you for confirming receipt of '{copy.book_title}'! Happy studying!")

    return redirect('requests:student_request_detail', request_id=delivery.allocation.book_request.id)


# ==============================================================================
# NGO STAFF VERIFICATION & ALLOCATION WORKFLOW (Strict Organization Isolation)
# ==============================================================================

@require_ngo_staff('can_verify_students')
def ngo_students_verification_queue(request):
    """Queue of student profiles requiring document check and eligibility verification."""
    status_filter = request.GET.get('status', 'PENDING')
    search_query = request.GET.get('q', '').strip()

    profiles_qs = StudentProfile.objects.select_related('user').prefetch_related('documents')

    if status_filter != 'ALL':
        profiles_qs = profiles_qs.filter(verification_status=status_filter)

    if search_query:
        profiles_qs = profiles_qs.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(institution_name__icontains=search_query) |
            Q(student_id_number__icontains=search_query) |
            Q(course_of_study__icontains=search_query)
        )

    paginator = Paginator(profiles_qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'requests/ngo_students_verification_queue.html', {
        'ngo': request.ngo,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
    })


@require_ngo_staff('can_verify_students')
def ngo_verify_student(request, profile_id):
    """Review student's institutional documents and grant/deny verified status."""
    student_profile = get_object_or_404(
        StudentProfile.objects.select_related('user').prefetch_related('documents'),
        id=profile_id
    )

    verification_record, _ = StudentVerification.objects.get_or_create(
        student_profile=student_profile,
        ngo=request.ngo
    )

    if request.method == 'POST':
        form = StudentVerificationForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data['status']
            comments = form.cleaned_data['comments']

            with transaction.atomic():
                verification_record.status = decision
                verification_record.verified_by = request.user
                verification_record.comments = comments
                verification_record.verified_at = timezone.now()
                verification_record.save()

                if decision == 'APPROVED':
                    student_profile.verification_status = StudentVerificationStatus.VERIFIED
                    student_profile.verified_at = timezone.now()
                    notif_msg = f"{request.ngo.name} has verified your student profile and eligibility! Your book requests can now be approved and allocated."
                    notif_type = NotificationType.SUCCESS
                elif decision == 'REJECTED':
                    student_profile.verification_status = StudentVerificationStatus.REJECTED
                    notif_msg = f"Your student verification was not approved by {request.ngo.name}. Reason: {comments}"
                    notif_type = NotificationType.DANGER
                else:  # CORRECTION_REQUESTED
                    student_profile.verification_status = StudentVerificationStatus.NEEDS_UPDATE
                    notif_msg = f"{request.ngo.name} requested updated enrollment/ID documents. Note: {comments}"
                    notif_type = NotificationType.WARNING

                student_profile.save()

                Notification.objects.create(
                    user=student_profile.user,
                    title="Student Verification Update",
                    message=notif_msg,
                    notification_type=notif_type,
                    link_url="/accounts/profile/"
                )

                log_audit(
                    request,
                    action=f"STUDENT_VERIFICATION_{decision}",
                    entity=student_profile.user,
                    organization=request.ngo,
                    details={"decision": decision, "notes": comments}
                )

                messages.success(request, f"Student verification recorded as {decision}.")
                return redirect('requests:ngo_students_verification_queue')
    else:
        form = StudentVerificationForm(initial={
            'status': verification_record.status if verification_record.status != 'PENDING' else 'APPROVED',
            'comments': verification_record.comments,
        })

    return render(request, 'requests/ngo_verify_student.html', {
        'student_profile': student_profile,
        'verification_record': verification_record,
        'form': form,
        'ngo': request.ngo,
    })


@require_ngo_staff('can_review_requests')
def ngo_requests_queue(request):
    """
    NGO staff book request queue for books managed by this NGO.
    Strict organization isolation: only displays requests for this NGO.
    """
    tab = request.GET.get('tab', 'pending')
    search_query = request.GET.get('q', '').strip()

    qs = BookRequest.objects.filter(ngo=request.ngo).select_related(
        'student__student_profile', 'inventory_copy'
    )

    if tab == 'pending':
        qs = qs.filter(status__in=[RequestStatus.PENDING, RequestStatus.UNDER_REVIEW])
    elif tab == 'approved':
        qs = qs.filter(status__in=[RequestStatus.APPROVED, RequestStatus.ALLOCATED])
    elif tab == 'waitlisted':
        qs = qs.filter(status=RequestStatus.WAITLISTED)
    elif tab == 'completed':
        qs = qs.filter(status=RequestStatus.COMPLETED)
    elif tab == 'rejected':
        qs = qs.filter(status__in=[RequestStatus.REJECTED, RequestStatus.CANCELLED])

    if search_query:
        qs = qs.filter(
            Q(inventory_copy__book_title__icontains=search_query) |
            Q(student__username__icontains=search_query) |
            Q(student__first_name__icontains=search_query) |
            Q(delivery_city__icontains=search_query)
        )

    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    counts = {
        'pending': BookRequest.objects.filter(ngo=request.ngo, status__in=[RequestStatus.PENDING, RequestStatus.UNDER_REVIEW]).count(),
        'approved': BookRequest.objects.filter(ngo=request.ngo, status__in=[RequestStatus.APPROVED, RequestStatus.ALLOCATED]).count(),
        'waitlisted': BookRequest.objects.filter(ngo=request.ngo, status=RequestStatus.WAITLISTED).count(),
        'completed': BookRequest.objects.filter(ngo=request.ngo, status=RequestStatus.COMPLETED).count(),
        'all': BookRequest.objects.filter(ngo=request.ngo).count(),
    }

    return render(request, 'requests/ngo_requests_queue.html', {
        'ngo': request.ngo,
        'page_obj': page_obj,
        'tab': tab,
        'search_query': search_query,
        'counts': counts,
    })


@require_ngo_staff('can_review_requests')
def ngo_request_review_detail(request, request_id):
    """Inspect student educational relevance and execute approval, waitlist, or rejection."""
    book_req = get_object_or_404(
        BookRequest.objects.select_related('student__student_profile', 'inventory_copy', 'ngo'),
        id=request_id,
        ngo=request.ngo
    )
    student_profile = book_req.student.student_profile
    documents = student_profile.documents.all()

    return render(request, 'requests/ngo_request_review_detail.html', {
        'book_req': book_req,
        'student_profile': student_profile,
        'documents': documents,
        'ngo': request.ngo,
    })


@require_ngo_staff('can_review_requests')
def ngo_execute_allocation(request, request_id):
    """
    TRANSACTIONAL ALLOCATION LOGIC WITH ROW LOCKING:
    - Atomically locks the InventoryCopy with select_for_update()
    - Verifies copy is strictly AVAILABLE
    - Binds copy to student request
    - Generates Allocation and DeliveryJob
    - Prevents double-allocation even under high concurrent traffic!
    """
    if request.method != 'POST':
        return redirect('requests:ngo_requests_queue')

    book_req = get_object_or_404(BookRequest, id=request_id, ngo=request.ngo)
    copy_id = book_req.inventory_copy_id

    with transaction.atomic():
        # Concurrency safety: acquire row-level lock on InventoryCopy
        locked_copy = InventoryCopy.objects.select_for_update().get(id=copy_id)

        if locked_copy.status != InventoryStatus.AVAILABLE:
            messages.error(
                request,
                f"Concurrent Conflict: Book copy [{locked_copy.tracking_code}] is currently {locked_copy.get_status_display()} and cannot be allocated."
            )
            book_req.status = RequestStatus.WAITLISTED
            book_req.save()
            return redirect('requests:ngo_requests_queue')

        # Verify student eligibility
        student_profile = book_req.student.student_profile
        if not student_profile.is_verified:
            # Auto-mark verified if reviewer approves
            student_profile.verification_status = StudentVerificationStatus.VERIFIED
            student_profile.verified_at = timezone.now()
            student_profile.save()

        # Update InventoryCopy status to ALLOCATED
        locked_copy.status = InventoryStatus.ALLOCATED
        locked_copy.save()

        # Update BookRequest status
        book_req.status = RequestStatus.ALLOCATED
        book_req.save()

        # Create formal Allocation record
        allocation = Allocation.objects.create(
            book_request=book_req,
            inventory_copy=locked_copy,
            ngo=request.ngo,
            allocated_by=request.user,
            status=AllocationStatus.ACTIVE,
            notes=f"Allocated by {request.user.full_name} from {locked_copy.location_shelf}"
        )

        # Generate unique tracking number for shipment
        unique_trk = f"DEL-{uuid.uuid4().hex[:8].upper()}"

        # Create associated DeliveryJob
        delivery_job = DeliveryJob.objects.create(
            allocation=allocation,
            ngo=request.ngo,
            recipient_student=book_req.student,
            tracking_number=unique_trk,
            courier_name="NGO Dispatch Team",
            delivery_address=f"{book_req.delivery_address}, {book_req.delivery_city}, {book_req.delivery_state} - {book_req.delivery_postal_code}",
            status=DeliveryStatus.PREPARING
        )

        # Record review justification
        RequestReview.objects.create(
            book_request=book_req,
            reviewer=request.user,
            decision='APPROVED',
            justification="Educational need verified and book allocated from shelf inventory."
        )

        # Notify student
        Notification.objects.create(
            user=book_req.student,
            title="Book Request Approved & Allocated!",
            message=f"Congratulations! Your request for '{locked_copy.book_title}' has been approved and allocated. Tracking ID: {unique_trk}. Preparing for dispatch.",
            notification_type=NotificationType.SUCCESS,
            link_url=f"/student/requests/{book_req.id}/"
        )

        log_audit(
            request,
            action="ALLOCATION_SUCCESSFUL",
            entity=allocation,
            organization=request.ngo,
            details={
                "sku": locked_copy.tracking_code,
                "student": book_req.student.username,
                "tracking_number": unique_trk
            }
        )

        messages.success(
            request,
            f"Book '{locked_copy.book_title}' [{locked_copy.tracking_code}] successfully allocated to {book_req.student.full_name}! Delivery job created."
        )

    return redirect('requests:ngo_deliveries_list')


@require_ngo_staff('can_review_requests')
def ngo_reject_request(request, request_id):
    book_req = get_object_or_404(BookRequest, id=request_id, ngo=request.ngo)
    reason = request.POST.get('rejection_reason', 'Educational relevance criteria not met.').strip()

    with transaction.atomic():
        book_req.status = RequestStatus.REJECTED
        book_req.rejection_reason = reason
        book_req.save()

        RequestReview.objects.create(
            book_request=book_req,
            reviewer=request.user,
            decision='REJECTED',
            justification=reason
        )

        Notification.objects.create(
            user=book_req.student,
            title="Book Request Status Update",
            message=f"Your request for '{book_req.inventory_copy.book_title}' could not be approved. Reason: {reason}",
            notification_type=NotificationType.DANGER,
            link_url=f"/student/requests/{book_req.id}/"
        )

        log_audit(request, action="REQUEST_REJECTED", entity=book_req, organization=request.ngo, details={"reason": reason})
        messages.info(request, f"Request for '{book_req.inventory_copy.book_title}' was rejected.")

    return redirect('requests:ngo_requests_queue')


@require_ngo_staff('can_review_requests')
def ngo_waitlist_request(request, request_id):
    book_req = get_object_or_404(BookRequest, id=request_id, ngo=request.ngo)
    book_req.status = RequestStatus.WAITLISTED
    book_req.save()

    Notification.objects.create(
        user=book_req.student,
        title="Placed on Book Waitlist",
        message=f"You have been placed on the priority waitlist for '{book_req.inventory_copy.book_title}'. We will allocate as soon as copies are ready.",
        notification_type=NotificationType.WARNING,
        link_url=f"/student/requests/{book_req.id}/"
    )

    log_audit(request, action="REQUEST_WAITLISTED", entity=book_req, organization=request.ngo)
    messages.info(request, f"Request waitlisted.")
    return redirect('requests:ngo_requests_queue')


@require_ngo_staff('can_manage_deliveries')
def ngo_deliveries_list(request):
    """Manage packaging, courier dispatch, tracking numbers, and delivery states."""
    status_filter = request.GET.get('status', '').strip()
    search_query = request.GET.get('q', '').strip()

    qs = DeliveryJob.objects.filter(ngo=request.ngo).select_related(
        'allocation__inventory_copy', 'recipient_student'
    ).order_by('-created_at')

    if status_filter:
        qs = qs.filter(status=status_filter)

    if search_query:
        qs = qs.filter(
            Q(tracking_number__icontains=search_query) |
            Q(recipient_student__username__icontains=search_query) |
            Q(recipient_student__first_name__icontains=search_query) |
            Q(courier_name__icontains=search_query) |
            Q(allocation__inventory_copy__book_title__icontains=search_query)
        )

    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'requests/ngo_deliveries_list.html', {
        'ngo': request.ngo,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'DeliveryStatus': DeliveryStatus,
    })


@require_ngo_staff('can_manage_deliveries')
def ngo_delivery_dispatch(request, delivery_id):
    """Update shipment tracking number, courier partner, and mark DISPATCHED."""
    delivery = get_object_or_404(DeliveryJob, id=delivery_id, ngo=request.ngo)

    if request.method == 'POST':
        form = DeliveryDispatchForm(request.POST, instance=delivery)
        if form.is_valid():
            with transaction.atomic():
                delivery = form.save(commit=False)
                delivery.status = DeliveryStatus.DISPATCHED
                delivery.dispatched_at = timezone.now()
                delivery.save()

                Notification.objects.create(
                    user=delivery.recipient_student,
                    title="Book Dispatched!",
                    message=f"Your allocated book has been dispatched via {delivery.courier_name}. Tracking Number: {delivery.tracking_number}.",
                    notification_type=NotificationType.INFO,
                    link_url=f"/student/requests/{delivery.allocation.book_request.id}/"
                )

                log_audit(
                    request,
                    action="DELIVERY_DISPATCHED",
                    entity=delivery,
                    organization=request.ngo,
                    details={"courier": delivery.courier_name, "tracking": delivery.tracking_number}
                )

                messages.success(request, f"Shipment dispatched with tracking {delivery.tracking_number}!")
                return redirect('requests:ngo_deliveries_list')
    else:
        form = DeliveryDispatchForm(instance=delivery)

    return render(request, 'requests/ngo_delivery_dispatch.html', {
        'delivery': delivery,
        'form': form,
        'ngo': request.ngo,
    })


@require_ngo_staff('can_manage_deliveries')
def ngo_delivery_status_update(request, delivery_id):
    """Mark shipment as OUT_FOR_DELIVERY, DELIVERED, or FAILED."""
    delivery = get_object_or_404(DeliveryJob, id=delivery_id, ngo=request.ngo)
    new_status = request.POST.get('status')
    reason = request.POST.get('reason', '').strip()

    if new_status in [DeliveryStatus.OUT_FOR_DELIVERY, DeliveryStatus.DELIVERED, DeliveryStatus.FAILED]:
        with transaction.atomic():
            delivery.status = new_status
            if new_status == DeliveryStatus.DELIVERED:
                delivery.delivered_at = timezone.now()
            elif new_status == DeliveryStatus.FAILED:
                delivery.failure_reason = reason or "Address incorrect or student unreachable."

            delivery.save()

            notif_msg = f"Delivery status update for your book: {delivery.get_status_display()}."
            if reason:
                notif_msg += f" Note: {reason}"

            Notification.objects.create(
                user=delivery.recipient_student,
                title="Delivery Status Update",
                message=notif_msg,
                notification_type=NotificationType.INFO,
                link_url=f"/student/requests/{delivery.allocation.book_request.id}/"
            )

            log_audit(
                request,
                action=f"DELIVERY_STATUS_{new_status}",
                entity=delivery,
                organization=request.ngo,
                details={"status": new_status, "reason": reason}
            )

            messages.info(request, f"Delivery status updated to {new_status}.")

    return redirect('requests:ngo_deliveries_list')
