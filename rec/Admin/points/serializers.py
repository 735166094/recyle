# points/serializers.py
from rest_framework import serializers
from .models import PointsRule, PointsRecord, UserDailyPoints, PointsTransaction, UserMonthlySummary
from django.conf import settings


class PointsRuleSerializer(serializers.ModelSerializer):
    """积分规则序列化器"""
    rule_type_display = serializers.CharField(source='get_rule_type_display', read_only=True)
    green_type_display = serializers.CharField(source='get_green_type_display', read_only=True)
    condition_type_display = serializers.CharField(source='get_condition_type_display', read_only=True)

    class Meta:
        model = PointsRule
        fields = [
            'id', 'rule_id', 'rule_name', 'rule_type', 'rule_type_display',
            'green_type', 'green_type_display', 'points_value', 'points_limit',
            'daily_limit', 'monthly_limit', 'condition_type', 'condition_type_display',
            'condition_value', 'condition_unit', 'description', 'instructions',
            'need_upload', 'upload_desc', 'certificate_name', 'is_active',
            'sort_order', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PointsRecordSerializer(serializers.ModelSerializer):
    """积分记录序列化器"""
    points_type_display = serializers.CharField(source='get_points_type_display', read_only=True)
    green_type_display = serializers.CharField(source='get_green_type_display', read_only=True)
    user_name = serializers.CharField(source='user.display_name', read_only=True)

    class Meta:
        model = PointsRecord
        fields = [
            'id', 'user', 'user_name', 'points_rule', 'points_type', 'points_type_display',
            'green_type', 'green_type_display', 'points_change', 'current_points',
            'related_id', 'order_no', 'recycle_id', 'upload_image', 'certificate_image',
            'steps_count', 'days_count', 'is_verified', 'verified_by', 'verified_at',
            'description', 'remark', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'current_points', 'created_at', 'updated_at']


class GreenLifeUploadSerializer(serializers.Serializer):
    """绿色生活上传序列化器"""
    green_type = serializers.ChoiceField(
        choices=PointsRecord.GREEN_LIFE_TYPE_CHOICES,
        required=True,
        help_text="绿色生活类型"
    )
    upload_image = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="上传凭证图片"
    )
    certificate_image = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="证书图片"
    )
    steps_count = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
        max_value=100000,
        help_text="步数（仅低碳行走需要）"
    )
    days_count = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
        max_value=31,
        help_text="连续天数"
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="描述说明"
    )


class DailyPointsSerializer(serializers.ModelSerializer):
    """每日积分统计序列化器"""
    user_name = serializers.CharField(source='user.display_name', read_only=True)

    class Meta:
        model = UserDailyPoints
        fields = [
            'id', 'user', 'user_name', 'date', 'sign_points', 'task_points',
            'green_points', 'purchase_points', 'recycle_points', 'consume_points',
            'total_points', 'transport_days', 'food_days', 'walk_steps',
            'learning_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PointsTransactionSerializer(serializers.ModelSerializer):
    """积分交易序列化器"""
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_name = serializers.CharField(source='user.display_name', read_only=True)

    class Meta:
        model = PointsTransaction
        fields = [
            'id', 'transaction_no', 'user', 'user_name', 'transaction_type',
            'transaction_type_display', 'points_amount', 'product_id', 'product_name',
            'product_points', 'redeem_address', 'express_no', 'status', 'status_display',
            'remark', 'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = ['id', 'transaction_no', 'created_at', 'updated_at']


class MonthlySummarySerializer(serializers.ModelSerializer):
    """月度汇总序列化器"""
    user_name = serializers.CharField(source='user.display_name', read_only=True)
    month_display = serializers.SerializerMethodField()

    class Meta:
        model = UserMonthlySummary
        fields = [
            'id', 'user', 'user_name', 'year', 'month', 'month_display',
            'total_earned', 'total_consumed', 'ending_balance', 'green_days_total',
            'green_points_total', 'transport_days', 'food_days', 'walk_points',
            'learning_points', 'is_transport_qualified', 'is_food_qualified',
            'is_walk_qualified', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    @staticmethod
    def get_month_display(obj):
        return f"{obj.year}年{obj.month}月"


class PointsSummarySerializer(serializers.Serializer):
    """积分汇总序列化器"""
    total_points = serializers.IntegerField(help_text="总积分")
    today_earned = serializers.IntegerField(help_text="今日获得")
    today_consumed = serializers.IntegerField(help_text="今日消费")
    month_earned = serializers.IntegerField(help_text="本月获得")
    month_consumed = serializers.IntegerField(help_text="本月消费")
    green_points = serializers.IntegerField(help_text="绿色积分")
    available_points = serializers.IntegerField(help_text="可用积分")

    continuous_days = serializers.IntegerField(help_text="连续签到天数")

    # 绿色生活统计
    green_days = serializers.IntegerField(help_text="绿色生活天数")
    transport_days = serializers.IntegerField(help_text="绿色出行天数")
    food_days = serializers.IntegerField(help_text="光盘行动天数")
    walk_steps = serializers.IntegerField(help_text="低碳行走步数")
    learning_count = serializers.IntegerField(help_text="学习次数")

    # 达标状态
    transport_qualified = serializers.BooleanField(help_text="绿色出行达标")
    food_qualified = serializers.BooleanField(help_text="光盘行动达标")
    walk_qualified = serializers.BooleanField(help_text="低碳行走达标")


class ExchangePointsSerializer(serializers.Serializer):
    """积分兑换序列化器"""
    product_id = serializers.CharField(required=True, help_text="商品ID")
    product_name = serializers.CharField(required=True, help_text="商品名称")
    product_points = serializers.IntegerField(required=True, min_value=1, help_text="所需积分")
    address_id = serializers.IntegerField(required=True, help_text="收货地址ID")
    quantity = serializers.IntegerField(default=1, min_value=1, help_text="兑换数量")