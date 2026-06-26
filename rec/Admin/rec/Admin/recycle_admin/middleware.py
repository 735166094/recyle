# recycle_admin/middleware.py
import logging
from django.http import HttpResponseForbidden

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """添加安全响应头"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # 添加安全响应头
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'

        # 严格传输安全（HTTPS）
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        return response


class RequestFilterMiddleware:
    """过滤恶意请求"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 记录可疑请求
        if any(path in request.path for path in ['.env', '/.env', 'wp-admin', 'phpMyAdmin']):
            logger.warning(f"可疑请求路径: {request.path} from {request.META.get('REMOTE_ADDR')}")

        return self.get_response(request)