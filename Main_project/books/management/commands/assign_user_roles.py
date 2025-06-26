from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from books.models import Role, UserRole

class Command(BaseCommand):
    help = 'Назначает роль "user" всем пользователям без ролей'

    def handle(self, *args, **options):
        # Получаем или создаем роль "user"
        user_role, created = Role.objects.get_or_create(
            name='user',
            defaults={'description': 'Обычный пользователь'}
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Создана роль "{user_role.name}"')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Найдена роль "{user_role.name}"')
            )
        
        # Находим всех пользователей без ролей
        users_without_roles = []
        for user in User.objects.all():
            if not hasattr(user, 'roles') or not user.roles.exists():
                users_without_roles.append(user)
        
        if not users_without_roles:
            self.stdout.write(
                self.style.SUCCESS('Все пользователи уже имеют роли')
            )
            return
        
        # Назначаем роль "user" пользователям без ролей
        for user in users_without_roles:
            UserRole.objects.get_or_create(user=user, role=user_role)
            self.stdout.write(
                self.style.SUCCESS(f'Назначена роль "{user_role.name}" пользователю "{user.username}"')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Роль "{user_role.name}" назначена {len(users_without_roles)} пользователям')
        ) 