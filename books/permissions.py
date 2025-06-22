from rest_framework import permissions

class IsOrderOwnerOrAdmin(permissions.BasePermission):
    """
    Разрешение для проверки, является ли пользователь владельцем заказа или администратором
    """
    def has_object_permission(self, request, view, obj):
        # Разрешаем доступ администраторам
        if request.user.is_staff or request.user.roles.filter(name='admin').exists():
            return True
        
        # Разрешаем доступ владельцу заказа
        return obj.user == request.user 