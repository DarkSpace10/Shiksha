import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class DocumentType(models.TextChoices):
    STUDENT_ID = 'STUDENT_ID', _('Institutional Student ID Card')
    ENROLLMENT_LETTER = 'ENROLLMENT_LETTER', _('Bonafide / Enrollment Certificate')
    FEE_RECEIPT = 'FEE_RECEIPT', _('Tuition Fee Receipt / Concession Proof')
    INCOME_CERTIFICATE = 'INCOME_CERTIFICATE', _('Income / Need Assessment Certificate')
    TRANSCRIPT = 'TRANSCRIPT', _('Recent Marksheet / Grade Transcript')
    OTHER = 'OTHER', _('Other Supporting Document')


class VerificationDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student_profile = models.ForeignKey(
        'accounts.StudentProfile',
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        default=DocumentType.STUDENT_ID
    )
    document_file = models.FileField(upload_to='student_docs/%Y/%m/')
    document_title = models.CharField(max_length=200)
    is_verified = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bb_verification_documents'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.get_document_type_display()} for {self.student_profile.user.username}"


class VerificationDecision(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    APPROVED = 'APPROVED', _('Verified Eligible')
    REJECTED = 'REJECTED', _('Rejected')
    CORRECTION_REQUESTED = 'CORRECTION_REQUESTED', _('More Information / Documents Needed')


class StudentVerification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student_profile = models.ForeignKey(
        'accounts.StudentProfile',
        on_delete=models.CASCADE,
        related_name='verifications'
    )
    ngo = models.ForeignKey(
        'ngos.NGO',
        on_delete=models.CASCADE,
        related_name='student_verifications'
    )
    status = models.CharField(
        max_length=25,
        choices=VerificationDecision.choices,
        default=VerificationDecision.PENDING
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conducted_student_verifications'
    )
    comments = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bb_student_verifications'
        unique_together = ('student_profile', 'ngo')
        ordering = ['-created_at']

    def __str__(self):
        return f"Verification of {self.student_profile.user.username} by {self.ngo.name} ({self.get_status_display()})"


class RequestStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending NGO Review')
    UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review & Eligibility Check')
    APPROVED = 'APPROVED', _('Approved (Awaiting Allocation & Dispatch)')
    WAITLISTED = 'WAITLISTED', _('Waitlisted (Copy Currently Reserved)')
    ALLOCATED = 'ALLOCATED', _('Book Allocated & Dispatched')
    REJECTED = 'REJECTED', _('Request Rejected')
    CANCELLED = 'CANCELLED', _('Cancelled by Student')
    COMPLETED = 'COMPLETED', _('Delivered & Confirmed Received')


class BookRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='book_requests'
    )
    inventory_copy = models.ForeignKey(
        'inventory.InventoryCopy',
        on_delete=models.CASCADE,
        related_name='requests'
    )
    ngo = models.ForeignKey(
        'ngos.NGO',
        on_delete=models.CASCADE,
        related_name='book_requests'
    )
    educational_purpose = models.TextField(
        help_text=_('Describe how this book supports your current syllabus, exams, or studies')
    )
    urgent_need = models.BooleanField(
        default=False,
        help_text=_('Check if this request is urgent for upcoming exams')
    )
    urgency_reason = models.TextField(blank=True)
    delivery_address = models.TextField()
    delivery_city = models.CharField(max_length=100)
    delivery_state = models.CharField(max_length=100)
    delivery_postal_code = models.CharField(max_length=20)
    contact_phone = models.CharField(max_length=20)
    status = models.CharField(
        max_length=25,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING
    )
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bb_book_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"Request for {self.inventory_copy.book_title} by {self.student.username} ({self.get_status_display()})"


class RequestReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book_request = models.ForeignKey(
        BookRequest,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='request_reviews'
    )
    decision = models.CharField(
        max_length=25,
        choices=[
            ('APPROVED', _('Approve Allocation')),
            ('REJECTED', _('Reject Request')),
            ('WAITLISTED', _('Place on Waitlist')),
            ('CORRECTION_REQUESTED', _('Request Student Documents'))
        ]
    )
    justification = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bb_request_reviews'
        ordering = ['-created_at']

    def __str__(self):
        return f"Review ({self.decision}) for {self.book_request.inventory_copy.book_title}"


class AllocationStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', _('Active Allocation')
    CANCELLED = 'CANCELLED', _('Cancelled')
    FULFILLED = 'FULFILLED', _('Fulfilled & Received')


class Allocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book_request = models.OneToOneField(
        BookRequest,
        on_delete=models.CASCADE,
        related_name='allocation'
    )
    inventory_copy = models.ForeignKey(
        'inventory.InventoryCopy',
        on_delete=models.CASCADE,
        related_name='allocations'
    )
    ngo = models.ForeignKey(
        'ngos.NGO',
        on_delete=models.CASCADE,
        related_name='allocations'
    )
    allocated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conducted_allocations'
    )
    allocated_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=AllocationStatus.choices,
        default=AllocationStatus.ACTIVE
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'bb_allocations'
        ordering = ['-allocated_at']

    def __str__(self):
        return f"Allocation: [{self.inventory_copy.tracking_code}] to {self.book_request.student.username}"


class DeliveryStatus(models.TextChoices):
    PREPARING = 'PREPARING', _('Preparing Shipment / Packaging')
    DISPATCHED = 'DISPATCHED', _('Dispatched with Courier / Volunteer')
    OUT_FOR_DELIVERY = 'OUT_FOR_DELIVERY', _('Out for Delivery')
    DELIVERED = 'DELIVERED', _('Delivered to Address')
    FAILED = 'FAILED', _('Delivery Attempt Failed')


class DeliveryJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    allocation = models.OneToOneField(
        Allocation,
        on_delete=models.CASCADE,
        related_name='delivery_job'
    )
    ngo = models.ForeignKey(
        'ngos.NGO',
        on_delete=models.CASCADE,
        related_name='delivery_jobs'
    )
    recipient_student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='deliveries'
    )
    tracking_number = models.CharField(
        max_length=100,
        unique=True,
        help_text=_('Courier tracking ID or internal dispatch tracking code')
    )
    courier_name = models.CharField(
        max_length=150,
        default='NGO Direct Delivery',
        help_text=_('Courier / Delivery Partner / Volunteer name')
    )
    dispatch_notes = models.TextField(blank=True)
    delivery_address = models.TextField()
    status = models.CharField(
        max_length=25,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PREPARING
    )
    dispatched_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    student_confirmed = models.BooleanField(
        default=False,
        help_text=_('Student verified receipt of book')
    )
    student_confirmed_at = models.DateTimeField(null=True, blank=True)
    student_feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bb_delivery_jobs'
        ordering = ['-created_at']

    def __str__(self):
        return f"Delivery [{self.tracking_number}] to {self.recipient_student.username} ({self.get_status_display()})"
