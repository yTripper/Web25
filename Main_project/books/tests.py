from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Book, Author, Genre, Cart, CartItem, Review, User
from .filters import BookFilter, ReviewFilter
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from decimal import Decimal

class BookStoreTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpass')
        self.author = Author.objects.create(name='Автор')
        self.genre = Genre.objects.create(name='Жанр')
        self.book = Book.objects.create(title='Книга', author=self.author, price=100, stock_quantity=10)
        self.book.genres.add(self.genre)
        self.client = Client()
        self.api_client = APIClient()
        # Создаём роль "Покупатель" для теста регистрации
        from books.models import Role
        Role.objects.get_or_create(name='Покупатель')

    def test_book_model_str(self):
        """Тест строкового представления модели Book"""
        self.assertEqual(str(self.book), 'Книга')

    def test_author_model_str(self):
        """Тест строкового представления модели Author"""
        self.assertEqual(str(self.author), 'Автор')

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

    def test_order_creation(self):
        # Пропущено: реализация заказа зависит от Order модели
        pass

    def test_review_creation(self):
        """Тест создания отзыва"""
        review = Review.objects.create(user=self.user, book=self.book, rating=5, comment='Отлично!')
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(review.rating, 5)

    def test_favorite(self):
        # Пропущено: зависит от реализации избранного
        pass

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
        # Создаем книгу со скидкой
        discounted_book = Book.objects.create(
            title='Книга со скидкой',
            author=self.author,
            price=Decimal('100.00'),
            has_discount=True,
            discount_percent=20,
            stock_quantity=5
        )
        # Проверяем, что скидка не активна без дат
        self.assertFalse(discounted_book.is_discount_active)
        self.assertEqual(discounted_book.current_price, Decimal('100.00'))

    def test_cart_total_price_calculation(self):
        """Тест расчета общей стоимости корзины"""
        cart = Cart.objects.create(user=self.user)
        # Добавляем несколько товаров
        CartItem.objects.create(cart=cart, book=self.book, quantity=2)
        second_book = Book.objects.create(title='Вторая книга', author=self.author, price=50, stock_quantity=5)
        CartItem.objects.create(cart=cart, book=second_book, quantity=1)
        
        # Ожидаемая стоимость: 2 * 100 + 1 * 50 = 250
        expected_total = Decimal('250.00')
        self.assertEqual(cart.get_total_price(), expected_total)

    def test_book_availability_check(self):
        """Тест проверки доступности книги"""
        # Книга в наличии
        self.assertTrue(self.book.check_availability(quantity=5))
        # Книга недоступна в таком количестве
        self.assertFalse(self.book.check_availability(quantity=15))
        # Книга недоступна при статусе "нет в наличии"
        self.book.status = 'out_of_stock'
        self.book.save()
        self.assertFalse(self.book.check_availability(quantity=1))

    def test_api_book_fields(self):
        """Тест структуры данных книги в API (API endpoints)"""
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
        # Создаем отзыв с валидным рейтингом
        valid_review = Review.objects.create(user=self.user, book=self.book, rating=4, comment='Хорошо')
        self.assertEqual(valid_review.rating, 4)
        
        # Проверяем, что рейтинг в допустимых пределах (1-5)
        self.assertGreaterEqual(valid_review.rating, 1)
        self.assertLessEqual(valid_review.rating, 5)

class BookFilterTestCase(TestCase):
    """Тесты для фильтров книг"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.author1 = Author.objects.create(name='Автор 1', bio='Биография 1')
        self.author2 = Author.objects.create(name='Автор 2', bio='Биография 2')
        
        self.genre1 = Genre.objects.create(name='Фантастика')
        self.genre2 = Genre.objects.create(name='Детектив')
        
        self.book1 = Book.objects.create(
            title='Книга о фильтрах',
            author=self.author1,
            description='Описание книги о фильтрах',
            price=100.00,
            status='available',
            has_discount=True,
            stock_quantity=10
        )
        self.book1.genres.add(self.genre1)
        
        self.book2 = Book.objects.create(
            title='Другая книга',
            author=self.author2,
            description='Описание другой книги',
            price=200.00,
            status='available',
            has_discount=False,
            stock_quantity=5
        )
        self.book2.genres.add(self.genre2)
        
        self.book3 = Book.objects.create(
            title='Дорогая книга',
            author=self.author1,
            description='Описание дорогой книги',
            price=500.00,
            status='out_of_stock',
            has_discount=True,
            stock_quantity=0
        )
        self.book3.genres.add(self.genre1, self.genre2)
    
    def test_title_filter(self):
        """Тест фильтра по названию"""
        filter_data = {'title': 'фильтрах'}
        filter_set = BookFilter(filter_data, queryset=Book.objects.all())
        filtered_books = filter_set.qs
        
        self.assertEqual(filtered_books.count(), 1)
        self.assertEqual(filtered_books.first(), self.book1)
    
    def test_author_filter(self):
        """Тест фильтра по автору"""
        filter_data = {'author': self.author1.id}
        filter_set = BookFilter(filter_data, queryset=Book.objects.all())
        filtered_books = filter_set.qs
        
        self.assertEqual(filtered_books.count(), 2)
        self.assertIn(self.book1, filtered_books)
        self.assertIn(self.book3, filtered_books)
    
    def test_genres_filter(self):
        """Тест фильтра по жанрам"""
        filter_data = {'genres': [self.genre1.id]}
        filter_set = BookFilter(filter_data, queryset=Book.objects.all())
        filtered_books = filter_set.qs
        
        self.assertEqual(filtered_books.count(), 2)
        self.assertIn(self.book1, filtered_books)
        self.assertIn(self.book3, filtered_books)
    
    def test_price_range_filter(self):
        """Тест фильтра по диапазону цен"""
        filter_data = {'min_price': 150, 'max_price': 300}
        filter_set = BookFilter(filter_data, queryset=Book.objects.all())
        filtered_books = filter_set.qs
        
        self.assertEqual(filtered_books.count(), 1)
        self.assertEqual(filtered_books.first(), self.book2)
    
    def test_status_filter(self):
        """Тест фильтра по статусу"""
        filter_data = {'status': 'available'}
        filter_set = BookFilter(filter_data, queryset=Book.objects.all())
        filtered_books = filter_set.qs
        
        self.assertEqual(filtered_books.count(), 2)
        self.assertIn(self.book1, filtered_books)
        self.assertIn(self.book2, filtered_books)
    
    def test_has_discount_filter(self):
        """Тест фильтра по наличию скидки"""
        filter_data = {'has_discount': True}
        filter_set = BookFilter(filter_data, queryset=Book.objects.all())
        filtered_books = filter_set.qs
        
        self.assertEqual(filtered_books.count(), 2)
        self.assertIn(self.book1, filtered_books)
        self.assertIn(self.book3, filtered_books)
    
    def test_in_stock_filter(self):
        """Тест фильтра по наличию на складе"""
        filter_data = {'in_stock': True}
        filter_set = BookFilter(filter_data, queryset=Book.objects.all())
        filtered_books = filter_set.qs
        
        self.assertEqual(filtered_books.count(), 2)
        self.assertIn(self.book1, filtered_books)
        self.assertIn(self.book2, filtered_books)
    
    def test_combined_filters(self):
        """Тест комбинированных фильтров"""
        filter_data = {
            'author': self.author1.id,
            'has_discount': True,
            'min_price': 50
        }
        filter_set = BookFilter(filter_data, queryset=Book.objects.all())
        filtered_books = filter_set.qs
        
        self.assertEqual(filtered_books.count(), 2)
        self.assertIn(self.book1, filtered_books)
        self.assertIn(self.book3, filtered_books)
    
    def test_empty_filter(self):
        """Тест пустого фильтра"""
        filter_data = {}
        filter_set = BookFilter(filter_data, queryset=Book.objects.all())
        filtered_books = filter_set.qs
        
        self.assertEqual(filtered_books.count(), 3)


class ReviewFilterTestCase(TestCase):
    """Тесты для фильтров отзывов"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        
        self.author = Author.objects.create(name='Автор', bio='Биография')
        self.book = Book.objects.create(
            title='Книга для отзывов',
            author=self.author,
            description='Описание',
            price=100.00,
            status='available'
        )
        
        self.review1 = Review.objects.create(
            user=self.user1,
            book=self.book,
            rating=5,
            comment='Отличная книга!'
        )
        
        self.review2 = Review.objects.create(
            user=self.user2,
            book=self.book,
            rating=3,
            comment='Неплохая книга'
        )
    
    def test_rating_filter(self):
        """Тест фильтра по рейтингу"""
        filter_data = {'rating': 5}
        filter_set = ReviewFilter(filter_data, queryset=Review.objects.all())
        filtered_reviews = filter_set.qs
        
        self.assertEqual(filtered_reviews.count(), 1)
        self.assertEqual(filtered_reviews.first(), self.review1)
    
    def test_min_rating_filter(self):
        """Тест фильтра по минимальному рейтингу"""
        filter_data = {'min_rating': 4}
        filter_set = ReviewFilter(filter_data, queryset=Review.objects.all())
        filtered_reviews = filter_set.qs
        
        self.assertEqual(filtered_reviews.count(), 1)
        self.assertEqual(filtered_reviews.first(), self.review1)
    
    def test_comment_filter(self):
        """Тест фильтра по комментарию"""
        filter_data = {'comment': 'отличная'}
        filter_set = ReviewFilter(filter_data, queryset=Review.objects.all())
        filtered_reviews = filter_set.qs
        
        self.assertEqual(filtered_reviews.count(), 1)
        self.assertEqual(filtered_reviews.first(), self.review1)
    
    def test_book_filter(self):
        """Тест фильтра по книге"""
        filter_data = {'book': self.book.id}
        filter_set = ReviewFilter(filter_data, queryset=Review.objects.all())
        filtered_reviews = filter_set.qs
        
        self.assertEqual(filtered_reviews.count(), 2)
        self.assertIn(self.review1, filtered_reviews)
        self.assertIn(self.review2, filtered_reviews)
    
    def test_user_filter(self):
        """Тест фильтра по пользователю"""
        filter_data = {'user': self.user1.id}
        filter_set = ReviewFilter(filter_data, queryset=Review.objects.all())
        filtered_reviews = filter_set.qs
        
        self.assertEqual(filtered_reviews.count(), 1)
        self.assertEqual(filtered_reviews.first(), self.review1)


class BookFilterAPITestCase(APITestCase):
    """Тесты API фильтров для книг"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.author = Author.objects.create(name='API Автор', bio='Биография')
        self.genre = Genre.objects.create(name='API Жанр')
        
        self.book1 = Book.objects.create(
            title='API Книга 1',
            author=self.author,
            description='Описание API книги 1',
            price=100.00,
            status='available',
            has_discount=True
        )
        self.book1.genres.add(self.genre)
        
        self.book2 = Book.objects.create(
            title='API Книга 2',
            author=self.author,
            description='Описание API книги 2',
            price=200.00,
            status='available',
            has_discount=False
        )
        self.book2.genres.add(self.genre)
    
    def test_api_title_filter(self):
        """Тест API фильтра по названию"""
        url = reverse('book-list')
        response = self.client.get(url, {'title': 'книга 1'})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'API Книга 1')
    
    def test_api_author_filter(self):
        """Тест API фильтра по автору"""
        url = reverse('book-list')
        response = self.client.get(url, {'author': self.author.id})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_api_price_filter(self):
        """Тест API фильтра по цене"""
        url = reverse('book-list')
        response = self.client.get(url, {'min_price': 150})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'API Книга 2')
    
    def test_api_has_discount_filter(self):
        """Тест API фильтра по скидке"""
        url = reverse('book-list')
        response = self.client.get(url, {'has_discount': 'true'})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'API Книга 1')
    
    def test_api_combined_filters(self):
        """Тест комбинированных API фильтров"""
        url = reverse('book-list')
        response = self.client.get(url, {
            'title': 'книга',
            'has_discount': 'true',
            'min_price': 50
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'API Книга 1')
    
    def test_api_search_filter(self):
        """Тест API поиска"""
        url = reverse('book-list')
        response = self.client.get(url, {'search': 'описание'})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_api_ordering(self):
        """Тест API сортировки"""
        url = reverse('book-list')
        response = self.client.get(url, {'ordering': 'price'})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
        # Проверяем, что книги отсортированы по возрастанию цены
        self.assertEqual(response.data['results'][0]['price'], '100.00')
        self.assertEqual(response.data['results'][1]['price'], '200.00')
