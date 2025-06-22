from django.urls import path, re_path
from django.shortcuts import render
from . import views

app_name = 'books'

urlpatterns = [
    # Главная страница приложения books
    path('', views.index, name='index'),

    # Тестовая страница для проверки пользователя
    path('test-user/', lambda request: render(request, 'test_user.html'), name='test-user'),

    # Страница полного списка книг
    path('list/', views.book_list, name='book-list'),

    # Обычные URL-паттерны
    path('book/<int:pk>/', views.book_detail, name='book-detail'),
    path('book/create/', views.book_create, name='book-create'),
    path('book/<int:pk>/edit/', views.book_edit, name='book-edit'),
    path('book/<int:pk>/delete/', views.book_delete, name='book-delete'),
    path('author/<int:pk>/', views.author_detail, name='author-detail'),
    path('cart/<int:pk>/', views.cart_detail, name='cart-detail'),
    path('discounts/', views.discount_books, name='discount-books'),
    path('demo/', views.demo_features, name='demo-features'),

    # Добавляем URL для демонстрационной страницы ORM
    path('orm-demo/', views.orm_demonstration_view, name='orm_demonstration'),

    # URL-паттерны с регулярными выражениями
    re_path(r'^books/(?P<year>\d{4})/$', views.book_list, name='book-list-by-year'),
    re_path(r'^books/(?P<year>\d{4})/(?P<month>\d{2})/$', views.book_list, name='book-list-by-month'),
    re_path(r'^books/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/$', views.book_list, name='book-list-by-day'),
    
    # Поиск по названию книги (слова, начинающиеся с определенных букв)
    path('search/', views.book_search, name='book-search'),
    re_path(r'^books/search/(?P<query>[a-zA-Zа-яА-Я]+)/$', views.book_search, name='book-search-by-query'),
    
    # Фильтрация по цене
    re_path(r'^books/price/(?P<min_price>\d+)-(?P<max_price>\d+)/$', views.book_list, name='book-price-range'),
    
    # Фильтрация по рейтингу
    re_path(r'^books/rating/(?P<rating>[1-5])/$', views.book_list, name='book-rating'),

    path('register/', views.register, name='register'),
] 