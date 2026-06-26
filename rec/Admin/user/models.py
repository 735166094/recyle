# user/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.utils.crypto import get_random_string
import uuid


class CustomUserManager(BaseUserManager):
    """自定义用户管理器"""

    def create_user(self, phone=None, username=None, password=None, **extra_fields):
        """创建普通用户"""
        if not phone and not username:
            raise ValueError('必须提供手机号或用户名')

        # 优先使用手机号作为用户名
        if not username and phone:
            username = phone

        user = self.model(
            username=username,
            phone=phone,
            **extra_fields
        )

        # 设置密码
        if password:
            user.set_password(password)
        else:
            # 生成随机密码
            random_password = get_random_string(12)
            user.set_password(random_password)

        user.save(using=self._db)
        return user

    def create_employee(self, staff_id, real_name, department, position, password='111@chery', **extra_fields):
        """创建员工账号"""
        if not staff_id:
            raise ValueError('必须提供员工工号')

        # 检查员工工号是否已存在
        if self.model.objects.filter(staff_id=staff_id, user_type='employee').exists():
            raise ValueError('该员工工号已存在')

        # 生成用户名
        username = f'emp_{staff_id}'

        user = self.model(
            username=username,
            staff_id=staff_id,
            real_name=real_name,
            user_type='employee',
            is_staff_member=True,
            **extra_fields
        )

        # 设置密码
        if password:
            user.set_password(password)
        else:
            user.set_default_password()

        # 员工额外信息
        user.department = department
        user.position = position

        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        """创建管理员"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'admin')
        extra_fields.setdefault('is_staff_member', True)

        return self.create_user(username=username, password=password, **extra_fields)


class User(AbstractUser):
    """
    统一用户模型
    """
    # 账号类型
    USER_TYPE_CHOICES = (
        ('customer', '普通用户'),
        ('employee', '员工账号'),
        ('admin', '管理员')
    )

    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='customer', verbose_name="账号类型")

    # 微信相关字段
    openid = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name="微信OpenID")
    unionid = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name="微信UnionID",
                               error_messages={
                                   'unique': "该微信已被绑定"
                               }
                               )
    session_key = models.CharField(max_length=100, blank=True, null=True, verbose_name="微信会话密钥")
    nickname = models.CharField(max_length=100, blank=True, null=True, verbose_name="微信昵称")
    avatar_url = models.URLField(blank=True, null=True, verbose_name="微信头像")

    # 手机号
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="手机号", db_index=True)

    # 用户基础信息
    gender = models.IntegerField(choices=((0, '未知'), (1, '男'), (2, '女')), default=0, verbose_name="性别")
    country = models.CharField(max_length=50, blank=True, null=True, verbose_name="国家")
    province = models.CharField(max_length=50, blank=True, null=True, verbose_name="省份")
    city = models.CharField(max_length=50, blank=True, null=True, verbose_name="城市")

    # 积分基础字段
    points = models.IntegerField(default=0, verbose_name="积分")

    # 员工相关字段
    is_staff_member = models.BooleanField(default=False, verbose_name="是否为员工")
    staff_id = models.CharField(max_length=50, blank=True, null=True, unique=True, verbose_name="员工工号")
    department = models.CharField(max_length=100, blank=True, null=True, verbose_name="部门")
    position = models.CharField(max_length=100, blank=True, null=True, verbose_name="职位")

    # 实名认证
    is_verified = models.BooleanField(default=False, verbose_name="是否实名认证")
    real_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="真实姓名")
    id_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="身份证号")

    # 账号状态
    is_phone_bound = models.BooleanField(default=False, verbose_name="是否绑定手机号")
    is_wechat_bound = models.BooleanField(default=False, verbose_name="是否绑定微信")

    # 时间字段
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="注册时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="信息更新时间")
    last_login_time = models.DateTimeField(blank=True, null=True, verbose_name="最后登录时间")

    # 使用自定义管理器
    objects = CustomUserManager()

    class Meta:
        db_table = "user_info"
        verbose_name = "用户"
        verbose_name_plural = "用户"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['phone', 'user_type']),
            models.Index(fields=['staff_id', 'user_type']),
            models.Index(fields=['openid']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        if self.phone:
            return f"{self.phone} - {self.real_name or self.nickname or '用户'}"
        elif self.staff_id:
            return f"{self.staff_id} - {self.real_name or '员工'}"
        else:
            return f"{self.username} ({self.get_user_type_display()})"

    @property
    def display_name(self):
        """获取显示名称（用于前端显示）"""
        if self.real_name:
            return self.real_name
        elif self.phone:
            return self.phone
        elif self.staff_id:
            return self.staff_id
        elif self.nickname:
            return self.nickname
        else:
            return self.username

    def save(self, *args, **kwargs):
        # 自动设置员工标识
        if self.user_type in ['employee', 'admin']:
            self.is_staff_member = True
        else:
            self.is_staff_member = False

        # 如果是员工账号，确保有员工工号
        if self.user_type == 'employee' and not self.staff_id and not self.pk:
            base_id = f"EMP{timezone.now().strftime('%Y%m%d')}"
            existing_count = User.objects.filter(staff_id__startswith=base_id).count()
            self.staff_id = f"{base_id}{existing_count + 1:04d}"

        # 处理空的 unionid - 更严格的处理
        if self.unionid == '':
            # 完全设置为 None，而不是空字符串
            self.unionid = None
        elif self.unionid is not None and self.unionid.strip() == '':
            # 处理空格情况
            self.unionid = None

        super().save(*args, **kwargs)
    def update_login_time(self):
        """更新最后登录时间"""
        self.last_login_time = timezone.now()
        self.save(update_fields=['last_login_time', 'updated_at'])

    def bind_phone(self, phone, commit=True):
        """绑定手机号"""
        # 检查手机号是否已被其他用户使用
        existing_user = User.objects.filter(
            phone=phone,
            is_active=True
        ).exclude(id=self.id).first()

        if existing_user:
            raise ValueError("该手机号已被其他账号使用")

        self.phone = phone
        self.is_phone_bound = True

        if commit:
            self.save(update_fields=['phone', 'is_phone_bound', 'updated_at'])

    def bind_wechat(self, openid, session_key, nickname=None, avatar_url=None, commit=True):
        """绑定微信"""
        # 检查微信是否已被其他用户绑定
        existing_user = User.objects.filter(
            openid=openid,
            is_active=True
        ).exclude(id=self.id).first()

        if existing_user:
            raise ValueError("该微信已被其他账号绑定")

        self.openid = openid
        self.session_key = session_key
        self.is_wechat_bound = True

        if nickname:
            self.nickname = nickname
        if avatar_url:
            self.avatar_url = avatar_url

        if commit:
            update_fields = ['openid', 'session_key', 'is_wechat_bound', 'updated_at']
            if nickname:
                update_fields.append('nickname')
            if avatar_url:
                update_fields.append('avatar_url')
            self.save(update_fields=update_fields)

    def can_login_with_phone(self):
        """是否可用手机号登录"""
        return self.phone and self.is_phone_bound and self.is_active

    def can_login_with_wechat(self):
        """是否可用微信登录"""
        return self.openid and self.is_wechat_bound and self.is_active

    def can_login_with_staff_id(self):
        """是否可用员工工号登录"""
        return self.staff_id and self.user_type in ['employee', 'admin'] and self.is_active

    @property
    def has_password_set(self):
        """是否设置了密码"""
        return self.password and not self.password.startswith('!')  # Django的不可用密码以!开头

    def set_default_password(self):
        """设置默认密码 111@chery（仅员工账号）"""
        if self.user_type != 'employee':
            raise ValueError("只有员工账号可以设置默认密码")

        self.set_password("111@chery")
        self.save(update_fields=['password', 'updated_at'])

    def check_employee_password(self, password):
        """检查员工密码（支持默认密码）"""
        # 员工账号支持默认密码
        if self.user_type == 'employee' and password == "111@chery":
            return True
        return self.check_password(password)

    @property
    def available_login_methods(self):
        """获取可用的登录方式"""
        methods = []

        # 手机号登录
        if self.phone and self.is_phone_bound and self.is_active:
            methods.append('phone')

        # 微信登录
        if self.openid and self.is_wechat_bound and self.is_active:
            methods.append('wechat')

        # 员工工号登录（仅员工）
        if self.staff_id and self.user_type in ['employee', 'admin'] and self.is_active:
            methods.append('staff_id')

        # 用户名密码登录（如果有设置密码）
        if self.has_password_set and self.is_active:
            methods.append('password')

        return methods

    def can_login_with_password(self):
        """是否可用密码登录"""
        return self.has_password_set and self.is_active


class UserAddress(models.Model):
    """
    用户地址模型
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name="用户"
    )
    receiver_name = models.CharField(max_length=50, verbose_name="收货人姓名")
    receiver_phone = models.CharField(max_length=20, verbose_name="收货人电话")
    country = models.CharField(max_length=50, default="中国", verbose_name="国家")
    province = models.CharField(max_length=50, verbose_name="省份")
    city = models.CharField(max_length=50, verbose_name="城市")
    district = models.CharField(max_length=50, verbose_name="区县")
    detail_address = models.CharField(max_length=200, verbose_name="详细地址")
    postal_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="邮政编码")
    address_tag = models.CharField(
        max_length=20,
        choices=(
            ('home', '家'),
            ('company', '公司'),
            ('school', '学校'),
            ('other', '其他')
        ),
        default='home',
        verbose_name="地址标签"
    )
    is_default = models.BooleanField(default=False, verbose_name="默认地址")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "user_address"
        verbose_name = "用户地址"
        verbose_name_plural = "用户地址"
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.receiver_name} - {self.province}{self.city}{self.district}{self.detail_address}"

    def save(self, *args, **kwargs):
        if self.is_default:
            UserAddress.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class UserCoupon(models.Model):
    """
    用户优惠券模型
    """
    COUPON_TYPE_CHOICES = (
        ('jd', '京东优惠券'),
        ('mall', '商城优惠券'),
        ('recycle', '回收优惠券'),
        ('other', '其他'),
    )

    COUPON_STATUS_CHOICES = (
        ('unused', '未使用'),
        ('used', '已使用'),
        ('expired', '已过期'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='coupons',
        verbose_name="用户"
    )
    coupon_type = models.CharField(max_length=20, choices=COUPON_TYPE_CHOICES, verbose_name="优惠券类型")
    coupon_name = models.CharField(max_length=100, verbose_name="优惠券名称")
    coupon_code = models.CharField(max_length=50, unique=True, verbose_name="优惠券码")
    description = models.TextField(blank=True, null=True, verbose_name="优惠券描述")
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="优惠金额/折扣")
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="最低订单金额")
    valid_from = models.DateTimeField(verbose_name="有效期开始")
    valid_to = models.DateTimeField(verbose_name="有效期结束")
    status = models.CharField(max_length=20, choices=COUPON_STATUS_CHOICES, default='unused', verbose_name="状态")
    used_at = models.DateTimeField(blank=True, null=True, verbose_name="使用时间")
    used_order = models.CharField(max_length=100, blank=True, null=True, verbose_name="使用订单")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="获取时间")

    class Meta:
        db_table = "user_coupon"
        verbose_name = "用户优惠券"
        verbose_name_plural = "用户优惠券"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.coupon_name}"

    @property
    def is_valid(self):
        """检查优惠券是否有效"""
        now = timezone.now()
        return (self.status == 'unused' and
                self.valid_from <= now <= self.valid_to)


class UserFavorite(models.Model):
    """
    用户收藏模型
    """
    FAVORITE_TYPE_CHOICES = (
        ('product', '商品'),
        ('news', '资讯'),
        ('activity', '活动'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name="用户"
    )
    favorite_type = models.CharField(max_length=20, choices=FAVORITE_TYPE_CHOICES, verbose_name="收藏类型")
    item_id = models.IntegerField(verbose_name="收藏项目ID")
    item_name = models.CharField(max_length=200, verbose_name="项目名称")
    item_image = models.URLField(blank=True, null=True, verbose_name="项目图片")
    item_url = models.CharField(max_length=500, blank=True, null=True, verbose_name="项目链接")
    notes = models.TextField(blank=True, null=True, verbose_name="备注")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="收藏时间")

    class Meta:
        db_table = "user_favorite"
        verbose_name = "用户收藏"
        verbose_name_plural = "用户收藏"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'favorite_type', 'item_id'],
                name='unique_user_favorite'
            )
        ]

    def __str__(self):
        return f"{self.user.username} 收藏了 {self.item_name}"


class EmployeeApp(models.Model):
    """
    应用系统配置模型
    """
    # 新增打开方式字段
    OPEN_TYPE_CHOICES = (
        ('internal', '内部页面'),
        ('webview', '外部网页'),
        ('miniapp', '跳转小程序'),
    )

    app_id = models.CharField(max_length=50, unique=True, verbose_name="应用ID")
    app_name = models.CharField(max_length=100, verbose_name="应用名称")
    app_desc = models.TextField(verbose_name="应用描述")
    icon_class = models.CharField(max_length=100, default='iconfont icon-app', verbose_name="图标类名")

    # 应用路径配置
    app_url = models.CharField(max_length=500, blank=True, null=True, verbose_name="应用URL/路径")
    internal_path = models.CharField(max_length=200, blank=True, null=True, verbose_name="内部页面路径")
    webview_url = models.CharField(max_length=500, blank=True, null=True, verbose_name="WebView地址")
    miniapp_path = models.CharField(max_length=500, blank=True, null=True, verbose_name="小程序路径")

    # 打开方式配置
    open_type = models.CharField(
        max_length=20,
        choices=OPEN_TYPE_CHOICES,
        default='internal',
        verbose_name="打开方式"
    )

    # 访问权限配置
    access_roles = models.JSONField(default=list, blank=True, verbose_name="可访问角色")
    require_auth = models.BooleanField(default=True, verbose_name="需要认证")

    # 应用配置
    app_config = models.JSONField(default=dict, blank=True, null=True, verbose_name="应用配置")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    sort_order = models.IntegerField(default=0, verbose_name="排序")

    # 时间字段
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "employee_app"
        verbose_name = "应用系统"
        verbose_name_plural = "应用系统"
        ordering = ["sort_order", "app_name"]

    def __str__(self):
        return self.app_name

    def get_app_access_url(self):
        """根据打开方式获取访问地址"""
        if self.open_type == 'internal' and self.internal_path:
            # 确保路径以 / 开头
            path = self.internal_path
            if not path.startswith('/'):
                path = '/' + path
            return {
                'type': 'internal',
                'path': path,
                'need_redirect': True
            }
        elif self.open_type == 'webview' and self.webview_url:
            return {
                'type': 'webview',
                'url': self.webview_url,
                'need_redirect': True
            }
        elif self.open_type == 'miniapp' and self.miniapp_path:
            return {
                'type': 'miniapp',
                'path': self.miniapp_path
            }
        elif self.app_url:
            # 默认使用app_url
            if self.app_url.startswith('http://') or self.app_url.startswith('https://'):
                return {
                    'type': 'webview',
                    'url': self.app_url,
                    'need_redirect': True
                }
            else:
                # 同样处理内部路径
                path = self.app_url
                if not path.startswith('/'):
                    path = '/' + path
                return {
                    'type': 'internal',
                    'path': path,
                    'need_redirect': True
                }
        else:
            return {
                'type': 'internal',
                'path': f'/pages/apps/{self.app_id}/{self.app_id}',
                'need_redirect': True
            }


class EmployeeLoginRecord(models.Model):
    """
    员工登录记录
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employee_logins', verbose_name="员工")
    login_ip = models.GenericIPAddressField(verbose_name="登录IP")
    user_agent = models.TextField(blank=True, null=True, verbose_name="用户代理")
    login_type = models.CharField(
        max_length=20,
        choices=(
            ('password', '密码登录'),
            ('wechat', '微信登录'),
            ('token', 'Token登录'),
        ),
        default='password',
        verbose_name="登录方式"
    )
    is_success = models.BooleanField(default=True, verbose_name="是否成功")
    fail_reason = models.CharField(max_length=200, blank=True, null=True, verbose_name="失败原因")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登录时间")

    class Meta:
        db_table = "employee_login_record"
        verbose_name = "员工登录记录"
        verbose_name_plural = "员工登录记录"
        ordering = ["-created_at"]

    def __str__(self):
        status = "成功" if self.is_success else f"失败({self.fail_reason})"
        return f"{self.user.staff_id} - {self.login_type} - {status}"


class SMSVerificationCode(models.Model):
    """
    短信验证码模型
    """
    phone = models.CharField(max_length=20, verbose_name="手机号")
    code = models.CharField(max_length=6, verbose_name="验证码")
    purpose = models.CharField(
        max_length=20,
        choices=(
            ('login', '登录'),
            ('register', '注册'),
            ('bind_phone', '绑定手机号'),
            ('reset_password', '重置密码'),
            ('other', '其他'),
        ),
        default='login',
        verbose_name="用途"
    )
    is_used = models.BooleanField(default=False, verbose_name="是否已使用")
    expires_at = models.DateTimeField(verbose_name="过期时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="使用时间")

    class Meta:
        db_table = "sms_verification_code"
        verbose_name = "短信验证码"
        verbose_name_plural = "短信验证码"
        ordering = ["-created_at"]
        # Django 4.0+ 使用 indexes 替代 index_together
        indexes = [
            models.Index(fields=['phone', 'purpose']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.phone} - {self.code} ({self.purpose})"

    @property
    def is_expired(self):
        """是否已过期"""
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """是否有效（未使用且未过期）"""
        return not self.is_used and not self.is_expired
