# vin/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import VinConfig, VinQueryResult
User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """用户信息序列化器"""

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = fields


class VinConfigSerializer(serializers.ModelSerializer):
    """VIN配置序列化器"""

    class Meta:
        model = VinConfig
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
        extra_kwargs = {
            'password': {'write_only': True}
        }


class VinQueryResultSerializer(serializers.ModelSerializer):
    """VIN查询结果序列化器"""

    user_info = UserSerializer(source='user', read_only=True)
    config_used_name = serializers.ReadOnlyField(source='config_used.name')
    is_success = serializers.ReadOnlyField()
    has_vehicle_info = serializers.ReadOnlyField()
    first_model = serializers.SerializerMethodField()
    model_images = serializers.SerializerMethodField()
    model_count = serializers.ReadOnlyField()
    original_attributes_count = serializers.SerializerMethodField()
    gonggao_count = serializers.SerializerMethodField()
    import_count = serializers.SerializerMethodField()
    original_epc_count = serializers.SerializerMethodField()
    has_images = serializers.ReadOnlyField()
    complete_data = serializers.SerializerMethodField()

    class Meta:
        model = VinQueryResult
        fields = '__all__'
        read_only_fields = ('query_time', 'user', 'config_used', 'model_count', 'has_vehicle_info', 'has_images')

    def get_first_model(self, obj):
        """获取第一个车型信息"""
        first_model = obj.get_first_model()
        if first_model:
            first_model['images'] = obj.get_model_images(0)
        return first_model

    def get_model_images(self, obj):
        """获取第一个车型的图片列表"""
        return obj.get_model_images(0)

    def get_original_attributes_count(self, obj):
        """获取原厂属性数量"""
        return len(obj.original_attributes) if obj.original_attributes else 0

    def get_gonggao_count(self, obj):
        """获取公告数量"""
        return len(obj.gonggao_list) if obj.gonggao_list else 0

    def get_import_count(self, obj):
        """获取进口车型数量"""
        return len(obj.import_list) if obj.import_list else 0

    def get_original_epc_count(self, obj):
        """获取原厂EPC数量"""
        return len(obj.original_epc_list) if obj.original_epc_list else 0

    def get_complete_data(self, obj):
        """获取完整数据"""
        return obj.get_complete_data()


class VinQueryRequestSerializer(serializers.Serializer):
    """VIN查询请求序列化器"""

    vin_code = serializers.CharField(
        max_length=50,
        required=True,
        help_text="VIN码（17位车辆识别代号）"
    )
    config_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="VIN配置ID，如果为空则使用默认配置"
    )
    save_result = serializers.BooleanField(
        default=True,
        help_text="是否保存查询结果"
    )

    @staticmethod
    def validate_vin_code(value):
        """验证VIN码格式"""
        if not value or len(value.strip()) < 5:
            raise serializers.ValidationError("VIN码不能为空且至少5位字符")

        cleaned_vin = value.strip().upper()
        if len(cleaned_vin) != 17:
            raise serializers.ValidationError("VIN码应为17位字符")

        import re
        if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', cleaned_vin):
            raise serializers.ValidationError("VIN码格式不正确")

        return cleaned_vin


class VinQueryStatisticsSerializer(serializers.Serializer):
    """VIN查询统计序列化器"""

    total_queries = serializers.IntegerField()
    success_queries = serializers.IntegerField()
    failed_queries = serializers.IntegerField()
    success_rate = serializers.FloatField()
    today_queries = serializers.IntegerField()
    week_queries = serializers.IntegerField()
    month_queries = serializers.IntegerField()
    popular_brands = serializers.ListField()
    popular_models = serializers.ListField()
    query_trends = serializers.ListField()
    data_quality = serializers.DictField()


class VinBatchQuerySerializer(serializers.Serializer):
    """批量VIN查询序列化器"""

    vin_codes = serializers.ListField(
        child=serializers.CharField(max_length=50),
        min_length=1,
        max_length=50,
        help_text="VIN码列表，最多50个"
    )
    config_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="VIN配置ID，如果为空则使用默认配置"
    )
    save_results = serializers.BooleanField(
        default=True,
        help_text="是否保存查询结果"
    )

    def validate_vin_codes(self, value):
        """验证VIN码列表"""
        if not value:
            raise serializers.ValidationError("VIN码列表不能为空")

        if len(value) > 50:
            raise serializers.ValidationError("单次最多查询50个VIN码")

        validated_vin_codes = []
        for vin_code in value:
            try:
                validated_vin = VinQueryRequestSerializer.validate_vin_code(vin_code)
                validated_vin_codes.append(validated_vin)
            except serializers.ValidationError as e:
                raise serializers.ValidationError(f"VIN码 {vin_code} 格式错误: {e.detail[0]}")

        return validated_vin_codes
