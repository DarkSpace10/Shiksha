from django import forms
from .models import (
    BookRequest, VerificationDocument, DocumentType,
    StudentVerification, RequestReview, DeliveryJob, DeliveryStatus
)


class VerificationDocumentUploadForm(forms.ModelForm):
    class Meta:
        model = VerificationDocument
        fields = ['document_type', 'document_title', 'document_file']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'document_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Current Year College ID Card / Semester Fee Receipt'}),
            'document_file': forms.FileInput(attrs={'class': 'form-control'}),
        }


class BookRequestCreateForm(forms.ModelForm):
    class Meta:
        model = BookRequest
        fields = [
            'educational_purpose', 'urgent_need', 'urgency_reason',
            'delivery_address', 'delivery_city', 'delivery_state',
            'delivery_postal_code', 'contact_phone'
        ]
        widgets = {
            'educational_purpose': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Explain which subject/course this book is needed for, and why you are requesting it from BookBridge.'
            }),
            'urgent_need': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'urgency_reason': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'If urgent, mention exam date or assignment deadline'
            }),
            'delivery_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Complete residential or campus address for delivery'
            }),
            'delivery_city': forms.TextInput(attrs={'class': 'form-control'}),
            'delivery_state': forms.TextInput(attrs={'class': 'form-control'}),
            'delivery_postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class StudentVerificationForm(forms.Form):
    DECISION_CHOICES = [
        ('APPROVED', 'Approve — Student Eligibility & Genuine Need Verified'),
        ('REJECTED', 'Reject — Documents Inadequate / Need Not Established'),
        ('CORRECTION_REQUESTED', 'Request More Documents / Re-submission'),
    ]
    status = forms.ChoiceField(choices=DECISION_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    comments = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Verification notes, verification call details, or documents required.'})
    )


class DeliveryDispatchForm(forms.ModelForm):
    class Meta:
        model = DeliveryJob
        fields = ['courier_name', 'tracking_number', 'dispatch_notes']
        widgets = {
            'courier_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. India Post / Blue Dart / NGO Volunteer Team'}),
            'tracking_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Consignment Tracking ID'}),
            'dispatch_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Dispatch notes, parcel weight, packaging details'}),
        }


class StudentConfirmReceiptForm(forms.Form):
    student_feedback = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Leave a thank-you note or feedback for the book donor and NGO team!'
        })
    )
