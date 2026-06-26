import logging
import sys
import traceback
from django.http import JsonResponse
from django.conf import settings
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


class ErrorHandler:
    """错误处理器"""

    @staticmethod
    def safe_exception_message(exception, include_traceback=False):
        """生成安全的异常消息"""
        if settings.DEBUG:
            # 调试模式返回详细信息
            return {
                'error': str(exception),
                'type': type(exception).__name__,
                'traceback': traceback.format_exc() if include_traceback else None
            }
        else:
            # 生产环境返回通用信息
            error_type = type(exception).__name__

            # 根据异常类型返回不同的用户友好消息
            user_friendly_messages = {
                'ValidationError': '请求参数验证失败',
                'PermissionDenied': '权限不足',
                'AuthenticationFailed': '认证失败',
                'DoesNotExist': '请求的资源不存在',
                'MultipleObjectsReturned': '找到多个资源',
                'ValueError': '无效的请求参数',
                'TypeError': '请求参数类型错误',
            }

            message = user_friendly_messages.get(error_type, '服务器内部错误')

            # 记录详细错误到日志
            logger.error(
                f"异常类型: {error_type}, "
                f"异常消息: {str(exception)}, "
                f"追踪信息: {traceback.format_exc()}"
            )

            return {
                'error': message,
                'code': error_type.lower()
            }

    @staticmethod
    def handle_validation_error(exception):
        """处理验证错误"""
        errors = {}
        if hasattr(exception, 'detail'):
            # DRF验证错误
            if isinstance(exception.detail, dict):
                for field, field_errors in exception.detail.items():
                    if isinstance(field_errors, list):
                        errors[field] = [str(err) for err in field_errors]
                    else:
                        errors[field] = [str(field_errors)]
            else:
                errors['non_field_errors'] = [str(exception.detail)]
        else:
            # Django验证错误
            errors['non_field_errors'] = [str(exception)]

        return {
            'error': '数据验证失败',
            'code': 'validation_error',
            'details': errors
        }


def custom_exception_handler(exc, context):
    """
    自定义异常处理器
    用于DRF视图的异常处理
    """
    # 先让DRF处理异常
    response = drf_exception_handler(exc, context)

    if response is not None:
        # DRF已经处理了异常，但我们想要统一错误格式
        error_data = ErrorHandler.safe_exception_message(exc)

        # 对于验证错误，提供更详细的信息
        if hasattr(exc, 'detail') and isinstance(exc.detail, dict):
            error_data = ErrorHandler.handle_validation_error(exc)

        response.data = error_data
        return response

    # 处理DRF未捕获的异常
    error_data = ErrorHandler.safe_exception_message(exc)

    # 记录未处理异常
    logger.critical(
        f"未处理的异常: {type(exc).__name__}, "
        f"消息: {str(exc)}, "
        f"上下文: {context}, "
        f"追踪: {traceback.format_exc()}"
    )

    return Response(
        error_data,
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def handle_500_error(request):
    """处理500错误"""
    exception_type, exception_value, exception_traceback = sys.exc_info()

    error_data = ErrorHandler.safe_exception_message(exception_value, include_traceback=settings.DEBUG)

    # 记录错误
    logger.error(
        f"500错误: {exception_type.__name__}, "
        f"路径: {request.path}, "
        f"方法: {request.method}, "
        f"用户: {request.user}, "
        f"IP: {request.META.get('REMOTE_ADDR')}"
    )

    return JsonResponse(error_data, status=500)


def handle_404_error(request, exception):
    """处理404错误"""
    logger.warning(
        f"404错误: 路径: {request.path}, "
        f"方法: {request.method}, "
        f"用户: {request.user}, "
        f"IP: {request.META.get('REMOTE_ADDR')}"
    )

    if request.headers.get('Content-Type') == 'application/json':
        return JsonResponse({
            'error': '请求的资源不存在',
            'code': 'not_found',
            'path': request.path
        }, status=404)

    from django.http import HttpResponseNotFound
    return HttpResponseNotFound("""
    <html>
        <head><title>页面未找到</title></head>
        <body>
            <h1>页面未找到</h1>
            <p>您请求的页面不存在。</p>
        </body>
    </html>
    """)