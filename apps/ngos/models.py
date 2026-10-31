import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class NGOStatus(models.TextChoices):
    PENDING_APPROVAL = 'PENDING', _('Pending Administrator Approval')
    APPROVED = 'APPROVED', _('Verified & Approved')
    REJECTED = 'REJECTED', _('Application Rejected')
    SUSPENDED = 'SUSPENDED', _('Temporarily Suspended')


class NGO(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    registration_number = models.CharField(
        max_length=100,
        unique=True,
        help_text=_('Government / Trust / Society Registration Number')
    )
    email = models.EmailField(help_text=_('Official NGO contact email'))
    phone = models.CharField(max_length=20)
    website = models.URLField(blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    description = models.TextField(help_text=_('About the organization and book distribution initiatives'))
    mission_statement = models.TextField(blank=True)
    logo = models.ImageField(upload_to='ngo_logos/', blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=NGOStatus.choices,
        default=NGOStatus.PENDING_APPROVAL
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_ngos'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bb_ngos'
        ordering = ['name']
        verbose_name = 'NGO'
        verbose_name_plural = 'NGOs'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            candidate = base_slug
            counter = 1
            while NGO.objects.filter(slug=candidate).exclude(id=self.id).exists():
                candidate = f"{base_slug}-{counter}"
                counter += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    @property
    def is_operational(self):
        return self.status == NGOStatus.APPROVED

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class NGOMemberRole(models.TextChoices):
    NGO_ADMIN = 'NGO_ADMIN', _('NGO Administrator / Director')
    COORDINATOR = 'COORDINATOR', _('Operations Coordinator')
    INSPECTOR = 'INSPECTOR', _('Quality & Inventory Inspector')
    VERIFIER = 'VERIFIER', _('Student Verification Specialist')


class NGOMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ngo_memberships'
    )
    ngo = models.ForeignKey(
        NGO,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    role = models.CharField(
        max_length=20,
        choices=NGOMemberRole.choices,
        default=NGOMemberRole.COORDINATOR
    )
    can_review_donations = models.BooleanField(default=True)
    can_schedule_pickups = models.BooleanField(default=True)
    can_inspect_books = models.BooleanField(default=True)
    can_manage_inventory = models.BooleanField(default=True)
    can_verify_students = models.BooleanField(default=True)
    can_review_requests = models.BooleanField(default=True)
    can_manage_deliveries = models.BooleanField(default=True)
    can_manage_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bb_ngo_memberships'
        unique_together = ('user', 'ngo')
        verbose_name = 'NGO Membership'
        verbose_name_plural = 'NGO Memberships'

    def save(self, *args, **kwargs):
        if self.role == NGOMemberRole.NGO_ADMIN:
            self.can_manage_staff = True
            self.can_review_donations = True
            self.can_schedule_pickups = True
            self.can_inspect_books = True
            self.can_manage_inventory = True
            self.can_verify_students = True
            self.can_review_requests = True
            self.can_manage_deliveries = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} @ {self.ngo.name} ({self.get_role_display()})"


class NGOServiceArea(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ngo = models.ForeignKey(
        NGO,
        on_delete=models.CASCADE,
        related_name='service_areas'
    )
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bb_ngo_service_areas'
        ordering = ['city', 'state']

    def __str__(self):
        return f"{self.ngo.name} covers {self.city}, {self.state} ({self.postal_code or 'All'})"
