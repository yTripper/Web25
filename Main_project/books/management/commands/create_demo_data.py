from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from books.models import Author, Genre, Book, Role, UserRole, BookGenre, Review
from decimal import Decimal
from django.utils import timezone
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Создание демонстрационных данных для ManyToManyField с through, select_related и prefetch_related'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Создание демонстрационных данных...')
        )
        try:
            # --- РОЛИ ---
            role_names = [
                Role.USER, Role.MODERATOR, Role.ADMIN,
                'Редактор', 'Читатель', 'Критик', 'Библиотекарь', 'Гость', 'VIP', 'Писатель'
            ]
            roles = []
            for name in role_names:
                role, _ = Role.objects.get_or_create(name=name)
                roles.append(role)
            self.stdout.write(f'Ролей: {Role.objects.count()}')

            # --- ПОЛЬЗОВАТЕЛИ ---
            users_data = [
                {'username': f'user{i}', 'email': f'user{i}@example.com', 'first_name': f'Имя{i}'}
                for i in range(1, 11)
            ]
            for user_data in users_data:
                user, created = User.objects.get_or_create(
                    username=user_data['username'],
                    defaults=user_data
                )
                if created:
                    user.set_password('password123')
                    user.save()
            users = list(User.objects.all()[:10])
            self.stdout.write(f'Пользователей: {User.objects.count()}')

            # --- РОЛИ ПОЛЬЗОВАТЕЛЕЙ ---
            for user in users:
                assigned_roles = random.sample(roles, k=random.randint(1, 3))
                for role in assigned_roles:
                    UserRole.objects.get_or_create(user=user, role=role)
            self.stdout.write(f'Связей пользователь-роль: {UserRole.objects.count()}')

            # --- ЖАНРЫ ---
            genre_names = [
                'Классика', 'Роман', 'Поэзия', 'Драма', 'Философия',
                'Фантастика', 'Детектив', 'Приключения', 'История', 'Научная литература'
            ]
            for name in genre_names:
                Genre.objects.get_or_create(name=name)
            genres = list(Genre.objects.all()[:10])
            self.stdout.write(f'Жанров: {Genre.objects.count()}')

            # --- АВТОРЫ ---
            author_names = [
                'Александр Пушкин', 'Лев Толстой', 'Федор Достоевский', 'Антон Чехов', 'Иван Тургенев',
                'Михаил Булгаков', 'Владимир Набоков', 'Николай Гоголь', 'Сергей Есенин', 'Марина Цветаева'
            ]
            for name in author_names:
                Author.objects.get_or_create(name=name, defaults={'bio': f'Биография {name}'})
            authors = list(Author.objects.all()[:10])
            self.stdout.write(f'Авторов: {Author.objects.count()}')

            # --- КНИГИ ---
            books_data = [
                {
                    'title': f'Книга {i}',
                    'author': random.choice(authors),
                    'description': f'Описание книги {i}',
                    'price': Decimal(str(random.randint(500, 3000)))
                }
                for i in range(1, 11)
            ]
            for book_data in books_data:
                Book.objects.get_or_create(title=book_data['title'], defaults=book_data)
            books = list(Book.objects.all()[:10])
            self.stdout.write(f'Книг: {Book.objects.count()}')

            # --- СВЯЗИ КНИГА-ЖАНР ---
            for book in books:
                assigned_genres = random.sample(genres, k=random.randint(1, 3))
                for genre in assigned_genres:
                    BookGenre.objects.get_or_create(book=book, genre=genre)
            self.stdout.write(f'Связей книга-жанр: {BookGenre.objects.count()}')

            # --- ОТЗЫВЫ ---
            comments = [
                'Отличная книга!', 'Очень понравилось', 'Рекомендую', 'Не зашло', 'Шедевр!',
                'Можно было лучше', 'Восхитительно', 'Скучно', 'Захватывающе', 'Прочитал на одном дыхании'
            ]
            for i in range(10):
                Review.objects.get_or_create(
                    user=random.choice(users),
                    book=random.choice(books),
                    defaults={
                        'rating': random.randint(3, 5),
                        'comment': random.choice(comments)
                    }
                )
            self.stdout.write(f'Отзывов: {Review.objects.count()}')

            self.stdout.write(self.style.SUCCESS('Демонстрационные данные успешно созданы!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при создании данных: {e}'))
 