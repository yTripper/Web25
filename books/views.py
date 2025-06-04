from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from .models import Book, Author, Genre, Review, Cart, CartItem, User, Role, UserRole, BookGenre, Cover
from .forms import BookForm
from django.db.models import Avg, Prefetch
from django.template.loader import render_to_string
from django.conf import settings
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import logout
from django.contrib import messages
from django.db.models import Q, Count, Sum, F, ExpressionWrapper, DecimalField, Max, Min, Case, When, Value, IntegerField, CharField
from django.utils import timezone
from datetime import timedelta

# Импорты из utils
from .utils import search_books, get_book_data, check_book_availability

def index(request):
    """
    Представление для главной страницы с виджетами.
    """
    now = timezone.now()

    # QuerySet для виджета "Новинки"
    # Используем пользовательский менеджер, если он есть и корректно работает,
    # иначе - прямой QuerySet
    try:
        # Попробуем использовать менеджер
        new_books = Book.objects.get_new_books()[:10] # Получаем до 10 новинок
    except AttributeError:
        # Если менеджера нет или метод не найден, используем прямой QuerySet
        thirty_days_ago = now - timedelta(days=30)
        new_books = Book.objects.filter(created_at__gte=thirty_days_ago).order_by('-created_at')[:10]

    # QuerySet для виджета "Популярные книги" (по среднему рейтингу, например)
    # Используем annotate для расчета среднего рейтинга и order_by
    popular_books = Book.objects.annotate(
        avg_rating=Avg('reviews__rating')
    ).exclude(avg_rating__isnull=True).order_by('-avg_rating')[:10] # Исключаем книги без отзывов и берем топ-10

    # QuerySet для виджета "Книги со скидкой"
    discounted_books = Book.objects.filter(
        has_discount=True,
        discount_start__lte=now,
        discount_end__gte=now,
        discount_percent__gt=0
    ).order_by('-discount_percent')[:10] # Берем до 10 книг с самой большой скидкой

    context = {
        'new_books': new_books,
        'popular_books': popular_books,
        'discounted_books': discounted_books,
    }
    return render(request, 'books/index.html', context)

def book_list(request):
    """
    Список книг с демонстрацией всех требуемых методов
    
    Примеры использования timezone:
    1. Фильтрация новых книг (созданных за последние 30 дней)
    2. Проверка активных скидок по текущему времени
    3. Сортировка по давности создания
    """
    
    # ПРИМЕР 1: Использование timezone для фильтрации новых книг
    thirty_days_ago = timezone.now() - timedelta(days=30)
    seven_days_ago = timezone.now() - timedelta(days=7)
    
    # Базовый queryset с select_related для оптимизации
    books = Book.objects.select_related('author').prefetch_related(
        Prefetch('reviews', queryset=Review.objects.select_related('user'))
    )

    # ПРИМЕР filter() с __ (обращение к связанной таблице)
    if request.GET.get('author'):
        books = books.filter(author__name__icontains=request.GET.get('author'))
    
    if request.GET.get('genre'):
        books = books.filter(genres__name__icontains=request.GET.get('genre'))
    
    # ПРИМЕР filter() с __ (метод поля модели)
    if request.GET.get('min_price'):
        books = books.filter(price__gte=request.GET.get('min_price'))
    
    if request.GET.get('max_price'):
        books = books.filter(price__lte=request.GET.get('max_price'))

    # ПРИМЕР 2: Использование timezone для активных скидок
    now = timezone.now()
    if request.GET.get('only_discounted'):
        books = books.filter(
            has_discount=True,
            discount_start__lte=now,
            discount_end__gte=now,
            discount_percent__gt=0
        )

    # ПРИМЕР exclude() - исключаем книги
    if request.GET.get('exclude_out_of_stock'):
        books = books.exclude(status='out_of_stock')
    
    if request.GET.get('exclude_old'):
        # Исключаем книги старше года
        one_year_ago = timezone.now() - timedelta(days=365)
        books = books.exclude(created_at__lt=one_year_ago)

    # ПРИМЕР order_by() - различные варианты сортировки
    sort_by = request.GET.get('sort', '-created_at')
    if sort_by == 'price_asc':
        books = books.order_by('price')
    elif sort_by == 'price_desc':
        books = books.order_by('-price')
    elif sort_by == 'author':
        books = books.order_by('author__name', 'title')
    elif sort_by == 'rating':
        books = books.order_by('-reviews__rating')
    else:
        books = books.order_by(sort_by)

    # ПРИМЕР агрегации и аннотации (3 примера)
    books = books.annotate(
        # 1. Подсчет количества отзывов
        reviews_count=Count('reviews'),
        # 2. Средний рейтинг
        avg_rating=Avg('reviews__rating'),
        # 3. Условная аннотация для популярности (числовые значения)
        popularity_level=Case(
            When(reviews__rating__gte=4.5, then=Value(3)),  # Высокая = 3
            When(reviews__rating__gte=3.5, then=Value(2)),  # Средняя = 2
            default=Value(1),  # Низкая = 1
            output_field=IntegerField()
        ),
        # 4. Дополнительная аннотация с текстовыми значениями
        price_category=Case(
            When(price__gte=2000, then=Value('Дорогая')),
            When(price__gte=1000, then=Value('Средняя')),
            default=Value('Дешевая'),
            output_field=CharField(max_length=20)
        )
    )

    # Использование собственного менеджера
    new_books = Book.objects.get_new_books()
    bestsellers = Book.objects.get_bestsellers()
    highly_rated = Book.objects.get_highly_rated()

    # ПРИМЕР 3: Использование timezone для статистики по времени
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    
    # Статистика по времени создания
    time_stats = Book.objects.aggregate(
        total_books=Count('id'),
        books_this_week=Count('id', filter=Q(created_at__date__gte=week_start)),
        books_last_30_days=Count('id', filter=Q(created_at__gte=thirty_days_ago)),
        newest_book_date=Max('created_at'),
        oldest_book_date=Min('created_at')
    )

    context = {
        'books': books,
        'new_books': new_books,
        'bestsellers': bestsellers,
        'highly_rated': highly_rated,
        'time_stats': time_stats,
        'current_time': timezone.now(),  # Для отображения текущего времени
    }
    return render(request, 'books/book_list.html', context)

def book_detail(request, pk):
    """
    Детальная информация о книге с демонстрацией related_name и агрегации
    """
    book = get_object_or_404(Book, pk=pk)
    
    # Пример использования related_name: book.reviews
    reviews = book.reviews.all().select_related('user').order_by('-created_at')
    
    # Агрегация для статистики отзывов
    review_stats = book.reviews.aggregate(
        avg_rating=Avg('rating'),
        max_rating=Max('rating'),
        min_rating=Min('rating'),
        total_reviews=Count('id')
    )
    
    # Проверка активности скидки с использованием timezone
    now = timezone.now()
    is_discount_active = (
        book.has_discount and 
        book.discount_start and 
        book.discount_end and
        book.discount_start <= now <= book.discount_end
    )
    
    context = {
        'book': book,
        'reviews': reviews,
        'review_stats': review_stats,
        'is_discounted': is_discount_active,
        'current_price': book.current_price,
        'discount_amount': book.discount_amount,
        'time_until_discount_end': book.discount_end - now if is_discount_active else None,
    }
    return render(request, 'books/book_detail.html', context)

@login_required
def book_create(request):
    """Создание новой книги с использованием timezone"""
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
def book_edit(request, pk):
    """Редактирование книги с использованием timezone"""
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
def book_delete(request, pk):
    """Удаление книги"""
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        title = book.title
        book.delete()
        messages.success(request, f'Книга "{title}" успешно удалена!')
        return redirect('books:book-list')  # Редирект на список книг
    return render(request, 'books/book_confirm_delete.html', {'book': book})

def author_detail(request, pk):
    """
    Детальная информация об авторе с демонстрацией related_name и агрегации
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

def cart_detail(request, pk):
    """
    Детальная информация о корзине с демонстрацией related_name и агрегации
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

def discount_books(request):
    """
    Представление для книг со скидками с использованием timezone
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

def book_search(request):
    """
    Представление для поиска книг по названию
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
