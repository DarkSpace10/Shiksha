from .models import AuditLog


def get_client_ip(request):
    """Safely extract remote client IP address from request headers."""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_audit(request=None, action="", entity=None, organization=None, details=None, user=None):
    """
    Log an auditable platform event with structured metadata.
    """
    if details is None:
        details = {}
    
    actor = user
    ip_addr = None
    if request:
        if not actor and hasattr(request, 'user') and request.user.is_authenticated:
            actor = request.user
        ip_addr = get_client_ip(request)

    entity_type = ""
    entity_id = ""
    if entity is not None:
        entity_type = entity.__class__.__name__
        entity_id = str(getattr(entity, 'id', getattr(entity, 'pk', '')))
        # If organization not explicitly provided, try to extract from entity
        if not organization and hasattr(entity, 'ngo'):
            organization = getattr(entity, 'ngo', None)

    try:
        return AuditLog.objects.create(
            user=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            organization=organization,
            details=details,
            ip_address=ip_addr
        )
    except Exception as e:
        # Non-fatal fallback so logging failures never break primary business logic
        print(f"Audit log recording error: {e}")
        return None
