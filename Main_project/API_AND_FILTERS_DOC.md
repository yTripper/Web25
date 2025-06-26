# 📚 Документация по API и фильтрам

## 1. Архитектура API

### 1.1 ViewSets

```python
class BookViewSet(viewsets.ModelViewSet):
    """API для работы с книгами"""
    queryset = Book.objects.all().select_related('author').prefetch_related('genres')
    serializer_class = BookSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BookFilter
    search_fields = ['title', 'author__name', 'description']
    ordering_fields = ['price', 'created_at', 'title']
    ordering = ['-created_at']
```

- `ModelViewSet` реализует CRUD (создание, чтение, обновление, удаление)
- Оптимизация запросов через `select_related` и `prefetch_related`
- Подключение фильтров, поиска и сортировки
- Использование кастомного фильтра `BookFilter`

### 1.2 URL маршрутизация

```python
router = DefaultRouter()
router.register(r'books', BookViewSet)
...
urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', api_login, name='api-login'),
    ...
]
```

- Автоматически создаются эндпоинты `/api/books/`, `/api/books/{id}/` и др.

### 1.3 Сериализаторы

```python
class BookSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    author_id = serializers.IntegerField(write_only=True)
    genres = GenreSerializer(many=True, read_only=True)
    genre_ids = serializers.ListField(write_only=True)
    avg_rating = serializers.SerializerMethodField()
    ...
```

- Вложенные сериализаторы для связанных моделей
- `SerializerMethodField` для вычисляемых полей
- `read_only`/`write_only` для управления доступностью полей

### 1.4 Аутентификация

```python
@csrf_exempt
def api_login(request):
    ...
```

- Используется Django Session Auth
- CSRF отключён для API
- Возвращается JSON с данными пользователя и ошибками

### 1.5 Валидация и обработка ошибок

```python
def validate(self, data):
    ...
```

- Преобразование типов
- Обработка FormData
- Удаление лишних полей
- Значения по умолчанию

---

## 2. Фильтры (filters.py)

### 2.1 BookFilter

```python
class BookFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr='icontains')
    author = django_filters.ModelChoiceFilter(queryset=Author.objects.all().order_by('name'))
    genres = django_filters.ModelMultipleChoiceFilter(queryset=Genre.objects.all().order_by('name'), field_name='genres__name', lookup_expr='in')
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    status = django_filters.ChoiceFilter(choices=Book.STATUS_CHOICES)
    has_discount = django_filters.BooleanFilter()
    in_stock = django_filters.BooleanFilter(method='filter_in_stock')
    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(status='available', stock_quantity__gt=0)
        return queryset
```

- Поддержка поиска, выбора, диапазонов, булевых фильтров
- Кастомные методы для сложных фильтров

### 2.2 ReviewFilter

```python
class ReviewFilter(django_filters.FilterSet):
    rating = django_filters.NumberFilter()
    min_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    max_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='lte')
    comment = django_filters.CharFilter(lookup_expr='icontains')
    book = django_filters.NumberFilter(field_name='book__id')
    user = django_filters.NumberFilter(field_name='user__id')
```

- Фильтрация по рейтингу, тексту, связанным объектам

### 2.3 Интеграция фильтров в API

```python
filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
filterset_class = BookFilter
search_fields = ['title', 'author__name', 'description']
ordering_fields = ['price', 'created_at', 'title']
```

- Фильтры, поиск и сортировка работают одновременно

### 2.4 Примеры использования фильтров

- `GET /api/books/?title=книга` — поиск по названию
- `GET /api/books/?author=1` — фильтр по автору
- `GET /api/books/?genres=1,2,3` — фильтр по жанрам
- `GET /api/books/?min_price=100&max_price=500` — диапазон цен
- `GET /api/books/?has_discount=true` — только со скидкой
- `GET /api/books/?search=программирование` — поиск по всем полям
- `GET /api/books/?ordering=price` — сортировка по цене
- `GET /api/books/?title=книга&author=1&min_price=100&has_discount=true&ordering=-created_at` — комбинированный фильтр

### 2.5 Настройки фильтров

```python
REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
FILTERS_DEFAULT_LOOKUP_EXPR = 'icontains'
```

---

## 3. Использование на фронтенде

- Формирование параметров фильтрации и поиска в React-компонентах
- Передача параметров в API через URL
- Отображение вычисляемых и аннотированных полей (рейтинг, отзывы, продажи, избранное)

---

## 4. Преимущества архитектуры

- ✅ Автоматические CRUD и фильтрация
- ✅ Валидация и обработка ошибок на бекенде
- ✅ Оптимизация запросов
- ✅ Гибкая сериализация и расширяемость
- ✅ Удобная интеграция с фронтендом
- ✅ Высокая производительность и масштабируемость 