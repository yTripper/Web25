from django import template

register = template.Library()

@register.filter
def has_role(user, role_name):
    """Проверяет, есть ли у пользователя определенная роль"""
    if not user.is_authenticated:
        return False
    return user.roles.filter(name=role_name).exists()

@register.filter
def is_admin_or_moderator(user):
    """Проверяет, является ли пользователь администратором или модератором"""
    if not user.is_authenticated:
        return False
    return user.roles.filter(name__in=['admin', 'moderator']).exists() 