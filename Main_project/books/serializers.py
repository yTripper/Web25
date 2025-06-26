from rest_framework import serializers
from django.db.models import Avg, Sum
from .models import Book, Author, Genre, Review, Cover, Favorite, Order, OrderItem, User, Role
from decimal import Decimal
from typing import Any
from django.contrib.auth import get_user_model

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
        Возвращает средний рейтинг книг автора.

        Args:
            obj (Author): Экземпляр автора.

        Returns:
            float: Средний рейтинг.
        """
        avg_rating = obj.books.aggregate(avg_rating=Avg('reviews__rating'))['avg_rating']
        return round(avg_rating, 2) if avg_rating else 0.0

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
        return obj.books.count()

class BookSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    author_id = serializers.IntegerField(write_only=True, required=False)
    genres = GenreSerializer(many=True, read_only=True)
    genre_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    cover_image = serializers.SerializerMethodField()
    ebook_file = serializers.FileField(required=False, allow_null=True)
    discounted_price = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    total_sales = serializers.SerializerMethodField()
    favorites_count = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()
    publication_year = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'author_id', 'genres', 'genre_ids',
            'description', 'price', 'status', 'stock_quantity',
            'has_discount', 'discount_percent', 'discount_start', 'discount_end',
            'ebook_file', 'book_url', 'created_at', 'updated_at', 'published_at',
            'cover_image', 'discounted_price', 'is_favorite', 'avg_rating',
            'reviews_count', 'total_sales', 'favorites_count', 'final_price',
            'publication_year'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        """
        Валидация данных перед сохранением.
        Игнорируем поля, которых нет в модели.
        """
        print(f"DEBUG: BookSerializer.validate called with data: {data}")
        
        # Удаляем поля, которых нет в модели Book
        fields_to_remove = ['publication_year', 'isbn', 'language', 'pages', 'title_en', 'genre']
        for field in fields_to_remove:
            if field in data:
                print(f"DEBUG: Removing field {field}: {data[field]}")
                del data[field]
        
        # Обрабатываем автора из FormData
        if 'author' in data:
            author_value = data['author']
            print(f"DEBUG: Processing author field: {author_value} (type: {type(author_value)})")
            if isinstance(author_value, str) and author_value.isdigit():
                # Если author пришел как строка с ID, конвертируем в int
                data['author_id'] = int(author_value)
                del data['author']
                print(f"DEBUG: Converted author to author_id: {data['author_id']}")
        
        # Обрабатываем stock_quantity
        if 'stock_quantity' in data:
            stock_value = data['stock_quantity']
            print(f"DEBUG: Processing stock_quantity: {stock_value} (type: {type(stock_value)})")
            if isinstance(stock_value, str):
                try:
                    data['stock_quantity'] = int(stock_value)
                    print(f"DEBUG: Converted stock_quantity to int: {data['stock_quantity']}")
                except ValueError:
                    print(f"DEBUG: Failed to convert stock_quantity to int: {stock_value}")
                    data['stock_quantity'] = 0
        else:
            # Если stock_quantity не передано, устанавливаем значение по умолчанию
            data['stock_quantity'] = 0
            print(f"DEBUG: Set default stock_quantity: 0")
        
        # Обрабатываем price
        if 'price' in data:
            price_value = data['price']
            print(f"DEBUG: Processing price: {price_value} (type: {type(price_value)})")
            if isinstance(price_value, str):
                try:
                    data['price'] = float(price_value)
                    print(f"DEBUG: Converted price to float: {data['price']}")
                except ValueError:
                    print(f"DEBUG: Failed to convert price to float: {price_value}")
        
        # Обрабатываем жанры
        if 'genres' in data:
            genres_value = data['genres']
            print(f"DEBUG: Processing genres: {genres_value} (type: {type(genres_value)})")
            if isinstance(genres_value, str):
                # Если жанры пришли как строка с ID через запятую
                try:
                    genre_ids = [int(id.strip()) for id in genres_value.split(',') if id.strip().isdigit()]
                    data['genre_ids'] = genre_ids
                    del data['genres']
                    print(f"DEBUG: Converted genres to genre_ids: {genre_ids}")
                except ValueError:
                    print(f"DEBUG: Failed to convert genres to IDs: {genres_value}")
                    data['genre_ids'] = []
                    del data['genres']
        
        print(f"DEBUG: Validated data: {data}")
        return data

    def update(self, instance, validated_data):
        """
        Обновление экземпляра книги.
        """
        print(f"DEBUG: BookSerializer.update called with data: {validated_data}")
        
        # Обрабатываем автора отдельно
        author_id = validated_data.pop('author_id', None)
        if author_id:
            validated_data['author_id'] = author_id
        
        # Обрабатываем жанры отдельно
        genre_ids = validated_data.pop('genre_ids', None)
        
        print(f"DEBUG: Final validated_data: {validated_data}")
        book = super().update(instance, validated_data)
        
        # Обновляем жанры если они были переданы
        if genre_ids is not None:
            print(f"DEBUG: Updating genres with IDs: {genre_ids}")
            book.genres.clear()
            for genre_id in genre_ids:
                try:
                    genre = Genre.objects.get(id=genre_id)
                    book.genres.add(genre)
                except Genre.DoesNotExist:
                    print(f"DEBUG: Genre with ID {genre_id} does not exist")
        
        return book

    def get_cover_image(self, obj: Book) -> str:
        """
        Возвращает URL обложки книги.

        Args:
            obj (Book): Экземпляр книги.

        Returns:
            str: URL обложки или пустая строка.
        """
        if hasattr(obj, 'cover') and obj.cover and obj.cover.image:
            return obj.cover.image.url
        return ''

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

    def get_publication_year(self, obj: Book) -> str:
        """
        Возвращает год публикации из даты публикации.

        Args:
            obj (Book): Экземпляр книги.

        Returns:
            str: Год публикации или пустая строка.
        """
        if obj.published_at:
            return str(obj.published_at.year)
        return ''

class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(write_only=True, required=False)
    book = serializers.SerializerMethodField()
    book_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Review
        fields = ['id', 'user', 'user_id', 'book', 'book_id', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        """
        Валидация данных перед сохранением.
        """
        print(f"DEBUG: ReviewSerializer.validate called with data: {data}")
        
        # Обрабатываем book_id
        if 'book' in data:
            book_value = data['book']
            print(f"DEBUG: Processing book field: {book_value} (type: {type(book_value)})")
            if isinstance(book_value, str) and book_value.isdigit():
                data['book_id'] = int(book_value)
                del data['book']
                print(f"DEBUG: Converted book to book_id: {data['book_id']}")
        
        # Обрабатываем user_id
        if 'user' in data:
            user_value = data['user']
            print(f"DEBUG: Processing user field: {user_value} (type: {type(user_value)})")
            if isinstance(user_value, str) and user_value.isdigit():
                data['user_id'] = int(user_value)
                del data['user']
                print(f"DEBUG: Converted user to user_id: {data['user_id']}")
        
        # Обрабатываем text -> comment
        if 'text' in data:
            data['comment'] = data['text']
            del data['text']
            print(f"DEBUG: Converted text to comment: {data['comment']}")
        
        print(f"DEBUG: Validated data: {data}")
        return data

    def create(self, validated_data):
        """
        Создание нового отзыва.
        """
        print(f"DEBUG: ReviewSerializer.create called with data: {validated_data}")
        
        # Обрабатываем book_id
        book_id = validated_data.pop('book_id', None)
        if book_id:
            validated_data['book_id'] = book_id
        
        # Обрабатываем user_id
        user_id = validated_data.pop('user_id', None)
        if user_id:
            validated_data['user_id'] = user_id
        
        # Если пользователь не указан, берем из контекста
        if 'user_id' not in validated_data:
            request = self.context.get('request')
            if request and request.user.is_authenticated:
                validated_data['user_id'] = request.user.id
                print(f"DEBUG: Set user_id from context: {validated_data['user_id']}")
        
        print(f"DEBUG: Final validated_data: {validated_data}")
        return super().create(validated_data)

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
        Возвращает название книги, к которой относится отзыв.

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
            'id', 'user_name', 'order_items', 'items_count', 'total_amount',
            'status', 'payment_method', 'created_at'
        ]

    def get_user_name(self, obj):
        return obj.user.username

    def get_order_items(self, obj):
        return [{'book': item.book.title, 'quantity': item.quantity, 'price': item.price} for item in obj.order_items.all()]

    def get_items_count(self, obj):
        return obj.order_items.count() 

class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'roles']
        read_only_fields = ['id', 'is_staff']
    
    def get_roles(self, obj):
        return [{'id': role.id, 'name': role.name} for role in obj.roles.all()] 