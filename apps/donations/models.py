import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import AcademicLevel


class BookCategory(models.TextChoices):
    TEXTBOOK = 'TEXTBOOK', _('School / College Textbook')
    REFERENCE = 'REFERENCE', _('Reference Book / Encyclopedia')
    EXAM_PREP = 'EXAM_PREP', _('Competitive Exam Prep & Guides')
    SCIENCE_TECH = 'SCIENCE_TECH', _('Science, Engineering & Tech')
    MEDICINE_HEALTH = 'MEDICINE_HEALTH', _('Medicine & Healthcare')
    COMMERCE_BUSINESS = 'COMMERCE_BUSINESS', _('Commerce & Economics')
    HUMANITIES_ARTS = 'HUMANITIES_ARTS', _('Humanities, History & Literature')
    CHILDREN_STORY = 'CHILDREN_STORY', _('Children Learning & Storybooks')
    GENERAL_NONFICTION = 'GENERAL_NONFICTION', _('General Knowledge & Self-Help')
    OTHER = 'OTHER', _('Other Educational Material')


class ConditionGrade(models.TextChoices):
    LIKE_NEW = 'LIKE_NEW', _('Like New (Pristine, crisp, no marks)')
    VERY_GOOD = 'VERY_GOOD', _('Very Good (Minimal wear, all pages clean)')
    GOOD = 'GOOD', _('Good (Readable, minor highlighting, intact spine)')
    ACCEPTABLE = 'ACCEPTABLE', _('Acceptable (Noticeable wear, fully intact and readable)')


class DonationStatus(models.TextChoices):
    SUBMITTED = 'SUBMITTED', _('Submitted (Awaiting NGO Review)')
    UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review by NGO')
    CORRECTION_REQUESTED = 'CORRECTION_REQUESTED', _('Corrections Requested')
    APPROVED = 'APPROVED', _('Approved (Awaiting Pickup Schedule)')
    PICKUP_SCHEDULED = 'PICKUP_SCHEDULED', _('Pickup Scheduled')
    COLLECTED = 'COLLECTED', _('Collected (At NGO Facility)')
    FAILED_PICKUP = 'FAILED_PICKUP', _('Pickup Failed / Rescheduling Needed')
    INSPECTION_PASSED = 'INSPECTION_PASSED', _('Physical Inspection Passed')
    INSPECTION_FAILED = 'INSPECTION_FAILED', _('Physical Inspection Failed')
    INVENTORIED = 'INVENTORIED', _('Inventoried & Published')
    REJECTED = 'REJECTED', _('Rejected')
    CANCELLED = 'CANCELLED', _('Cancelled by Donor')


class DonationListing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='donations'
    )
    ngo = models.ForeignKey(
        'ngos.NGO',
        on_delete=models.CASCADE,
        related_name='received_donations'
    )
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=30, blank=True)
    publisher = models.CharField(max_length=255, blank=True)
    publication_year = models.PositiveIntegerField(blank=True, null=True)
    category = models.CharField(
        max_length=30,
        choices=BookCategory.choices,
        default=BookCategory.TEXTBOOK
    )
    academic_level = models.CharField(
        max_length=30,
        choices=AcademicLevel.choices,
        default=AcademicLevel.UNDERGRADUATE
    )
    subject = models.CharField(max_length=150, blank=True)
    edition = models.CharField(max_length=50, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    declared_condition = models.CharField(
        max_length=20,
        choices=ConditionGrade.choices,
        default=ConditionGrade.VERY_GOOD
    )
    donor_condition_description = models.TextField(
        help_text=_('Honest description of book condition, markings, missing pages if any')
    )
    # Pickup details
    pickup_address = models.TextField()
    pickup_city = models.CharField(max_length=100)
    pickup_state = models.CharField(max_length=100)
    pickup_postal_code = models.CharField(max_length=20)
    donor_contact_phone = models.CharField(max_length=20)
    preferred_pickup_time = models.CharField(max_length=100, blank=True)
    # Status and workflow
    status = models.CharField(
        max_length=25,
        choices=DonationStatus.choices,
        default=DonationStatus.SUBMITTED
    )
    donor_notes = models.TextField(blank=True)
    correction_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    # Physical inspection details
    inspected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inspected_donations'
    )
    inspected_at = models.DateTimeField(null=True, blank=True)
    verified_condition = models.CharField(
        max_length=20,
        choices=ConditionGrade.choices,
        blank=True,
        null=True
    )
    inspection_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bb_donation_listings'
        ordering = ['-created_at']

    @property
    def primary_image(self):
        primary = self.images.filter(is_primary=True).first()
        if not primary:
            primary = self.images.first()
        return primary

    def __str__(self):
        return f"{self.title} by {self.author} (Donor: {self.donor.username} -> {self.ngo.name})"


class DonationImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donation = models.ForeignKey(
        DonationListing,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='donation_books/%Y/%m/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bb_donation_images'
        ordering = ['-is_primary', 'uploaded_at']

    def __str__(self):
        return f"Image for {self.donation.title}"


class ReviewDecision(models.TextChoices):
    APPROVED = 'APPROVED', _('Approve for Pickup')
    REJECTED = 'REJECTED', _('Reject Donation')
    CORRECTION_REQUESTED = 'CORRECTION_REQUESTED', _('Request Information / Photo Correction')


class DonationReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donation = models.ForeignKey(
        DonationListing,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donation_reviews'
    )
    decision = models.CharField(
        max_length=25,
        choices=ReviewDecision.choices
    )
    comments = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bb_donation_reviews'
        ordering = ['-created_at']

    def __str__(self):
        return f"Review ({self.get_decision_display()}) for {self.donation.title}"


class PickupStatus(models.TextChoices):
    SCHEDULED = 'SCHEDULED', _('Pickup Scheduled')
    RESCHEDULED = 'RESCHEDULED', _('Rescheduled')
    IN_PROGRESS = 'IN_PROGRESS', _('Agent Dispatched / In Progress')
    COMPLETED = 'COMPLETED', _('Collected Successfully')
    FAILED = 'FAILED', _('Attempt Failed')
    CANCELLED = 'CANCELLED', _('Cancelled')


class TimeSlot(models.TextChoices):
    MORNING = 'MORNING', _('Morning (09:00 AM - 12:00 PM)')
    AFTERNOON = 'AFTERNOON', _('Afternoon (12:00 PM - 04:00 PM)')
    EVENING = 'EVENING', _('Evening (04:00 PM - 07:00 PM)')


class PickupJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donation = models.OneToOneField(
        DonationListing,
        on_delete=models.CASCADE,
        related_name='pickup_job'
    )
    ngo = models.ForeignKey(
        'ngos.NGO',
        on_delete=models.CASCADE,
        related_name='pickup_jobs'
    )
    scheduled_date = models.DateField()
    time_slot = models.CharField(
        max_length=20,
        choices=TimeSlot.choices,
        default=TimeSlot.MORNING
    )
    assigned_agent_name = models.CharField(max_length=150, blank=True)
    assigned_agent_phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=20,
        choices=PickupStatus.choices,
        default=PickupStatus.SCHEDULED
    )
    notes = models.TextField(blank=True)
    failure_reason = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bb_pickup_jobs'
        ordering = ['-scheduled_date', '-created_at']

    def __str__(self):
        return f"Pickup for {self.donation.title} on {self.scheduled_date} ({self.get_status_display()})"
