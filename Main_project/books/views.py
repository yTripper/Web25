from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.http import HttpResponse, JsonResponse, HttpRequest
from .models import Book, Author, Genre, Review, Cart, CartItem, User, Role, UserRole, BookGenre, Cover, Order, OrderItem, Favorite
from .forms import BookForm, ReviewForm, OrderForm, UserRegistrationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum, Prefetch, Case, When, Value, CharField, IntegerField
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import BookSerializer, AuthorSerializer, GenreSerializer, ReviewSerializer, OrderSerializer, UserSerializer
from .filters import BookFilter, ReviewFilter
from .permissions import IsOrderOwnerOrAdmin
from typing import Any, Dict, List
from django.db.models import QuerySet
from datetime import timedelta
import json
from django.utils.decorators import method_decorator
from django.views import View

# Импорты из utils
from .utils import search_books, get_book_data, check_book_availability

def index(request):
    """
    Представление для главной страницы с виджетами.
    """
    now = timezone.now()

    # QuerySet для виджета "Новинки"
    try:
        new_books = Book.objects.get_new_books()[:8]
    except AttributeError:
        thirty_days_ago = now - timedelta(days=30)
        new_books = Book.objects.filter(created_at__gte=thirty_days_ago).order_by('-created_at')[:8]

    # QuerySet для виджета "Популярные книги"
    popular_books = Book.objects.annotate(
        avg_rating=Avg('reviews__rating')
    ).exclude(avg_rating__isnull=True).order_by('-avg_rating')[:8]

    # QuerySet для виджета "Книги со скидкой"
    discounted_books = Book.objects.filter(
        has_discount=True,
        discount_start__lte=now,
        discount_end__gte=now,
        discount_percent__gt=0
    ).order_by('-discount_percent')[:8]

    # Отладочная информация
    print(f"DEBUG: User: {request.user}")
    print(f"DEBUG: User authenticated: {request.user.is_authenticated}")
    print(f"DEBUG: User username: {getattr(request.user, 'username', 'No username')}")

    context = {
        'new_books': new_books,
        'popular_books': popular_books,
        'discounted_books': discounted_books,
        'debug_user': request.user,  # Добавляем для отладки
        'debug_authenticated': request.user.is_authenticated,
    }
    return render(request, 'books/index.html', context)

def book_list(request):
    """
    Представление для отображения списка книг с фильтрацией, аннотациями и избранным
    """
    books = Book.objects.all().select_related('author').prefetch_related('genres')
    
    # Применяем фильтры
    book_filter = BookFilter(request.GET, queryset=books)
    
    # Добавляем аннотации
    books = book_filter.qs.annotate(
        # Средний рейтинг книги
        avg_rating=Avg('reviews__rating'),
        # Количество отзывов
        reviews_count=Count('reviews'),
        # Количество продаж (через корзину)
        total_sales=Sum('order_items__quantity'),
        # Количество добавлений в избранное
        favorites_count=Count('favorites'),
        # Категория цены
        price_category=Case(
            When(price__gte=2000, then=Value('Дорогая')),
            When(price__gte=1000, then=Value('Средняя')),
            default=Value('Дешевая'),
            output_field=CharField(max_length=20)
        ),
        # Уровень популярности
        popularity_level=Case(
            When(avg_rating__gte=4.5, then=Value(3)),
            When(avg_rating__gte=3.5, then=Value(2)),
            default=Value(1),
            output_field=IntegerField()
        )
    )
    
    context = {
        'books': books,
        'filter': book_filter,
    }
    return render(request, 'books/book_list.html', context)

def book_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Отображает детальную информацию о книге, включая отзывы.

    Args:
        request (HttpRequest): Объект запроса.
        pk (int): Первичный ключ книги.

    Returns:
        HttpResponse: Страница с детальной информацией о книге.
    """
    book = get_object_or_404(
        Book.objects.prefetch_related('reviews__user', 'genres'),
        pk=pk
    )
    reviews = book.reviews.all()
    return render(request, 'books/book_detail.html', {'book': book, 'reviews': reviews})

@login_required
def book_create(request: HttpRequest) -> HttpResponse:
    """
    Создание новой книги с использованием timezone.

    Args:
        request (HttpRequest): Объект запроса.

    Returns:
        HttpResponse: Форма для создания книги или редирект на страницу книги.
    """
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)  # Добавляем request.FILES для обработки файлов
        if form.is_valid():
            book = form.save(commit=False)
            book.created_at = timezone.now()
            book.save()
            form.save_m2m()
            messages.success(request, f'Книга "{book.title}" успешно создана!')
            return redirect('books:book-detail', pk=book.pk)  # Редирект на детальную страницу
    else:
        form = BookForm()
    return render(request, 'books/book_form.html', {'form': form, 'action': 'Создать'})

@login_required
def book_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Редактирование книги с использованием timezone.

    Args:
        request (HttpRequest): Объект запроса.
        pk (int): Первичный ключ книги.

    Returns:
        HttpResponse: Форма для редактирования книги или редирект.
    """
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)  # Добавляем request.FILES
        if form.is_valid():
            book = form.save(commit=False)
            book.updated_at = timezone.now()
            book.save()
            form.save_m2m()
            messages.success(request, f'Книга "{book.title}" успешно обновлена!')
            return redirect('books:book-detail', pk=book.pk)  # Редирект на детальную страницу
    else:
        form = BookForm(instance=book)
    return render(request, 'books/book_form.html', {'form': form, 'action': 'Редактировать'})

@login_required
def book_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Удаление книги.

    Args:
        request (HttpRequest): Объект запроса.
        pk (int): Первичный ключ книги.

    Returns:
        HttpResponse: Страница подтверждения удаления или редирект.
    """
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        title = book.title
        book.delete()
        messages.success(request, f'Книга "{title}" успешно удалена!')
        return redirect('books:book-list')  # Редирект на список книг
    return render(request, 'books/book_confirm_delete.html', {'book': book})

def author_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Отображает детальную информацию об авторе и его книгах.

    Args:
        request (HttpRequest): Объект запроса.
        pk (int): Первичный ключ автора.

    Returns:
        HttpResponse: Страница с информацией об авторе.
    """
    author = get_object_or_404(Author, pk=pk)
    
    # Пример использования related_name: author.books
    books = author.books.all().order_by('-created_at')
    
    # Фильтрация книг автора
    available_books = books.filter(status='available')
    discounted_books = books.filter(has_discount=True)
    
    # Исключение книг без отзывов
    books_with_reviews = books.exclude(reviews__isnull=True)
    
    # Агрегация статистики автора
    author_stats = books.aggregate(
        total_books=Count('id'),
        avg_price=Avg('price'),
        max_price=Max('price'),
        min_price=Min('price'),
        total_reviews=Count('reviews'),
        avg_rating=Avg('reviews__rating'),
        books_with_discount=Count('id', filter=Q(has_discount=True))
    )
    
    # Аннотация книг с дополнительной информацией
    annotated_books = books.annotate(
        reviews_count=Count('reviews'),
        avg_book_rating=Avg('reviews__rating'),
        latest_review_date=Max('reviews__created_at')
    ).order_by('-reviews_count')

    context = {
        'author': author,
        'books': annotated_books,
        'available_books': available_books,
        'discounted_books': discounted_books,
        'books_with_reviews': books_with_reviews,
        'author_stats': author_stats,
    }
    return render(request, 'books/author_detail.html', context)

def cart_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Отображает содержимое корзины пользователя.

    Args:
        request (HttpRequest): Объект запроса.
        pk (int): Первичный ключ корзины.

    Returns:
        HttpResponse: Страница с содержимым корзины.
    """
    cart = get_object_or_404(Cart, pk=pk)
    
    # Пример использования related_name: cart.cart_items
    items = cart.cart_items.all().select_related('book', 'book__author')
    
    # Фильтрация элементов корзины
    expensive_items = items.filter(book__price__gte=1000)
    discounted_items = items.filter(book__has_discount=True)
    
    # Исключение товаров, которых нет в наличии
    available_items = items.exclude(book__status='out_of_stock')
    
    # Агрегация для подсчета общей стоимости и статистики
    cart_stats = items.aggregate(
        total_price=Sum(F('quantity') * F('book__price')),
        total_items=Sum('quantity'),
        unique_books=Count('book', distinct=True),
        avg_book_price=Avg('book__price'),
        max_quantity=Max('quantity')
    )
    
    # Аннотация элементов с дополнительной информацией
    annotated_items = items.annotate(
        item_total=F('quantity') * F('book__price'),
        book_rating=Avg('book__reviews__rating')
    ).order_by('-item_total')

    context = {
        'cart': cart,
        'items': annotated_items,
        'expensive_items': expensive_items,
        'discounted_items': discounted_items,
        'available_items': available_items,
        'cart_stats': cart_stats,
    }
    return render(request, 'books/cart_detail.html', context)

def discount_books(request: HttpRequest) -> HttpResponse:
    """
    Отображает список всех книг со скидками.

    Args:
        request (HttpRequest): Объект запроса.

    Returns:
        HttpResponse: Страница с книгами со скидкой.
    """
    now = timezone.now()
    
    # Фильтрация активных скидок
    discounted_books = Book.objects.filter(
        has_discount=True,
        discount_start__lte=now,
        discount_end__gte=now,
        discount_percent__gt=0
    ).select_related('author')
    
    # Исключение книг с маленькой скидкой
    significant_discounts = discounted_books.exclude(discount_percent__lt=10)
    
    # Сортировка по размеру скидки
    discounted_books = discounted_books.order_by('-discount_percent', '-discount_start')
    
    # Аннотация с расчетом экономии
    discounted_books = discounted_books.annotate(
        savings=F('price') * F('discount_percent') / 100,
        time_left=F('discount_end') - Value(now)
    )

    context = {
        'discounted_books': discounted_books,
        'significant_discounts': significant_discounts,
        'current_time': now,
    }
    return render(request, 'books/discount_books.html', context)

def demo_features(request):
    """
    Демонстрация различных функций Django ORM
    """
    # ===== ДЕМОНСТРАЦИЯ ManyToManyField с through =====
    
    # 1. Работа с User roles через through модель
    users_with_roles = User.objects.prefetch_related(
        'user_roles__role'  # Prefetch через промежуточную модель
    ).annotate(
        role_count=Count('user_roles')
    )
    
    # Получаем роли пользователя через ManyToManyField с through
    sample_user = User.objects.first()
    user_roles_through_m2m = []
    user_roles_through_intermediate = []
    
    if sample_user:
        # Через ManyToManyField
        user_roles_through_m2m = sample_user.roles.all()
        # Через промежуточную модель
        user_roles_through_intermediate = UserRole.objects.filter(user=sample_user).select_related('role')
    
    # 2. Работа с Book genres через through модель
    books_with_genres = Book.objects.prefetch_related(
        'book_genres__genre'  # Prefetch через BookGenre
    ).annotate(
        genre_count=Count('genres')
    )
    
    sample_book = Book.objects.first()
    book_genres_through_m2m = []
    book_genres_through_intermediate = []
    
    if sample_book:
        # Через ManyToManyField
        book_genres_through_m2m = sample_book.genres.all()
        # Через промежуточную модель
        book_genres_through_intermediate = BookGenre.objects.filter(book=sample_book).select_related('genre')

    # ===== ДЕМОНСТРАЦИЯ select_related() =====
    
    # 3. select_related для оптимизации запросов ForeignKey и OneToOne
    books_with_author = Book.objects.select_related('author')  # ForeignKey
    books_with_cover = Book.objects.select_related('cover')    # OneToOneField
    
    # Комбинированный select_related
    books_optimized = Book.objects.select_related('author', 'cover')
    
    # select_related в отзывах
    reviews_with_user_and_book = Review.objects.select_related('user', 'book', 'book__author')
    
    # ===== ДЕМОНСТРАЦИЯ prefetch_related() =====
    
    # 4. prefetch_related для оптимизации ManyToMany и обратных ForeignKey связей
    books_with_reviews = Book.objects.prefetch_related('reviews')
    books_with_genres_prefetch = Book.objects.prefetch_related('genres')
    
    # Комбинированный prefetch_related
    books_full_prefetch = Book.objects.prefetch_related('reviews', 'genres', 'book_genres')
    
    # prefetch_related с дополнительными select_related в Prefetch
    from django.db.models import Prefetch
    books_complex_prefetch = Book.objects.select_related('author').prefetch_related(
        Prefetch('reviews', queryset=Review.objects.select_related('user')),
        Prefetch('book_genres', queryset=BookGenre.objects.select_related('genre'))
    )
    
    # Авторы с их книгами
    authors_with_books = Author.objects.prefetch_related('books')
    
    # ===== КОМБИНИРОВАННЫЕ ПРИМЕРЫ =====
    
    # 5. Сложная оптимизация запросов
    optimized_books = Book.objects.select_related(
        'author',  # select_related для ForeignKey
        'cover'    # select_related для OneToOneField
    ).prefetch_related(
        Prefetch('reviews', queryset=Review.objects.select_related('user')),  # prefetch с select_related
        Prefetch('genres'),  # prefetch для ManyToMany
        Prefetch('book_genres', queryset=BookGenre.objects.select_related('genre'))  # prefetch через through
    ).annotate(
        reviews_count=Count('reviews'),
        avg_rating=Avg('reviews__rating'),
        genre_count=Count('genres')
    )

    # ===== ОСТАЛЬНЫЕ ДЕМОНСТРАЦИИ =====
    
    # 6. Демонстрация filter() с __
    books_by_author = Book.objects.filter(author__name__icontains='Пушкин')
    books_by_price = Book.objects.filter(price__gte=1000)

    # 7. Демонстрация exclude()
    available_books = Book.objects.exclude(status='out_of_stock')
    new_books = Book.objects.exclude(
        created_at__lt=timezone.now() - timedelta(days=365)
    )

    # 8. Демонстрация order_by()
    books_by_price_asc = Book.objects.order_by('price')
    books_by_price_desc = Book.objects.order_by('-price')
    books_by_author_title = Book.objects.order_by('author__name', 'title')

    # 9. Демонстрация собственного менеджера
    new_books_manager = Book.objects.get_new_books()
    bestsellers = Book.objects.get_bestsellers()
    highly_rated = Book.objects.get_highly_rated()

    # 10. Демонстрация get_absolute_url
    sample_book = Book.objects.first()
    book_url = sample_book.get_absolute_url() if sample_book else None

    # 11. Демонстрация агрегации и аннотации
    books_with_stats = Book.objects.annotate(
        reviews_count=Count('reviews'),
        avg_rating=Avg('reviews__rating'),
        total_sales=Sum('cartitem__quantity'),
        price_category=Case(
            When(price__gte=2000, then=Value('Дорогая')),
            When(price__gte=1000, then=Value('Средняя')),
            default=Value('Дешевая'),
            output_field=CharField(max_length=20)
        )
    )

    context = {
        # ManyToManyField через through
        'users_with_roles': users_with_roles,
        'user_roles_through_m2m': user_roles_through_m2m,
        'user_roles_through_intermediate': user_roles_through_intermediate,
        'books_with_genres': books_with_genres,
        'book_genres_through_m2m': book_genres_through_m2m,
        'book_genres_through_intermediate': book_genres_through_intermediate,
        'sample_user': sample_user,
        'sample_book': sample_book,
        
        # select_related
        'books_with_author': books_with_author,
        'books_with_cover': books_with_cover,
        'books_optimized': books_optimized,
        'reviews_with_user_and_book': reviews_with_user_and_book,
        
        # prefetch_related
        'books_with_reviews': books_with_reviews,
        'books_with_genres_prefetch': books_with_genres_prefetch,
        'books_full_prefetch': books_full_prefetch,
        'books_complex_prefetch': books_complex_prefetch,
        'authors_with_books': authors_with_books,
        'optimized_books': optimized_books,
        
        # Остальные демонстрации
        'books_by_author': books_by_author,
        'books_by_price': books_by_price,
        'available_books': available_books,
        'new_books': new_books,
        'books_by_price_asc': books_by_price_asc,
        'books_by_price_desc': books_by_price_desc,
        'books_by_author_title': books_by_author_title,
        'new_books_manager': new_books_manager,
        'bestsellers': bestsellers,
        'highly_rated': highly_rated,
        'book_url': book_url,
        'books_with_stats': books_with_stats,
    }
    return render(request, 'books/demo_features.html', context)

def orm_demonstration_view(request):
    query = request.GET.get('q') # Получаем поисковый запрос из GET-параметров
    search_results = []
    if query:
        search_results = search_books(query) # Вызываем функцию поиска

    book_data = get_book_data() # Получаем данные через values/values_list
    book_stats = check_book_availability() # Получаем данные через count/exists

    context = {
        'query': query,
        'search_results': search_results,
        'book_data': book_data,
        'book_stats': book_stats,
    }
    return render(request, 'books/orm_demonstration.html', context)

def book_search(request: HttpRequest) -> HttpResponse:
    """
    Представление для поиска книг по названию.

    Args:
        request (HttpRequest): Объект запроса.

    Returns:
        HttpResponse: Страница с результатами поиска.
    """
    query = request.GET.get('query', '')
    if query:
        books = Book.objects.filter(title__icontains=query).select_related('author')
    else:
        books = Book.objects.none()
    
    context = {
        'books': books,
        'query': query,
    }
    return render(request, 'books/book_list.html', context)

@login_required
def add_to_cart(request: HttpRequest, book_id: int) -> HttpResponse:
    """
    Добавление книги в корзину с проверкой наличия.

    Args:
        request (HttpRequest): Объект запроса.
        book_id (int): ID книги.

    Returns:
        HttpResponse: Редирект на страницу корзины или детали книги.
    """
    book = get_object_or_404(Book, id=book_id)
    quantity = int(request.POST.get('quantity', 1))
    
    # Проверка наличия книги
    is_available, message = book.check_stock(quantity)
    if not is_available:
        messages.error(request, message)
        return redirect('books:book-detail', pk=book_id)
    
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, book=book)
    
    if not created:
        # Проверяем, не превысит ли новое количество доступное количество
        new_quantity = cart_item.quantity + quantity
        is_available, message = book.check_stock(new_quantity)
        if not is_available:
            messages.error(request, message)
            return redirect('books:book-detail', pk=book_id)
        cart_item.quantity = new_quantity
    else:
        cart_item.quantity = quantity
    
    cart_item.save()
    messages.success(request, f'Книга "{book.title}" добавлена в корзину')
    return redirect('books:cart')

@login_required
def order_list(request: HttpRequest) -> HttpResponse:
    """
    Список заказов с оптимизацией запросов.

    Args:
        request (HttpRequest): Объект запроса.

    Returns:
        HttpResponse: Страница со списком заказов.
    """
    if request.user.is_staff:
        # Для администраторов показываем все заказы
        orders = Order.objects.select_related('user').prefetch_related(
            Prefetch('order_items', queryset=OrderItem.objects.select_related('book'))
        ).order_by('-created_at')
    else:
        # Для обычных пользователей только их заказы
        orders = Order.objects.select_related('user').prefetch_related(
            Prefetch('order_items', queryset=OrderItem.objects.select_related('book'))
        ).filter(user=request.user).order_by('-created_at')
    
    context = {
        'orders': orders,
    }
    return render(request, 'books/order_list.html', context)

@login_required
def user_reviews(request: HttpRequest) -> HttpResponse:
    """
    Список отзывов пользователя с оптимизацией запросов.

    Args:
        request (HttpRequest): Объект запроса.

    Returns:
        HttpResponse: Страница со списком отзывов пользователя.
    """
    reviews = Review.objects.select_related(
        'book', 'book__author'
    ).filter(user=request.user).order_by('-created_at')
    
    context = {
        'reviews': reviews,
    }
    return render(request, 'books/user_reviews.html', context)

@login_required
def book_reviews(request: HttpRequest, book_id: int) -> HttpResponse:
    """
    Список отзывов на книгу с оптимизацией запросов.

    Args:
        request (HttpRequest): Объект запроса.
        book_id (int): ID книги.

    Returns:
        HttpResponse: Страница со списком отзывов на книгу.
    """
    book = get_object_or_404(Book.objects.select_related('author'), id=book_id)
    reviews = Review.objects.select_related('user').filter(book=book).order_by('-created_at')
    
    context = {
        'book': book,
        'reviews': reviews,
    }
    return render(request, 'books/book_reviews.html', context)

def register(request: HttpRequest) -> HttpResponse:
    """
    Регистрация нового пользователя.
    """
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            buyer_role = Role.objects.get(name='Покупатель')
            UserRole.objects.create(user=user, role=buyer_role)
            login(request, user)
            return redirect('books:book-list')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

class BookViewSet(viewsets.ModelViewSet):
    """API для работы с книгами"""
    queryset = Book.objects.all().select_related('author').prefetch_related('genres')
    serializer_class = BookSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BookFilter
    search_fields = ['title', 'author__name', 'description']
    ordering_fields = ['price', 'created_at', 'title']
    ordering = ['-created_at']
    
    def update(self, request, *args, **kwargs):
        """Переопределяем метод update для логирования"""
        print(f"DEBUG: BookViewSet.update called with method: {request.method}")
        print(f"DEBUG: Request data: {request.data}")
        print(f"DEBUG: Request FILES: {request.FILES}")
        print(f"DEBUG: Request content type: {request.content_type}")
        print(f"DEBUG: Request headers: {dict(request.headers)}")
        print(f"DEBUG: Request body: {request.body}")
        
        try:
            result = super().update(request, *args, **kwargs)
            print(f"DEBUG: Update successful: {result}")
            return result
        except Exception as e:
            print(f"DEBUG: Update failed with error: {e}")
            print(f"DEBUG: Error type: {type(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            
            # Если это ошибка валидации, логируем детали
            if hasattr(e, 'detail'):
                print(f"DEBUG: Validation error details: {e.detail}")
            
            raise
    
    def get_queryset(self) -> QuerySet:
        """
        Возвращает QuerySet с аннотациями для API.

        Returns:
            QuerySet: QuerySet с дополнительными полями.
        """
        queryset = super().get_queryset()
        queryset = queryset.annotate(
            avg_rating=Avg('reviews__rating'),
            reviews_count=Count('reviews'),
            total_sales=Sum('order_items__quantity'),
            favorites_count=Count('favorites')
        )
        return queryset

    def get_serializer_context(self) -> dict:
        """
        Возвращает контекст для сериализатора.

        Returns:
            dict: Контекст с информацией об избранных книгах.
        """
        context = super().get_serializer_context()
        if self.request.user.is_authenticated:
            favorites_books = self.request.user.favorites.values_list('book_id', flat=True)
            context['favorites_books'] = list(favorites_books)
        return context

    def partial_update(self, request, *args, **kwargs):
        """Переопределяем метод partial_update для логирования"""
        print(f"DEBUG: BookViewSet.partial_update called with method: {request.method}")
        print(f"DEBUG: Request data: {request.data}")
        print(f"DEBUG: Request FILES: {request.FILES}")
        print(f"DEBUG: Request content type: {request.content_type}")
        print(f"DEBUG: Request headers: {dict(request.headers)}")
        print(f"DEBUG: Request body: {request.body}")
        
        try:
            result = super().partial_update(request, *args, **kwargs)
            print(f"DEBUG: Partial update successful: {result}")
            return result
        except Exception as e:
            print(f"DEBUG: Partial update failed with error: {e}")
            print(f"DEBUG: Error type: {type(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            
            # Если это ошибка валидации, логируем детали
            if hasattr(e, 'detail'):
                print(f"DEBUG: Validation error details: {e.detail}")
            
            raise

class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
    """API для работы с авторами (только чтение)"""
    queryset = Author.objects.all().prefetch_related('books')
    serializer_class = AuthorSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'bio']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

class GenreViewSet(viewsets.ReadOnlyModelViewSet):
    """API для работы с жанрами (только чтение)"""
    queryset = Genre.objects.all().prefetch_related('books')
    serializer_class = GenreSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

class ReviewViewSet(viewsets.ModelViewSet):
    """API для работы с отзывами"""
    queryset = Review.objects.all().select_related('user', 'book')
    serializer_class = ReviewSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = ReviewFilter
    search_fields = ['comment']
    ordering = ['-created_at']
    
    def get_queryset(self) -> QuerySet:
        """
        Возвращает QuerySet отзывов с возможностью фильтрации по книге.

        Returns:
            QuerySet: QuerySet отзывов с фильтрацией.
        """
        queryset = super().get_queryset()
        
        # Фильтрация по книге через параметр запроса
        book_id = self.request.query_params.get('book', None)
        if book_id is not None:
            queryset = queryset.filter(book_id=book_id)
        
        return queryset
    
    def perform_create(self, serializer: ReviewSerializer) -> None:
        """
        Создает новый отзыв с привязкой к текущему пользователю.

        Args:
            serializer (ReviewSerializer): Сериализатор отзыва.
        """
        serializer.save(user=self.request.user)

class OrderViewSet(viewsets.ModelViewSet):
    """API для работы с заказами"""
    queryset = Order.objects.all().select_related('user').prefetch_related('order_items__book')
    serializer_class = OrderSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_method']
    ordering = ['-created_at']
    permission_classes = [permissions.IsAuthenticated, IsOrderOwnerOrAdmin]
    
    def get_queryset(self) -> QuerySet:
        """
        Возвращает QuerySet заказов с учетом прав доступа.

        Returns:
            QuerySet: QuerySet заказов для текущего пользователя.
        """
        queryset = super().get_queryset()
        if not self.request.user.is_staff and not self.request.user.roles.filter(name='admin').exists():
            # Обычные пользователи видят только свои заказы
            queryset = queryset.filter(user=self.request.user)
        return queryset
    
    def perform_create(self, serializer: OrderSerializer) -> None:
        """
        Создает новый заказ с привязкой к текущему пользователю.

        Args:
            serializer (OrderSerializer): Сериализатор заказа.
        """
        serializer.save(user=self.request.user)

@login_required
def order_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Детальный просмотр заказа с проверкой прав доступа.

    Args:
        request (HttpRequest): Объект запроса.
        pk (int): Первичный ключ заказа.

    Returns:
        HttpResponse: Страница с деталями заказа или редирект.
    """
    order = get_object_or_404(Order, pk=pk)
    
    # Проверка прав доступа
    if not request.user.is_staff and not request.user.roles.filter(name='admin').exists():
        if order.user != request.user:
            messages.error(request, 'У вас нет прав для просмотра этого заказа')
            return redirect('order-list')
    
    # Оптимизация запросов
    order = Order.objects.select_related('user').prefetch_related(
        Prefetch('order_items', queryset=OrderItem.objects.select_related('book'))
    ).get(pk=pk)
    
    context = {
        'order': order,
    }
    return render(request, 'books/order_detail.html', context)

# API endpoints для аутентификации
@csrf_exempt
def api_login(request):
    if request.method == 'POST':
        try:
            print(f"DEBUG: Request body: {request.body}")
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            print(f"DEBUG: Username: {username}")
            print(f"DEBUG: Password provided: {'yes' if password else 'no'}")
            
            user = authenticate(request, username=username, password=password)
            
            print(f"DEBUG: Authenticated user: {user}")
            
            if user is not None:
                login(request, user)
                
                # Безопасно получаем роли пользователя
                try:
                    roles = list(user.roles.values('name')) if hasattr(user, 'roles') else []
                except:
                    roles = []
                
                print(f"DEBUG: User roles: {roles}")
                
                return JsonResponse({
                    'success': True,
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'is_staff': user.is_staff,
                        'roles': roles
                    }
                })
            else:
                print(f"DEBUG: Authentication failed for username: {username}")
                return JsonResponse({
                    'success': False,
                    'error': 'Неверные учетные данные'
                }, status=400)
                
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON decode error: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Неверный формат данных'
            }, status=400)
        except Exception as e:
            print(f"DEBUG: Exception in api_login: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Метод не поддерживается'}, status=405)

@csrf_exempt
def api_register(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            
            print(f"DEBUG: Registering user: {username}, email: {email}")
            
            if User.objects.filter(username=username).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Пользователь с таким именем уже существует'
                }, status=400)
            
            if User.objects.filter(email=email).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Пользователь с таким email уже существует'
                }, status=400)
            
            # Создаем пользователя с правильным хешированием пароля
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            print(f"DEBUG: User created: {user}, is_active: {user.is_active}")
            
            # Назначаем роль "user" новому пользователю
            try:
                user_role = Role.objects.get(name='user')
                UserRole.objects.create(user=user, role=user_role)
                print(f"DEBUG: Role 'user' assigned to {user}")
            except Role.DoesNotExist:
                # Если роль "user" не существует, создаем её
                user_role = Role.objects.create(name='user')
                UserRole.objects.create(user=user, role=user_role)
                print(f"DEBUG: Role 'user' created and assigned to {user}")
            
            # Сразу логиним пользователя
            login(request, user)
            
            return JsonResponse({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_staff': user.is_staff,
                    'roles': list(user.roles.values('name')) if hasattr(user, 'roles') else []
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Неверный формат данных'
            }, status=400)
        except Exception as e:
            print(f"DEBUG: Exception in api_register: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Метод не поддерживается'}, status=405)

@csrf_exempt
def api_logout(request):
    if request.method == 'POST':
        logout(request)
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Метод не поддерживается'}, status=405)

@csrf_exempt
def api_get_current_user(request):
    """API для получения информации о текущем пользователе"""
    if request.user.is_authenticated:
        # Безопасно получаем роли пользователя
        try:
            roles = list(request.user.roles.values('name')) if hasattr(request.user, 'roles') else []
        except:
            roles = []
        
        return JsonResponse({
            'success': True,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'is_staff': request.user.is_staff,
                'roles': roles
            }
        })
    else:
        return JsonResponse({
            'success': False,
            'error': 'Пользователь не авторизован'
        }, status=401)

def api_filter_demo(request: HttpRequest) -> HttpResponse:
    """
    Демонстрация работы фильтров в API.
    
    Args:
        request (HttpRequest): Объект запроса.
        
    Returns:
        HttpResponse: Страница с примерами использования фильтров.
    """
    # Получаем все доступные авторы и жанры для демонстрации
    authors = Author.objects.all().order_by('name')
    genres = Genre.objects.all().order_by('name')
    
    # Примеры URL для фильтрации
    filter_examples = [
        {
            'name': 'Поиск по названию',
            'url': '/api/books/?title=книга',
            'description': 'Найти книги, в названии которых содержится "книга"'
        },
        {
            'name': 'Фильтр по автору',
            'url': '/api/books/?author=1',
            'description': 'Найти книги конкретного автора (ID=1)'
        },
        {
            'name': 'Фильтр по жанрам',
            'url': '/api/books/?genres=1,2',
            'description': 'Найти книги жанров с ID 1 и 2'
        },
        {
            'name': 'Диапазон цен',
            'url': '/api/books/?min_price=100&max_price=500',
            'description': 'Найти книги в ценовом диапазоне 100-500 рублей'
        },
        {
            'name': 'Книги со скидкой',
            'url': '/api/books/?has_discount=true',
            'description': 'Найти только книги со скидкой'
        },
        {
            'name': 'Книги в наличии',
            'url': '/api/books/?status=available',
            'description': 'Найти только книги в наличии'
        },
        {
            'name': 'Комбинированный фильтр',
            'url': '/api/books/?title=книга&min_price=100&has_discount=true',
            'description': 'Комбинация нескольких фильтров'
        },
        {
            'name': 'Поиск с сортировкой',
            'url': '/api/books/?title=книга&ordering=price',
            'description': 'Поиск с сортировкой по цене'
        },
        {
            'name': 'Фильтр отзывов по рейтингу',
            'url': '/api/reviews/?min_rating=4',
            'description': 'Найти отзывы с рейтингом 4 и выше'
        },
        {
            'name': 'Отзывы к конкретной книге',
            'url': '/api/reviews/?book=1',
            'description': 'Найти все отзывы к книге с ID=1'
        }
    ]
    
    context = {
        'authors': authors,
        'genres': genres,
        'filter_examples': filter_examples,
    }
    
    return render(request, 'books/api_filter_demo.html', context)
