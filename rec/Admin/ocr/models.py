import os

from django.db import models
from django.contrib.auth.models import User
from datetime import datetime
from django.utils import timezone
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from pydantic_core import ValidationError
import logging
from django.conf import settings

from vin.models import VinConfig

logger = logging.getLogger('ocr')


def image_upload_path(instance, filename):
    """
    生成图片上传路径
    按日期和用户ID分类存储
    例如: ocr_images/20231123/20231123123045_5.jpg
    """
    user_id = instance.user.id
    date_str = datetime.now().strftime('%Y%m%d')
    ext = filename.split('.')[-1]
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}.{ext}"
    return f"ocr_images/{date_str}/{filename}"


def thumbnail_upload_path(instance, filename):
    """
    生成缩略图上传路径
    """
    user_id = instance.user.id
    date_str = datetime.now().strftime('%Y%m%d')
    ext = filename.split('.')[-1]
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}_thumbnail.{ext}"
    return f"ocr_thumbnails/{date_str}/{filename}"


class HuaweiCloudConfig(models.Model):
    """华为云配置模型 """
    name = models.CharField(max_length=100, verbose_name="配置名称")
    ak = models.CharField(max_length=100, verbose_name="Access Key")
    sk = models.CharField(max_length=100, verbose_name="Secret Key")
    region = models.CharField(max_length=50, verbose_name="区域", default="cn-north-4")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "ocr_huawei_cloud_config"
        verbose_name = "华为云配置"
        verbose_name_plural = "华为云配置"

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        """物理删除配置"""
        super().delete(*args, **kwargs)


class OcrInterface(models.Model):
    """OCR接口模型"""
    INTERFACE_TYPE_CHOICES = (
        ('general_text', '通用文字识别'),
        ('id_card', '身份证识别'),
        ('vehicle_license', '行驶证识别'),
        ('business_license', '营业执照识别'),
        ('auto_classification', '智能分类识别'),
        ('vin', 'VIN码查询'),  # 添加VIN接口类型
    )

    name = models.CharField(max_length=100, verbose_name="接口名称")
    interface_type = models.CharField(max_length=50, choices=INTERFACE_TYPE_CHOICES, verbose_name="接口类型")
    description = models.TextField(blank=True, null=True, verbose_name="接口描述")
    huawei_config = models.ForeignKey(
        HuaweiCloudConfig,
        on_delete=models.CASCADE,
        related_name="interfaces",
        verbose_name="华为云配置",
        null=True,  # 添加 null=True 允许为空
        blank=True  # 添加 blank=True 允许在表单中为空
    )
    vin_config = models.ForeignKey(
        VinConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vin_interfaces",
        verbose_name="VIN查询配置"
    )
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "ocr_interface"
        verbose_name = "OCR接口"
        verbose_name_plural = "OCR接口"

    def __str__(self):
        return f"{self.name}({self.get_interface_type_display()})"

    def delete(self, *args, **kwargs):
        """物理删除接口"""
        super().delete(*args, **kwargs)


class CertificateType(models.Model):
    """
    证件类型模型 - 定义可识别的证件类型
    """
    CERTIFICATE_TYPE_CHOICES = (
        ('id_card', '身份证'),
        ('vehicle_license', '行驶证'),
        ('business_license', '营业执照'),
        ('auto', '自动识别'),
        ('other', '其他'),
    )

    name = models.CharField(max_length=100, verbose_name="证件名称")
    type_code = models.CharField(max_length=50, choices=CERTIFICATE_TYPE_CHOICES, verbose_name="证件类型编码")
    interface = models.ForeignKey(
        OcrInterface,
        on_delete=models.CASCADE,
        related_name="certificate_types",
        verbose_name="关联接口"
    )
    keywords = models.CharField(max_length=200, blank=True, null=True, verbose_name="识别关键字，逗号分隔")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "ocr_certificate_type"
        verbose_name = "证件类型"
        verbose_name_plural = "证件类型"

    def __str__(self):
        return f"{self.name}({self.get_type_code_display()})"

    def delete(self, *args, **kwargs):
        """物理删除证件类型"""
        super().delete(*args, **kwargs)


class RecognitionRecord(models.Model):
    """识别记录模型 """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # 使用自定义用户模型
        on_delete=models.CASCADE,
        related_name="recognition_records",
        verbose_name="用户"
    )
    image = models.ImageField(upload_to=image_upload_path, verbose_name="识别图片")
    thumbnail = models.ImageField(
        upload_to=thumbnail_upload_path,
        verbose_name="缩略图",
        null=True,
        blank=True
    )
    certificate_type = models.ForeignKey(
        CertificateType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="records",
        verbose_name="证件类型"
    )
    interface_used = models.ForeignKey(
        OcrInterface,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="used_records",
        verbose_name="使用的接口"
    )
    recognition_status = models.BooleanField(default=False, verbose_name="识别是否成功")
    recognition_time = models.DateTimeField(null=True, blank=True, verbose_name="识别时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "ocr_recognition_record"
        verbose_name = "识别记录"
        verbose_name_plural = "识别记录"
        ordering = ['-created_at']

    def __str__(self):
        certificate_type_name = self.certificate_type.name if self.certificate_type else "未知类型"
        return f"[{self.user.username}] {certificate_type_name} {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        """重写保存方法，自动生成缩略图"""
        # 如果是新记录或者图片被更新，生成缩略图
        if not self.pk or 'image' in kwargs.get('update_fields', []) or not self.thumbnail:
            self._create_thumbnail()

        super().save(*args, **kwargs)

    def _create_thumbnail(self):
        """创建缩略图"""
        try:
            if not self.image:
                return

            # 打开原始图片
            img = Image.open(self.image)

            # 转换为RGB模式（处理PNG透明背景）
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            else:
                img = img.convert('RGB')

            # 计算缩略图尺寸，保持宽高比
            thumbnail_size = (100, 100)  # 统一缩略图尺寸
            img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)

            # 保存到内存
            thumb_io = BytesIO()
            img.save(thumb_io, format='JPEG', quality=85, optimize=True)
            thumb_io.seek(0)

            # 生成缩略图文件名
            thumb_name = f"{os.path.splitext(os.path.basename(self.image.name))[0]}_thumbnail.jpg"

            # 删除旧的缩略图
            if self.thumbnail:
                self._delete_thumbnail_file()

            # 保存新的缩略图
            self.thumbnail.save(thumb_name, ContentFile(thumb_io.getvalue()), save=False)
            thumb_io.close()

            logger.info(f"为记录 {self.id} 生成缩略图成功")

        except Exception as e:
            logger.error(f"创建缩略图失败: {str(e)}")

    def _delete_thumbnail_file(self):
        """删除缩略图文件"""
        try:
            if self.thumbnail and os.path.isfile(self.thumbnail.path):
                os.remove(self.thumbnail.path)
                logger.info(f"删除缩略图文件: {self.thumbnail.path}")
        except Exception as e:
            logger.error(f"删除缩略图文件失败: {str(e)}")

    def delete(self, *args, **kwargs):
        """删除方法，物理删除图片文件和缩略图"""
        # 删除缩略图文件
        self._delete_thumbnail_file()

        # 删除原始图片文件
        if self.image and os.path.isfile(self.image.path):
            try:
                os.remove(self.image.path)
                logger.info(f"删除图片文件: {self.image.path}")
            except Exception as e:
                logger.error(f"删除图片文件失败: {str(e)}")

        super().delete(*args, **kwargs)

    def get_thumbnail_url(self):
        """获取缩略图URL"""
        if self.thumbnail:
            return self.thumbnail.url
        return None

    def get_image_url(self):
        """获取原始图片URL"""
        if self.image:
            return self.image.url
        return None


class VehicleLicenseResult(models.Model):
    """行驶证识别结果模型"""
    record = models.OneToOneField(RecognitionRecord, on_delete=models.CASCADE, related_name="vehicle_result",
                                  verbose_name="识别记录")

    # 主页信息
    number = models.CharField(max_length=50, blank=True, null=True, verbose_name="号牌号码")
    vehicle_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="车辆类型")
    owner_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="所有人")
    address = models.CharField(max_length=200, blank=True, null=True, verbose_name="地址")
    engine_no = models.CharField(max_length=100, blank=True, null=True, verbose_name="发动机号码")
    vin = models.CharField(max_length=50, blank=True, null=True, verbose_name="VIN码")
    model = models.CharField(max_length=200, blank=True, null=True, verbose_name="品牌型号")
    brand = models.CharField(max_length=100, blank=True, null=True, verbose_name="车辆品牌")
    vehicle_model = models.CharField(max_length=100, blank=True, null=True, verbose_name="车辆型号")
    # 新增字段：车辆名称（品牌+系列+排量）如：江淮骏铃 骏铃E3 2.156L
    vehicle_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="车辆名称")
    # 新增字段：生产年份（如：2013款）
    production_year = models.CharField(max_length=50, blank=True, null=True, verbose_name="生产年份")
    register_date = models.CharField(max_length=50, blank=True, null=True, verbose_name="注册日期")
    issue_date = models.CharField(max_length=50, blank=True, null=True, verbose_name="发证日期")
    use_character = models.CharField(max_length=50, blank=True, null=True, verbose_name="使用性质")

    # 副页信息
    file_no = models.CharField(max_length=100, blank=True, null=True, verbose_name="档案编码")
    approved_passengers = models.CharField(max_length=50, blank=True, null=True, verbose_name="核定载人数")
    gross_mass = models.CharField(max_length=50, blank=True, null=True, verbose_name="总质量")
    unladen_mass = models.CharField(max_length=50, blank=True, null=True, verbose_name="整备质量")
    dimension = models.CharField(max_length=100, blank=True, null=True, verbose_name="外廓尺寸")
    energy_type = models.CharField(max_length=50, blank=True, null=True, verbose_name="燃料种类")
    remarks = models.TextField(blank=True, null=True, verbose_name="备注")
    inspection_record = models.TextField(blank=True, null=True, verbose_name="校验记录")
    code_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="条码号")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "ocr_vehicle_license_result"
        verbose_name = "行驶证识别结果"
        verbose_name_plural = "行驶证识别结果"

    def __str__(self):
        return f"行驶证结果: {self.number or '未知号牌'} - {self.owner_name or '未知车主'}"

    def save(self, *args, **kwargs):
        """重写保存方法，自动查询VIN信息"""
        # 如果是新记录或者VIN码被更新
        is_new = not self.pk
        vin_changed = False

        if not is_new:
            try:
                old_instance = VehicleLicenseResult.objects.get(pk=self.pk)
                vin_changed = old_instance.vin != self.vin
            except VehicleLicenseResult.DoesNotExist:
                vin_changed = True

        # 调用父类保存方法
        super().save(*args, **kwargs)

        # 如果VIN码存在且（是新记录或VIN码被更新）
        if self.vin and (is_new or vin_changed or not self.vehicle_name or not self.production_year):
            # 异步查询VIN信息
            self._query_vin_async()

    def _query_vin_async(self):
        """异步查询VIN信息"""
        try:
            from .vin_tasks import query_vin_for_vehicle_result_task
            query_vin_for_vehicle_result_task.delay(self.id)
            logger.info(f"已触发VIN查询任务，行驶证结果ID: {self.id}, VIN: {self.vin}")
        except Exception as e:
            logger.error(f"触发VIN查询任务失败: {str(e)}")
            # 如果异步任务失败，尝试同步查询
            try:
                from .utils import enrich_vehicle_license_with_vin
                enrich_vehicle_license_with_vin(self)
            except Exception as sync_error:
                logger.error(f"同步VIN查询也失败: {str(sync_error)}")


class IdCardResult(models.Model):
    """身份证识别结果模型"""
    record = models.OneToOneField(RecognitionRecord, on_delete=models.CASCADE, related_name="id_card_result",
                                  verbose_name="识别记录")

    # 人像面信息
    name = models.CharField(max_length=100, blank=True, null=True, verbose_name="姓名")
    gender = models.CharField(max_length=10, blank=True, null=True, verbose_name="性别")
    ethnicity = models.CharField(max_length=20, blank=True, null=True, verbose_name="民族")
    birth = models.CharField(max_length=20, blank=True, null=True, verbose_name="出生日期")
    address = models.CharField(max_length=200, blank=True, null=True, verbose_name="住址")
    number = models.CharField(max_length=20, blank=True, null=True, verbose_name="身份证号码")

    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="手机号")

    # 国徽面信息
    issue_authority = models.CharField(max_length=100, blank=True, null=True, verbose_name="签发机关")
    valid_from = models.CharField(max_length=20, blank=True, null=True, verbose_name="有效期起始")
    valid_to = models.CharField(max_length=20, blank=True, null=True, verbose_name="有效期结束")

    # 身份证正反面标识
    side = models.CharField(max_length=20, blank=True, null=True, verbose_name="正反面",
                            choices=[('front', '人像面'), ('back', '国徽面'), ('double_side', '双面')])

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "ocr_id_card_result"
        verbose_name = "身份证识别结果"
        verbose_name_plural = "身份证识别结果"

    def __str__(self):
        return f"身份证结果: {self.name or '未知姓名'}"


class BusinessLicenseResult(models.Model):
    """营业执照识别结果模型"""
    record = models.OneToOneField(RecognitionRecord, on_delete=models.CASCADE, related_name="business_result",
                                  verbose_name="识别记录")

    # 营业执照基本信息
    registration_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="注册号")
    name = models.CharField(max_length=200, blank=True, null=True, verbose_name="企业名称")
    type = models.CharField(max_length=100, blank=True, null=True, verbose_name="企业类型")
    address = models.CharField(max_length=300, blank=True, null=True, verbose_name="住所")
    legal_representative = models.CharField(max_length=100, blank=True, null=True, verbose_name="法定代表人")
    registered_capital = models.CharField(max_length=50, blank=True, null=True, verbose_name="注册资本")
    found_date = models.CharField(max_length=20, blank=True, null=True, verbose_name="成立日期")
    business_term = models.CharField(max_length=100, blank=True, null=True, verbose_name="营业期限")
    business_scope = models.TextField(blank=True, null=True, verbose_name="经营范围")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "ocr_business_license_result"
        verbose_name = "营业执照识别结果"
        verbose_name_plural = "营业执照识别结果"

    def __str__(self):
        return f"营业执照结果: {self.name or '未知企业名称'}"


class ScrapCarInfo(models.Model):
    """报废车信息识别模型"""
    MATCH_STATUS_CHOICES = (
        ('matched', '已匹配'),
        ('unmatched', '未匹配'),
        ('manual_review', '待人工审核'),
    )

    # 匹配的证件记录
    vehicle_record = models.ForeignKey(
        RecognitionRecord,
        on_delete=models.CASCADE,
        related_name="scrap_car_vehicle_records",
        verbose_name="行驶证记录"
    )
    id_card_record = models.ForeignKey(
        RecognitionRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scrap_car_id_card_records",
        verbose_name="身份证记录"
    )
    business_record = models.ForeignKey(
        RecognitionRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scrap_car_business_records",
        verbose_name="营业执照记录"
    )

    # 匹配状态
    match_status = models.CharField(
        max_length=20,
        choices=MATCH_STATUS_CHOICES,
        default='unmatched',
        verbose_name="匹配状态"
    )
    match_score = models.IntegerField(default=0, verbose_name="匹配分数")
    match_rules = models.JSONField(default=dict, verbose_name="匹配规则")

    # 汇总信息
    owner_name = models.CharField(max_length=100, blank=True, default='', verbose_name="报废单位或个人姓名")
    identification_number = models.CharField(max_length=50, blank=True, default='', verbose_name="身份证号或信用代码")
    id_card_phone_number = models.CharField(max_length=20, blank=True, default='', verbose_name="手机号")
    address = models.CharField(max_length=300, blank=True, default='', verbose_name="地址")
    vin = models.CharField(max_length=50, blank=True, default='', verbose_name="VIN码")
    vehicle_number = models.CharField(max_length=50, blank=True, default='', verbose_name="车牌号码")
    vehicle_type = models.CharField(max_length=100, blank=True, default='', verbose_name="车辆类型")
    use_character = models.CharField(max_length=50, blank=True, default='', verbose_name="使用性质")
    brand = models.CharField(max_length=100, blank=True, default='', verbose_name="车辆品牌")
    vehicle_model = models.CharField(max_length=100, blank=True, default='', verbose_name="车辆型号")
    engine_no = models.CharField(max_length=100, blank=True, default='', verbose_name="发动机号码")
    approved_passengers = models.CharField(max_length=50, blank=True, default='', verbose_name="核定载人数")
    register_date = models.CharField(max_length=50, blank=True, default='', verbose_name="注册日期")
    energy_type = models.CharField(max_length=50, blank=True, default='', verbose_name="燃料种类")
    unladen_mass = models.CharField(max_length=50, blank=True, default='', verbose_name="整备质量")
    remarks = models.CharField(max_length=100, blank=True, default='', verbose_name="备注")

    # 匹配时间
    matched_at = models.DateTimeField(null=True, blank=True, verbose_name="匹配时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "ocr_scrap_car_info"
        verbose_name = "报废车信息识别"
        verbose_name_plural = "报废车信息识别"
        indexes = [
            models.Index(fields=['vehicle_number'], name='idx_scrap_vehicle_number'),
            models.Index(fields=['owner_name'], name='idx_scrap_owner_name'),
            models.Index(fields=['match_status'], name='idx_scrap_match_status'),
            models.Index(fields=['vin'], name='idx_scrap_vin'),
            models.Index(fields=['created_at'], name='idx_scrap_created_at'),
        ]

    def __str__(self):
        return f"报废车信息: {self.vehicle_number or '未知车牌'} - {self.owner_name or '未知所有人'}"

    @property
    def match_type(self):
        """获取匹配类型"""
        if self.id_card_record and self.business_record:
            return 'both'
        elif self.id_card_record:
            return 'id_card'
        elif self.business_record:
            return 'business'
        else:
            return 'none'

    def clean(self):
        """数据清洗和验证"""
        try:
            # 只有在有vehicle_record时才验证其类型
            if self.vehicle_record and self.vehicle_record.certificate_type:
                if self.vehicle_record.certificate_type.type_code != 'vehicle_license':
                    raise ValidationError("关联的行驶证记录类型不正确")

            # 验证身份证记录类型（如果存在）
            if self.id_card_record and self.id_card_record.certificate_type:
                if self.id_card_record.certificate_type.type_code != 'id_card':
                    raise ValidationError("关联的身份证记录类型不正确")

            # 验证营业执照记录类型（如果存在）
            if self.business_record and self.business_record.certificate_type:
                if self.business_record.certificate_type.type_code != 'business_license':
                    raise ValidationError("关联的营业执照记录类型不正确")

        except Exception as e:
            # 如果是由于关联记录不存在导致的错误，只是记录下来不抛出异常
            logger.warning(f"报废车信息验证时出现异常（可能是有字段未关联）: {str(e)}")
            # 不抛出异常，允许管理员手动创建记录

    def save(self, *args, **kwargs):
        """保存方法，允许手动创建"""
        # 如果是新记录
        if not self.pk:
            logger.info(f"开始保存新的报废车信息记录")

            # 如果有行驶证记录，尝试填充数据
            if self.vehicle_record:
                logger.info(f"有行驶证记录，尝试填充数据: {self.vehicle_record.id}")
                self._populate_from_related_records()

                # 验证是否有有效数据
                if not self._has_valid_data():
                    logger.warning(f"报废车信息记录数据不完整，但继续创建（可能是手动创建）")

            # 检查是否已存在记录（如果有行驶证记录）
            if self.vehicle_record:
                existing_scrap_info = ScrapCarInfo.objects.filter(vehicle_record=self.vehicle_record).first()
                if existing_scrap_info:
                    logger.info(f"车辆记录 {self.vehicle_record.id} 已存在报废车信息: {existing_scrap_info.id}")
                    # 更新现有记录
                    self._update_existing_record(existing_scrap_info)
                    return

        # 调用父类保存方法
        super().save(*args, **kwargs)
        logger.info(f"报废车信息记录保存成功: ID {self.id}")

    def _has_valid_data(self):
        """检查是否有有效数据  """
        # 检查关键字段是否有值
        required_fields = [
            self.owner_name, self.vehicle_number, self.vin,
            self.brand, self.vehicle_model
        ]

        # 至少有一个关键字段有值
        has_data = any(field and str(field).strip() for field in required_fields)

        # 额外检查：如果有关联记录但关键字段都为空，也不应该创建
        if (self.id_card_record or self.business_record) and not has_data:
            logger.warning(
                f"有关联记录但数据不完整: 车主={self.owner_name}, 车牌={self.vehicle_number}, VIN={self.vin}")
            return False

        if not has_data:
            logger.warning(
                f"报废车信息记录数据不完整: 车主='{self.owner_name}', 车牌='{self.vehicle_number}', VIN='{self.vin}'")

        return has_data

    def _populate_from_related_records(self):
        """从关联记录填充数据  """
        logger.info(f"开始从关联记录填充数据，车辆记录: {self.vehicle_record.id}")

        try:
            # 从行驶证记录提取信息
            if hasattr(self.vehicle_record, 'vehicle_result'):
                vehicle_result = self.vehicle_record.vehicle_result

                # 按照顺序填充字段
                self.vehicle_number = vehicle_result.number or ''
                self.vin = vehicle_result.vin or ''
                self.vehicle_type = vehicle_result.vehicle_type or ''
                self.use_character = vehicle_result.use_character or ''
                self.brand = vehicle_result.brand or ''
                self.vehicle_model = vehicle_result.vehicle_model or ''
                self.engine_no = vehicle_result.engine_no or ''
                self.approved_passengers = vehicle_result.approved_passengers or ''
                self.register_date = vehicle_result.register_date or ''
                self.energy_type = vehicle_result.energy_type or ''
                self.unladen_mass = vehicle_result.unladen_mass or ''

                # 所有人信息
                self.owner_name = vehicle_result.owner_name or ''
                self.address = vehicle_result.address or ''

                logger.info(f"从行驶证填充数据: 车主={self.owner_name}, 车牌={self.vehicle_number}")

            # 从身份证记录提取信息
            if self.id_card_record and hasattr(self.id_card_record, 'id_card_result'):
                id_card_result = self.id_card_record.id_card_result
                if self.match_score >= 50 or self.match_type == 'id_card':
                    self.identification_number = id_card_result.number or ''
                    self.id_card_phone_number = id_card_result.phone_number or ''
                    logger.info(
                        f"从身份证填充数据: 身份证号={self.identification_number}, 手机号={self.id_card_phone_number}")

            # 从营业执照记录提取信息
            if self.business_record and hasattr(self.business_record, 'business_result'):
                business_result = self.business_record.business_result
                if self.match_score >= 50 or self.match_type == 'business':
                    self.identification_number = business_result.registration_number or ''
                    logger.info(f"从营业执照填充数据: 信用代码={self.identification_number}")

            # 如果同时匹配身份证和营业执照，优先使用身份证号码
            if self.match_type == 'both' and self.id_card_record:
                id_card_result = self.id_card_record.id_card_result
                self.identification_number = id_card_result.number or ''
                logger.info("同时匹配身份证和营业执照，优先使用身份证号码")

            logger.info(
                f"数据填充完成: 车主={self.owner_name}, 识别号={self.identification_number}, 手机号={self.id_card_phone_number}")

        except Exception as e:
            logger.error(f"填充关联记录数据失败: {str(e)}")
            raise

    def update_match_status(self):
        """更新匹配状态"""
        from django.utils import timezone

        if self.match_score >= 50:
            self.match_status = 'matched'
            self.matched_at = timezone.now()
        elif self.match_score > 0:
            self.match_status = 'manual_review'
            self.matched_at = None
        else:
            self.match_status = 'unmatched'
            self.matched_at = None

    def get_vehicle_image_thumbnail(self):
        """获取行驶证图片缩略图"""
        if self.vehicle_record and self.vehicle_record.thumbnail:
            return self.vehicle_record.thumbnail.url
        return None

    def get_id_card_image_thumbnail(self):
        """获取身份证图片缩略图"""
        if self.id_card_record and self.id_card_record.thumbnail:
            return self.id_card_record.thumbnail.url
        return None

    def get_business_image_thumbnail(self):
        """获取营业执照图片缩略图"""
        if self.business_record and self.business_record.thumbnail:
            return self.business_record.thumbnail.url
        return None

    def is_duplicate_of(self, other_record):
        """
        判断当前记录是否与另一条记录重复

        Args:
            other_record: 另一条ScrapCarInfo记录

        Returns:
            bool: 是否重复
        """
        # VIN码匹配
        if (self.vin and other_record.vin and
                self.vin.strip() and other_record.vin.strip() and
                self.vin == other_record.vin):
            return True

        # 车牌号码匹配
        if (self.vehicle_number and other_record.vehicle_number and
                self.vehicle_number.strip() and other_record.vehicle_number.strip() and
                self.vehicle_number == other_record.vehicle_number):
            return True

        # 车主+品牌+型号组合匹配
        if (self.owner_name and other_record.owner_name and
                self.brand and other_record.brand and
                self.vehicle_model and other_record.vehicle_model and
                self.owner_name.strip() and other_record.owner_name.strip() and
                self.brand.strip() and other_record.brand.strip() and
                self.vehicle_model.strip() and other_record.vehicle_model.strip() and
                self.owner_name == other_record.owner_name and
                self.brand == other_record.brand and
                self.vehicle_model == other_record.vehicle_model):
            return True

        # 发动机号匹配
        if (self.engine_no and other_record.engine_no and
                self.engine_no.strip() and other_record.engine_no.strip() and
                self.engine_no == other_record.engine_no):
            return True

        return False

    @staticmethod
    def find_duplicate_records(new_record):
        """
        查找重复的报废车信息记录

        Args:
            new_record: 新创建的ScrapCarInfo记录

        Returns:
            QuerySet: 重复记录查询集
        """
        from django.db.models import Q

        # 定义重复判断条件
        duplicate_conditions = Q()

        # 清理字符串的辅助函数
        def clean_string(s):
            if not s:
                return ""
            return str(s).strip().upper().replace(' ', '').replace('-', '').replace('_', '')

        # 1. VIN码匹配（最准确的判断）
        new_vin = clean_string(new_record.vin)
        if new_vin and len(new_vin) >= 5:
            duplicate_conditions |= Q(vin__iexact=new_record.vin)

        # 2. 车牌号码匹配
        new_vehicle_number = clean_string(new_record.vehicle_number)
        if new_vehicle_number and len(new_vehicle_number) >= 4:
            duplicate_conditions |= Q(vehicle_number__iexact=new_record.vehicle_number)

        # 3. 车主姓名 + 车辆品牌型号组合匹配
        new_owner_name = clean_string(new_record.owner_name)
        new_brand = clean_string(new_record.brand)
        new_vehicle_model = clean_string(new_record.vehicle_model)
        if (new_owner_name and len(new_owner_name) >= 2 and
                new_brand and len(new_brand) >= 2 and
                new_vehicle_model and len(new_vehicle_model) >= 2):
            duplicate_conditions |= Q(
                owner_name__iexact=new_record.owner_name,
                brand__iexact=new_record.brand,
                vehicle_model__iexact=new_record.vehicle_model
            )

        # 4. 发动机号匹配
        new_engine_no = clean_string(new_record.engine_no)
        if new_engine_no and len(new_engine_no) >= 4:
            duplicate_conditions |= Q(engine_no__iexact=new_record.engine_no)

        # 如果没有有效的匹配条件，返回空查询集
        if not duplicate_conditions:
            return ScrapCarInfo.objects.none()

        # 查找重复记录（排除自身）
        existing_records = ScrapCarInfo.objects.filter(duplicate_conditions)
        if new_record.pk:
            existing_records = existing_records.exclude(pk=new_record.pk)

        return existing_records

    def replace_duplicate_record(self, duplicate_record):
        """
        用当前记录替换重复记录

        Args:
            duplicate_record: 要替换的重复记录

        Returns:
            bool: 替换是否成功
        """
        try:
            logger.info(f"开始替换重复记录: 新记录={self.id}, 旧记录={duplicate_record.id}")

            # 记录替换前的信息用于日志
            old_data = {
                'owner_name': duplicate_record.owner_name,
                'vehicle_number': duplicate_record.vehicle_number,
                'vin': duplicate_record.vin,
                'match_status': duplicate_record.match_status
            }

            # 更新重复记录的字段为新记录的值
            duplicate_record.owner_name = self.owner_name
            duplicate_record.identification_number = self.identification_number
            duplicate_record.address = self.address
            duplicate_record.vin = self.vin
            duplicate_record.vehicle_number = self.vehicle_number
            duplicate_record.vehicle_type = self.vehicle_type
            duplicate_record.use_character = self.use_character
            duplicate_record.brand = self.brand
            duplicate_record.vehicle_model = self.vehicle_model
            duplicate_record.engine_no = self.engine_no
            duplicate_record.approved_passengers = self.approved_passengers
            duplicate_record.register_date = self.register_date
            duplicate_record.energy_type = self.energy_type
            duplicate_record.unladen_mass = self.unladen_mass
            duplicate_record.remarks = self.remarks

            # 更新匹配信息
            duplicate_record.vehicle_record = self.vehicle_record
            duplicate_record.id_card_record = self.id_card_record
            duplicate_record.business_record = self.business_record
            duplicate_record.match_status = self.match_status
            duplicate_record.match_score = self.match_score
            duplicate_record.match_rules = self.match_rules
            duplicate_record.matched_at = self.matched_at

            # 保存更新后的记录
            duplicate_record.save()

            logger.info(f"成功替换重复记录: 旧记录ID={duplicate_record.id}, 旧数据={old_data}")
            return True

        except Exception as e:
            logger.error(f"替换重复记录失败: {str(e)}")
            return False

    def _update_existing_record(self, existing_scrap_info):
        """
        更新已存在的记录
        """
        try:
            logger.info(f"开始更新已存在的记录: {existing_scrap_info.id}")

            # 复制当前记录的数据到已存在记录
            existing_scrap_info.owner_name = self.owner_name
            existing_scrap_info.identification_number = self.identification_number
            existing_scrap_info.address = self.address
            existing_scrap_info.vin = self.vin
            existing_scrap_info.vehicle_number = self.vehicle_number
            existing_scrap_info.vehicle_type = self.vehicle_type
            existing_scrap_info.use_character = self.use_character
            existing_scrap_info.brand = self.brand
            existing_scrap_info.vehicle_model = self.vehicle_model
            existing_scrap_info.engine_no = self.engine_no
            existing_scrap_info.approved_passengers = self.approved_passengers
            existing_scrap_info.register_date = self.register_date
            existing_scrap_info.energy_type = self.energy_type
            existing_scrap_info.unladen_mass = self.unladen_mass
            existing_scrap_info.remarks = self.remarks

            # 复制关联记录
            if self.id_card_record:
                existing_scrap_info.id_card_record = self.id_card_record
            if self.business_record:
                existing_scrap_info.business_record = self.business_record

            # 更新匹配信息
            existing_scrap_info.match_status = self.match_status
            existing_scrap_info.match_score = self.match_score
            existing_scrap_info.match_rules = self.match_rules
            existing_scrap_info.matched_at = self.matched_at

            # 保存更新后的记录
            existing_scrap_info.save()

            # 设置当前对象的ID为已存在记录的ID，这样后续调用super().save()时会更新而不是创建新记录
            self.pk = existing_scrap_info.pk
            self.created_at = existing_scrap_info.created_at
            self.updated_at = existing_scrap_info.updated_at

            logger.info(f"成功更新记录: {existing_scrap_info.id}")

        except Exception as e:
            logger.error(f"更新已存在记录失败: {str(e)}")
            raise