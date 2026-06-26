# points/admin.py
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import Order, PointsRule, PointsRecord, UserDailyPoints, PointsTransaction, UserMonthlySummary


@admin.register(PointsRule)
class PointsRuleAdmin(admin.ModelAdmin):
    list_display = ('rule_id', 'rule_name', 'rule_type', 'green_type', 'points_value', 'is_active', 'sort_order')
    list_filter = ('rule_type', 'green_type', 'is_active')
    search_fields = ('rule_id', 'rule_name', 'description')
    list_per_page = 20

    fieldsets = (
        ('基本信息', {'fields': ('rule_id', 'rule_name', 'rule_type', 'green_type')}),
        ('积分设置', {'fields': ('points_value', 'points_limit', 'daily_limit', 'monthly_limit')}),
        ('条件设置', {'fields': ('condition_type', 'condition_value', 'condition_unit')}),
        ('绿色生活设置', {'fields': ('need_upload', 'upload_desc', 'certificate_name')}),
        ('规则说明', {'fields': ('description', 'instructions')}),
        ('状态设置', {'fields': ('is_active', 'sort_order')}),
        ('时间信息', {'fields': ('created_at', 'updated_at')}),
    )

    readonly_fields = ('created_at', 'updated_at')


@admin.register(PointsRecord)
class PointsRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'points_type', 'green_type', 'points_change', 'current_points', 'is_verified', 'created_at')
    list_filter = ('points_type', 'green_type', 'is_verified', 'created_at')
    search_fields = ('user__username', 'user__phone', 'description')
    list_per_page = 30

    # 添加这个字段配置，使 current_points 在表单中只读
    fieldsets = (
        ('基本信息', {'fields': ('user', 'points_rule', 'points_type', 'green_type')}),
        ('积分变动', {'fields': ('points_change',)}),
        ('关联信息', {'fields': ('related_id', 'order_no', 'recycle_id')}),
        ('绿色生活详情', {'fields': (
            'upload_image',
            'certificate_image',
            'steps_count',
            'days_count',
            'is_verified',
            'verified_by',
            'verified_at'
        )}),
        ('备注信息', {'fields': ('description', 'remark')}),
        ('时间信息', {'fields': ('created_at', 'updated_at')}),
    )

    # 只读字段
    readonly_fields = ('created_at', 'updated_at', 'current_points')

    def get_readonly_fields(self, request, obj=None):
        """
        根据对象状态返回只读字段
        """
        if obj:  # 编辑现有记录时
            return self.readonly_fields + ('user', 'points_change', 'current_points')
        else:  # 创建新记录时
            return self.readonly_fields

    def save_model(self, request, obj, form, change):
        """
        重写保存模型的方法，确保积分正确更新
        """
        # 如果是新建记录并且 current_points 未设置
        if not change and not obj.current_points:
            # 获取用户当前积分
            user_points = obj.user.points

            # 计算变动后的积分
            obj.current_points = user_points + obj.points_change

            # 更新用户总积分
            obj.user.points = obj.current_points
            obj.user.save(update_fields=['points', 'updated_at'])

        super().save_model(request, obj, form, change)


@admin.register(UserDailyPoints)
class UserDailyPointsAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'total_points', 'green_points', 'transport_days', 'food_days', 'walk_steps')
    list_filter = ('date',)
    search_fields = ('user__username', 'user__phone')
    list_per_page = 20

    fieldsets = (
        ('基本信息', {'fields': ('user', 'date')}),
        ('积分统计', {'fields': (
            'sign_points', 'task_points', 'green_points',
            'purchase_points', 'recycle_points', 'consume_points',
            'total_points'
        )}),
        ('绿色生活统计', {'fields': (
            'transport_days', 'food_days', 'walk_steps', 'learning_count'
        )}),
        ('时间信息', {'fields': ('created_at', 'updated_at')}),
    )

    readonly_fields = ('created_at', 'updated_at')


@admin.register(PointsTransaction)
class PointsTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_no', 'user', 'transaction_type', 'points_amount', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('transaction_no', 'user__username', 'product_name')
    list_per_page = 20

    fieldsets = (
        ('基本信息', {'fields': ('transaction_no', 'user', 'transaction_type', 'points_amount', 'status')}),
        ('商品信息', {'fields': ('product_id', 'product_name', 'product_points')}),
        ('兑换信息', {'fields': ('redeem_address', 'express_no')}),
        ('备注信息', {'fields': ('remark',)}),
        ('时间信息', {'fields': ('created_at', 'updated_at', 'completed_at')}),
    )

    readonly_fields = ('created_at', 'updated_at', 'transaction_no')


@admin.register(UserMonthlySummary)
class UserMonthlySummaryAdmin(admin.ModelAdmin):
    list_display = ('user', 'year', 'month', 'total_earned', 'total_consumed', 'green_days_total')
    list_filter = ('year', 'month')
    search_fields = ('user__username', 'user__phone')
    list_per_page = 20

    fieldsets = (
        ('基本信息', {'fields': ('user', 'year', 'month')}),
        ('积分统计', {'fields': ('total_earned', 'total_consumed', 'ending_balance')}),
        ('绿色生活统计', {'fields': (
            'green_days_total', 'green_points_total',
            'transport_days', 'food_days', 'walk_points', 'learning_points'
        )}),
        ('达标情况', {'fields': (
            'is_transport_qualified', 'is_food_qualified', 'is_walk_qualified'
        )}),
        ('时间信息', {'fields': ('created_at', 'updated_at')}),
    )

    readonly_fields = ('created_at', 'updated_at')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'product_name', 'product_points', 'quantity_display',
        'receiver_name', 'receiver_phone', 'full_address', 'express_no',
        'status', 'created_at', 'completed_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['transaction_no', 'user__username', 'product_name']
    list_editable = ['status', 'express_no']   # 允许直接填写快递单号
    readonly_fields = ['transaction_no', 'created_at', 'updated_at', 'completed_at']
    actions = ['mark_as_shipped', 'mark_as_completed', 'mark_as_cancelled']
    fieldsets = (
        ('基本信息', {'fields': ('transaction_no', 'user', 'transaction_type', 'points_amount', 'status')}),
        ('商品信息', {'fields': ('product_id', 'product_name', 'product_points')}),
        ('收货信息', {'fields': ('redeem_address', 'express_no')}),
        ('时间信息', {'fields': ('created_at', 'updated_at', 'completed_at')}),
        ('备注', {'fields': ('remark',)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(transaction_type='redeem').select_related('user', 'redeem_address')

    def quantity_display(self, obj):
        if obj.remark and '×' in obj.remark:
            try:
                return int(obj.remark.split('×')[-1].strip())
            except (ValueError, IndexError):
                pass
        return 1
    quantity_display.short_description = '数量'

    def receiver_name(self, obj):
        return obj.redeem_address.receiver_name if obj.redeem_address else '-'
    receiver_name.short_description = '收货人'

    def receiver_phone(self, obj):
        return obj.redeem_address.receiver_phone if obj.redeem_address else '-'
    receiver_phone.short_description = '联系电话'

    def full_address(self, obj):
        if obj.redeem_address:
            addr = obj.redeem_address
            return f"{addr.province}{addr.city}{addr.district}{addr.detail_address}"
        return '-'
    full_address.short_description = '收货地址'

    # 批量操作（同上）
    def mark_as_shipped(self, request, queryset):
        updated = queryset.update(status='completed', completed_at=timezone.now())
        self.message_user(request, f"已标记 {updated} 个订单为已发货")
    mark_as_shipped.short_description = "标记为已发货"

    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed', completed_at=timezone.now())
        self.message_user(request, f"已标记 {updated} 个订单为已完成")
    mark_as_completed.short_description = "标记为已完成"

    def mark_as_cancelled(self, request, queryset):
        from django.db import transaction as db_transaction
        with db_transaction.atomic():
            for order in queryset:
                if order.status == 'pending' and order.points_amount < 0:
                    PointsRecord.objects.create(
                        user=order.user,
                        points_type='order_refund',
                        points_change=abs(order.points_amount),
                        description=f"订单取消，返还积分: {order.transaction_no}",
                        related_id=order.transaction_no
                    )
            updated = queryset.update(status='cancelled')
        self.message_user(request, f"已取消 {updated} 个订单并返还积分")

    mark_as_cancelled.short_description = "标记为已取消（返还积分）"