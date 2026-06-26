# vin/models.py
from django.db import models
from django.conf import settings
import logging

logger = logging.getLogger('vin')


class VinConfig(models.Model):
    """VIN查询配置模型"""
    name = models.CharField(max_length=100, verbose_name="配置名称")
    username = models.CharField(max_length=100, verbose_name="用户名")
    password = models.CharField(max_length=100, verbose_name="密码")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    # 控制是否保存查询结果
    save_query_results = models.BooleanField(
        default=True,
        verbose_name="保存查询结果",
        help_text="启用后，所有使用此配置的查询结果都会被保存到数据库"
    )

    # 控制微信小程序是否保存结果
    save_miniprogram_results = models.BooleanField(
        default=False,
        verbose_name="保存小程序查询结果",
        help_text="启用后，微信小程序的VIN查询结果也会被保存到数据库"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "vin_config"
        verbose_name = "VIN查询配置"
        verbose_name_plural = "VIN查询配置"
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class VinQueryResult(models.Model):
    """VIN查询结果模型 """

    QUERY_STATUS_CHOICES = (
        ('pending', '待查询'),
        ('processing', '处理中'),
        ('success', '成功'),
        ('failed', '失败')
    )

    # 基础信息
    vin_code = models.CharField(max_length=50, verbose_name="VIN码", db_index=True)
    config_used = models.ForeignKey(
        VinConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="使用的配置"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vin_query_results",
        verbose_name="查询用户",
    )


    # 查询状态
    query_status = models.CharField(
        max_length=20,
        choices=QUERY_STATUS_CHOICES,
        default='pending',
        verbose_name="查询状态"
    )
    error_message = models.TextField(blank=True, null=True, verbose_name="错误信息")
    query_time = models.DateTimeField(auto_now_add=True, verbose_name="查询时间")
    processing_time = models.FloatField(default=0, verbose_name="处理时间(秒)")

    # 核心车辆信息 - 只保留品牌、车型、年份
    brand = models.CharField(max_length=100, blank=True, null=True, verbose_name="品牌")
    model_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="车型名称")
    model_year = models.CharField(max_length=50, blank=True, null=True, verbose_name="车型年份")
    build_date = models.CharField(max_length=50, blank=True, null=True, verbose_name="生产日期")

    # 详细数据（JSON格式存储）
    model_list = models.JSONField(default=list, verbose_name="车型列表")
    original_epc_list = models.JSONField(default=list, verbose_name="原厂EPC列表")
    gonggao_list = models.JSONField(default=list, verbose_name="公告列表")
    import_list = models.JSONField(default=list, verbose_name="进口车型列表")
    original_attributes = models.JSONField(default=list, verbose_name="原厂属性")

    # 原始响应数据
    raw_response_data = models.JSONField(default=dict, verbose_name="原始响应数据")

    # 车型统计信息
    model_count = models.IntegerField(default=0, verbose_name="车型数量")

    class Meta:
        db_table = "vin_query_result"
        verbose_name = "VIN查询结果"
        verbose_name_plural = "VIN查询结果"
        ordering = ['-query_time']
        indexes = [
            models.Index(fields=['vin_code'], name='idx_vin_code'),
            models.Index(fields=['user', 'query_time'], name='idx_user_query_time'),
            models.Index(fields=['query_status'], name='idx_query_status'),
            models.Index(fields=['brand'], name='idx_brand'),
            models.Index(fields=['model_year'], name='idx_model_year'),
            models.Index(fields=['model_name'], name='idx_model_name'),
        ]

    def __str__(self):
        return f"VIN查询: {self.vin_code} - {self.get_query_status_display()}"

    def save(self, *args, **kwargs):
        """保存时确保数据完整性"""
        if self.raw_response_data:
            self._populate_from_raw_data()
        self._calculate_statistics()
        super().save(*args, **kwargs)

    def _populate_from_raw_data(self):
        """从原始响应数据填充字段"""
        try:
            if not self.raw_response_data:
                return

            if isinstance(self.raw_response_data, str):
                import json
                try:
                    self.raw_response_data = json.loads(self.raw_response_data)
                except json.JSONDecodeError:
                    logger.error(f"无法解析 raw_response_data JSON 字符串")
                    return

            data = self.raw_response_data.get('data', {})
            if not data:
                logger.warning(f"raw_response_data 中没有 data 字段")
                return

            # 品牌信息
            self.brand = data.get('brand', '') or self.brand or ''

            # 车型年份
            self.model_year = data.get('model_year_from_vin', '') or self.model_year or ''

            # 生产日期
            self.build_date = data.get('build_date', '') or self.build_date or ''

            # 车型名称 - 从model_list中提取第一个车型的Model_detail
            model_list = data.get('model_list', [])
            if model_list and isinstance(model_list, list) and len(model_list) > 0:
                first_model = model_list[0]
                if isinstance(first_model, dict):
                    # 优先使用Model_detail，如果没有则使用Model
                    self.model_name = first_model.get('Model_detail', '') or \
                                      first_model.get('Model', '') or \
                                      self.model_name or ''

            # 列表数据
            self.model_list = model_list or self.model_list or []
            self.original_epc_list = data.get('model_original_epc_list', []) or self.original_epc_list or []
            self.gonggao_list = data.get('model_gonggao_list', []) or self.gonggao_list or []
            self.import_list = data.get('model_import_list', []) or self.import_list or []

            # 原厂EPC数据
            original_epc_list = data.get('model_original_epc_list', []) or []
            if original_epc_list:
                attributes = []
                for epc in original_epc_list:
                    if not isinstance(epc, dict):
                        continue
                    car_attrs = epc.get('CarAttributes', [])
                    if not isinstance(car_attrs, list):
                        continue
                    for attr in car_attrs:
                        if isinstance(attr, dict) and attr.get('Language') == 'zh':
                            attributes.append(attr)
                self.original_attributes = attributes
            elif not self.original_attributes:
                self.original_attributes = []

            # 查询状态
            code = self.raw_response_data.get('code')
            if code == 1:
                self.query_status = 'success'
                self.error_message = None
            else:
                self.query_status = 'failed'
                self.error_message = self.raw_response_data.get('msg', '查询失败')

        except Exception as e:
            logger.error(f"从原始数据填充字段失败: {str(e)}", exc_info=True)

    def _calculate_statistics(self):
        """计算统计信息"""
        try:
            self.model_count = len(self.model_list) if self.model_list and isinstance(self.model_list, list) else 0
        except Exception as e:
            logger.error(f"计算统计信息失败: {str(e)}")
            self.model_count = 0

    @property
    def is_success(self):
        """是否查询成功"""
        return self.query_status == 'success'

    @property
    def has_vehicle_info(self):
        """是否有车辆信息"""
        return bool(self.brand and self.model_name and self.model_year)

    @property
    def has_images(self):
        """是否有图片"""
        if not self.model_list or not isinstance(self.model_list, list):
            return False
        try:
            return any(
                model.get('Img_adress')
                for model in self.model_list
                if isinstance(model, dict)
            )
        except Exception:
            return False

    def get_first_model(self):
        """获取第一个车型信息"""
        if self.model_list and len(self.model_list) > 0:
            return self.model_list[0]
        return None

    def get_model_images(self, model_index=0):
        """获取车型图片URL列表"""
        if not self.model_list or len(self.model_list) <= model_index:
            return []

        model = self.model_list[model_index]
        img_address = model.get('Img_adress', '')
        if not img_address:
            return []

        base_url = "http://resource.17vin.com/img/car/all/"
        img_paths = [path.strip() for path in img_address.split(',')]
        return [f"{base_url}{path}" for path in img_paths if path]

    def get_complete_data(self):
        """获取完整数据"""
        return {
            'basic_info': self.get_basic_info(),
            'model_list': self.model_list,
            'original_attributes': self.original_attributes,
            'gonggao_list': self.gonggao_list,
            'import_list': self.import_list,
            'original_epc_list': self.original_epc_list,
            'statistics': self.get_detailed_info()
        }

    def get_basic_info(self):
        """获取基础信息字典"""
        return {
            'brand': self.brand,
            'model_name': self.model_name,
            'model_year': self.model_year,
            'build_date': self.build_date,
        }

    def get_detailed_info(self):
        """获取详细信息字典"""
        return {
            'basic_info': self.get_basic_info(),
            'model_count': self.model_count,
            'original_attributes_count': len(self.original_attributes) if self.original_attributes else 0,
            'gonggao_count': len(self.gonggao_list) if self.gonggao_list else 0,
            'import_count': len(self.import_list) if self.import_list else 0,
            'has_images': self.has_images,
            'original_epc_count': len(self.original_epc_list) if self.original_epc_list else 0,
        }
