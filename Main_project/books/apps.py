from django.apps import AppConfig


class BooksConfig(AppConfig):
    """
    Конфигурация приложения Books.
    
    Определяет основные настройки приложения, включая
    автоматическое поле по умолчанию и название приложения.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'books'
