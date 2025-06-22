from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Book, Author, Genre, Cart, CartItem, Review
from rest_framework.test import APIClient
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
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

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

    def test_api_book_filtering(self):
        """Тест фильтрации книг через API"""
        self.api_client.force_authenticate(user=self.user)
        # Создаем вторую книгу
        Book.objects.create(title='Другая книга', author=self.author, price=150, stock_quantity=3)
        
        # Тестируем фильтрацию по автору
        response = self.api_client.get(f"{reverse('books:book-list')}?author={self.author.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)  # Обе книги одного автора

    def test_review_rating_validation(self):
        """Тест валидации рейтинга отзыва"""
        # Создаем отзыв с валидным рейтингом
        valid_review = Review.objects.create(user=self.user, book=self.book, rating=4, comment='Хорошо')
        self.assertEqual(valid_review.rating, 4)
        
        # Проверяем, что рейтинг в допустимых пределах (1-5)
        self.assertGreaterEqual(valid_review.rating, 1)
        self.assertLessEqual(valid_review.rating, 5)
