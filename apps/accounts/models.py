import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    DONOR = 'DONOR', _('Book Donor')
    STUDENT = 'STUDENT', _('Student / Learner')
    NGO_STAFF = 'NGO_STAFF', _('NGO Staff / Volunteer')
    PLATFORM_ADMIN = 'PLATFORM_ADMIN', _('Platform Administrator')


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.DONOR,
        help_text=_('Platform access role')
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_verified = models.BooleanField(
        default=False,
        help_text=_('Whether user email/identity has been verified')
    )
    is_suspended = models.BooleanField(
        default=False,
        help_text=_('Platform-wide suspension state')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bb_users'
        ordering = ['-created_at']

    @property
    def is_donor(self):
        return self.role == UserRole.DONOR

    @property
    def is_student(self):
        return self.role == UserRole.STUDENT

    @property
    def is_ngo_staff(self):
        return self.role == UserRole.NGO_STAFF

    @property
    def is_platform_admin(self):
        return self.role == UserRole.PLATFORM_ADMIN or self.is_superuser

    @property
    def full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else self.username

    def get_dashboard_url(self):
        if self.is_platform_admin:
            return '/admin-panel/'
        elif self.is_ngo_staff:
            return '/ngo/dashboard/'
        elif self.is_student:
            return '/student/dashboard/'
        return '/donor/dashboard/'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class DonorProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='donor_profile')
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    total_donations_count = models.PositiveIntegerField(default=0)
    preferred_pickup_instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bb_donor_profiles'

    def __str__(self):
        return f"Donor Profile: {self.user.username}"


class AcademicLevel(models.TextChoices):
    PRIMARY = 'PRIMARY', _('Primary School (Grade 1-5)')
    MIDDLE = 'MIDDLE', _('Middle School (Grade 6-8)')
    HIGH_SCHOOL = 'HIGH_SCHOOL', _('High School (Grade 9-10)')
    SENIOR_SECONDARY = 'SENIOR_SECONDARY', _('Senior Secondary / Higher Secondary (Grade 11-12)')
    UNDERGRADUATE = 'UNDERGRADUATE', _('Undergraduate / College')
    POSTGRADUATE = 'POSTGRADUATE', _('Postgraduate / Masters')
    VOCATIONAL = 'VOCATIONAL', _('Vocational / Competitive Exam Prep')
    OTHER = 'OTHER', _('Other Learning Pursuit')


class StudentVerificationStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending Verification')
    VERIFIED = 'VERIFIED', _('Verified')
    REJECTED = 'REJECTED', _('Verification Rejected')
    NEEDS_UPDATE = 'NEEDS_UPDATE', _('Additional Documents Needed')


class StudentProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    institution_name = models.CharField(max_length=255)
    student_id_number = models.CharField(max_length=100)
    course_of_study = models.CharField(max_length=255)
    academic_level = models.CharField(
        max_length=30,
        choices=AcademicLevel.choices,
        default=AcademicLevel.UNDERGRADUATE
    )
    graduation_year = models.PositiveIntegerField(blank=True, null=True)
    financial_need_statement = models.TextField(
        help_text=_('Explanation of genuine need for free educational book resources')
    )
    delivery_address = models.TextField(blank=True, help_text=_('Default physical address for book deliveries'))
    delivery_city = models.CharField(max_length=100, blank=True)
    delivery_state = models.CharField(max_length=100, blank=True)
    delivery_postal_code = models.CharField(max_length=20, blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=StudentVerificationStatus.choices,
        default=StudentVerificationStatus.PENDING
    )
    verified_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bb_student_profiles'

    @property
    def is_verified(self):
        return self.verification_status == StudentVerificationStatus.VERIFIED

    def __str__(self):
        return f"Student: {self.user.username} ({self.institution_name})"


class NotificationType(models.TextChoices):
    INFO = 'INFO', _('Information')
    SUCCESS = 'SUCCESS', _('Success')
    WARNING = 'WARNING', _('Warning')
    DANGER = 'DANGER', _('Alert / Urgent')


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=10,
        choices=NotificationType.choices,
        default=NotificationType.INFO
    )
    is_read = models.BooleanField(default=False)
    link_url = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bb_notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification to {self.user.username}: {self.title}"
