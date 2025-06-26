import re
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.middleware.csrf import CsrfViewMiddleware

class CSRFExemptMiddleware(MiddlewareMixin):
    """
    Middleware для исключения CSRF проверки для определенных URL
    """
    def process_request(self, request):
        # Проверяем, нужно ли исключить CSRF для этого URL
        for pattern in getattr(settings, 'CSRF_EXEMPT_URLS', []):
            if re.match(pattern, request.path_info):
                setattr(request, '_dont_enforce_csrf_checks', True)
                break
        return None

    def process_view(self, request, callback, callback_args, callback_kwargs):
        # Проверяем, нужно ли исключить CSRF для этого URL
        for pattern in getattr(settings, 'CSRF_EXEMPT_URLS', []):
            if re.match(pattern, request.path_info):
                setattr(request, '_dont_enforce_csrf_checks', True)
                break
        return None 