# recycle/serializers.py
from rest_framework import serializers
from .models import ScrapCar, PriceRule, LocationCache, EvaluationMaterial
from django.core.files.base import ContentFile
import os


class ScrapCarSerializer(serializers.ModelSerializer):
    """报废车信息序列化器"""

    # 只读字段，用于前端显示
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    submit_time_formatted = serializers.DateTimeField(format='%Y-%m-%d %H:%M', read_only=True)
    car_image_url = serializers.SerializerMethodField(read_only=True)
    user_info = serializers.SerializerMethodField(read_only=True)
    can_start_display = serializers.SerializerMethodField(read_only=True)
    # 小程序专用字段
    display_price = serializers.SerializerMethodField(read_only=True)
    status_class = serializers.SerializerMethodField(read_only=True)
    # 新增状态历史字段
    status_history = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ScrapCar
        fields = [
            'id', 'contact_name', 'contact_phone', 'region', 'address',
            'car_model', 'car_count', 'wheel_type', 'wheel_count',
            'ternary_count', 'battery_count', 'battery_pack_count',
            'engine_count', 'weight', 'can_start', 'can_start_display',
            'car_image', 'car_image_path', 'car_image_url', 'remark',
            'status', 'status_display', 'estimated_price', 'final_price',
            'submit_time', 'submit_time_formatted', 'user', 'user_info',
            'display_price', 'status_class', 'status_history'  # 新增字段
        ]
        read_only_fields = [
            'id', 'estimated_price', 'final_price',
            'submit_time', 'user', 'car_image_url', 'user_info',
            'status_display', 'submit_time_formatted', 'can_start_display',
            'display_price', 'status_class', 'status_history'
        ]

    def get_car_image_url(self, obj):
        """获取完整的图片URL"""
        image_url = obj.get_car_image_url()
        if image_url:
            request = self.context.get('request')
            if request and not image_url.startswith(('http://', 'https://')):
                return request.build_absolute_uri(image_url)
        return image_url

    @staticmethod
    def get_user_info(obj):
        """获取用户信息"""
        return obj.get_user_info()

    @staticmethod
    def get_can_start_display(obj):
        """获取能否启动的显示文本"""
        return obj.get_can_start_display()

    @staticmethod
    def get_display_price(obj):
        """获取显示价格（小程序专用）"""
        return obj.get_display_price()

    @staticmethod
    def get_status_class(obj):
        """获取状态对应的CSS类名"""
        return obj.get_status_class()

    @staticmethod
    def get_status_history(obj):
        """获取状态变更历史"""
        return obj.get_status_history_display()

    @staticmethod
    def validate_contact_phone(value):
        """验证手机号格式"""
        if len(value) != 11 or not value.isdigit():
            raise serializers.ValidationError("请输入正确的11位手机号码")
        return value

    @staticmethod
    def validate_car_count(value):
        """验证车辆数量"""
        if value < 1:
            raise serializers.ValidationError("车辆数量至少为1")
        if value > 100:
            raise serializers.ValidationError("车辆数量不能超过100")
        return value

    @staticmethod
    def validate_weight(value):
        """验证整备质量"""
        if value and (value < 500 or value > 5000):
            raise serializers.ValidationError("整备质量应在500-5000千克之间")
        return value

    def validate(self, attrs):
        """整体验证"""
        # 确保必填字段存在
        required_fields = ['contact_name', 'contact_phone', 'region', 'car_model']
        for field in required_fields:
            if field not in attrs or not attrs[field]:
                raise serializers.ValidationError({field: "该字段为必填项"})

        return attrs

    def create(self, validated_data):
        """创建报废车记录"""
        # 处理图片路径
        car_image_path = validated_data.pop('car_image_path', None)

        # 创建实例
        instance = ScrapCar(**validated_data)

        # 如果有图片路径，保存到 car_image_path 字段
        if car_image_path:
            instance.car_image_path = car_image_path

        # 保存到数据库
        instance.save()
        return instance


class ScrapCarListSerializer(serializers.ModelSerializer):
    """报废车列表序列化器"""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    submit_time_formatted = serializers.DateTimeField(format='%Y-%m-%d %H:%M', read_only=True)
    car_image_url = serializers.SerializerMethodField(read_only=True)
    user_info = serializers.SerializerMethodField(read_only=True)
    # 小程序专用字段
    display_price = serializers.SerializerMethodField(read_only=True)
    status_class = serializers.SerializerMethodField(read_only=True)
    contact_info = serializers.SerializerMethodField(read_only=True)
    submit_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)  # 添加原始时间字段

    class Meta:
        model = ScrapCar
        fields = [
            'id', 'car_model', 'contact_name', 'contact_phone', 'region',
            'car_image', 'car_image_path', 'car_image_url', 'status',
            'status_display', 'status_class', 'estimated_price', 'final_price',
            'display_price', 'submit_time', 'submit_time_formatted', 'user_info', 'contact_info',
            'can_start', 'weight', 'car_count', 'wheel_type', 'wheel_count',
            'ternary_count', 'battery_count', 'battery_pack_count', 'engine_count'
        ]

    def get_car_image_url(self, obj):
        """获取完整的图片URL"""
        image_url = obj.get_car_image_url()
        if image_url:
            request = self.context.get('request')
            if request and not image_url.startswith(('http://', 'https://')):
                return request.build_absolute_uri(image_url)
        return image_url or '/static/images/default-car.jpg'  # 默认图片

    @staticmethod
    def get_user_info(obj):
        """获取用户信息"""
        return obj.get_user_display_info()

    @staticmethod
    def get_display_price(obj):
        """获取显示价格（小程序专用）"""
        return obj.get_display_price()

    @staticmethod
    def get_status_class(obj):
        """获取状态对应的CSS类名"""
        return obj.get_status_class()

    @staticmethod
    def get_contact_info(obj):
        """获取联系人信息"""
        return {
            'name': obj.contact_name,
            'phone': obj.contact_phone
        }


class PriceRuleSerializer(serializers.ModelSerializer):
    """价格规则序列化器"""

    class Meta:
        model = PriceRule
        fields = ['id', 'name', 'car_type', 'base_price', 'weight_factor', 'condition_factor', 'is_active']


class CarImageUploadSerializer(serializers.Serializer):
    """车辆图片上传序列化器"""
    image = serializers.ImageField(max_length=100, allow_empty_file=False)

    @staticmethod
    def validate_image(value):
        """验证图片文件"""
        # 验证文件大小（5MB限制）
        max_size = 5 * 1024 * 1024  # 5MB
        if value.size > max_size:
            raise serializers.ValidationError("图片大小不能超过5MB")

        # 验证文件类型
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/jpg']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("只支持JPEG、PNG、GIF格式的图片")

        return value


class LocationSerializer(serializers.Serializer):
    """位置序列化器"""
    latitude = serializers.DecimalField(max_digits=10, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=6)


class ReverseGeocodeSerializer(serializers.ModelSerializer):
    """逆地理编码序列化器"""

    class Meta:
        model = LocationCache
        fields = ['province', 'city', 'district', 'address']


class ScrapCarStatusUpdateSerializer(serializers.Serializer):
    """报废车状态更新序列化器"""
    status = serializers.ChoiceField(choices=['confirmed', 'cancelled'])
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate_status(self, value):
        """验证状态值"""
        if value not in ['confirmed', 'cancelled']:
            raise serializers.ValidationError("状态值必须是 'confirmed' 或 'cancelled'")
        return value



class EvaluationMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationMaterial
        fields = ['id', 'name', 'price_per_ton','factor']