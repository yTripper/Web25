import django_filters
from .models import Book, Author, Genre, Review

class BookFilter(django_filters.FilterSet):
    """
    Фильтр для книг с поддержкой различных критериев поиска.
    
    Поддерживаемые фильтры:
    - title: поиск по названию (содержит)
    - author: выбор автора из списка
    - genres: множественный выбор жанров
    - min_price/max_price: диапазон цен
    - status: статус книги (в наличии, нет в наличии, предзаказ)
    - has_discount: наличие скидки
    - created_after/created_before: диапазон дат создания
    """
    
    title = django_filters.CharFilter(
        lookup_expr='icontains',
        help_text='Поиск по названию книги (содержит)'
    )
    
    author = django_filters.ModelChoiceFilter(
        queryset=Author.objects.all().order_by('name'),
        help_text='Выберите автора'
    )
    
    genres = django_filters.ModelMultipleChoiceFilter(
        queryset=Genre.objects.all().order_by('name'),
        field_name='genres__name',
        lookup_expr='in',
        help_text='Выберите один или несколько жанров'
    )
    
    min_price = django_filters.NumberFilter(
        field_name='price', 
        lookup_expr='gte',
        help_text='Минимальная цена'
    )
    
    max_price = django_filters.NumberFilter(
        field_name='price', 
        lookup_expr='lte',
        help_text='Максимальная цена'
    )
    
    status = django_filters.ChoiceFilter(
        choices=Book.STATUS_CHOICES,
        help_text='Статус книги'
    )
    
    has_discount = django_filters.BooleanFilter(
        help_text='Только книги со скидкой'
    )
    
    created_after = django_filters.DateTimeFilter(
        field_name='created_at', 
        lookup_expr='gte',
        help_text='Дата создания после (YYYY-MM-DD HH:MM:SS)'
    )
    
    created_before = django_filters.DateTimeFilter(
        field_name='created_at', 
        lookup_expr='lte',
        help_text='Дата создания до (YYYY-MM-DD HH:MM:SS)'
    )
    
    # Дополнительные фильтры для демонстрации
    price_range = django_filters.RangeFilter(
        field_name='price',
        help_text='Диапазон цен (например: 100,500)'
    )
    
    rating_min = django_filters.NumberFilter(
        field_name='reviews__rating',
        lookup_expr='gte',
        help_text='Минимальный рейтинг'
    )
    
    in_stock = django_filters.BooleanFilter(
        method='filter_in_stock',
        help_text='Только книги в наличии'
    )
    
    def filter_in_stock(self, queryset, name, value):
        """Фильтр для книг в наличии"""
        if value:
            return queryset.filter(status='available', stock_quantity__gt=0)
        return queryset

    class Meta:
        model = Book
        fields = {
            'title': ['exact', 'icontains'],
            'author': ['exact'],
            'genres': ['exact'],
            'price': ['exact', 'gte', 'lte'],
            'status': ['exact'],
            'has_discount': ['exact'],
            'created_at': ['exact', 'gte', 'lte'],
        }

class ReviewFilter(django_filters.FilterSet):
    """
    Фильтр для отзывов с поддержкой различных критериев поиска.
    """
    
    rating = django_filters.NumberFilter(
        help_text='Точный рейтинг'
    )
    
    min_rating = django_filters.NumberFilter(
        field_name='rating', 
        lookup_expr='gte',
        help_text='Минимальный рейтинг'
    )
    
    max_rating = django_filters.NumberFilter(
        field_name='rating', 
        lookup_expr='lte',
        help_text='Максимальный рейтинг'
    )
    
    comment = django_filters.CharFilter(
        lookup_expr='icontains',
        help_text='Поиск по комментарию'
    )
    
    created_after = django_filters.DateFilter(
        field_name='created_at', 
        lookup_expr='gte',
        help_text='Дата создания после (YYYY-MM-DD)'
    )
    
    created_before = django_filters.DateFilter(
        field_name='created_at', 
        lookup_expr='lte',
        help_text='Дата создания до (YYYY-MM-DD)'
    )
    
    book = django_filters.NumberFilter(
        field_name='book__id',
        help_text='ID книги'
    )
    
    user = django_filters.NumberFilter(
        field_name='user__id',
        help_text='ID пользователя'
    )

    class Meta:
        model = Review
        fields = {
            'rating': ['exact', 'gte', 'lte'],
            'comment': ['icontains'],
            'created_at': ['gte', 'lte'],
            'book': ['exact'],
            'user': ['exact'],
        } 