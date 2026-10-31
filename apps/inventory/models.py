import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.donations.models import BookCategory, ConditionGrade
from apps.accounts.models import AcademicLevel


class InventoryStatus(models.TextChoices):
    AVAILABLE = 'AVAILABLE', _('Available for Allocation')
    RESERVED = 'RESERVED', _('Reserved for Student Request')
    ALLOCATED = 'ALLOCATED', _('Allocated (In Dispatch)')
    DELIVERED = 'DELIVERED', _('Delivered to Student')
    DAMAGED = 'DAMAGED', _('Damaged / Unusable')
    WITHDRAWN = 'WITHDRAWN', _('Withdrawn from Catalogue')


class InventoryCopy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ngo = models.ForeignKey(
        'ngos.NGO',
        on_delete=models.CASCADE,
        related_name='inventory_copies'
    )
    donation_listing = models.ForeignKey(
        'donations.DonationListing',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_copies'
    )
    tracking_code = models.CharField(
        max_length=64,
        unique=True,
        help_text=_('Unique inventory SKU/tracking code e.g. BB-NGO-2026-001')
    )
    book_title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=30, blank=True)
    publisher = models.CharField(max_length=255, blank=True)
    publication_year = models.PositiveIntegerField(blank=True, null=True)
    edition = models.CharField(max_length=50, blank=True)
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
    condition_grade = models.CharField(
        max_length=20,
        choices=ConditionGrade.choices,
        default=ConditionGrade.VERY_GOOD
    )
    location_shelf = models.CharField(
        max_length=100,
        help_text=_('Physical storage location in NGO facility e.g. Shelf A-3, Box 12')
    )
    status = models.CharField(
        max_length=20,
        choices=InventoryStatus.choices,
        default=InventoryStatus.AVAILABLE
    )
    is_published = models.BooleanField(
        default=True,
        help_text=_('Published in the public searchable student catalogue')
    )
    published_at = models.DateTimeField(default=timezone.now)
    cover_image = models.ImageField(upload_to='inventory_covers/', blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bb_inventory_copies'
        ordering = ['-created_at']
        verbose_name = 'Inventory Copy'
        verbose_name_plural = 'Inventory Copies'

    @property
    def is_available(self):
        return self.status == InventoryStatus.AVAILABLE and self.is_published

    def __str__(self):
        return f"[{self.tracking_code}] {self.book_title} ({self.ngo.name})"
