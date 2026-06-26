from rest_framework import permissions
import logging
from user.models import User
logger = logging.getLogger(__name__)


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    自定义权限类：
    - 允许管理员访问所有记录
    - 普通用户只能访问自己创建的记录
    - 加强安全检查，防止权限绕过
    """

    def has_permission(self, request, view):
        """视图级别的权限检查"""
        # 确保用户已认证
        if not request.user or not request.user.is_authenticated:
            return False

        # 管理员有所有权限
        if request.user.is_staff:
            return True

        # 普通用户只能访问安全的方法
        if request.method in permissions.SAFE_METHODS:
            return True

        # 非安全方法需要进一步的对象级别检查
        return True

    def has_object_permission(self, request, view, obj):
        """对象级别的权限检查 - 加强安全性"""
        # 记录权限检查尝试
        logger.info(f"权限检查: 用户={request.user.username}, 方法={request.method}, 对象类型={type(obj).__name__}")

        # 1. 管理员有全部权限
        if request.user and request.user.is_staff:
            logger.info("管理员权限通过")
            return True

        # 2. 检查对象是否有user属性
        if not hasattr(obj, 'user'):
            logger.warning(f"权限检查失败: 对象 {type(obj).__name__} 没有user属性")
            return False

        # 3. 验证用户身份
        if not request.user.is_authenticated:
            logger.warning("权限检查失败: 用户未认证")
            return False

        # 4. 检查对象所有者
        is_owner = obj.user == request.user
        if is_owner:
            logger.info("对象所有者权限通过")
        else:
            logger.warning(f"权限检查失败: 用户 {request.user.username} 不是对象的所有者")

        return is_owner


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    自定义权限类：
    - 允许管理员进行所有操作
    - 普通用户只能进行只读操作
    - 加强安全检查
    """

    def has_permission(self, request, view):
        """视图级别的权限检查"""
        if not request.user or not request.user.is_authenticated:
            return False

        # 允许所有用户进行安全操作（GET, HEAD, OPTIONS）
        if request.method in permissions.SAFE_METHODS:
            return True

        # 只允许管理员进行修改操作
        is_admin = request.user and request.user.is_staff
        if not is_admin:
            logger.warning(f"权限拒绝: 用户 {request.user.username} 尝试执行 {request.method} 操作")

        return is_admin


class IsOwner(permissions.BasePermission):
    """
    自定义权限类：
    - 只允许对象的所有者访问
    - 加强安全检查
    """

    def has_permission(self, request, view):
        """视图级别的权限检查"""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """对象级别的权限检查"""
        # 检查对象是否有user属性
        if not hasattr(obj, 'user'):
            logger.warning(f"权限检查失败: 对象 {type(obj).__name__} 没有user属性")
            return False

        # 检查用户身份
        if not request.user.is_authenticated:
            return False

        is_owner = obj.user == request.user
        if not is_owner:
            logger.warning(f"权限检查失败: 用户 {request.user.username} 不是对象的所有者")

        return is_owner


class StrictObjectPermission(permissions.BasePermission):
    """
    严格的权限检查类
    - 要求明确的对象权限映射
    """

    # 定义对象类型与权限检查方法的映射
    OBJECT_PERMISSION_MAP = {
        'RecognitionRecord': lambda obj, user: hasattr(obj, 'user') and obj.user == user,
        'ScrapCarInfo': lambda obj, user: (
                (hasattr(obj, 'vehicle_record') and hasattr(obj.vehicle_record,
                                                            'user') and obj.vehicle_record.user == user) or
                (hasattr(obj, 'id_card_record') and hasattr(obj.id_card_record,
                                                            'user') and obj.id_card_record.user == user) or
                (hasattr(obj, 'business_record') and hasattr(obj.business_record,
                                                             'user') and obj.business_record.user == user)
        )
    }

    def has_object_permission(self, request, view, obj):
        """基于对象类型的严格权限检查"""
        if request.user and request.user.is_staff:
            return True

        obj_type = type(obj).__name__
        permission_check = self.OBJECT_PERMISSION_MAP.get(obj_type)

        if permission_check:
            return permission_check(obj, request.user)
        else:
            # 对于未知对象类型，使用保守策略
            logger.warning(f"未知对象类型 {obj_type} 的权限检查，使用保守策略")
            return False