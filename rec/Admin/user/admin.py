# user/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserAddress, UserCoupon, UserFavorite, EmployeeApp, EmployeeLoginRecord, \
    SMSVerificationCode
from django.utils.html import format_html
from django.contrib import messages
from django import forms


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    自定义用户管理界面
    """
    # 列表中显示的字段
    list_display = (
        'username', 'staff_id', 'real_name', 'phone', 'user_type',
        'department', 'position', 'is_staff_member', 'is_active',
        'last_login_time', 'created_at'
    )

    # 可搜索的字段
    search_fields = ('username', 'staff_id', 'real_name', 'phone', 'email', 'department')

    # 列表过滤器
    list_filter = ('user_type', 'is_staff_member', 'is_active', 'department', 'created_at')

    # 排序字段
    ordering = ('-created_at',)

    # 只读字段
    readonly_fields = ('created_at', 'updated_at', 'last_login', 'last_login_time')

    # 字段分组显示
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('账号类型', {'fields': ('user_type', 'is_staff_member', 'staff_id')}),
        ('微信信息', {'fields': ('openid', 'unionid', 'session_key', 'nickname', 'avatar_url')}),
        ('个人信息', {'fields': ('email', 'phone', 'gender', 'country', 'province', 'city')}),
        ('员工信息', {'fields': ('real_name', 'department', 'position')}),
        ('账号状态', {'fields': ('is_phone_bound', 'is_wechat_bound', 'is_verified', 'id_number')}),
        ('权限状态', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('时间信息', {'fields': ('last_login', 'last_login_time', 'created_at', 'updated_at')}),
    )

    # 添加用户时的字段分组
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
        ('账号类型', {
            'classes': ('wide',),
            'fields': ('user_type', 'staff_id', 'real_name'),
        }),
        ('员工信息', {
            'classes': ('wide',),
            'fields': ('department', 'position'),
        }),
        ('个人信息', {
            'classes': ('wide',),
            'fields': ('email', 'phone'),
        }),
    )

    # 每页显示数量
    list_per_page = 20

    actions = ['set_as_employee', 'set_as_customer', 'set_default_password', 'activate_users', 'deactivate_users']

    def set_as_employee(self, request, queryset):
        """批量设置为员工"""
        updated = 0
        for user in queryset:
            if user.user_type != 'employee':
                user.user_type = 'employee'
                user.is_staff_member = True

                # 如果没有员工工号，生成一个
                if not user.staff_id:
                    base_id = f"EMP{user.created_at.strftime('%Y%m%d')}"
                    existing_count = User.objects.filter(staff_id__startswith=base_id).count()
                    user.staff_id = f"{base_id}{existing_count + 1:04d}"

                user.save(update_fields=['user_type', 'is_staff_member', 'staff_id', 'updated_at'])
                updated += 1

        self.message_user(request, f'成功将 {updated} 个用户设置为员工')

    set_as_employee.short_description = "设置为员工"

    def set_as_customer(self, request, queryset):
        """批量设置为普通用户"""
        updated = 0
        for user in queryset:
            if user.user_type != 'customer':
                user.user_type = 'customer'
                user.is_staff_member = False
                user.staff_id = None
                user.department = None
                user.position = None
                user.save(
                    update_fields=['user_type', 'is_staff_member', 'staff_id', 'department', 'position', 'updated_at'])
                updated += 1

        self.message_user(request, f'成功将 {updated} 个用户设置为普通用户')

    set_as_customer.short_description = "设置为普通用户"

    def set_default_password(self, request, queryset):
        """设置默认密码 111@chery（仅员工账号）"""
        count = 0
        for user in queryset:
            if user.user_type == 'employee':
                user.set_default_password()
                count += 1

        if count > 0:
            self.message_user(request, f'成功为 {count} 个员工账号设置默认密码')
        else:
            self.message_user(request, '请选择员工账号', messages.WARNING)

    set_default_password.short_description = "设置默认密码(111@chery)"

    def get_form(self, request, obj=None, **kwargs):
        """自定义表单"""
        form = super().get_form(request, obj, **kwargs)

        # 如果是员工账号，显示部门职位字段
        if obj and obj.user_type == 'employee':
            form.base_fields['department'].required = True
            form.base_fields['position'].required = True

        return form

    def save_model(self, request, obj, form, change):
        """保存模型"""
        # 如果是新创建的员工账号，设置默认密码
        if not change and obj.user_type == 'employee' and not obj.has_password_set:
            obj.set_default_password()

        super().save_model(request, obj, form, change)


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    """用户地址管理界面"""
    list_display = (
        'user', 'receiver_name', 'receiver_phone', 'province', 'city', 'district', 'is_default', 'created_at')
    list_filter = ('province', 'city', 'is_default', 'address_tag')
    search_fields = ('user__username', 'receiver_name', 'receiver_phone', 'detail_address')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20

    fieldsets = (
        ('用户信息', {'fields': ('user',)}),
        ('收货人信息', {'fields': ('receiver_name', 'receiver_phone')}),
        ('地址信息', {'fields': ('country', 'province', 'city', 'district', 'detail_address', 'postal_code')}),
        ('地址配置', {'fields': ('address_tag', 'is_default')}),
        ('时间信息', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(UserCoupon)
class UserCouponAdmin(admin.ModelAdmin):
    """用户优惠券管理界面"""
    list_display = ('user', 'coupon_name', 'coupon_type', 'discount_value', 'status', 'valid_to', 'created_at')
    list_filter = ('coupon_type', 'status', 'valid_to')
    search_fields = ('user__username', 'coupon_name', 'coupon_code')
    readonly_fields = ('created_at',)
    list_per_page = 20

    fieldsets = (
        ('用户信息', {'fields': ('user',)}),
        ('优惠券信息', {'fields': ('coupon_type', 'coupon_name', 'coupon_code', 'description')}),
        ('优惠规则', {'fields': ('discount_value', 'min_order_amount')}),
        ('有效期', {'fields': ('valid_from', 'valid_to')}),
        ('使用状态', {'fields': ('status', 'used_at', 'used_order')}),
        ('时间信息', {'fields': ('created_at',)}),
    )


@admin.register(UserFavorite)
class UserFavoriteAdmin(admin.ModelAdmin):
    """用户收藏管理界面"""
    list_display = ('user', 'favorite_type', 'item_name', 'created_at')
    list_filter = ('favorite_type', 'created_at')
    search_fields = ('user__username', 'item_name')
    readonly_fields = ('created_at',)
    list_per_page = 20

    fieldsets = (
        ('用户信息', {'fields': ('user',)}),
        ('收藏内容', {'fields': ('favorite_type', 'item_id', 'item_name', 'item_image', 'item_url')}),
        ('备注信息', {'fields': ('notes',)}),
        ('时间信息', {'fields': ('created_at',)}),
    )


@admin.register(EmployeeApp)
class EmployeeAppAdmin(admin.ModelAdmin):
    """OCR应用系统管理界面"""
    list_display = ('app_name', 'app_id', 'open_type', 'is_active', 'sort_order', 'created_at')
    list_filter = ('is_active', 'open_type')
    search_fields = ('app_name', 'app_id', 'app_desc')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20

    fieldsets = (
        ('基本信息', {'fields': ('app_name', 'app_id', 'app_desc', 'icon_class')}),
        ('访问配置', {'fields': (
            'open_type',
            'app_url',
            'internal_path',
            'webview_url',
            'miniapp_path'
        )}),
        ('权限控制', {'fields': ('access_roles', 'require_auth')}),
        ('应用配置', {'fields': ('app_config', 'sort_order', 'is_active')}),
        ('时间信息', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(EmployeeLoginRecord)
class EmployeeLoginRecordAdmin(admin.ModelAdmin):
    """员工登录记录管理界面"""
    list_display = ('user', 'login_ip', 'login_type', 'is_success', 'created_at')
    list_filter = ('login_type', 'is_success', 'created_at')
    search_fields = ('user__username', 'user__staff_id', 'login_ip')
    readonly_fields = ('created_at',)
    list_per_page = 50

    fieldsets = (
        ('登录信息', {'fields': ('user', 'login_ip', 'user_agent', 'login_type')}),
        ('登录结果', {'fields': ('is_success', 'fail_reason')}),
        ('时间信息', {'fields': ('created_at',)}),
    )
