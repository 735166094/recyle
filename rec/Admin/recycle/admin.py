# recycle/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django import forms
from .models import ScrapCar, PriceRule, LocationCache, EvaluationMaterial
import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from datetime import datetime
import uuid


class ScrapCarAdminForm(forms.ModelForm):
    """自定义报废车管理表单，添加上传图片功能"""
    upload_image = forms.ImageField(
        required=False,
        label='上传新图片',
        help_text='选择新的车辆图片文件上传，将替换现有图片'
    )

    class Meta:
        model = ScrapCar
        fields = '__all__'


@admin.register(ScrapCar)
class ScrapCarAdmin(admin.ModelAdmin):
    form = ScrapCarAdminForm

    # 列表页面显示的字段
    list_display = [
        'id', 'contact_name', 'contact_phone', 'car_model', 'car_count',
        'region', 'status', 'can_start_display', 'wheel_type',
        'wheel_count', 'ternary_count', 'battery_count', 'battery_pack_count',
        'engine_count', 'weight', 'car_image_preview', 'estimated_price',
        'final_price', 'user_info', 'submit_time_formatted'
    ]

    # 列表过滤器
    list_filter = ['status', 'submit_time', 'region', 'can_start', 'wheel_type']

    # 搜索字段
    search_fields = [
        'contact_name', 'contact_phone', 'car_model',
        'user__username', 'user__phone', 'region'
    ]

    # 可编辑字段 - 直接在列表中使用status字段
    list_editable = ['status', 'estimated_price', 'final_price']

    # 每页显示数量
    list_per_page = 20

    # 只读字段 - 移除状态字段，使其可编辑
    readonly_fields = [
        'contact_name_display', 'contact_phone_display', 'car_model_display',
        'car_count_display', 'region_display', 'can_start_display',
        'wheel_type_display', 'wheel_count_display', 'ternary_count_display',
        'battery_count_display', 'battery_pack_count_display', 'engine_count_display',
        'weight_display', 'car_image_preview_large', 'user_info',
        'submit_time_formatted', 'address_display', 'remark_display', 'update_time',
        'status_history_display'
    ]

    # 字段分组显示 - 优化显示布局，状态字段可编辑
    fieldsets = (
        (_('联系人信息'), {
            'fields': (
                'contact_name_display',
                'contact_phone_display',
            )
        }),
        (_('车辆基本信息'), {
            'fields': (
                'car_model_display',
                'car_count_display',
                'region_display',
                'status',  # 状态字段改为可编辑
                'can_start_display',
            )
        }),
        (_('车辆部件详情'), {
            'fields': (
                'wheel_type_display',
                'wheel_count_display',
                'ternary_count_display',
                'battery_count_display',
                'battery_pack_count_display',
                'engine_count_display',
                'weight_display',
            )
        }),
        (_('车辆图片管理'), {
            'fields': (
                'car_image_preview_large',
                'upload_image',  # 上传新图片
                'car_image_path',  # 修改图片路径
            ),
            'classes': ('wide',),
            'description': '可以通过上传新图片或直接修改图片路径来更新车辆图片'
        }),
        (_('价格信息'), {
            'fields': (
                'estimated_price',
                'final_price'
            )
        }),
        (_('其他信息'), {
            'fields': (
                'address_display',
                'remark_display'
            )
        }),
        (_('系统信息'), {
            'fields': (
                'user_info',
                'submit_time_formatted',
                'update_time',
                'status_history_display'  # 新增状态历史
            )
        }),
    )

    # 自定义显示方法 - 确保所有字段都有对应的显示方法
    def contact_name_display(self, obj):
        return obj.contact_name

    contact_name_display.short_description = '联系人姓名'

    def contact_phone_display(self, obj):
        return obj.contact_phone

    contact_phone_display.short_description = '联系电话'

    def car_model_display(self, obj):
        return obj.car_model

    car_model_display.short_description = '车型'

    def car_count_display(self, obj):
        return obj.car_count

    car_count_display.short_description = '车辆数量'

    def region_display(self, obj):
        return obj.region

    region_display.short_description = '所在地区'

    def address_display(self, obj):
        return obj.address if obj.address else '未填写'

    address_display.short_description = '详细地址'

    def remark_display(self, obj):
        return obj.remark if obj.remark else '无'

    remark_display.short_description = '备注信息'

    def wheel_type_display(self, obj):
        return obj.wheel_type if obj.wheel_type else '未填写'

    wheel_type_display.short_description = '轮毂类型'

    def wheel_count_display(self, obj):
        return obj.wheel_count

    wheel_count_display.short_description = '轮毂数量'

    def ternary_count_display(self, obj):
        return obj.ternary_count

    ternary_count_display.short_description = '三元催化器数量'

    def battery_count_display(self, obj):
        return obj.battery_count

    battery_count_display.short_description = '铅蓄电池数量'

    def battery_pack_count_display(self, obj):
        return obj.battery_pack_count

    battery_pack_count_display.short_description = '电池包数量'

    def engine_count_display(self, obj):
        return obj.engine_count

    engine_count_display.short_description = '发动机数量'

    def weight_display(self, obj):
        return f"{obj.weight}千克" if obj.weight else '未填写'

    weight_display.short_description = '整备质量'

    # 修改状态显示方法，使其在列表中也显示颜色
    def get_status_display_colored(self, obj):
        status_color = {
            'pending': '#ffa500',  # 橙色
            'priced': '#1890ff',  # 蓝色
            'confirmed': '#52c41a',  # 绿色
            'cancelled': '#f5222d'  # 红色
        }.get(obj.status, 'gray')

        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 4px 8px; border-radius: 4px; background-color: {};">{}</span>',
            'white',
            status_color,
            obj.get_status_display()
        )

    get_status_display_colored.short_description = '状态显示'

    def user_info(self, obj):
        if obj.user:
            user_info = f"{obj.user.username}"
            if obj.user.phone:
                user_info += f" ({obj.user.phone})"
            if obj.user.nickname:
                user_info += f" - {obj.user.nickname}"
            return user_info
        return "未知用户"

    user_info.short_description = '提交用户'

    def submit_time_formatted(self, obj):
        return obj.submit_time.strftime('%Y-%m-%d %H:%M:%S')

    submit_time_formatted.short_description = '提交时间'

    def can_start_display(self, obj):
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            'green' if obj.can_start else 'red',
            "能" if obj.can_start else "不能"
        )

    can_start_display.short_description = '能否启动'

    # 列表页图片预览 - 小尺寸
    def car_image_preview(self, obj):
        image_url = obj.get_car_image_url()
        if image_url:
            return format_html(
                '<a href="{}" target="_blank" title="点击查看大图">'
                '<img src="{}" style="width: 60px; height: 60px; object-fit: cover; border-radius: 4px; border: 1px solid #ddd;" />'
                '</a>',
                image_url, image_url
            )
        return format_html(
            '<div style="width: 60px; height: 60px; background: #f5f5f5; display: flex; align-items: center; justify-content: center; border-radius: 4px; border: 1px solid #ddd; color: #999;">'
            '无图片'
            '</div>'
        )

    car_image_preview.short_description = '车辆图片'

    # 详情页图片预览 - 大尺寸（统一大小）
    def car_image_preview_large(self, obj):
        image_url = obj.get_car_image_url()
        if image_url:
            return format_html(
                '<div style="text-align: center;">'
                '<a href="{}" target="_blank" title="点击查看原图">'
                '<img src="{}" style="width: 300px; height: 200px; object-fit: contain; border: 1px solid #ddd; border-radius: 8px; background: #f9f9f9;" />'
                '</a>'
                '<div style="margin-top: 8px; color: #666; font-size: 12px;">点击图片查看原图</div>'
                '</div>',
                image_url, image_url
            )
        return format_html(
            '<div style="width: 300px; height: 200px; background: #f5f5f5; display: flex; align-items: center; justify-content: center; border-radius: 8px; border: 1px dashed #ddd; color: #999; margin: 0 auto;">'
            '暂无车辆图片'
            '</div>'
        )

    car_image_preview_large.short_description = '车辆图片预览'

    def status_history_display(self, obj):
        """状态变更历史显示"""
        return obj.status_history_display()

    status_history_display.short_description = '状态变更历史'

    def save_model(self, request, obj, form, change):
        """保存模型时处理图片上传和状态更新"""
        # 检查是否有上传新图片
        upload_image = form.cleaned_data.get('upload_image')

        if upload_image:
            try:
                # 生成唯一文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                unique_id = uuid.uuid4().hex[:8]
                file_extension = os.path.splitext(upload_image.name)[1].lower()
                if not file_extension:
                    file_extension = '.jpg'
                filename = f"car_image_{timestamp}_{unique_id}{file_extension}"

                # 保存路径
                save_path = os.path.join('scrap_cars', datetime.now().strftime('%Y/%m'), filename)

                # 保存文件
                saved_path = default_storage.save(save_path, ContentFile(upload_image.read()))

                # 更新图片路径
                obj.car_image_path = saved_path

            except Exception as e:
                # 如果上传失败，保留原有图片路径
                pass

        # 记录状态变更
        if change:
            original_obj = ScrapCar.objects.get(pk=obj.pk)
            if original_obj.status != obj.status:
                # 使用新的状态更新方法
                obj.update_status(obj.status, f'管理员操作：{request.user.username}', request.user)

        # 调用父类保存方法
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        """优化查询性能"""
        queryset = super().get_queryset(request)
        return queryset.select_related('user')

    def has_add_permission(self, request):
        """禁止在后台手动添加记录，只能通过小程序提交"""
        return False

    def has_delete_permission(self, request, obj=None):
        """只有超级用户可以删除记录"""
        return request.user.is_superuser

    # 自定义操作
    actions = ['mark_as_priced', 'mark_as_confirmed', 'mark_as_cancelled']

    def mark_as_priced(self, request, queryset):
        """标记为已报价"""
        for obj in queryset:
            obj.update_status('priced', '批量操作：管理员标记为已报价', request.user)
            obj.save()
        self.message_user(request, f'成功将 {queryset.count()} 条记录标记为已报价')

    mark_as_priced.short_description = "标记选中的记录为已报价"

    def mark_as_confirmed(self, request, queryset):
        """标记为已同意"""
        for obj in queryset:
            obj.update_status('confirmed', '批量操作：管理员标记为已同意', request.user)
            obj.save()
        self.message_user(request, f'成功将 {queryset.count()} 条记录标记为已同意')

    mark_as_confirmed.short_description = "标记选中的记录为已同意"

    def mark_as_cancelled(self, request, queryset):
        """标记为已取消"""
        for obj in queryset:
            obj.update_status('cancelled', '批量操作：管理员标记为已取消', request.user)
            obj.save()
        self.message_user(request, f'成功将 {queryset.count()} 条记录标记为已取消')

    mark_as_cancelled.short_description = "标记选中的记录为已取消"

    # 修改详情页的显示标题
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj:
            form.base_fields['status'].help_text = '可编辑字段 - 修改后会自动保存并记录变更历史'
            form.base_fields['estimated_price'].help_text = '可编辑字段 - 填写后状态将自动更新为"已报价"'
            form.base_fields['final_price'].help_text = '可编辑字段'
            form.base_fields['car_image_path'].help_text = '可编辑字段 - 输入图片URL或相对路径'
            form.base_fields['upload_image'].help_text = '上传新图片将替换现有图片'
        return form


@admin.register(PriceRule)
class PriceRuleAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'car_type', 'base_price', 'weight_factor',
        'condition_factor', 'is_active', 'created_at_formatted'
    ]
    list_filter = ['car_type', 'is_active', 'created_at']
    search_fields = ['name', 'car_type']
    list_editable = ['base_price', 'weight_factor', 'condition_factor', 'is_active']
    readonly_fields = ['created_at_formatted']

    fieldsets = (
        (None, {
            'fields': ('name', 'car_type', 'is_active')
        }),
        (_('价格参数'), {
            'fields': ('base_price', 'weight_factor', 'condition_factor')
        }),
        (_('时间信息'), {
            'fields': ('created_at_formatted',)
        }),
    )

    def created_at_formatted(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M') if obj.created_at else '-'

    created_at_formatted.short_description = '创建时间'


@admin.register(EvaluationMaterial)
class EvaluationMaterialAdmin(admin.ModelAdmin):
    list_display = ['name', 'price_per_ton', 'factor', 'is_active', 'sort_order', 'created_at']
    list_editable = ['price_per_ton', 'factor', 'is_active', 'sort_order']
    search_fields = ['name']
    list_filter = ['is_active']
    ordering = ['sort_order', 'id']
