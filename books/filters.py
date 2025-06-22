import django_filters
from .models import Book, Author, Genre

class BookFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr='icontains')
    author = django_filters.ModelChoiceFilter(queryset=Author.objects.all())
    genres = django_filters.ModelMultipleChoiceFilter(
        queryset=Genre.objects.all(),
        field_name='genres__name',
        lookup_expr='in'
    )
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    status = django_filters.ChoiceFilter(choices=Book.STATUS_CHOICES)
    has_discount = django_filters.BooleanFilter()
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

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