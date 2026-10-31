from django import forms
from .models import (
    DonationListing, DonationImage, DonationReview, PickupJob,
    BookCategory, ConditionGrade, ReviewDecision, TimeSlot
)
from apps.ngos.models import NGO, NGOStatus
from apps.accounts.models import AcademicLevel


class DonationCreateForm(forms.ModelForm):
    ngo = forms.ModelChoiceField(
        queryset=NGO.objects.filter(status=NGOStatus.APPROVED).order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Select a verified partner NGO to receive and distribute your book"
    )

    class Meta:
        model = DonationListing
        fields = [
            'ngo', 'title', 'author', 'isbn', 'publisher', 'publication_year',
            'category', 'academic_level', 'subject', 'edition', 'declared_condition',
            'donor_condition_description', 'pickup_address', 'pickup_city',
            'pickup_state', 'pickup_postal_code', 'donor_contact_phone',
            'preferred_pickup_time', 'donor_notes'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Concepts of Physics - Vol 1'}),
            'author': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. H.C. Verma'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 978-8177091878 (Optional)'}),
            'publisher': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Publisher / Press name'}),
            'publication_year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2021'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'academic_level': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Physics, Data Structures, English'}),
            'edition': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 3rd Edition'}),
            'declared_condition': forms.Select(attrs={'class': 'form-select'}),
            'donor_condition_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Note any missing pages, pencil markings, torn corners or highlighting'}),
            'pickup_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Complete pickup address'}),
            'pickup_city': forms.TextInput(attrs={'class': 'form-control'}),
            'pickup_state': forms.TextInput(attrs={'class': 'form-control'}),
            'pickup_postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'donor_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'preferred_pickup_time': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Weekdays after 5pm'}),
            'donor_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Additional instructions for pickup agent'}),
        }


class DonationReviewForm(forms.Form):
    decision = forms.ChoiceField(
        choices=ReviewDecision.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    comments = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Provide feedback, reasons for approval/rejection, or specific details/photos requested from the donor.'
        })
    )


class PickupScheduleForm(forms.ModelForm):
    class Meta:
        model = PickupJob
        fields = ['scheduled_date', 'time_slot', 'assigned_agent_name', 'assigned_agent_phone', 'notes']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'time_slot': forms.Select(attrs={'class': 'form-select'}),
            'assigned_agent_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Volunteer / Courier name'}),
            'assigned_agent_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Agent contact number'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Special pickup notes or vehicle instructions'}),
        }


class PhysicalInspectionForm(forms.Form):
    INSPECTION_CHOICES = [
        ('PASSED', 'Inspection Passed — Book is Fit for Inventory & Distribution'),
        ('FAILED', 'Inspection Failed — Book is Heavily Damaged / Unusable'),
    ]
    decision = forms.ChoiceField(
        choices=INSPECTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    verified_condition = forms.ChoiceField(
        choices=ConditionGrade.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    location_shelf = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Aisle 2 - Shelf B4 - Box 08'})
    )
    inspection_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Detailed notes on physical checks: binding intact, page count, markings, water damage assessment.'
        })
    )
