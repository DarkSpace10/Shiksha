from apps.accounts.models import UserRole, Notification
from apps.ngos.models import NGOMembership


def global_context(request):
    """
    Inject globally accessible context variables into all Django templates.
    """
    context = {
        'UserRole': UserRole,
        'unread_notifications_count': 0,
        'recent_notifications': [],
        'current_ngo': None,
        'current_membership': None,
    }

    if request.user.is_authenticated:
        # Fetch unread notifications
        notifications_qs = Notification.objects.filter(user=request.user)
        context['unread_notifications_count'] = notifications_qs.filter(is_read=False).count()
        context['recent_notifications'] = notifications_qs[:5]

        # If user is NGO staff, attach their primary active NGO and membership
        if request.user.role == UserRole.NGO_STAFF:
            membership = NGOMembership.objects.filter(
                user=request.user,
                is_active=True
            ).select_related('ngo').first()
            if membership:
                context['current_membership'] = membership
                context['current_ngo'] = membership.ngo

    return context
