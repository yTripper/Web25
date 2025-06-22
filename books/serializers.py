from rest_framework import serializers
from django.db.models import Avg, Sum
from .models import Book, Author, Genre, Review, Cover, Favorite, Order, OrderItem

class BookSerializer(serializers.ModelSerializer):
    discounted_price = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    total_sales = serializers.SerializerMethodField()
    favorites_count = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'genres', 'description', 'price',
            'status', 'has_discount', 'discount_percent', 'discounted_price',
            'is_favorite', 'avg_rating', 'reviews_count', 'total_sales',
            'favorites_count'
        ]

    def get_discounted_price(self, obj):
        if obj.is_discount_active:
            return obj.current_price
        return obj.price

    def get_is_favorite(self, obj):
        favorites_books = self.context.get('favorites_books', [])
        return obj.id in favorites_books

    def get_avg_rating(self, obj):
        return obj.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0

    def get_reviews_count(self, obj):
        return obj.reviews.count()

    def get_total_sales(self, obj):
        return obj.order_items.aggregate(total=Sum('quantity'))['total'] or 0

    def get_favorites_count(self, obj):
        return obj.favorites.count()

class AuthorSerializer(serializers.ModelSerializer):
    books_count = serializers.SerializerMethodField()
    avg_book_rating = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = ['id', 'name', 'bio', 'birth_date', 'books_count', 'avg_book_rating']

    def get_books_count(self, obj):
        return obj.books.count()

    def get_avg_book_rating(self, obj):
        return obj.books.aggregate(
            avg_rating=Avg('reviews__rating')
        )['avg_rating'] or 0

class GenreSerializer(serializers.ModelSerializer):
    books_count = serializers.SerializerMethodField()

    class Meta:
        model = Genre
        fields = ['id', 'name', 'books_count']

    def get_books_count(self, obj):
        return obj.books.count()

class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    book_title = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'user', 'user_name', 'book', 'book_title', 'rating', 'comment', 'created_at']

    def get_user_name(self, obj):
        return obj.user.username

    def get_book_title(self, obj):
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