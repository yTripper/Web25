# 📊 Аннотации в Django и их отображение на фронтенде

## Обзор

Аннотации в Django позволяют добавлять вычисляемые поля к QuerySet, которые затем передаются на фронтенд через API. Это мощный способ оптимизации запросов и добавления дополнительной информации без изменения моделей.

## 🔧 Аннотации в Django Backend

### 1. Аннотации в BookViewSet

```python
def get_queryset(self) -> QuerySet:
    """
    Возвращает QuerySet с аннотациями для API.
    """
    queryset = super().get_queryset()
    queryset = queryset.annotate(
        avg_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews'),
        total_sales=Sum('order_items__quantity'),
        favorites_count=Count('favorites')
    )
    return queryset
```

**Что добавляется:**
- `avg_rating` - средний рейтинг книги
- `reviews_count` - количество отзывов
- `total_sales` - общее количество продаж
- `favorites_count` - количество добавлений в избранное

### 2. Аннотации в представлениях

```python
def book_list(request: HttpRequest) -> HttpResponse:
    """Список книг с аннотациями"""
    books = Book.objects.all().select_related('author').prefetch_related('genres')
    
    # Применяем фильтры
    book_filter = BookFilter(request.GET, queryset=books)
    
    # Добавляем аннотации
    books = book_filter.qs.annotate(
        avg_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews'),
        total_sales=Sum('order_items__quantity'),
        favorites_count=Count('favorites')
    )
    
    context = {
        'books': books,
        'filter': book_filter
    }
    return render(request, 'books/book_list.html', context)
```

### 3. Аннотации в Manager модели Book

```python
class BookManager(models.Manager):
    def get_bestsellers(self):
        """Получить книги с наибольшим количеством продаж"""
        return self.annotate(
            total_sales=Sum('order_items__quantity')
        ).filter(total_sales__gt=0).order_by('-total_sales')
    
    def get_popular(self):
        """Получить популярные книги по рейтингу"""
        return self.annotate(
            avg_rating=Avg('reviews__rating'),
            reviews_count=Count('reviews')
        ).filter(reviews_count__gte=1).order_by('-avg_rating')
```

## 📡 Передача аннотаций через API

### 1. Сериализатор с SerializerMethodField

```python
class BookSerializer(serializers.ModelSerializer):
    avg_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    total_sales = serializers.SerializerMethodField()
    favorites_count = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()

    def get_avg_rating(self, obj: Book) -> float:
        """Возвращает средний рейтинг книги."""
        return obj.reviews.aggregate(avg=Avg('rating'))['avg'] or 0.0

    def get_reviews_count(self, obj: Book) -> int:
        """Возвращает количество отзывов к книге."""
        return obj.reviews.count()

    def get_total_sales(self, obj: Book) -> int:
        """Возвращает общее количество проданных экземпляров."""
        return OrderItem.objects.filter(book=obj).aggregate(
            total=Sum('quantity')
        )['total'] or 0

    def get_favorites_count(self, obj: Book) -> int:
        """Возвращает количество избранных."""
        return obj.favorites.count()

    def get_is_favorite(self, obj: Book) -> bool:
        """Проверяет, находится ли книга в избранном."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorites.filter(user=request.user).exists()
        return False

    def get_final_price(self, obj: Book) -> Decimal:
        """Возвращает итоговую цену с учетом скидки."""
        return obj.current_price
```

### 2. Структура API ответа

```json
{
  "id": 1,
  "title": "Название книги",
  "author": {
    "id": 1,
    "name": "Автор"
  },
  "price": "100.00",
  "avg_rating": 4.5,
  "reviews_count": 12,
  "total_sales": 25,
  "favorites_count": 8,
  "is_favorite": true,
  "final_price": "80.00",
  "has_discount": true,
  "discount_percent": 20
}
```

## 🎨 Отображение на фронтенде

### 1. Список книг (BooksPage.js)

```javascript
// Отображение рейтинга и количества отзывов
{book.avg_rating && (
  <p className="card-text">
    <small className="text-warning">
      ⭐ {book.avg_rating.toFixed(1)} ({book.reviews_count || 0} отзывов)
    </small>
  </p>
)}

// Отображение цены с учетом скидки
<div className="price-info">
  {book.has_discount ? (
    <div>
      <span className="text-decoration-line-through text-muted">
        {book.price} ₽
      </span>
      <span className="text-success ms-2">
        {book.final_price} ₽
      </span>
      <span className="badge bg-danger ms-2">
        -{book.discount_percent}%
      </span>
    </div>
  ) : (
    <span>{book.price} ₽</span>
  )}
</div>
```

### 2. Детальная страница книги (BookDetailPage.js)

```javascript
// Отображение рейтинга с звездами
{book.avg_rating && (
  <div className="mb-3">
    <h6>Рейтинг:</h6>
    <div className="d-flex align-items-center">
      <span className="text-warning fs-4 me-2">
        {'⭐'.repeat(Math.round(book.avg_rating))}
      </span>
      <span className="fs-5">{book.avg_rating.toFixed(1)}</span>
      <span className="text-muted ms-2">
        ({book.reviews_count || 0} отзывов)
      </span>
    </div>
  </div>
)}

// Отображение статистики
<div className="row mb-3">
  <div className="col-md-6">
    <p><strong>Продажи:</strong> {book.total_sales || 0} экз.</p>
    <p><strong>В избранном:</strong> {book.favorites_count || 0} раз</p>
  </div>
  <div className="col-md-6">
    <p><strong>Цена:</strong> {book.final_price} ₽</p>
    {book.has_discount && (
      <p><strong>Скидка:</strong> {book.discount_percent}%</p>
    )}
  </div>
</div>
```

### 3. Компонент карточки книги

```javascript
const BookCard = ({ book }) => {
  return (
    <div className="card h-100">
      <img src={book.cover_image} className="card-img-top" alt={book.title} />
      <div className="card-body">
        <h5 className="card-title">{book.title}</h5>
        <p className="card-text">{book.author?.name}</p>
        
        {/* Рейтинг */}
        {book.avg_rating > 0 && (
          <div className="rating-info mb-2">
            <span className="text-warning">
              {'⭐'.repeat(Math.round(book.avg_rating))}
            </span>
            <small className="text-muted ms-1">
              {book.avg_rating.toFixed(1)} ({book.reviews_count})
            </small>
          </div>
        )}
        
        {/* Цена */}
        <div className="price-info">
          {book.has_discount ? (
            <div>
              <span className="text-decoration-line-through text-muted">
                {book.price} ₽
              </span>
              <span className="text-success ms-2 fw-bold">
                {book.final_price} ₽
              </span>
            </div>
          ) : (
            <span className="fw-bold">{book.price} ₽</span>
          )}
        </div>
        
        {/* Статистика */}
        <div className="stats-info mt-2">
          <small className="text-muted">
            Продажи: {book.total_sales || 0} | 
            Избранное: {book.favorites_count || 0}
          </small>
        </div>
      </div>
    </div>
  );
};
```

## 🔍 Валидация на бекенде

### 1. Валидация в моделях

```python
class Book(models.Model):
    def clean(self) -> None:
        """Валидация полей модели"""
        super().clean()
        
        # Валидация скидок
        if self.has_discount:
            if self.discount_percent == 0:
                raise ValidationError(_('Процент скидки должен быть больше 0'))
            if self.discount_percent > 100:
                raise ValidationError(_('Процент скидки не может быть больше 100'))
        
        # Валидация статуса и количества
        if self.status == 'available' and self.stock_quantity == 0:
            raise ValidationError(_('Книга не может быть в наличии при нулевом количестве'))
```

### 2. Валидация в сериализаторах

```python
class BookSerializer(serializers.ModelSerializer):
    def validate(self, data):
        """Валидация данных перед сохранением"""
        # Обрабатываем автора из FormData
        if 'author' in data:
            author_value = data['author']
            if isinstance(author_value, str) and author_value.isdigit():
                data['author_id'] = int(author_value)
                del data['author']
        
        # Обрабатываем stock_quantity
        if 'stock_quantity' in data:
            stock_value = data['stock_quantity']
            if isinstance(stock_value, str):
                try:
                    data['stock_quantity'] = int(stock_value)
                except ValueError:
                    data['stock_quantity'] = 0
        
        return data
```

### 3. Валидация в ReviewSerializer

```python
class ReviewSerializer(serializers.ModelSerializer):
    def validate(self, data):
        """Валидация данных отзыва"""
        # Обрабатываем book_id
        if 'book' in data:
            book_value = data['book']
            if isinstance(book_value, str) and book_value.isdigit():
                data['book_id'] = int(book_value)
                del data['book']
        
        # Обрабатываем text -> comment
        if 'text' in data:
            data['comment'] = data['text']
            del data['text']
        
        return data

    def create(self, validated_data):
        """Создание отзыва с привязкой к пользователю"""
        # Если пользователь не указан, берем из контекста
        if 'user_id' not in validated_data:
            request = self.context.get('request')
            if request and request.user.is_authenticated:
                validated_data['user_id'] = request.user.id
        
        return super().create(validated_data)
```

## 📊 Примеры использования аннотаций

### 1. Популярные книги

```python
def get_popular_books():
    """Получить популярные книги по рейтингу"""
    return Book.objects.annotate(
        avg_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews')
    ).filter(
        reviews_count__gte=1,
        avg_rating__gte=4.0
    ).order_by('-avg_rating')[:10]
```

### 2. Бестселлеры

```python
def get_bestsellers():
    """Получить книги с наибольшими продажами"""
    return Book.objects.annotate(
        total_sales=Sum('order_items__quantity')
    ).filter(
        total_sales__gt=0
    ).order_by('-total_sales')[:10]
```

### 3. Книги со скидкой

```python
def get_discounted_books():
    """Получить книги со скидкой"""
    return Book.objects.annotate(
        final_price=F('price') * (100 - F('discount_percent')) / 100
    ).filter(
        has_discount=True,
        discount_percent__gt=0
    ).order_by('-discount_percent')
```

## 🎯 Преимущества использования аннотаций

### 1. Производительность
- Вычисления происходят на уровне базы данных
- Меньше запросов к БД
- Оптимизированные JOIN операции

### 2. Гибкость
- Легко добавлять новые вычисляемые поля
- Не требует изменения моделей
- Можно комбинировать с фильтрами

### 3. Читаемость кода
- Логика вычислений централизована
- Понятные названия полей
- Легко тестировать

## 🧪 Тестирование аннотаций

```python
class BookAnnotationsTestCase(TestCase):
    def test_avg_rating_annotation(self):
        """Тест аннотации среднего рейтинга"""
        book = Book.objects.create(title='Тестовая книга', price=100)
        Review.objects.create(book=book, rating=5, user=self.user)
        Review.objects.create(book=book, rating=3, user=self.user2)
        
        books_with_rating = Book.objects.annotate(
            avg_rating=Avg('reviews__rating')
        )
        
        book_with_rating = books_with_rating.get(id=book.id)
        self.assertEqual(book_with_rating.avg_rating, 4.0)
    
    def test_reviews_count_annotation(self):
        """Тест аннотации количества отзывов"""
        book = Book.objects.create(title='Тестовая книга', price=100)
        Review.objects.create(book=book, rating=5, user=self.user)
        Review.objects.create(book=book, rating=3, user=self.user2)
        
        books_with_count = Book.objects.annotate(
            reviews_count=Count('reviews')
        )
        
        book_with_count = books_with_count.get(id=book.id)
        self.assertEqual(book_with_count.reviews_count, 2)
```

## 📈 Мониторинг производительности

### 1. Использование Django Debug Toolbar
```python
# settings.py
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

### 2. Логирование запросов
```python
import logging
logger = logging.getLogger('django.db.backends')

# В views.py
logger.info(f"Query: {queryset.query}")
```

### 3. Оптимизация запросов
```python
# Используем select_related для ForeignKey
books = Book.objects.select_related('author').annotate(
    avg_rating=Avg('reviews__rating')
)

# Используем prefetch_related для ManyToMany
books = Book.objects.prefetch_related('genres').annotate(
    reviews_count=Count('reviews')
)
```

Аннотации - это мощный инструмент для оптимизации и расширения функциональности Django приложений, который позволяет эффективно передавать вычисляемые данные на фронтенд без дополнительных запросов к базе данных. 