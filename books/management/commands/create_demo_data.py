from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from books.models import Author, Genre, Book, Role, UserRole, BookGenre, Review
from decimal import Decimal
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = 'Создание демонстрационных данных для ManyToManyField с through, select_related и prefetch_related'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Создание демонстрационных данных...')
        )
        
        try:
            # Создаем роли
            user_role, _ = Role.objects.get_or_create(name=Role.USER)
            moderator_role, _ = Role.objects.get_or_create(name=Role.MODERATOR)
            admin_role, _ = Role.objects.get_or_create(name=Role.ADMIN)
            
            # Создаем пользователей
            users_data = [
                {'username': 'alice', 'email': 'alice@example.com', 'first_name': 'Алиса'},
                {'username': 'bob', 'email': 'bob@example.com', 'first_name': 'Боб'},
                {'username': 'charlie', 'email': 'charlie@example.com', 'first_name': 'Чарли'},
            ]
            
            for user_data in users_data:
                user, created = User.objects.get_or_create(
                    username=user_data['username'],
                    defaults=user_data
                )
                if created:
                    user.set_password('password123')
                    user.save()
                    self.stdout.write(f'Создан пользователь: {user.username}')
            
            # Назначаем роли пользователям через промежуточную модель
            alice = User.objects.get(username='alice')
            bob = User.objects.get(username='bob')
            charlie = User.objects.get(username='charlie')
            
            # UserRole через промежуточную модель
            UserRole.objects.get_or_create(user=alice, role=user_role)
            UserRole.objects.get_or_create(user=alice, role=moderator_role)
            UserRole.objects.get_or_create(user=bob, role=user_role)
            UserRole.objects.get_or_create(user=charlie, role=admin_role)
            
            # Создаем авторов
            authors_data = [
                {'name': 'Александр Пушкин', 'bio': 'Великий русский поэт'},
                {'name': 'Лев Толстой', 'bio': 'Русский писатель и мыслитель'},
                {'name': 'Федор Достоевский', 'bio': 'Русский писатель, мыслитель'},
            ]
            
            for author_data in authors_data:
                author, created = Author.objects.get_or_create(
                    name=author_data['name'],
                    defaults=author_data
                )
                if created:
                    self.stdout.write(f'Создан автор: {author.name}')
            
            # Создаем жанры
            genres_data = [
                {'name': 'Классика'},
                {'name': 'Роман'},
                {'name': 'Поэзия'},
                {'name': 'Драма'},
                {'name': 'Философия'},
            ]
            
            for genre_data in genres_data:
                genre, created = Genre.objects.get_or_create(**genre_data)
                if created:
                    self.stdout.write(f'Создан жанр: {genre.name}')
            
            # Создаем книги
            pushkin = Author.objects.get(name='Александр Пушкин')
            tolstoy = Author.objects.get(name='Лев Толстой')
            dostoevsky = Author.objects.get(name='Федор Достоевский')
            
            books_data = [
                {
                    'title': 'Евгений Онегин',
                    'author': pushkin,
                    'description': 'Роман в стихах',
                    'price': Decimal('1500.00')
                },
                {
                    'title': 'Война и мир',
                    'author': tolstoy,
                    'description': 'Эпический роман',
                    'price': Decimal('2500.00')
                },
                {
                    'title': 'Преступление и наказание',
                    'author': dostoevsky,
                    'description': 'Психологический роман',
                    'price': Decimal('1800.00')
                },
                {
                    'title': 'Анна Каренина',
                    'author': tolstoy,
                    'description': 'Роман о любви и обществе',
                    'price': Decimal('2200.00')
                },
            ]
            
            for book_data in books_data:
                book, created = Book.objects.get_or_create(
                    title=book_data['title'],
                    defaults=book_data
                )
                if created:
                    self.stdout.write(f'Создана книга: {book.title}')
            
            # Создаем связи жанров с книгами через промежуточную модель BookGenre
            classic = Genre.objects.get(name='Классика')
            novel = Genre.objects.get(name='Роман')
            poetry = Genre.objects.get(name='Поэзия')
            philosophy = Genre.objects.get(name='Философия')
            
            onegin = Book.objects.get(title='Евгений Онегин')
            war_peace = Book.objects.get(title='Война и мир')
            crime = Book.objects.get(title='Преступление и наказание')
            anna = Book.objects.get(title='Анна Каренина')
            
            # BookGenre через промежуточную модель
            book_genre_relations = [
                (onegin, classic),
                (onegin, poetry),
                (war_peace, classic),
                (war_peace, novel),
                (crime, classic),
                (crime, philosophy),
                (anna, classic),
                (anna, novel),
            ]
            
            for book, genre in book_genre_relations:
                BookGenre.objects.get_or_create(book=book, genre=genre)
            
            # Создаем отзывы
            reviews_data = [
                {'user': alice, 'book': onegin, 'rating': 5, 'comment': 'Прекрасный роман в стихах!'},
                {'user': bob, 'book': onegin, 'rating': 4, 'comment': 'Классика русской литературы'},
                {'user': alice, 'book': war_peace, 'rating': 5, 'comment': 'Эпическое произведение'},
                {'user': charlie, 'book': crime, 'rating': 5, 'comment': 'Глубокий психологический роман'},
                {'user': bob, 'book': anna, 'rating': 4, 'comment': 'Трогательная история'},
            ]
            
            for review_data in reviews_data:
                review, created = Review.objects.get_or_create(
                    user=review_data['user'],
                    book=review_data['book'],
                    defaults={
                        'rating': review_data['rating'],
                        'comment': review_data['comment']
                    }
                )
                if created:
                    self.stdout.write(f'Создан отзыв от {review.user.username} на {review.book.title}')
            
            self.stdout.write(
                self.style.SUCCESS('Демонстрационные данные успешно созданы!')
            )
            
            # Вывод статистики
            self.stdout.write('\n=== СТАТИСТИКА ===')
            self.stdout.write(f'Пользователей: {User.objects.count()}')
            self.stdout.write(f'Ролей: {Role.objects.count()}')
            self.stdout.write(f'Связей пользователь-роль: {UserRole.objects.count()}')
            self.stdout.write(f'Авторов: {Author.objects.count()}')
            self.stdout.write(f'Жанров: {Genre.objects.count()}')
            self.stdout.write(f'Книг: {Book.objects.count()}')
            self.stdout.write(f'Связей книга-жанр: {BookGenre.objects.count()}')
            self.stdout.write(f'Отзывов: {Review.objects.count()}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при создании данных: {e}')
            )
 