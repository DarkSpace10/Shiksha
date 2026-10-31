from django import forms
from .models import NGO, NGOMembership, NGOMemberRole, NGOServiceArea
from apps.accounts.models import User, UserRole


class NGORegistrationForm(forms.ModelForm):
    # Admin account details
    admin_username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. vidya_director'}))
    admin_email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'director@ngo.org'}))
    admin_first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}))
    admin_last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}))
    admin_phone = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 9876543210'}))
    admin_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Min. 8 characters'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}))

    # Service area initial city
    primary_service_city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. New Delhi'}))
    primary_service_state = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Delhi'}))

    class Meta:
        model = NGO
        fields = [
            'name', 'registration_number', 'email', 'phone', 'website',
            'address', 'city', 'state', 'postal_code', 'description', 'mission_statement', 'logo'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Official NGO / Trust Name'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Societies / Trust Reg No.'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'info@ngo.org'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone contact'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.ngo.org'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Head office address'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Tell us about your organization and community book initiatives'}),
            'mission_statement': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Core mission'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_admin_username(self):
        u = self.cleaned_data['admin_username']
        if User.objects.filter(username__iexact=u).exists():
            raise forms.ValidationError("Username already taken.")
        return u

    def clean_admin_email(self):
        e = self.cleaned_data['admin_email']
        if User.objects.filter(email__iexact=e).exists():
            raise forms.ValidationError("User with this email already exists.")
        return e

    def clean(self):
        data = super().clean()
        p1 = data.get('admin_password')
        p2 = data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Passwords do not match.")
        return data


class NGOStaffCreateForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    role = forms.ChoiceField(choices=NGOMemberRole.choices, widget=forms.Select(attrs={'class': 'form-select'}))

    # Permissions
    can_review_donations = forms.BooleanField(required=False, initial=True)
    can_schedule_pickups = forms.BooleanField(required=False, initial=True)
    can_inspect_books = forms.BooleanField(required=False, initial=True)
    can_manage_inventory = forms.BooleanField(required=False, initial=True)
    can_verify_students = forms.BooleanField(required=False, initial=True)
    can_review_requests = forms.BooleanField(required=False, initial=True)
    can_manage_deliveries = forms.BooleanField(required=False, initial=True)
    can_manage_staff = forms.BooleanField(required=False, initial=False)

    def clean_username(self):
        u = self.cleaned_data['username']
        if User.objects.filter(username__iexact=u).exists():
            raise forms.ValidationError("Username is already taken.")
        return u

    def clean_email(self):
        e = self.cleaned_data['email']
        if User.objects.filter(email__iexact=e).exists():
            raise forms.ValidationError("Email is already registered.")
        return e


class NGOServiceAreaForm(forms.ModelForm):
    class Meta:
        model = NGOServiceArea
        fields = ['city', 'state', 'postal_code', 'is_active']
        widgets = {
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal code (Optional)'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
