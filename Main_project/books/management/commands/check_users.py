from django.core.management.base import BaseCommand
from books.models import User, Role, UserRole

class Command(BaseCommand):
    help = 'Проверяет пользователей и их роли'

    def handle(self, *args, **options):
        self.stdout.write('Проверка пользователей...')
        
        users = User.objects.all()
        self.stdout.write(f'Всего пользователей: {users.count()}')
        
        for user in users:
            self.stdout.write(f'\nПользователь: {user.username}')
            self.stdout.write(f'  Email: {user.email}')
            self.stdout.write(f'  Активен: {user.is_active}')
            self.stdout.write(f'  Staff: {user.is_staff}')
            self.stdout.write(f'  Superuser: {user.is_superuser}')
            
            # Проверяем роли
            try:
                roles = user.roles.all()
                if roles.exists():
                    role_names = [role.name for role in roles]
                    self.stdout.write(f'  Роли: {", ".join(role_names)}')
                else:
                    self.stdout.write('  Роли: НЕТ РОЛЕЙ!')
            except Exception as e:
                self.stdout.write(f'  Ошибка при получении ролей: {e}')
            
            # Проверяем UserRole связи
            user_roles = UserRole.objects.filter(user=user)
            self.stdout.write(f'  UserRole записей: {user_roles.count()}')
        
        # Проверяем существующие роли
        self.stdout.write('\n\nСуществующие роли:')
        roles = Role.objects.all()
        for role in roles:
            self.stdout.write(f'  {role.name}')
        
        self.stdout.write('\nПроверка завершена!') 