from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Создаем роутер для API
router = DefaultRouter()
router.register(r'books', views.BookViewSet)
router.register(r'authors', views.AuthorViewSet)
router.register(r'reviews', views.ReviewViewSet)
router.register(r'orders', views.OrderViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('rest_framework.urls')),  # Для авторизации в браузере
] 