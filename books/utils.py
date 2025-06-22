from django.db.models import Q
from .models import Book, Author, Genre
from typing import Any, Dict

def search_books(query: str) -> Any:
    """
    Демонстрация __icontains и __contains
    :param query: поисковый запрос
    :return: QuerySet книг
    """
    # __icontains - поиск без учета регистра
    books_by_title = Book.objects.filter(title__icontains=query)
    
    # __contains - поиск с учетом регистра
    books_by_description = Book.objects.filter(description__contains=query)
    
    return books_by_title | books_by_description

def get_book_data() -> Dict[str, Any]:
    """
    Демонстрация values() и values_list()
    :return: Словарь с данными о книгах
    """
    # values() - получение словарей с указанными полями
    books_dict = Book.objects.values('title', 'price', 'status')
    
    # values_list() - получение кортежей с указанными полями
    books_list = Book.objects.values_list('title', 'price', flat=False)
    
    # values_list() с flat=True - получение плоского списка
    book_titles = Book.objects.values_list('title', flat=True)
    
    return {
        'books_dict': books_dict,
        'books_list': books_list,
        'book_titles': book_titles
    }

def check_book_availability():
    """
    Демонстрация count() и exists()
    """
    # count() - подсчет количества объектов
    available_books_count = Book.objects.filter(status='available').count()
    
    # exists() - проверка существования объектов
    has_expensive_books = Book.objects.filter(price__gt=1000).exists()
    
    return {
        'available_books_count': available_books_count,
        'has_expensive_books': has_expensive_books
    }

def update_book_status() -> int:
    """
    Демонстрация update()
    :return: Количество обновленных книг
    """
    # Обновление всех книг определенного автора
    updated_count = Book.objects.filter(
        author__name='Достоевский'
    ).update(status='available')
    
    return updated_count

def delete_old_books() -> Any:
    """
    Демонстрация delete()
    :return: Количество удалённых книг
    """
    # Удаление книг, которые не в наличии более года
    from django.utils import timezone
    from datetime import timedelta
    
    old_date = timezone.now() - timedelta(days=365)
    deleted_count = Book.objects.filter(
        status='out_of_stock',
        updated_at__lt=old_date
    ).delete()
    
    return deleted_count

def get_author_books(author_name):
    """
    Комплексный пример использования всех методов
    """
    # Проверяем существование автора
    if not Author.objects.filter(name__icontains=author_name).exists():
        return None
    
    # Получаем книги автора
    author_books = Book.objects.filter(
        author__name__icontains=author_name
    ).values('title', 'price', 'status')
    
    # Считаем количество книг
    books_count = author_books.count()
    
    # Обновляем статус всех книг автора
    if books_count > 0:
        author_books.update(status='available')
    
    return {
        'books': author_books,
        'count': books_count
    } 