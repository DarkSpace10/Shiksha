from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from apps.accounts.models import UserRole
from apps.ngos.models import NGOMembership, NGOStatus


def require_role(*roles):
    """Decorator ensuring user is authenticated and has one of the specified roles."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Please sign in to access this portal.")
                return redirect('accounts:login')
            
            if request.user.is_suspended:
                messages.error(request, "Your account has been suspended. Please contact platform administration.")
                return redirect('core:home')

            if request.user.is_platform_admin:
                return view_func(request, *args, **kwargs)

            if request.user.role not in roles:
                messages.error(request, "You do not have authorized permissions to view that page.")
                return redirect(request.user.get_dashboard_url())

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def require_ngo_staff(permission_flag=None):
    """
    Decorator ensuring user is an active NGO staff member with an approved NGO.
    Attaches request.ngo and request.membership.
    Enforces strict organization-level isolation.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Please log in to your NGO staff account.")
                return redirect('accounts:login')

            if request.user.is_suspended:
                messages.error(request, "Your account has been suspended.")
                return redirect('core:home')

            membership = NGOMembership.objects.filter(
                user=request.user,
                is_active=True
            ).select_related('ngo').first()

            if not membership:
                messages.error(request, "You are not affiliated with an active NGO organization.")
                return redirect('core:home')

            if membership.ngo.status != NGOStatus.APPROVED and not request.user.is_platform_admin:
                messages.warning(
                    request,
                    f"Your NGO organization '{membership.ngo.name}' is currently {membership.ngo.get_status_display()}."
                )
                return redirect('ngos:ngo_status_page', ngo_id=membership.ngo.id)

            if permission_flag:
                if not getattr(membership, permission_flag, False):
                    messages.error(request, "Your NGO staff role does not have authorization for this operation.")
                    return redirect('ngos:dashboard')

            request.ngo = membership.ngo
            request.membership = membership
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
