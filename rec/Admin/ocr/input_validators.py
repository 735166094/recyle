import re
import logging
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class InputValidator:
    """输入验证器"""

    @staticmethod
    def validate_integer(value, field_name="ID", min_value=1, max_value=2 ** 31 - 1):
        """验证整数输入"""
        try:
            int_value = int(value)
            if int_value < min_value or int_value > max_value:
                raise ValidationError(
                    _(f"{field_name}必须在{min_value}到{max_value}之间")
                )
            return int_value
        except (ValueError, TypeError):
            raise ValidationError(_(f"无效的{field_name}格式"))

    @staticmethod
    def validate_string(value, field_name="字段", max_length=255, allow_empty=False):
        """验证字符串输入"""
        if not value and not allow_empty:
            raise ValidationError(_(f"{field_name}不能为空"))

        if value and len(value) > max_length:
            raise ValidationError(_(f"{field_name}长度不能超过{max_length}个字符"))

        # 防止XSS攻击
        dangerous_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'on\w+=',
            r'vbscript:'
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"检测到潜在的XSS攻击: {field_name}={value}")
                raise ValidationError(_(f"无效的{field_name}内容"))

        return value.strip() if value else value

    @staticmethod
    def validate_filename(filename):
        """验证文件名安全性"""
        if not filename:
            raise ValidationError(_("文件名不能为空"))

        # 防止路径遍历攻击
        dangerous_chars = ['..', '/', '\\', ':', ';', '|']
        for char in dangerous_chars:
            if char in filename:
                raise ValidationError(_("文件名包含非法字符"))

        # 限制文件扩展名
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
        file_ext = filename.lower()[filename.rfind('.'):]
        if file_ext not in allowed_extensions:
            raise ValidationError(_("不支持的文件类型"))

        return filename

    @staticmethod
    def validate_email(email):
        """验证邮箱格式"""
        if not email:
            return email

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError(_("无效的邮箱格式"))

        return email

    @staticmethod
    def validate_phone(phone):
        """验证手机号格式"""
        if not phone:
            return phone

        phone_pattern = r'^1[3-9]\d{9}$'
        if not re.match(phone_pattern, phone):
            raise ValidationError(_("无效的手机号格式"))

        return phone


class SQLInjectionValidator:
    """SQL注入防护验证器"""

    SQL_KEYWORDS = [
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
        'UNION', 'WHERE', 'FROM', 'TABLE', 'DATABASE', 'EXEC', 'TRUNCATE'
    ]

    @classmethod
    def validate_sql_safe(cls, value):
        """验证输入是否包含SQL注入攻击"""
        if not value:
            return value

        value_upper = value.upper()

        # 检查SQL关键字
        for keyword in cls.SQL_KEYWORDS:
            # 使用单词边界匹配，避免误判
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, value_upper):
                logger.warning(f"检测到潜在的SQL注入攻击: {value}")
                raise ValidationError(_("输入包含非法字符"))

        # 检查特殊字符
        dangerous_chars = ["'", '"', ';', '--', '/*', '*/', '`']
        for char in dangerous_chars:
            if char in value:
                logger.warning(f"检测到潜在的SQL注入攻击字符: {char} in {value}")
                raise ValidationError(_("输入包含非法字符"))

        return value