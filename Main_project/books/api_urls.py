from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .views import BookViewSet, AuthorViewSet, GenreViewSet, ReviewViewSet, api_login, api_register, api_logout, api_get_current_user

# CSRF endpoint
@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({'csrfToken': request.META.get('CSRF_COOKIE', '')})

# Создаем роутер для API
router = DefaultRouter()
router.register(r'books', BookViewSet)
router.register(r'authors', AuthorViewSet)
router.register(r'genres', GenreViewSet)
router.register(r'reviews', ReviewViewSet)

# API URLs без CSRF для аутентификации
auth_urlpatterns = [
    path('auth/login/', csrf_exempt(api_login), name='api_login'),
    path('auth/register/', csrf_exempt(api_register), name='api_register'),
    path('auth/logout/', csrf_exempt(api_logout), name='api_logout'),
    path('auth/user/', csrf_exempt(api_get_current_user), name='api_get_current_user'),
    path('csrf/', get_csrf_token, name='csrf_token'),
]

urlpatterns = [
    path('', include(router.urls)),
    path('', include(auth_urlpatterns)),
] 