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
        return str(self.username)

    def get_absolute_url(self):
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

    def get_absolute_url(self):
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

    def get_absolute_url(self):
        return reverse('genre-detail', kwargs={'pk': self.pk})

class Book(models.Model):
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

    def get_absolute_url(self):
        return reverse('books:book-detail', kwargs={'pk': self.pk})

    @property
    def is_discount_active(self):
        if not self.has_discount or self.discount_percent == 0:
            return False
        now = timezone.now()
        if self.discount_start and self.discount_end:
            return self.discount_start <= now <= self.discount_end
        return False

    @property
    def current_price(self):
        if self.is_discount_active:
            discount_amount = self.price * (Decimal(str(self.discount_percent)) / Decimal('100'))
            return self.price - discount_amount
        return self.price

    @property
    def discount_amount(self):
        if self.is_discount_active:
            return self.price - self.current_price
        return Decimal('0')

    def generate_pdf(self):
        """Генерирует PDF-документ с информацией о книге"""
        template = get_template('books/book_pdf.html')
        html_string = template.render({
            'book': self,
            'author': self.author,
            'genres': list(self.genres.all()),
            'current_price': self.current_price,
        })
        
        try:
            # Создаем PDF
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{self.title}.pdf"'
            
            # Генерируем PDF
            HTML(string=html_string).write_pdf(response)
            return response
                
        except Exception as e:
            return HttpResponse(f'Ошибка при создании PDF: {str(e)}', status=500)

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

    def get_absolute_url(self):
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

    def get_absolute_url(self):
        return reverse('cart-detail', kwargs={'pk': self.pk})

    def get_total_price(self):
        """Вычисляет общую стоимость корзины с учетом скидок"""
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
