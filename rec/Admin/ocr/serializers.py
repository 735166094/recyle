import logging
from rest_framework import serializers
from .models import (
    HuaweiCloudConfig, OcrInterface, CertificateType,
    RecognitionRecord, VehicleLicenseResult, IdCardResult, BusinessLicenseResult, ScrapCarInfo
)
from user.models import User

logger = logging.getLogger(__name__)


class HuaweiCloudConfigSerializer(serializers.ModelSerializer):
    """华为云配置序列化器"""

    class Meta:
        model = HuaweiCloudConfig
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class OcrInterfaceSerializer(serializers.ModelSerializer):
    """OCR接口序列化器"""

    class Meta:
        model = OcrInterface
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class CertificateTypeSerializer(serializers.ModelSerializer):
    """证件类型序列化器"""

    class Meta:
        model = CertificateType
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class VehicleLicenseResultSerializer(serializers.ModelSerializer):
    """行驶证识别结果序列化器"""

    # 添加额外的VIN查询信息
    vin_info = serializers.SerializerMethodField()
    # 添加车型选项
    vehicle_options = serializers.SerializerMethodField()

    class Meta:
        model = VehicleLicenseResult
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'record')

    @staticmethod
    def get_vin_info(obj):
        """获取VIN查询信息"""
        try:
            if not obj.vin:
                return None

            # 如果已经有vehicle_name和production_year字段，说明已经查询过VIN
            if obj.vehicle_name or obj.production_year:
                return {
                    'vehicle_name': obj.vehicle_name,
                    'production_year': obj.production_year,
                    'has_vin_info': True
                }

            # 否则尝试查询VIN
            from .utils import query_vin_for_vehicle_info
            vehicle_info = query_vin_for_vehicle_info(obj.vin)

            if vehicle_info:
                return {
                    'brand': vehicle_info.get('brand'),
                    'vehicle_name': vehicle_info.get('vehicle_name'),
                    'production_year': vehicle_info.get('production_year'),
                    'model_year': vehicle_info.get('model_year'),
                    'build_date': vehicle_info.get('build_date'),
                    'vehicle_options': vehicle_info.get('vehicle_options', []),
                    'model_count': len(vehicle_info.get('model_list', []))
                }
            return None
        except Exception as e:
            logger.error(f"获取VIN信息失败: {str(e)}")
            return None

    @staticmethod
    def get_vehicle_options(obj):
        """获取车型选项"""
        try:
            if not obj.vin:
                return []

            from .utils import query_vin_for_vehicle_info
            vehicle_info = query_vin_for_vehicle_info(obj.vin)

            if vehicle_info and 'vehicle_options' in vehicle_info:
                return vehicle_info['vehicle_options']

            return []
        except Exception as e:
            logger.error(f"获取车型选项失败: {str(e)}")
            return []


class IdCardResultSerializer(serializers.ModelSerializer):
    """身份证识别结果序列化器"""

    class Meta:
        model = IdCardResult
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'record')


class BusinessLicenseResultSerializer(serializers.ModelSerializer):
    """营业执照识别结果序列化器"""

    class Meta:
        model = BusinessLicenseResult
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'record')


class ScrapCarInfoSerializer(serializers.ModelSerializer):
    """报废车信息识别序列化器"""

    class Meta:
        model = ScrapCarInfo
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'matched_at')


class UserSerializer(serializers.ModelSerializer):
    """用户信息序列化器 - 使用自定义用户模型"""

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'date_joined', 'last_login', 'is_active', 'is_staff'
        ]
        read_only_fields = fields

    # 如果需要其他字段，但模型中不存在，可以添加 SerializerMethodField
    def get_avatar(self, obj):
        """获取头像 - 如果模型中不存在 avatar 字段"""
        # 尝试从关联模型获取或返回默认值
        return getattr(obj, 'avatar_url', None) or '/static/default-avatar.png'

    def get_employee_id(self, obj):
        """获取员工ID - 兼容处理"""
        # 尝试从不同字段获取
        return getattr(obj, 'employee_id', getattr(obj, 'staff_id', ''))


class RecognitionRecordSerializer(serializers.ModelSerializer):
    """识别记录序列化器 """
    user_info = UserSerializer(source='user', read_only=True)
    certificate_type_name = serializers.ReadOnlyField(source='certificate_type.name')
    interface_used_name = serializers.ReadOnlyField(source='interface_used.name')
    vehicle_result = serializers.SerializerMethodField()
    id_card_result = serializers.SerializerMethodField()
    business_result = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = RecognitionRecord
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'user', 'recognition_status', 'recognition_time')

    @staticmethod
    def get_vehicle_result(obj):
        """获取行驶证识别结果"""
        try:
            if hasattr(obj, 'vehicle_result'):
                return VehicleLicenseResultSerializer(obj.vehicle_result).data
            return None
        except Exception as e:
            logger.error(f"获取行驶证结果失败: {str(e)}")
            return None

    @staticmethod
    def get_id_card_result(obj):
        """获取身份证识别结果"""
        try:
            # 检查是否存在身份证结果关联
            if hasattr(obj, 'id_card_result'):
                id_card_result = obj.id_card_result
                logger.info(f"找到身份证结果关联: {id_card_result.id}")

                # 直接序列化，不进行有效性检查
                result_data = IdCardResultSerializer(id_card_result).data

                # 记录序列化后的数据用于调试
                logger.info(f"身份证序列化数据: {result_data}")

                # 检查是否有任何有效数据
                has_any_data = any([
                    result_data.get('name'),
                    result_data.get('number'),
                    result_data.get('issue_authority'),
                    result_data.get('valid_from'),
                    result_data.get('valid_to'),
                    result_data.get('gender'),
                    result_data.get('ethnicity'),
                    result_data.get('birth'),
                    result_data.get('address')
                ])

                if has_any_data:
                    logger.info(f"返回身份证结果: 姓名={result_data.get('name')}, 身份证号={result_data.get('number')}")
                    return result_data
                else:
                    logger.warning("身份证结果数据全部为空")
                    return None
            else:
                logger.warning(f"记录 {obj.id} 没有关联的身份证结果")
                return None

        except Exception as e:
            logger.error(f"获取身份证结果失败: {str(e)}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return None

    @staticmethod
    def get_business_result(obj):
        """获取营业执照识别结果"""
        try:
            if hasattr(obj, 'business_result'):
                return BusinessLicenseResultSerializer(obj.business_result).data
            return None
        except Exception as e:
            logger.error(f"获取营业执照结果失败: {str(e)}")
            return None

    def get_image_url(self, obj):
        """获取图片的完整URL"""
        request = self.context.get('request')
        if request and obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None


class ImageUploadSerializer(serializers.Serializer):
    """
    图片上传序列化器 - 处理单张图片上传
    """
    image = serializers.ImageField(required=True, allow_empty_file=False)
    certificate_type_id = serializers.IntegerField(required=False, allow_null=True)

    @staticmethod
    def validate_image(value):
        """验证图片文件"""
        # 检查文件类型
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("只支持JPEG和PNG格式的图片")

        # 检查文件大小（5MB）
        max_size = 5 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("图片大小不能超过5MB")

        return value

    @staticmethod
    def validate_certificate_type_id(value):
        """验证证件类型ID是否存在"""
        if value:
            try:
                CertificateType.objects.get(id=value, is_active=True)
            except CertificateType.DoesNotExist:
                raise serializers.ValidationError("指定的证件类型不存在或已禁用")
        return value


class BatchImageUploadSerializer(serializers.Serializer):
    """批量图片上传序列化器"""
    images = serializers.ListField(
        child=serializers.ImageField(required=True, allow_empty_file=False),
        required=True
    )
    certificate_type_id = serializers.IntegerField(required=False, allow_null=True)

    @staticmethod
    def validate_images(value):
        """验证图片列表"""
        if len(value) > 10:
            raise serializers.ValidationError("单次最多上传10张图片")

        for image in value:
            # 检查文件类型
            allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
            if image.content_type not in allowed_types:
                raise serializers.ValidationError(f"图片 {image.name} 格式不支持，只支持JPEG和PNG格式")

            # 检查文件大小（5MB）
            max_size = 5 * 1024 * 1024
            if image.size > max_size:
                raise serializers.ValidationError(f"图片 {image.name} 大小超过5MB限制")

        return value


class StatisticsSerializer(serializers.Serializer):
    """统计信息序列化器"""
    total_records = serializers.IntegerField()
    success_records = serializers.IntegerField()
    success_rate = serializers.FloatField()
    today_records = serializers.IntegerField()
    week_records = serializers.IntegerField()
    month_records = serializers.IntegerField()
    certificate_stats = serializers.ListField()
    date_stats = serializers.ListField()


class ScrapCarMatchResultSerializer(serializers.Serializer):
    """报废车匹配结果序列化器"""
    total_count = serializers.IntegerField()
    matched_count = serializers.IntegerField()
    unmatched_count = serializers.IntegerField()
    manual_review_count = serializers.IntegerField()
    processing_time = serializers.FloatField()
    results = ScrapCarInfoSerializer(many=True)


class ExportExcelSerializer(serializers.Serializer):
    """导出Excel序列化器"""
    export_all = serializers.BooleanField(default=False, help_text="是否导出所有数据")
    match_status = serializers.CharField(required=False, allow_blank=True, help_text="匹配状态过滤")
    vehicle_number = serializers.CharField(required=False, allow_blank=True, help_text="车牌号码过滤")
    owner_name = serializers.CharField(required=False, allow_blank=True, help_text="车主姓名过滤")
    vin = serializers.CharField(required=False, allow_blank=True, help_text="VIN码过滤")
    brand = serializers.CharField(required=False, allow_blank=True, help_text="品牌过滤")
    use_character = serializers.CharField(required=False, allow_blank=True, help_text="使用性质过滤")
    energy_type = serializers.CharField(required=False, allow_blank=True, help_text="燃料种类过滤")


class ExportFieldSelectionSerializer(serializers.Serializer):
    """导出字段选择序列化器"""
    fields = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        help_text="要导出的字段列表，如果为空则使用默认字段"
    )
    export_all = serializers.BooleanField(default=False, help_text="是否导出所有数据")
    match_status = serializers.CharField(required=False, allow_blank=True, help_text="匹配状态过滤")
    vehicle_number = serializers.CharField(required=False, allow_blank=True, help_text="车牌号码过滤")
    owner_name = serializers.CharField(required=False, allow_blank=True, help_text="车主姓名过滤")
    vin = serializers.CharField(required=False, allow_blank=True, help_text="VIN码过滤")
    brand = serializers.CharField(required=False, allow_blank=True, help_text="品牌过滤")
    use_character = serializers.CharField(required=False, allow_blank=True, help_text="使用性质过滤")
    energy_type = serializers.CharField(required=False, allow_blank=True, help_text="燃料种类过滤")

    @staticmethod
    def validate_fields(value):
        """验证字段列表"""
        from .excel_utils import ExcelExporter
        available_fields = ExcelExporter.get_available_fields().keys()

        invalid_fields = [field for field in value if field not in available_fields]
        if invalid_fields:
            raise serializers.ValidationError(f"无效的字段: {', '.join(invalid_fields)}")

        return value
