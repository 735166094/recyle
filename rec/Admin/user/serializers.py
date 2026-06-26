# user/serializers.py
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import User, UserAddress, UserCoupon, UserFavorite, EmployeeApp, SMSVerificationCode
from rest_framework_simplejwt.tokens import RefreshToken
import re
from django.db.models import Q
import logging
from .utils import AccountManager

logger = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    """
    用户序列化器
    """
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    display_name = serializers.SerializerMethodField(read_only=True)
    available_login_methods = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'nickname', 'avatar_url',
            'gender', 'country', 'province', 'city', 'points',
            'user_type', 'user_type_display', 'is_staff_member',
            'is_verified', 'real_name', 'staff_id', 'department', 'position',
            'is_phone_bound', 'is_wechat_bound', 'has_password_set',
            'display_name', 'available_login_methods',
            'created_at', 'updated_at', 'last_login', 'last_login_time'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'last_login',
            'points', 'last_login_time', 'has_password_set',
            'display_name', 'available_login_methods'
        ]

    @staticmethod
    def get_display_name(obj):
        """获取显示名称"""
        return obj.display_name

    @staticmethod
    def get_available_login_methods(obj):
        """获取可用的登录方式"""
        return obj.available_login_methods

    def validate_phone(self, value):
        """验证手机号唯一性"""
        if value:
            # 检查是否已被其他活跃账号使用
            existing_user = User.objects.filter(
                phone=value,
                is_active=True
            ).exclude(id=self.instance.id if self.instance else None).first()

            if existing_user:
                raise serializers.ValidationError("该手机号已被其他账号使用")

        return value


class UserSimpleSerializer(serializers.ModelSerializer):
    """ 用户信息序列化器"""

    avatar_url_full = serializers.SerializerMethodField()
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'nickname', 'avatar_url', 'avatar_url_full',
            'points', 'staff_id', 'real_name', 'user_type', 'user_type_display',
            'department', 'position'
        ]

    def get_avatar_url_full(self, obj):
        """获取完整的头像URL"""
        if obj.avatar_url:
            request = self.context.get('request')
            if request and obj.avatar_url.startswith('/'):
                return request.build_absolute_uri(obj.avatar_url)
        return obj.avatar_url


class UserLoginSerializer(serializers.Serializer):
    """
    通用登录序列化器
    """
    login_type = serializers.ChoiceField(
        choices=[('phone', '手机号'), ('staff_id', '员工工号'), ('username', '用户名')],
        required=True,
        help_text="登录类型"
    )
    identifier = serializers.CharField(required=True, help_text="登录标识（手机号/员工工号/用户名）")
    password = serializers.CharField(required=False, write_only=True, help_text="密码")
    code = serializers.CharField(required=False, help_text="短信验证码（手机号登录时使用）")

    def validate(self, attrs):
        login_type = attrs.get('login_type')
        identifier = attrs.get('identifier')
        password = attrs.get('password')
        code = attrs.get('code')

        # 根据登录类型查找用户
        user = None

        if login_type == 'phone':
            # 手机号登录
            if not code:
                raise serializers.ValidationError("手机号登录需要验证码")

            user = User.objects.filter(
                phone=identifier,
                is_active=True
            ).first()

            if not user:
                raise serializers.ValidationError("手机号未注册或账号已禁用")

            # 验证短信验证码
            is_valid, error_msg = AccountManager.verify_phone_code(identifier, code, 'login')
            if not is_valid:
                raise serializers.ValidationError(f"验证码错误: {error_msg}")

        elif login_type == 'staff_id':
            # 员工工号登录
            if not password:
                raise serializers.ValidationError("员工登录需要密码")

            user = User.objects.filter(
                staff_id=identifier,
                user_type__in=['employee', 'admin'],
                is_active=True
            ).first()

            if not user:
                raise serializers.ValidationError("员工工号不存在或账号已禁用")

            # 验证密码（支持默认密码）
            if not user.check_employee_password(password):
                raise serializers.ValidationError("密码错误")

        elif login_type == 'username':
            # 用户名登录
            if not password:
                raise serializers.ValidationError("用户名登录需要密码")

            user = User.objects.filter(
                username=identifier,
                is_active=True
            ).first()

            if not user:
                raise serializers.ValidationError("用户名不存在或账号已禁用")

            # 验证密码
            if not user.check_password(password):
                raise serializers.ValidationError("密码错误")

        if not user:
            raise serializers.ValidationError("登录失败")

        attrs['user'] = user
        return attrs


class EmployeeLoginSerializer(serializers.Serializer):
    """
    员工登录序列化器 - 专门用于员工后台登录
    """
    staff_id = serializers.CharField(required=True, max_length=50, help_text="员工工号")
    password = serializers.CharField(required=True, write_only=True, help_text="密码")

    def validate(self, attrs):
        staff_id = attrs.get('staff_id')
        password = attrs.get('password')

        try:
            user = User.objects.get(
                staff_id=staff_id,
                user_type__in=['employee', 'admin'],
                is_active=True
            )

            # 验证密码（支持默认密码）
            if not user.check_employee_password(password):
                raise serializers.ValidationError("密码错误")

            attrs['user'] = user
            return attrs

        except User.DoesNotExist:
            raise serializers.ValidationError("员工账号不存在或已被禁用")


class EmployeeRegisterSerializer(serializers.ModelSerializer):
    """员工注册序列化器（仅限管理员使用）"""
    password = serializers.CharField(
        write_only=True,
        min_length=6,
        validators=[validate_password],
        required=False,
        help_text="密码（默认：111@chery）"
    )
    password_confirm = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'staff_id', 'real_name', 'department', 'position',
            'phone', 'email', 'password', 'password_confirm'
        ]
        extra_kwargs = {
            'staff_id': {'required': True},
            'real_name': {'required': True},
            'department': {'required': True},
            'position': {'required': True},
        }

    def validate(self, attrs):
        # 检查密码确认
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise serializers.ValidationError({"password_confirm": "两次密码不一致"})

        # 检查员工工号是否已存在
        staff_id = attrs.get('staff_id')
        if staff_id and User.objects.filter(staff_id=staff_id, user_type='employee').exists():
            raise serializers.ValidationError({"staff_id": "该员工工号已存在"})

        # 检查手机号是否已被使用
        phone = attrs.get('phone')
        if phone and User.objects.filter(phone=phone, is_active=True).exists():
            raise serializers.ValidationError({"phone": "该手机号已被其他账号使用"})

        return attrs

    def create(self, validated_data):
        # 提取密码相关字段
        password = validated_data.pop('password', None)
        validated_data.pop('password_confirm', None)

        # 使用自定义管理器创建员工账号
        user = User.objects.create_employee(
            staff_id=validated_data['staff_id'],
            real_name=validated_data['real_name'],
            department=validated_data['department'],
            position=validated_data['position'],
            password=password or '111@chery',
            phone=validated_data.get('phone'),
            email=validated_data.get('email')
        )

        return user


class CustomerRegisterSerializer(serializers.ModelSerializer):
    """普通用户注册序列化器"""
    password = serializers.CharField(write_only=True, min_length=6, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    code = serializers.CharField(write_only=True, required=True, help_text="短信验证码")

    class Meta:
        model = User
        fields = ['phone', 'password', 'password_confirm', 'code']

    def validate(self, attrs):
        phone = attrs.get('phone')
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')
        code = attrs.get('code')

        if password != password_confirm:
            raise serializers.ValidationError({"password_confirm": "两次密码不一致"})

        # 验证手机号是否已注册
        if User.objects.filter(phone=phone, is_active=True).exists():
            raise serializers.ValidationError({"phone": "该手机号已注册"})

        # 验证短信验证码
        is_valid, error_msg = AccountManager.verify_phone_code(phone, code, 'register')
        if not is_valid:
            raise serializers.ValidationError({"code": f"验证码错误: {error_msg}"})

        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        validated_data.pop('code')

        # 使用手机号作为用户名
        phone = validated_data['phone']

        # 创建普通用户
        user = User.objects.create_user(
            username=phone,  # 使用手机号作为用户名
            phone=phone,
            password=validated_data['password'],
            user_type='customer',
            is_active=True,
            is_phone_bound=True,
            nickname=phone
        )

        return user


class WeChatLoginSerializer(serializers.Serializer):
    """微信登录序列化器"""
    code = serializers.CharField(required=True, help_text="微信登录code")
    encrypted_data = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="加密数据")
    iv = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="加密算法的初始向量")

    def validate(self, attrs):
        code = attrs.get('code')
        if not code:
            raise serializers.ValidationError("微信登录code不能为空")

        return attrs


class PhoneBindSerializer(serializers.Serializer):
    """绑定手机号序列化器"""
    phone = serializers.CharField(required=True, max_length=11, help_text="手机号")
    code = serializers.CharField(required=True, max_length=6, help_text="短信验证码")

    def validate(self, attrs):
        phone = attrs.get('phone')
        code = attrs.get('code')

        # 验证手机号格式
        phone_pattern = re.compile(r'^1[3-9]\d{9}$')
        if not phone_pattern.match(phone):
            raise serializers.ValidationError({"phone": "请输入有效的手机号码"})

        # 验证短信验证码
        is_valid, error_msg = AccountManager.verify_phone_code(phone, code, 'bind_phone')
        if not is_valid:
            raise serializers.ValidationError({"code": f"验证码错误: {error_msg}"})

        return attrs


class SMSVerifySerializer(serializers.Serializer):
    """短信验证序列化器"""
    phone = serializers.CharField(required=True, max_length=11, help_text="手机号")
    purpose = serializers.ChoiceField(
        choices=[
            ('login', '登录'),
            ('register', '注册'),
            ('bind_phone', '绑定手机号'),
            ('reset_password', '重置密码'),
            ('other', '其他')
        ],
        required=True,
        help_text="验证码用途"
    )

    def validate(self, attrs):
        phone = attrs.get('phone')
        purpose = attrs.get('purpose')

        # 验证手机号格式
        phone_pattern = re.compile(r'^1[3-9]\d{9}$')
        if not phone_pattern.match(phone):
            raise serializers.ValidationError({"phone": "请输入有效的手机号码"})

        # 根据不同用途进行验证
        if purpose == 'register':
            # 注册时检查手机号是否已注册
            if User.objects.filter(phone=phone, is_active=True).exists():
                raise serializers.ValidationError({"phone": "该手机号已注册"})

        return attrs


class UserProfileWithTokenSerializer(UserSerializer):
    """用户信息带token的序列化器"""
    token = serializers.SerializerMethodField()

    @staticmethod
    def get_token(obj):
        """获取token"""
        refresh = RefreshToken.for_user(obj)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['token']


class EmployeeProfileWithTokenSerializer(UserSimpleSerializer):
    """员工信息带token的序列化器"""
    token = serializers.SerializerMethodField()

    @staticmethod
    def get_token(obj):
        """获取token"""
        refresh = RefreshToken.for_user(obj)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    class Meta(UserSimpleSerializer.Meta):
        fields = UserSimpleSerializer.Meta.fields + ['token']


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """用户资料更新序列化器"""

    class Meta:
        model = User
        fields = [
            'nickname', 'avatar_url', 'gender',
            'country', 'province', 'city',
            'email', 'phone', 'real_name'
        ]

    def validate_phone(self, value):
        """验证手机号唯一性"""
        if value:
            # 检查是否已被其他活跃账号使用
            existing_user = User.objects.filter(
                phone=value,
                is_active=True
            ).exclude(id=self.instance.id).first()

            if existing_user:
                raise serializers.ValidationError("该手机号已被其他账号使用")

        return value

    def update(self, instance, validated_data):
        """更新用户信息"""
        # 如果是员工账号，可以更新真实姓名
        if instance.user_type in ['employee', 'admin'] and 'real_name' in validated_data:
            instance.real_name = validated_data['real_name']

        # 更新其他字段
        if 'nickname' in validated_data:
            instance.nickname = validated_data['nickname']

        if 'avatar_url' in validated_data:
            instance.avatar_url = validated_data['avatar_url']

        if 'gender' in validated_data:
            instance.gender = validated_data['gender']

        if 'country' in validated_data:
            instance.country = validated_data['country']

        if 'province' in validated_data:
            instance.province = validated_data['province']

        if 'city' in validated_data:
            instance.city = validated_data['city']

        if 'email' in validated_data:
            instance.email = validated_data['email']

        if 'phone' in validated_data:
            instance.phone = validated_data['phone']
            instance.is_phone_bound = True

        instance.save()
        return instance


class EmployeeProfileUpdateSerializer(serializers.ModelSerializer):
    """员工资料更新序列化器"""

    class Meta:
        model = User
        fields = [
            'real_name', 'department', 'position',
            'email', 'phone', 'avatar_url'
        ]

    def validate_phone(self, value):
        """验证手机号唯一性"""
        if value:
            # 检查是否已被其他活跃账号使用
            existing_user = User.objects.filter(
                phone=value,
                is_active=True
            ).exclude(id=self.instance.id).first()

            if existing_user:
                raise serializers.ValidationError("该手机号已被其他账号使用")

        return value

    def update(self, instance, validated_data):
        """更新员工信息"""
        if instance.user_type not in ['employee', 'admin']:
            raise serializers.ValidationError("只有员工账号可以更新这些信息")

        if 'real_name' in validated_data:
            instance.real_name = validated_data['real_name']

        if 'department' in validated_data:
            instance.department = validated_data['department']

        if 'position' in validated_data:
            instance.position = validated_data['position']

        if 'email' in validated_data:
            instance.email = validated_data['email']

        if 'phone' in validated_data:
            instance.phone = validated_data['phone']
            instance.is_phone_bound = True

        if 'avatar_url' in validated_data:
            instance.avatar_url = validated_data['avatar_url']

        instance.save()
        return instance


class UserPasswordChangeSerializer(serializers.Serializer):
    """用户密码修改序列化器"""
    old_password = serializers.CharField(required=True, write_only=True, help_text="旧密码")
    new_password = serializers.CharField(required=True, write_only=True, min_length=6, help_text="新密码")
    confirm_password = serializers.CharField(required=True, write_only=True, help_text="确认密码")

    def validate(self, attrs):
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')

        if new_password != confirm_password:
            raise serializers.ValidationError({"confirm_password": "两次输入的密码不一致"})

        return attrs


class EmployeePasswordChangeSerializer(serializers.Serializer):
    """员工密码修改序列化器"""
    old_password = serializers.CharField(required=True, write_only=True, help_text="旧密码")
    new_password = serializers.CharField(required=True, write_only=True, min_length=6, help_text="新密码")
    confirm_password = serializers.CharField(required=True, write_only=True, help_text="确认密码")

    def validate(self, attrs):
        user = self.context.get('user')
        old_password = attrs.get('old_password')
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')

        # 检查旧密码
        if not user.check_employee_password(old_password):
            raise serializers.ValidationError({"old_password": "旧密码错误"})

        if new_password != confirm_password:
            raise serializers.ValidationError({"confirm_password": "两次输入的密码不一致"})

        return attrs


class UserAddressSerializer(serializers.ModelSerializer):
    """用户地址序列化器"""
    region = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserAddress
        fields = [
            'id', 'user', 'receiver_name', 'receiver_phone', 'country', 'province', 'city', 'district',
            'detail_address', 'postal_code', 'address_tag', 'is_default', 'created_at', 'updated_at', 'region'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    @staticmethod
    def get_region(obj):
        """返回地区数组"""
        return [obj.province, obj.city, obj.district] if obj.province and obj.city and obj.district else []

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def validate(self, attrs):
        if not all([attrs.get('province'), attrs.get('city'), attrs.get('district')]):
            raise serializers.ValidationError("请选择完整的省市区信息")

        phone_pattern = re.compile(r'^1[3-9]\d{9}$')
        if not phone_pattern.match(attrs.get('receiver_phone', '')):
            raise serializers.ValidationError({"receiver_phone": "请输入有效的手机号码"})

        return attrs


class UserCouponSerializer(serializers.ModelSerializer):
    """用户优惠券序列化器"""
    coupon_type_display = serializers.CharField(source='get_coupon_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserCoupon
        fields = [
            'id', 'user', 'coupon_type', 'coupon_type_display', 'coupon_name',
            'coupon_code', 'description', 'discount_value', 'min_order_amount',
            'valid_from', 'valid_to', 'status', 'status_display', 'is_valid',
            'used_at', 'used_order', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']


class UserFavoriteSerializer(serializers.ModelSerializer):
    """用户收藏序列化器"""
    favorite_type_display = serializers.CharField(source='get_favorite_type_display', read_only=True)
    item_url = serializers.CharField(required=False, allow_blank=True, max_length=500)

    class Meta:
        model = UserFavorite
        fields = [
            'id', 'user', 'favorite_type', 'favorite_type_display', 'item_id',
            'item_name', 'item_image', 'item_url', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']

    def validate(self, attrs):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user
            favorite_type = attrs.get('favorite_type')
            item_id = attrs.get('item_id')

            if favorite_type and item_id:
                existing_favorite = UserFavorite.objects.filter(
                    user=user,
                    favorite_type=favorite_type,
                    item_id=item_id
                ).exists()

                if existing_favorite:
                    raise serializers.ValidationError({
                        'detail': '您已经收藏过此商品'
                    })

        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user

        favorite_type = validated_data.get('favorite_type')
        item_id = validated_data.get('item_id')
        user = validated_data.get('user')

        if user and favorite_type and item_id:
            existing_favorite = UserFavorite.objects.filter(
                user=user,
                favorite_type=favorite_type,
                item_id=item_id
            ).first()

            if existing_favorite:
                return existing_favorite

        return super().create(validated_data)


class EmployeeAppSerializer(serializers.ModelSerializer):
    """应用系统序列化器"""
    open_type_display = serializers.CharField(source='get_open_type_display', read_only=True)
    app_access_info = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeApp
        fields = [
            'id', 'app_id', 'app_name', 'app_desc', 'icon_class',
            'app_url', 'internal_path', 'webview_url', 'miniapp_path',
            'open_type', 'open_type_display', 'app_access_info',
            'access_roles', 'require_auth', 'app_config', 'is_active',
            'sort_order', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    @staticmethod
    def get_app_access_info(obj):
        """获取应用访问信息"""
        return obj.get_app_access_url()


class EmployeeAppAccessSerializer(serializers.Serializer):
    """员工应用访问序列化器"""
    app_id = serializers.CharField(required=True, help_text="应用ID")

    def validate(self, attrs):
        app_id = attrs.get('app_id')

        try:
            app = EmployeeApp.objects.get(app_id=app_id, is_active=True)
            attrs['app'] = app
        except EmployeeApp.DoesNotExist:
            raise serializers.ValidationError("应用不存在或已禁用")

        return attrs
