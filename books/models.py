from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse
from django.db.models import Avg, Count, Sum, F, ExpressionWrapper, DecimalField
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.conf import settings
from decimal import Decimal
import os
from io import BytesIO
from weasyprint import HTML, CSS
from django.template.loader import get_template
from django.core.exceptions import ValidationError
from typing import Any

class BookManager(models.Manager):
    def get_new_books(self):
        """Получить книги, добавленные за последние 30 дней"""
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        return self.filter(created_at__gte=thirty_days_ago)

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

class User(AbstractUser):
    roles = models.ManyToManyField('Role', through='UserRole', related_name='users', verbose_name=_('Роли'))
    
    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')
        ordering = ['-date_joined']

    def __str__(self) -> str:
        """
        Возвращает строковое представление пользователя.
        :return: Имя пользователя
        """
        return str(self.username)

    def get_absolute_url(self) -> str:
        """
        Возвращает абсолютный URL для пользователя.

        Returns:
            str: Абсолютный URL.
        """
        return reverse('user-detail', kwargs={'pk': self.pk})

class Author(models.Model):
    name = models.CharField(_('Имя'), max_length=255)
    bio = models.TextField(_('Биография'), blank=True, null=True)
    birth_date = models.DateField(_('Дата рождения'), blank=True, null=True)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('Автор')
        verbose_name_plural = _('Авторы')
        ordering = ['name']

    def __str__(self) -> str:
        return str(self.name)

    def get_absolute_url(self) -> str:
        """
        Возвращает абсолютный URL для автора.

        Returns:
            str: Абсолютный URL.
        """
        return reverse('author-detail', kwargs={'pk': self.pk})

class Genre(models.Model):
    name = models.CharField(_('Название'), max_length=100)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)

    class Meta:
        verbose_name = _('Жанр')
        verbose_name_plural = _('Жанры')
        ordering = ['name']

    def __str__(self) -> str:
        return str(self.name)

    def get_absolute_url(self) -> str:
        """
        Возвращает абсолютный URL для жанра.

        Returns:
            str: Абсолютный URL.
        """
        return reverse('genre-detail', kwargs={'pk': self.pk})

class Book(models.Model):
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name=_('Количество на складе'))

    STATUS_CHOICES = [
        ('available', 'В наличии'),
        ('out_of_stock', 'Нет в наличии'),
        ('pre_order', 'Предзаказ'),
    ]

    title = models.CharField(max_length=200, verbose_name=_('Название'))
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books', verbose_name=_('Автор'))
    genres = models.ManyToManyField(Genre, through='BookGenre', related_name='books', verbose_name=_('Жанры'))
    description = models.TextField(verbose_name=_('Описание'), null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('Цена'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available', verbose_name=_('Статус'))
    has_discount = models.BooleanField(default=False, verbose_name=_('Активна ли скидка'))
    discount_percent = models.PositiveIntegerField(default=0, verbose_name=_('Процент скидки'))
    discount_start = models.DateTimeField(null=True, blank=True, verbose_name=_('Начало скидки'))
    discount_end = models.DateTimeField(null=True, blank=True, verbose_name=_('Конец скидки'))
    ebook_file = models.FileField(upload_to='ebooks/', null=True, blank=True, verbose_name=_('Электронная версия книги'))
    book_url = models.URLField(max_length=200, null=True, blank=True, help_text='URL страницы книги на сайте издательства')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата обновления'))
    published_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Дата публикации'))
    objects = BookManager()

    class Meta:
        verbose_name = _('Книга')
        verbose_name_plural = _('Книги')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return str(self.title)

    def get_absolute_url(self) -> str:
        """
        Возвращает абсолютный URL для книги.

        Returns:
            str: Абсолютный URL.
        """
        return reverse('books:book-detail', kwargs={'pk': self.pk})

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

    def check_availability(self, quantity: int = 1) -> bool:
        """
        Проверяет доступность книги на складе в указанном количестве.

        Args:
            quantity (int): Требуемое количество.

        Returns:
            bool: True, если книга доступна, иначе False.
        """
        if self.status != 'available':
            return False
        return self.stock_quantity >= quantity

    @property
    def is_discount_active(self) -> bool:
        """
        Проверяет, активна ли скидка в данный момент.

        Returns:
            bool: True, если скидка активна.
        """
        if not self.has_discount or self.discount_percent == 0:
            return False
        now = timezone.now()
        if self.discount_start and self.discount_end:
            return self.discount_start <= now <= self.discount_end
        return False

    @property
    def current_price(self) -> Decimal:
        """
        Возвращает текущую цену с учетом скидки.

        Returns:
            Decimal: Текущая цена.
        """
        if self.is_discount_active:
            discount_amount = self.price * (Decimal(str(self.discount_percent)) / Decimal('100'))
            return self.price - discount_amount
        return self.price

    @property
    def discount_amount(self) -> Decimal:
        """
        Возвращает сумму скидки.

        Returns:
            Decimal: Сумма скидки.
        """
        if self.is_discount_active:
            return self.price - self.current_price
        return Decimal('0')

    def generate_pdf(self) -> Any:
        """
        Генерация PDF-файла с информацией о книге.

        Returns:
            HttpResponse or None: PDF-файл в виде HttpResponse или None в случае ошибки.
        """
        try:
            # Создаем HTML-шаблон
            html_string = render_to_string('books/pdf_template.html', {
            'book': self,
                'reviews': self.reviews.all().select_related('user'),
                'genres': self.genres.all(),
        })
        
            # Генерируем PDF
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{self.title}.pdf"'
        
            # Конвертируем HTML в PDF
            HTML(string=html_string).write_pdf(response)
            return response
            
        except Exception as e:
            print(f"Ошибка при генерации PDF: {str(e)}")
            return None

class Cover(models.Model):
    book = models.OneToOneField(Book, on_delete=models.CASCADE, verbose_name=_('Книга'),
                              related_name='cover')
    image = models.ImageField(upload_to='covers/', verbose_name=_('Обложка'), null=True, blank=True)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)

    class Meta:
        verbose_name = _('Обложка')
        verbose_name_plural = _('Обложки')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"Обложка для {str(self.book)}"

class BookGenre(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name=_('Книга'),
                           related_name='book_genres')
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE, verbose_name=_('Жанр'),
                            related_name='book_genres')
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)

    class Meta:
        verbose_name = _('Жанр книги')
        verbose_name_plural = _('Жанры книг')
        unique_together = ('book', 'genre')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{str(self.book)} - {str(self.genre)}"

class Role(models.Model):
    USER = 'user'
    MODERATOR = 'moderator'
    ADMIN = 'admin'
    
    ROLE_CHOICES = [
        (USER, _('Пользователь')),
        (MODERATOR, _('Модератор')),
        (ADMIN, _('Администратор')),
    ]

    name = models.CharField(_('Название'), max_length=50, unique=True, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)

    class Meta:
        verbose_name = _('Роль')
        verbose_name_plural = _('Роли')
        ordering = ['name']

    def __str__(self) -> str:
        return str(self.name)

class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Пользователь'),
                           related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name=_('Роль'),
                           related_name='user_roles')
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)

    class Meta:
        verbose_name = _('Роль пользователя')
        verbose_name_plural = _('Роли пользователей')
        unique_together = ('user', 'role')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{str(self.user)} - {str(self.role)}"

class Review(models.Model):
    RATING_CHOICES = [
        (1, _('1 - Ужасно')),
        (2, _('2 - Плохо')),
        (3, _('3 - Нормально')),
        (4, _('4 - Хорошо')),
        (5, _('5 - Отлично')),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Пользователь'),
                           related_name='reviews')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name=_('Книга'),
                           related_name='reviews')
    rating = models.IntegerField(_('Оценка'), choices=RATING_CHOICES)
    comment = models.TextField(_('Комментарий'), blank=True, null=True)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('Отзыв')
        verbose_name_plural = _('Отзывы')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"Отзыв от {str(self.user)} на {str(self.book)}"

    def get_absolute_url(self) -> str:
        """
        Возвращает абсолютный URL для отзыва.

        Returns:
            str: Абсолютный URL.
        """
        return reverse('review-detail', kwargs={'pk': self.pk})

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_('Пользователь'),
                              related_name='cart')
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('Корзина')
        verbose_name_plural = _('Корзины')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"Корзина {str(self.user)}"

    def get_absolute_url(self) -> str:
        """
        Возвращает абсолютный URL для корзины.

        Returns:
            str: Абсолютный URL.
        """
        return reverse('cart-detail', kwargs={'pk': self.pk})

    def get_total_price(self) -> Decimal:
        """
        Вычисляет общую стоимость корзины с учетом скидок.

        Returns:
            Decimal: Общая стоимость.
        """
        return self.cart_items.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('book__price') * F('quantity'),
                    output_field=DecimalField()
                )
            )
        )['total'] or Decimal('0')

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, verbose_name=_('Корзина'),
                           related_name='cart_items')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name=_('Книга'))
    quantity = models.PositiveIntegerField(_('Количество'), default=1)
    created_at = models.DateTimeField(_('Дата добавления'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('Элемент корзины')
        verbose_name_plural = _('Элементы корзины')
        unique_together = ('cart', 'book')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{str(self.book)} в корзине {str(self.cart)}"

    def get_absolute_url(self):
        return reverse('cart-item-detail', kwargs={'pk': self.pk})

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'В обработке'),
        ('processing', 'Обрабатывается'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменен'),
    ]

    PAYMENT_CHOICES = [
        ('card', 'Банковская карта'),
        ('cash', 'Наличные при получении'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', verbose_name=_('Пользователь'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name=_('Статус'))
    shipping_address = models.TextField(verbose_name=_('Адрес доставки'))
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, verbose_name=_('Способ оплаты'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('Общая сумма'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата обновления'))

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

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items', verbose_name=_('Заказ'))
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='order_items', verbose_name=_('Книга'))
    quantity = models.PositiveIntegerField(verbose_name=_('Количество'))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('Цена'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))

    class Meta:
        verbose_name = _('Элемент заказа')
        verbose_name_plural = _('Элементы заказа')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{str(self.book)} в заказе {str(self.order)}"

    def save(self, *args, **kwargs):
        # Обновляем количество книг на складе
        if not self.pk:  # Если это новый объект
            self.book.stock_quantity -= self.quantity
            self.book.save()
        super().save(*args, **kwargs)

class Favorite(models.Model):
    """Модель для избранных книг пользователя"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='favorites')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Избранная книга'
        verbose_name_plural = 'Избранные книги'
        unique_together = ('user', 'book')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"
