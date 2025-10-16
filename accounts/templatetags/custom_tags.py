from django import template
from accounts.permissions import is_coach

register = template.Library()


@register.filter
def is_coach_user(user):
    """Template filter pro kontrolu, zda je uživatel coach"""
    if not user or not user.is_authenticated:
        return False
    return is_coach(user)


@register.simple_tag
def user_role(user):
    """Template tag pro získání role uživatele"""
    if not user or not user.is_authenticated:
        return 'anonymous'
    
    try:
        from accounts.models import UserRole
        role = UserRole.objects.get(user=user)
        return role.role
    except UserRole.DoesNotExist:
        return 'company'  # default role