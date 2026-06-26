# vin/permissions.py
from rest_framework import permissions
import logging

logger = logging.getLogger(__name__)


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    只允许管理员进行修改，其他用户只读
    """

    def has_permission(self, request, view):
        # 允许所有用户进行安全方法（GET, HEAD, OPTIONS）
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class IsAdminUser(permissions.BasePermission):
    """
    只允许管理员访问
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class IsAdminOrSelf(permissions.BasePermission):
    """
    允许管理员访问所有，普通用户只能访问自己的数据
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.user == request.user


class VinConfigPermission(permissions.BasePermission):
    """
    VIN配置权限控制：
    - 管理员：完全控制
    - 普通用户：无任何权限
    """

    def has_permission(self, request, view):
        # 允许所有用户查看自己相关的配置（在get_queryset中过滤）
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class HasVinQueryPermission(permissions.BasePermission):
    """
    VIN查询权限控制：
    - 超级管理员：完全权限
    - 员工用户：需要是激活的员工
    - 普通用户：需要登录
    - 匿名用户：无权限
    """

    def has_permission(self, request, view):
        # 检查是否已认证
        if not request.user or not request.user.is_authenticated:
            return False

        # 超级管理员直接通过
        if request.user.is_superuser:
            return True

        # 检查是否为员工用户
        if hasattr(request.user, 'is_staff_member'):
            # 员工用户需要是激活状态
            if request.user.is_staff_member and request.user.is_active:
                return True

        # 检查用户类型
        if hasattr(request.user, 'ocr_user_type'):
            # 允许微信用户和员工用户查询
            if request.user.ocr_user_type in ['wechat', 'employee', 'admin']:
                return True

        # 默认拒绝
        return False

    def has_object_permission(self, request, view, obj):
        # 对象级权限检查
        return self.has_permission(request, view)


class VinSearchPermission(permissions.BasePermission):
    """
    VIN查询权限控制：
    - 超级管理员：完全权限
    - 员工用户：需要是激活的员工成员
    - 普通员工（is_staff）：需要VIN查询权限
    - 其他用户：拒绝访问
    """

    def has_permission(self, request, view):
        # 记录用户信息
        user = request.user

        if not user or not user.is_authenticated:
            logger.warning("VIN查询权限检查: 用户未认证")
            return False

        # 用户信息日志
        user_info = {
            'id': user.id,
            'username': user.username,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'is_staff_member': getattr(user, 'is_staff_member', False),
            'ocr_user_type': getattr(user, 'ocr_user_type', 'unknown'),
            'staff_role': getattr(user, 'staff_role', ''),
            'is_active': user.is_active
        }
        logger.info(f"VIN查询权限检查 - 用户信息: {user_info}")

        # 1. 超级管理员直接通过
        if user.is_superuser:
            logger.info("VIN查询权限检查: 超级管理员通过")
            return True

        # 2. 检查员工用户类型
        ocr_user_type = getattr(user, 'ocr_user_type', 'unknown')
        allowed_employee_types = ['employee', 'admin', 'manager']

        if ocr_user_type in allowed_employee_types:
            is_staff_member = getattr(user, 'is_staff_member', False)
            if not is_staff_member:
                logger.warning(f"VIN查询权限检查失败: 用户类型{ocr_user_type}但不是员工成员")
                return False

            if not user.is_active:
                logger.warning(f"VIN查询权限检查失败: 员工账号未激活")
                return False

            logger.info(f"VIN查询权限检查通过: 员工用户类型 {ocr_user_type}")
            return True

        # 3. 检查普通员工权限
        if user.is_staff:
            # 检查是否有VIN查询权限
            has_perm = self._check_vin_permissions(user)
            if has_perm:
                logger.info("VIN查询权限检查通过: 具有VIN查询权限的员工")
                return True
            else:
                logger.warning("VIN查询权限检查失败: 员工没有VIN查询权限")
                return False

        # 4. 默认拒绝
        logger.warning(f"VIN查询权限检查失败: 用户类型 {ocr_user_type} 不允许访问")
        return False

    def _check_vin_permissions(self, user):
        """检查VIN查询相关权限"""
        # 检查权限字符串
        vin_permissions = [
            'vin.can_query_vin',
            'vin.query_vin',
            'vin.add_vinqueryresult',
            'vin.view_vinqueryresult'
        ]

        for perm in vin_permissions:
            if user.has_perm(perm):
                return True

        # 检查用户组
        allowed_groups = ['VIN查询', '员工', '管理员']
        if user.groups.filter(name__in=allowed_groups).exists():
            return True

        return False
