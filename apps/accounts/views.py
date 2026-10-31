from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction

from .models import User, UserRole, DonorProfile, StudentProfile, Notification, NotificationType
from .forms import DonorRegistrationForm, StudentRegistrationForm, LoginForm, UserProfileForm
from apps.audit.utils import log_audit


def register_donor(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dispatch')

    if request.method == 'POST':
        form = DonorRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    phone_number=form.cleaned_data['phone_number'],
                    role=UserRole.DONOR,
                    is_verified=True
                )
                DonorProfile.objects.create(
                    user=user,
                    address_line1=form.cleaned_data['address_line1'],
                    city=form.cleaned_data['city'],
                    state=form.cleaned_data['state'],
                    postal_code=form.cleaned_data['postal_code'],
                    preferred_pickup_instructions=form.cleaned_data.get('preferred_pickup_instructions', '')
                )
                # Welcome notification
                Notification.objects.create(
                    user=user,
                    title="Welcome to BookBridge!",
                    message="Thank you for joining as a Book Donor. You can now list books you'd like to donate and schedule convenient NGO pickups.",
                    notification_type=NotificationType.SUCCESS,
                    link_url="/donations/create/"
                )
                log_audit(request, action="USER_REGISTER_DONOR", entity=user, user=user, details={"role": "DONOR"})
                login(request, user)
                messages.success(request, f"Welcome to BookBridge, {user.first_name}! Your donor account has been created.")
                return redirect('dashboard:donor_dashboard')
    else:
        form = DonorRegistrationForm()

    return render(request, 'accounts/register_donor.html', {'form': form})


def register_student(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dispatch')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    phone_number=form.cleaned_data['phone_number'],
                    role=UserRole.STUDENT,
                    is_verified=True
                )
                StudentProfile.objects.create(
                    user=user,
                    institution_name=form.cleaned_data['institution_name'],
                    student_id_number=form.cleaned_data['student_id_number'],
                    course_of_study=form.cleaned_data['course_of_study'],
                    academic_level=form.cleaned_data['academic_level'],
                    graduation_year=form.cleaned_data.get('graduation_year'),
                    financial_need_statement=form.cleaned_data['financial_need_statement'],
                    delivery_address=form.cleaned_data['delivery_address'],
                    delivery_city=form.cleaned_data['delivery_city'],
                    delivery_state=form.cleaned_data['delivery_state'],
                    delivery_postal_code=form.cleaned_data['delivery_postal_code']
                )
                # Welcome notification
                Notification.objects.create(
                    user=user,
                    title="Welcome to BookBridge Learner Portal",
                    message="Your student profile is active. Please upload your student ID / proof of enrollment to expedite book request approvals by partner NGOs.",
                    notification_type=NotificationType.INFO,
                    link_url="/student/documents/upload/"
                )
                log_audit(request, action="USER_REGISTER_STUDENT", entity=user, user=user, details={"role": "STUDENT"})
                login(request, user)
                messages.success(request, f"Welcome, {user.first_name}! Browse our verified textbook catalogue.")
                return redirect('dashboard:student_dashboard')
    else:
        form = StudentRegistrationForm()

    return render(request, 'accounts/register_student.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dispatch')

    next_url = request.GET.get('next', '')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['username_or_email'].strip()
            password = form.cleaned_data['password']

            # Check if identifier is email
            user_obj = None
            if '@' in identifier:
                user_obj = User.objects.filter(email__iexact=identifier).first()
                if user_obj:
                    user_obj = authenticate(request, username=user_obj.username, password=password)
            else:
                user_obj = authenticate(request, username=identifier, password=password)

            if user_obj is not None:
                if user_obj.is_suspended:
                    messages.error(request, "Your account has been suspended by the platform administrator.")
                    return render(request, 'accounts/login.html', {'form': form})

                login(request, user_obj)
                log_audit(request, action="USER_LOGIN", entity=user_obj, user=user_obj)
                messages.success(request, f"Welcome back, {user_obj.first_name or user_obj.username}!")
                
                if next_url and next_url.startswith('/'):
                    return redirect(next_url)
                return redirect(user_obj.get_dashboard_url())
            else:
                messages.error(request, "Invalid username/email or password.")
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})


def logout_view(request):
    if request.user.is_authenticated:
        log_audit(request, action="USER_LOGOUT", entity=request.user, user=request.user)
        logout(request)
        messages.info(request, "You have been logged out successfully.")
    return redirect('core:home')


@login_required
def profile_view(request):
    user = request.user
    donor_profile = getattr(user, 'donor_profile', None)
    student_profile = getattr(user, 'student_profile', None)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            
            # Update specific role profile fields if submitted
            if donor_profile:
                donor_profile.address_line1 = request.POST.get('address_line1', donor_profile.address_line1)
                donor_profile.city = request.POST.get('city', donor_profile.city)
                donor_profile.state = request.POST.get('state', donor_profile.state)
                donor_profile.postal_code = request.POST.get('postal_code', donor_profile.postal_code)
                donor_profile.preferred_pickup_instructions = request.POST.get('preferred_pickup_instructions', donor_profile.preferred_pickup_instructions)
                donor_profile.save()

            if student_profile:
                student_profile.institution_name = request.POST.get('institution_name', student_profile.institution_name)
                student_profile.course_of_study = request.POST.get('course_of_study', student_profile.course_of_study)
                student_profile.delivery_address = request.POST.get('delivery_address', student_profile.delivery_address)
                student_profile.delivery_city = request.POST.get('delivery_city', student_profile.delivery_city)
                student_profile.delivery_state = request.POST.get('delivery_state', student_profile.delivery_state)
                student_profile.delivery_postal_code = request.POST.get('delivery_postal_code', student_profile.delivery_postal_code)
                student_profile.save()

            log_audit(request, action="USER_PROFILE_UPDATE", entity=user, user=user)
            messages.success(request, "Your profile details have been successfully updated.")
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=user)

    documents = []
    if student_profile:
        documents = student_profile.documents.all()

    return render(request, 'accounts/profile.html', {
        'form': form,
        'donor_profile': donor_profile,
        'student_profile': student_profile,
        'documents': documents
    })


@login_required
def notifications_view(request):
    notifications_qs = Notification.objects.filter(user=request.user)
    paginator = Paginator(notifications_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'accounts/notifications.html', {'page_obj': page_obj})


@login_required
def mark_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('accounts:notifications')
