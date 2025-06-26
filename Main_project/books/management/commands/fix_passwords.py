from django.core.management.base import BaseCommand
from books.models import User
from django.contrib.auth import authenticate

class Command(BaseCommand):
    help = 'Исправляет пароли пользователей для тестирования'

    def add_arguments(self, parser):
        parser.add_argument('--password', type=str, default='12345678', help='Пароль для установки')

    def handle(self, *args, **options):
        password = options['password']
        self.stdout.write(f'Устанавливаем пароль "{password}" для всех пользователей...')
        
        users = User.objects.all()
        fixed_count = 0
        
        for user in users:
            try:
                # Устанавливаем пароль
                user.set_password(password)
                user.save()
                
                # Проверяем аутентификацию
                test_auth = authenticate(username=user.username, password=password)
                if test_auth:
                    self.stdout.write(f'✓ {user.username}: пароль исправлен')
                    fixed_count += 1
                else:
                    self.stdout.write(f'✗ {user.username}: ошибка аутентификации')
                    
            except Exception as e:
                self.stdout.write(f'✗ {user.username}: ошибка - {e}')
        
        self.stdout.write(f'\nИсправлено пользователей: {fixed_count}/{users.count()}')
        self.stdout.write('Теперь все пользователи могут войти с паролем "12345678"') 