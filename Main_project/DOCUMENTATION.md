# Документация проекта "Книжный магазин"

## 1. Валидация полей

### Валидация в моделях Django

#### Book.clean()
```python
def clean(self) -> None:
    """Валидация полей модели"""
    super().clean()
    
    # Валидация скидок
    if self.has_discount:
        if self.discount_percent == 0:
            raise ValidationError(_('Процент скидки должен быть больше 0'))
        if self.discount_percent > 100:
            raise ValidationError(_('Процент скидки не может быть больше 100'))
        if self.discount_start and self.discount_end and self.discount_start >= self.discount_end:
            raise ValidationError(_('Дата начала скидки должна быть раньше даты окончания'))
    
    # Валидация статуса и количества
    if self.status == 'available' and self.stock_quantity == 0:
        raise ValidationError(_('Книга не может быть в наличии при нулевом количестве'))
    if self.status == 'out_of_stock' and self.stock_quantity > 0:
        raise ValidationError(_('Книга не может быть отсутствовать при наличии на складе'))
```

#### Order.clean()
```python
def clean(self):
    # Валидация адреса доставки
    import re
    address_pattern = r'^[а-яА-ЯёЁ\s]+,\s*д\.\s*\d+,\s*(?:кв\.\s*\d+)?,\s*\d{6}$'
    if not re.match(address_pattern, self.shipping_address):
        raise ValidationError(_('Адрес должен содержать улицу, номер дома и почтовый индекс в формате: "Улица, д. 1, кв. 1, 123456"'))

    # Валидация суммы заказа
    if self.total_amount < 500:
        raise ValidationError(_('Минимальная сумма заказа должна быть не менее 500 рублей'))
    if self.total_amount > 100000:
        raise ValidationError(_('Максимальная сумма заказа не может превышать 100,000 рублей'))
```

### Валидация в сериализаторах DRF

#### BookSerializer.validate()
```python
def validate(self, data):
    """
    Валидация данных перед сохранением.
    Игнорируем поля, которых нет в модели.
    """
    # Удаляем поля, которых нет в модели Book
    fields_to_remove = ['publication_year', 'isbn', 'language', 'pages', 'title_en', 'genre']
    for field in fields_to_remove:
        if field in data:
            del data[field]
    
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
    else:
        data['stock_quantity'] = 0
    
    return data
```

## 2. Оптимизация запросов

### select_related() для ForeignKey и OneToOneField

```python
# В BookViewSet
queryset = Book.objects.all().select_related('author').prefetch_related('genres')

# В ReviewViewSet
queryset = Review.objects.all().select_related('user', 'book')

# В OrderViewSet
queryset = Order.objects.all().select_related('user').prefetch_related('order_items__book')
```

### prefetch_related() для ManyToManyField

```python
# Оптимизация запросов для жанров
books = Book.objects.all().select_related('author').prefetch_related('genres')

# Сложная оптимизация с Prefetch
books_complex_prefetch = Book.objects.select_related('author').prefetch_related(
    Prefetch('reviews', queryset=Review.objects.select_related('user')),
    Prefetch('book_genres', queryset=BookGenre.objects.select_related('genre'))
)
```

### Демонстрация оптимизации в views.py

```python
def demo_features(request):
    # ===== ДЕМОНСТРАЦИЯ select_related() =====
    # select_related для оптимизации запросов ForeignKey и OneToOne
    books_with_author = Book.objects.select_related('author')  # ForeignKey
    books_with_cover = Book.objects.select_related('cover')    # OneToOneField
    
    # Комбинированный select_related
    books_optimized = Book.objects.select_related('author', 'cover')
    
    # select_related в отзывах
    reviews_with_user_and_book = Review.objects.select_related('user', 'book', 'book__author')
    
    # ===== ДЕМОНСТРАЦИЯ prefetch_related() =====
    # prefetch_related для ManyToMany
    books_with_genres = Book.objects.prefetch_related('genres')
    
    # prefetch_related с дополнительными select_related в Prefetch
    books_complex_prefetch = Book.objects.select_related('author').prefetch_related(
        Prefetch('reviews', queryset=Review.objects.select_related('user')),
        Prefetch('book_genres', queryset=BookGenre.objects.select_related('genre'))
    )
```

## 3. Сериализаторы с SerializerMethodField

### BookSerializer с методами

```python
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
    discounted_price = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    total_sales = serializers.SerializerMethodField()
    favorites_count = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()
    publication_year = serializers.SerializerMethodField()

    def get_cover_image(self, obj: Book) -> str:
        """Возвращает URL обложки книги."""
        if hasattr(obj, 'cover') and obj.cover and obj.cover.image:
            return obj.cover.image.url
        return ''

    def get_discounted_price(self, obj: Book) -> Decimal:
        """Возвращает цену книги с учетом скидки."""
        return obj.current_price

    def get_is_favorite(self, obj: Book) -> bool:
        """Проверяет, находится ли книга в избранном у текущего пользователя."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorites.filter(user=request.user).exists()
        return False

    def get_avg_rating(self, obj: Book) -> float:
        """Возвращает средний рейтинг книги."""
        return obj.reviews.aggregate(avg=Avg('rating'))['avg'] or 0.0
```

### Передача параметров через контекст

```python
# В BookViewSet
def get_serializer_context(self) -> dict:
    """Добавляет дополнительные данные в контекст сериализатора."""
    context = super().get_serializer_context()
    context['request'] = self.request
    return context
```

## 4. Примеры использования аннотаций

### Аннотации в моделях

```python
class BookManager(models.Manager):
    def get_bestsellers(self):
        """Получить книги с наибольшим количеством продаж"""
        return self.annotate(
            total_sales=Sum('cartitem__quantity')
        ).order_by('-total_sales')

    def get_highly_rated(self):
        """Получить книги с высоким рейтингом"""
        return self.annotate(
            avg_rating=Avg('reviews__rating')
        ).filter(avg_rating__gte=4.0)
```

### Аннотации в сериализаторах

```python
class AuthorSerializer(serializers.ModelSerializer):
    books_count = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()

    def get_books_count(self, obj: Author) -> int:
        """Возвращает количество книг автора."""
        return obj.books.count()

    def get_avg_rating(self, obj: Author) -> float:
        """Возвращает средний рейтинг книг автора."""
        avg_rating = obj.books.aggregate(avg_rating=Avg('reviews__rating'))['avg_rating']
        return round(avg_rating, 2) if avg_rating else 0.0
```

### Аннотации в представлениях

```python
def cart_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Детальный просмотр корзины с аннотациями."""
    cart = get_object_or_404(Cart, pk=pk)
    
    # Аннотация для подсчета общего количества товаров
    cart_items = cart.cart_items.all().select_related('book', 'book__author').annotate(
        total_price=F('book__price') * F('quantity')
    )
    
    # Аннотация для общей стоимости корзины
    cart_total = cart_items.aggregate(
        total=Sum(F('book__price') * F('quantity'))
    )['total'] or Decimal('0')
```

## 5. Filterset с Django Filter

### BookFilter

```python
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
```

### ReviewFilter

```python
class ReviewFilter(django_filters.FilterSet):
    rating = django_filters.NumberFilter()
    min_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    max_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='lte')
    comment = django_filters.CharFilter(lookup_expr='icontains')
    created_after = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Review
        fields = {
            'rating': ['exact', 'gte', 'lte'],
            'comment': ['icontains'],
            'created_at': ['gte', 'lte'],
        }
```

### Использование в ViewSet

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

## 6. Тестирование приложения

### Примеры тестов (10+ тестов)

```python
class BookStoreTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpass')
        self.author = Author.objects.create(name='Автор')
        self.genre = Genre.objects.create(name='Жанр')
        self.book = Book.objects.create(title='Книга', author=self.author, price=100, stock_quantity=10)
        self.book.genres.add(self.genre)
        self.client = Client()
        self.api_client = APIClient()

    def test_book_model_str(self):
        """Тест строкового представления модели Book"""
        self.assertEqual(str(self.book), 'Книга')

    def test_book_list_view(self):
        """Тест отображения списка книг"""
        response = self.client.get(reverse('books:book-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'books/book_list.html')

    def test_book_detail_view(self):
        """Тест отображения детальной страницы книги"""
        response = self.client.get(reverse('books:book-detail', kwargs={'pk': self.book.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'books/book_detail.html')

    def test_create_book(self):
        """Тест создания новой книги"""
        book = Book.objects.create(title='Новая книга', author=self.author, price=200, stock_quantity=5)
        self.assertEqual(Book.objects.count(), 2)
        self.assertEqual(book.title, 'Новая книга')

    def test_filter_books_by_author(self):
        """Тест фильтрации книг по автору"""
        books = Book.objects.filter(author=self.author)
        self.assertIn(self.book, books)

    def test_add_to_cart(self):
        """Тест добавления товара в корзину"""
        self.client.login(username='testuser', password='testpass')
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, book=self.book, quantity=2)
        self.assertEqual(cart.cart_items.count(), 1)
        self.assertEqual(cart.cart_items.first().quantity, 2)

    def test_cart_stock_validation(self):
        """Тест валидации количества товара на складе"""
        cart = Cart.objects.create(user=self.user)
        item = CartItem.objects.create(cart=cart, book=self.book, quantity=20)
        self.assertFalse(self.book.check_availability(quantity=20))

    def test_review_creation(self):
        """Тест создания отзыва"""
        review = Review.objects.create(user=self.user, book=self.book, rating=5, comment='Отлично!')
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(review.rating, 5)

    def test_user_registration(self):
        """Тест регистрации нового пользователя"""
        response = self.client.post(reverse('register'), {
            'username': 'newuser', 
            'password1': 'testpass123', 
            'password2': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(get_user_model().objects.filter(username='newuser').exists())

    def test_user_login(self):
        """Тест входа пользователя"""
        response = self.client.post(reverse('login'), {
            'username': 'testuser', 
            'password': 'testpass'
        })
        self.assertEqual(response.status_code, 302)

    def test_api_books_list_unauthenticated(self):
        """Тест API списка книг без аутентификации"""
        response = self.api_client.get(reverse('books:book-list'))
        self.assertEqual(response.status_code, 200)

    def test_api_books_list_authenticated(self):
        """Тест API списка книг с аутентификацией"""
        self.api_client.force_authenticate(user=self.user)
        response = self.api_client.get(reverse('books:book-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_book_discount_logic(self):
        """Тест логики скидок на книги"""
        discounted_book = Book.objects.create(
            title='Книга со скидкой',
            author=self.author,
            price=Decimal('100.00'),
            has_discount=True,
            discount_percent=20,
            stock_quantity=5
        )
        self.assertFalse(discounted_book.is_discount_active)
        self.assertEqual(discounted_book.current_price, Decimal('100.00'))

    def test_cart_total_price_calculation(self):
        """Тест расчета общей стоимости корзины"""
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, book=self.book, quantity=2)
        second_book = Book.objects.create(title='Вторая книга', author=self.author, price=50, stock_quantity=5)
        CartItem.objects.create(cart=cart, book=second_book, quantity=1)
        
        expected_total = Decimal('250.00')
        self.assertEqual(cart.get_total_price(), expected_total)

    def test_book_availability_check(self):
        """Тест проверки доступности книги"""
        self.assertTrue(self.book.check_availability(quantity=5))
        self.assertFalse(self.book.check_availability(quantity=15))
        self.book.status = 'out_of_stock'
        self.book.save()
        self.assertFalse(self.book.check_availability(quantity=1))

    def test_api_book_fields(self):
        """Тест структуры данных книги в API"""
        response = self.api_client.get('/api/books/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        book = response.data['results'][0]
        expected_fields = [
            'id', 'title', 'author', 'genres', 'description', 'price',
            'status', 'has_discount', 'discount_percent', 'discounted_price',
            'is_favorite', 'avg_rating', 'reviews_count', 'total_sales',
            'favorites_count', 'final_price'
        ]
        for field in expected_fields:
            self.assertIn(field, book)

    def test_review_rating_validation(self):
        """Тест валидации рейтинга отзыва"""
        valid_review = Review.objects.create(user=self.user, book=self.book, rating=4, comment='Хорошо')
        self.assertEqual(valid_review.rating, 4)
        self.assertGreaterEqual(valid_review.rating, 1)
        self.assertLessEqual(valid_review.rating, 5)
```

## 7. Докстринги и типизация

### Примеры методов с докстрингами и типизацией

#### 1. Метод clean() в модели Book

```python
def clean(self) -> None:
    """
    Валидация полей модели.
    
    Проверяет корректность данных перед сохранением:
    - Валидирует скидки (процент, даты)
    - Проверяет соответствие статуса и количества на складе
    
    Raises:
        ValidationError: Если данные некорректны
    """
    super().clean()
    
    # Валидация скидок
    if self.has_discount:
        if self.discount_percent == 0:
            raise ValidationError(_('Процент скидки должен быть больше 0'))
        if self.discount_percent > 100:
            raise ValidationError(_('Процент скидки не может быть больше 100'))
        if self.discount_start and self.discount_end and self.discount_start >= self.discount_end:
            raise ValidationError(_('Дата начала скидки должна быть раньше даты окончания'))
    
    # Валидация статуса и количества
    if self.status == 'available' and self.stock_quantity == 0:
        raise ValidationError(_('Книга не может быть в наличии при нулевом количестве'))
    if self.status == 'out_of_stock' and self.stock_quantity > 0:
        raise ValidationError(_('Книга не может быть отсутствовать при наличии на складе'))
```

#### 2. Метод check_availability() в модели Book

```python
def check_availability(self, quantity: int = 1) -> bool:
    """
    Проверяет доступность книги на складе в указанном количестве.
    
    Args:
        quantity (int): Требуемое количество. По умолчанию 1.
        
    Returns:
        bool: True, если книга доступна в указанном количестве, иначе False.
        
    Examples:
        >>> book = Book.objects.get(id=1)
        >>> book.check_availability(5)
        True
        >>> book.check_availability(20)
        False
    """
    if self.status != 'available':
        return False
    return self.stock_quantity >= quantity
```

#### 3. Метод get_total_price() в модели Cart

```python
def get_total_price(self) -> Decimal:
    """
    Вычисляет общую стоимость корзины с учетом скидок.
    
    Использует аннотации Django для оптимизации запросов:
    - Sum() для подсчета общей суммы
    - ExpressionWrapper для вычисления стоимости каждого товара
    - F() для обращения к полям связанных моделей
    
    Returns:
        Decimal: Общая стоимость корзины. Возвращает 0, если корзина пуста.
        
    Examples:
        >>> cart = Cart.objects.get(id=1)
        >>> cart.get_total_price()
        Decimal('1250.00')
    """
    return self.cart_items.aggregate(
        total=Sum(
            ExpressionWrapper(
                F('book__price') * F('quantity'),
                output_field=DecimalField()
            )
        )
    )['total'] or Decimal('0')
```

## Демонстрация возможностей

### Как протестировать валидацию:

1. **Валидация скидок**: Попробуйте создать книгу со скидкой 0% или больше 100%
2. **Валидация статуса**: Создайте книгу со статусом "В наличии" и количеством 0
3. **Валидация адреса**: Попробуйте создать заказ с некорректным адресом

### Как протестировать оптимизацию запросов:

1. Откройте Django Debug Toolbar
2. Перейдите на страницу списка книг
3. Сравните количество запросов с и без select_related/prefetch_related

### Как протестировать фильтрацию:

1. Перейдите на страницу книг
2. Используйте фильтры по цене, автору, жанру
3. Проверьте URL параметры в адресной строке

### Как запустить тесты:

```bash
python manage.py test books.tests
```

### Как протестировать API:

1. Откройте Django REST Framework browsable API
2. Перейдите по адресу `/api/books/`
3. Используйте фильтры и поиск
4. Проверьте структуру ответов 