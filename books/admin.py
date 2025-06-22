from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.db import models
from .models import (
    User, Author, Genre, Book, Cover, BookGenre,
    Role, UserRole, Review, Cart, CartItem
)
from django.urls import reverse
from django.urls import path
from django.http import HttpResponse
from django.template.loader import render_to_string, get_template
from django.conf import settings
import os
from .forms import BookForm
from django import forms
from django.utils import timezone
import tempfile
from io import BytesIO
from weasyprint import HTML, CSS
from typing import Any, List
from django.db.models import QuerySet

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_roles', 'date_joined')
    list_display_links = ('username', 'email')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    date_hierarchy = 'date_joined'
    readonly_fields = ('date_joined', 'last_login')
    filter_horizontal = ('groups', 'user_permissions')

    @admin.display(description=_('Роли'))
    def get_roles(self, obj: User) -> str:
        """
        Возвращает список ролей пользователя.

        Args:
            obj (User): Экземпляр пользователя.

        Returns:
            str: Список ролей через запятую или "Нет ролей".
        """
        roles = [user_role.role.name for user_role in obj.user_roles.all()]
        if roles:
            return ", ".join(roles)
        return _('Нет ролей')

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'birth_date', 'get_books_count', 'get_books_list', 'created_at')
    list_display_links = ('name',)
    search_fields = ('name', 'bio')
    list_filter = ('birth_date', 'created_at')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'get_books_count')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'bio', 'birth_date')
        }),
        (_('Системная информация'), {
            'fields': ('created_at', 'updated_at', 'get_books_count'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description=_('Количество книг'))
    def get_books_count(self, obj: Author) -> int:
        """
        Возвращает количество книг автора.

        Args:
            obj (Author): Экземпляр автора.

        Returns:
            int: Количество книг.
        """
        return obj.books.count()

    @admin.display(description=_('Книги'))
    def get_books_list(self, obj: Author) -> str:
        """
        Возвращает список первых 3 книг автора.

        Args:
            obj (Author): Экземпляр автора.

        Returns:
            str: Список книг через запятую.
        """
        books = obj.books.all()[:3]  # Показываем только первые 3 книги
        if books:
            book_list = ", ".join([book.title for book in books])
            if obj.books.count() > 3:
                book_list += f" and more {obj.books.count() - 3}"
            return book_list
        return _('Нет книг')

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_books_count', 'get_books_list', 'created_at')
    list_display_links = ('name',)
    search_fields = ('name',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'get_books_count')
    
    fieldsets = (
        (None, {
            'fields': ('name',)
        }),
        (_('Системная информация'), {
            'fields': ('created_at', 'get_books_count'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description=_('Количество книг'))
    def get_books_count(self, obj: Genre) -> int:
        """
        Возвращает количество книг в жанре.

        Args:
            obj (Genre): Экземпляр жанра.

        Returns:
            int: Количество книг.
        """
        return obj.book_genres.count()

    @admin.display(description=_('Книги'))
    def get_books_list(self, obj: Genre) -> str:
        """
        Возвращает список первых 3 книг жанра.

        Args:
            obj (Genre): Экземпляр жанра.

        Returns:
            str: Список книг через запятую.
        """
        books = [bg.book.title for bg in obj.book_genres.all()[:3]]
        if books:
            book_list = ", ".join(books)
            if obj.book_genres.count() > 3:
                book_list += f" and more {obj.book_genres.count() - 3}"
            return book_list
        return _('Нет книг')

class CoverInline(admin.StackedInline):
    model = Cover
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('image_url', 'created_at')

class BookGenreInline(admin.TabularInline):
    model = BookGenre
    extra = 1
    raw_id_fields = ('genre',)
    readonly_fields = ('created_at',)
    fields = ('genre', 'created_at')

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    form = BookForm
    list_display = ('title', 'author', 'price', 'status', 'created_at', 'get_pdf_link')
    list_filter = ('status', 'author')
    search_fields = ('title', 'author__name', 'description')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    inlines = [BookGenreInline]
    
    fieldsets = (
        (None, {
            'fields': ('title', 'author', 'description', 'price', 'status')
        }),
        ('Скидки', {
            'fields': ('has_discount', 'discount_percent', 'discount_start', 'discount_end'),
            'classes': ('collapse',)
        }),
        ('Файлы', {
            'fields': ('ebook_file', 'book_url'),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        }),
    )

    def toggle_availability(self, request: Any, queryset: QuerySet) -> None:
        """
        Переключает статус наличия выбранных книг.

        Args:
            request: Объект запроса.
            queryset: QuerySet выбранных книг.
        """
        for book in queryset:
            if book.status == 'available':
                book.status = 'out_of_stock'
            else:
                book.status = 'available'
            book.save()
    toggle_availability.short_description = 'Изменить статус наличия'

    actions = ['toggle_availability']

    def get_pdf_link(self, obj: Book) -> str:
        """
        Возвращает ссылку для скачивания PDF книги.

        Args:
            obj (Book): Экземпляр книги.

        Returns:
            str: HTML-ссылка для скачивания PDF.
        """
        url = reverse('admin:book-pdf', args=[obj.id])
        return format_html('<a href="{}">Скачать PDF</a>', url)
    get_pdf_link.short_description = 'PDF'

    def get_urls(self) -> List[path]:
        """
        Возвращает дополнительные URL для админ-панели.

        Returns:
            List[path]: Список дополнительных URL-паттернов.
        """
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:book_id>/pdf/',
                self.admin_site.admin_view(self.generate_pdf),
                name='book-pdf',
            ),
        ]
        return custom_urls + urls

    def generate_pdf(self, request: Any, book_id: int) -> HttpResponse:
        """
        Генерирует PDF-файл для книги.

        Args:
            request: Объект запроса.
            book_id (int): ID книги.

        Returns:
            HttpResponse: PDF-файл или сообщение об ошибке.
        """
        try:
            book = self.get_object(request, book_id)
            if book is None:
                return HttpResponse('Книга не найдена', status=404)
                
            # Создаем HTML контент
            template = get_template('books/book_pdf.html')
            html_string = template.render({
                'book': book,
                'author': book.author,
                'genres': list(book.genres.all()),
                'current_price': book.current_price,
            })
            
            # Создаем PDF с обработкой ошибок
            try:
                # Создаем PDF
                response = HttpResponse(content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{book.title}.pdf"'
                
                # Генерируем PDF
                HTML(string=html_string).write_pdf(response)
                return response
                    
            except Exception as e:
                return HttpResponse(f'Ошибка при создании PDF: {str(e)}', status=500)
        except Exception as e:
            return HttpResponse(f'Произошла ошибка: {str(e)}', status=500)

@admin.register(Cover)
class CoverAdmin(admin.ModelAdmin):
    list_display = ('get_book_title', 'get_image_preview', 'created_at')
    list_display_links = ('get_book_title',)
    search_fields = ('book__title',)
    raw_id_fields = ('book',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'get_image_preview')
    
    @admin.display(description=_('Книга'))
    def get_book_title(self, obj):
        return obj.book.title

    @admin.display(description=_('Превью'))
    def get_image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="75" />', obj.image.url)
        return _('Нет изображения')

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_users_count', 'get_users_list', 'created_at')
    list_display_links = ('name',)
    list_filter = ('name', 'created_at')
    search_fields = ('name',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'get_users_count')

    @admin.display(description=_('Количество пользователей'))
    def get_users_count(self, obj):
        return obj.user_roles.count()

    @admin.display(description=_('Пользователи'))
    def get_users_list(self, obj):
        users = [ur.user.username for ur in obj.user_roles.all()[:3]]
        if users:
            user_list = ", ".join(users)
            if obj.user_roles.count() > 3:
                user_list += f" and more {obj.user_roles.count() - 3}"
            return user_list
        return _('Нет пользователей')

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('get_user_info', 'role', 'created_at')
    list_display_links = ('get_user_info',)
    list_filter = ('role', 'created_at')
    search_fields = ('user__username', 'user__email', 'role__name')
    raw_id_fields = ('user',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)

    @admin.display(description=_('Пользователь'))
    def get_user_info(self, obj):
        return f"{obj.user.username} ({obj.user.email})"

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('get_user_info', 'get_book_title', 'rating', 'get_comment_preview', 'created_at')
    list_display_links = ('get_user_info', 'get_book_title')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'book__title', 'comment')
    raw_id_fields = ('user', 'book')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('user', 'book', 'rating', 'comment')
        }),
        (_('Системная информация'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description=_('Пользователь'))
    def get_user_info(self, obj):
        return f"{obj.user.username}"

    @admin.display(description=_('Книга'))
    def get_book_title(self, obj):
        return obj.book.title

    @admin.display(description=_('Комментарий'))
    def get_comment_preview(self, obj):
        if obj.comment:
            preview = obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
            return preview
        return _('Без комментария')

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    raw_id_fields = ('book',)
    readonly_fields = ('created_at', 'updated_at', 'get_item_total')
    fields = ('book', 'quantity', 'get_item_total', 'created_at', 'updated_at')

    @admin.display(description=_('Сумма'))
    def get_item_total(self, obj):
        if obj.book:
            return f"{obj.book.current_price * obj.quantity}₽"
        return "0₽"

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('get_user_info', 'get_items_count', 'get_total_price', 'created_at')
    list_display_links = ('get_user_info',)
    search_fields = ('user__username', 'user__email')
    raw_id_fields = ('user',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'get_total_price', 'get_items_count')
    inlines = [CartItemInline]
    
    fieldsets = (
        (None, {
            'fields': ('user',)
        }),
        (_('Системная информация'), {
            'fields': ('created_at', 'updated_at', 'get_total_price', 'get_items_count'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description=_('Пользователь'))
    def get_user_info(self, obj):
        return f"{obj.user.username} ({obj.user.email})"

    @admin.display(description=_('Количество товаров'))
    def get_items_count(self, obj):
        return obj.cart_items.count()

    @admin.display(description=_('Общая стоимость'))
    def get_total_price(self, obj):
        total = sum(item.book.current_price * item.quantity for item in obj.cart_items.all())
        return f"{total}₽"

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('get_cart_user', 'get_book_title', 'quantity', 'get_item_total', 'created_at')
    list_display_links = ('get_cart_user', 'get_book_title')
    list_filter = ('created_at', 'quantity')
    search_fields = ('cart__user__username', 'book__title')
    raw_id_fields = ('cart', 'book')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'get_item_total')
    
    fieldsets = (
        (None, {
            'fields': ('cart', 'book', 'quantity')
        }),
        (_('Системная информация'), {
            'fields': ('created_at', 'updated_at', 'get_item_total'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description=_('Корзина пользователя'))
    def get_cart_user(self, obj):
        return f"Корзина {obj.cart.user.username}"

    @admin.display(description=_('Книга'))
    def get_book_title(self, obj):
        return obj.book.title

    @admin.display(description=_('Сумма'))
    def get_item_total(self, obj):
        return f"{obj.book.current_price * obj.quantity}₽"
