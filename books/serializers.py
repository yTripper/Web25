from rest_framework import serializers
from django.db.models import Avg, Sum
from .models import Book, Author, Genre, Review, Cover, Favorite, Order, OrderItem
from decimal import Decimal
from typing import Any

class BookSerializer(serializers.ModelSerializer):
    genres = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    total_sales = serializers.SerializerMethodField()
    favorites_count = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'genres', 'description', 'price',
            'status', 'has_discount', 'discount_percent', 'discounted_price',
            'is_favorite', 'avg_rating', 'reviews_count', 'total_sales',
            'favorites_count', 'final_price'
        ]

    def get_genres(self, obj: Book) -> list:
        """
        Возвращает список жанров книги.

        Args:
            obj (Book): Экземпляр книги.

        Returns:
            list: Список названий жанров.
        """
        return [genre.name for genre in obj.genres.all()]

    def get_author(self, obj: Book) -> str:
        """
        Возвращает имя автора книги.

        Args:
            obj (Book): Экземпляр книги.

        Returns:
            str: Имя автора.
        """
        return obj.author.name

    def get_discounted_price(self, obj: Book) -> Decimal:
        """
        Возвращает цену книги с учетом скидки.

        Args:
            obj (Book): Экземпляр книги.

        Returns:
            Decimal: Цена с учетом скидки.
        """
        return obj.current_price

    def get_is_favorite(self, obj: Book) -> bool:
        """
        Проверяет, находится ли книга в избранном у текущего пользователя.

        Args:
            obj (Book): Экземпляр книги.

        Returns:
            bool: True, если книга в избранном.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorites.filter(user=request.user).exists()
        return False

    def get_avg_rating(self, obj: Book) -> float:
        """
        Возвращает средний рейтинг книги.

        Args:
            obj (Book): Экземпляр книги.

        Returns:
            float: Средний рейтинг или 0.0.
        """
        return obj.reviews.aggregate(avg=Avg('rating'))['avg'] or 0.0

    def get_reviews_count(self, obj: Book) -> int:
        """
        Возвращает количество отзывов к книге.

        Args:
            obj (Book): Экземпляр книги.

        Returns:
            int: Количество отзывов.
        """
        return obj.reviews.count()

    def get_total_sales(self, obj: Book) -> int:
        """
        Возвращает общее количество проданных экземпляров книги.

        Args:
            obj (Book): Экземпляр книги.

        Returns:
            int: Общее количество продаж.
        """
        return OrderItem.objects.filter(book=obj).aggregate(
            total=Sum('quantity')
        )['total'] or 0

    def get_favorites_count(self, obj: Book) -> int:
        """
        Возвращает количество пользователей, добавивших книгу в избранное.

        Args:
            obj (Book): Экземпляр книги.

        Returns:
            int: Количество избранных.
        """
        return obj.favorites.count()

    def get_final_price(self, obj: Book) -> Decimal:
        """
        Возвращает итоговую цену книги с учётом скидки.

        Args:
            obj (Book): Экземпляр книги.

        Returns:
            Decimal: Итоговая цена.
        """
        return obj.current_price

class AuthorSerializer(serializers.ModelSerializer):
    books_count = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = ['id', 'name', 'bio', 'birth_date', 'books_count', 'avg_rating']

    def get_books_count(self, obj: Author) -> int:
        """
        Возвращает количество книг автора.

        Args:
            obj (Author): Экземпляр автора.

        Returns:
            int: Количество книг.
        """
        return obj.books.count()

    def get_avg_rating(self, obj: Author) -> float:
        """
        Возвращает средний рейтинг всех книг автора.

        Args:
            obj (Author): Экземпляр автора.

        Returns:
            float: Средний рейтинг или 0.0.
        """
        return Review.objects.filter(book__author=obj).aggregate(
            avg=Avg('rating')
        )['avg'] or 0.0

class GenreSerializer(serializers.ModelSerializer):
    books_count = serializers.SerializerMethodField()

    class Meta:
        model = Genre
        fields = ['id', 'name', 'books_count']

    def get_books_count(self, obj: Genre) -> int:
        """
        Возвращает количество книг в жанре.

        Args:
            obj (Genre): Экземпляр жанра.

        Returns:
            int: Количество книг.
        """
        return obj.book_genres.count()

class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    book = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'user', 'book', 'rating', 'comment', 'created_at']

    def get_user(self, obj: Review) -> str:
        """
        Возвращает имя пользователя, оставившего отзыв.

        Args:
            obj (Review): Экземпляр отзыва.

        Returns:
            str: Имя пользователя.
        """
        return obj.user.username

    def get_book(self, obj: Review) -> str:
        """
        Возвращает название книги.

        Args:
            obj (Review): Экземпляр отзыва.

        Returns:
            str: Название книги.
        """
        return obj.book.title

class OrderSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    order_items = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'user_name', 'status', 'shipping_address', 
            'payment_method', 'total_amount', 'created_at', 'updated_at',
            'order_items', 'items_count'
        ]

    def get_user_name(self, obj):
        return obj.user.username

    def get_order_items(self, obj):
        return [
            {
                'book_title': item.book.title,
                'quantity': item.quantity,
                'price': item.price,
                'total': item.quantity * item.price
            }
            for item in obj.order_items.all()
        ]

    def get_items_count(self, obj):
        return obj.order_items.count() 