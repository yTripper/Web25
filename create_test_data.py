#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookstore.settings')
django.setup()

from books.models import Author, Book, Genre, BookGenre, Role, User, UserRole
from django.utils import timezone
from decimal import Decimal

def create_test_data():
    print("Создание тестовых данных...")
    
    # Создаем роли
    admin_role, created = Role.objects.get_or_create(name='admin')
    moderator_role, created = Role.objects.get_or_create(name='moderator')
    user_role, created = Role.objects.get_or_create(name='user')
    
    # Создаем авторов
    authors_data = [
        {'name': 'Александр Пушкин', 'bio': 'Великий русский поэт и писатель'},
        {'name': 'Лев Толстой', 'bio': 'Русский писатель, философ'},
        {'name': 'Федор Достоевский', 'bio': 'Русский писатель, мыслитель'},
        {'name': 'Антон Чехов', 'bio': 'Русский писатель и драматург'},
        {'name': 'Иван Тургенев', 'bio': 'Русский писатель-реалист'},
    ]
    
    authors = []
    for author_data in authors_data:
        author, created = Author.objects.get_or_create(
            name=author_data['name'],
            defaults={'bio': author_data['bio']}
        )
        authors.append(author)
        if created:
            print(f"Создан автор: {author.name}")
    
    # Создаем жанры
    genres_data = ['Классика', 'Роман', 'Поэзия', 'Драма', 'Проза']
    genres = []
    for genre_name in genres_data:
        genre, created = Genre.objects.get_or_create(name=genre_name)
        genres.append(genre)
        if created:
            print(f"Создан жанр: {genre.name}")
    
    # Создаем книги
    books_data = [
        {
            'title': 'Евгений Онегин',
            'author': authors[0],  # Пушкин
            'description': 'Роман в стихах о любви и судьбе',
            'price': Decimal('850.00'),
            'stock_quantity': 15,
            'has_discount': True,
            'discount_percent': 15,
            'discount_start': timezone.now(),
            'discount_end': timezone.now() + timezone.timedelta(days=30),
        },
        {
            'title': 'Война и мир',
            'author': authors[1],  # Толстой
            'description': 'Эпический роман о войне 1812 года',
            'price': Decimal('1200.00'),
            'stock_quantity': 8,
            'has_discount': False,
        },
        {
            'title': 'Преступление и наказание',
            'author': authors[2],  # Достоевский
            'description': 'Психологический роман о преступлении и искуплении',
            'price': Decimal('950.00'),
            'stock_quantity': 12,
            'has_discount': True,
            'discount_percent': 20,
            'discount_start': timezone.now(),
            'discount_end': timezone.now() + timezone.timedelta(days=15),
        },
        {
            'title': 'Вишневый сад',
            'author': authors[3],  # Чехов
            'description': 'Пьеса о смене эпох в России',
            'price': Decimal('650.00'),
            'stock_quantity': 20,
            'has_discount': False,
        },
        {
            'title': 'Отцы и дети',
            'author': authors[4],  # Тургенев
            'description': 'Роман о конфликте поколений',
            'price': Decimal('750.00'),
            'stock_quantity': 10,
            'has_discount': True,
            'discount_percent': 10,
            'discount_start': timezone.now(),
            'discount_end': timezone.now() + timezone.timedelta(days=45),
        },
        {
            'title': 'Анна Каренина',
            'author': authors[1],  # Толстой
            'description': 'Роман о любви и трагедии',
            'price': Decimal('1100.00'),
            'stock_quantity': 6,
            'has_discount': False,
        },
        {
            'title': 'Капитанская дочка',
            'author': authors[0],  # Пушкин
            'description': 'Исторический роман о пугачевском восстании',
            'price': Decimal('550.00'),
            'stock_quantity': 25,
            'has_discount': False,
        },
        {
            'title': 'Братья Карамазовы',
            'author': authors[2],  # Достоевский
            'description': 'Философский роман о вере и сомнении',
            'price': Decimal('1350.00'),
            'stock_quantity': 4,
            'has_discount': True,
            'discount_percent': 25,
            'discount_start': timezone.now(),
            'discount_end': timezone.now() + timezone.timedelta(days=20),
        },
    ]
    
    books = []
    for book_data in books_data:
        book, created = Book.objects.get_or_create(
            title=book_data['title'],
            author=book_data['author'],
            defaults=book_data
        )
        books.append(book)
        if created:
            print(f"Создана книга: {book.title}")
    
    # Связываем книги с жанрами
    book_genre_mapping = [
        (books[0], [genres[0], genres[2]]),  # Евгений Онегин - Классика, Поэзия
        (books[1], [genres[0], genres[1]]),  # Война и мир - Классика, Роман
        (books[2], [genres[0], genres[1]]),  # Преступление и наказание - Классика, Роман
        (books[3], [genres[0], genres[3]]),  # Вишневый сад - Классика, Драма
        (books[4], [genres[0], genres[1]]),  # Отцы и дети - Классика, Роман
        (books[5], [genres[0], genres[1]]),  # Анна Каренина - Классика, Роман
        (books[6], [genres[0], genres[4]]),  # Капитанская дочка - Классика, Проза
        (books[7], [genres[0], genres[1]]),  # Братья Карамазовы - Классика, Роман
    ]
    
    for book, book_genres in book_genre_mapping:
        for genre in book_genres:
            book_genre, created = BookGenre.objects.get_or_create(book=book, genre=genre)
            if created:
                print(f"Связана книга {book.title} с жанром {genre.name}")
    
    print("Тестовые данные успешно созданы!")

if __name__ == '__main__':
    create_test_data() 