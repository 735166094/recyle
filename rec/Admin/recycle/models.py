# recycle/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
import json

from django.utils.html import format_html
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class ScrapCar(models.Model):
    """
    报废车回收信息模型
    """

    STATUS_CHOICES = (
        ('pending', '待评估'),
        ('priced', '已报价'),
        ('confirmed', '已同意'),
        ('cancelled', '已取消'),
    )

    # 联系人信息
    contact_name = models.CharField(max_length=50, verbose_name='联系人姓名')
    contact_phone = models.CharField(max_length=11, verbose_name='联系电话')
    region = models.CharField(max_length=200, verbose_name='所在地区')
    address = models.TextField(blank=True, verbose_name='详细地址')

    # 车辆信息
    car_model = models.CharField(max_length=100, verbose_name='车型')
    car_count = models.PositiveIntegerField(default=1, verbose_name='车辆数量')
    wheel_type = models.CharField(max_length=50, blank=True, verbose_name='轮毂类型')
    wheel_count = models.PositiveIntegerField(default=0, verbose_name='轮毂数量')
    ternary_count = models.PositiveIntegerField(default=0, verbose_name='三元催化器数量')
    battery_count = models.PositiveIntegerField(default=0, verbose_name='铅蓄电池数量')
    battery_pack_count = models.PositiveIntegerField(default=0, verbose_name='电池包数量')
    engine_count = models.PositiveIntegerField(default=0, verbose_name='发动机数量')
    weight = models.PositiveIntegerField(null=True, blank=True, verbose_name='整备质量(千克)')
    can_start = models.BooleanField(default=True, verbose_name='能否正常启动')
    car_image = models.ImageField(upload_to='scrap_cars/%Y/%m/', verbose_name='车辆照片', null=True, blank=True)
    car_image_path = models.CharField(max_length=500, blank=True, verbose_name='车辆照片路径')
    remark = models.TextField(blank=True, verbose_name='备注信息')

    # 系统字段
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='提交用户')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    estimated_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                          verbose_name='预估价格')
    final_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='最终价格')
    submit_time = models.DateTimeField(default=timezone.now, verbose_name='提交时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    # 状态变更日志
    status_history = models.TextField(blank=True, default='[]', verbose_name='状态变更历史')

    class Meta:
        db_table = 'recycle_scrap_car'
        verbose_name = '报废车回收信息'
        verbose_name_plural = '报废车回收信息'
        ordering = ['-submit_time']

    def __str__(self):
        return f"{self.contact_name} - {self.car_model} - {self.get_status_display()}"

    def get_status_display(self):
        """获取状态显示"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def get_can_start_display(self):
        """获取能否启动的显示文本"""
        return "能" if self.can_start else "不能"

    def get_car_image_url(self):
        """获取车辆图片URL"""
        if self.car_image and hasattr(self.car_image, 'url'):
            return self.car_image.url
        elif self.car_image_path:
            # 如果car_image_path是完整的URL，直接返回
            if self.car_image_path.startswith(('http://', 'https://')):
                return self.car_image_path
            # 否则构建完整的URL
            else:
                # 确保MEDIA_URL以/结尾
                media_url = getattr(settings, 'MEDIA_URL', '/media/')
                if not media_url.endswith('/'):
                    media_url += '/'
                return f"{media_url}{self.car_image_path}"
        return None

    def get_user_info(self):
        """获取用户信息"""
        if self.user:
            return {
                'username': self.user.username,
                'phone': self.user.phone,
                'nickname': self.user.nickname
            }
        return None

    def get_display_price(self):
        """获取显示价格 - 修改逻辑：当最终价格为空时显示预估价格"""
        if self.final_price is not None:
            return float(self.final_price)
        elif self.estimated_price is not None:
            return float(self.estimated_price)
        return None

    def get_status_class(self):
        """获取状态对应的CSS类名"""
        status_class_map = {
            'pending': 'status-pending',
            'priced': 'status-priced',
            'confirmed': 'status-confirmed',
            'cancelled': 'status-cancelled'
        }
        return status_class_map.get(self.status, 'status-pending')

    def get_user_display_info(self):
        """获取用户显示信息"""
        if self.user:
            return {
                'username': self.user.username,
                'nickname': self.user.nickname,
                'phone': self.user.phone
            }
        return None

    def update_status(self, new_status, reason='', user=None):
        """更新状态并记录变更历史"""
        old_status = self.status

        if old_status != new_status:
            # 记录状态变更历史
            history = json.loads(self.status_history)
            history.append({
                'old_status': old_status,
                'new_status': new_status,
                'old_status_display': self.get_status_display(),
                'new_status_display': dict(self.STATUS_CHOICES).get(new_status, new_status),
                'timestamp': timezone.now().isoformat(),
                'reason': reason,
                'changed_by': user.username if user else 'system'
            })
            self.status_history = json.dumps(history, ensure_ascii=False)
            self.status = new_status

    def save(self, *args, **kwargs):
        """重写保存方法，实现自动状态更新和价格填充"""
        # 如果状态变为confirmed且最终价格为None，且预估价格不为None，则自动填充最终价格
        if self.status == 'confirmed' and self.final_price is None and self.estimated_price is not None:
            self.final_price = self.estimated_price
            logger.info(f"模型保存时自动填充最终价格: 订单{self.id}的最终价格设置为预估价格{self.estimated_price}")

        # 如果预估价格被设置且不为空，并且当前状态是待评估，则更新状态
        if self.estimated_price is not None and self.estimated_price > 0 and self.status == 'pending':
            self.update_status('priced', '系统自动更新：已设置预估价格')

        # 如果状态历史为空，初始化
        if not self.status_history:
            self.status_history = json.dumps([{
                'old_status': '',
                'new_status': self.status,
                'old_status_display': '',
                'new_status_display': self.get_status_display(),
                'timestamp': self.submit_time.isoformat() if self.submit_time else timezone.now().isoformat(),
                'reason': '初始提交',
                'changed_by': self.user.username if self.user else 'system'
            }], ensure_ascii=False)

        super().save(*args, **kwargs)

    def get_status_history_display(self):
        """获取状态变更历史显示"""
        try:
            history = json.loads(self.status_history)
            return history
        except:
            return []

    # 为admin显示添加方法
    def contact_name_display(self):
        return self.contact_name

    contact_name_display.short_description = '联系人姓名'

    def contact_phone_display(self):
        return self.contact_phone

    contact_phone_display.short_description = '联系电话'

    def car_model_display(self):
        return self.car_model

    car_model_display.short_description = '车型'

    def car_count_display(self):
        return self.car_count

    car_count_display.short_description = '车辆数量'

    def region_display(self):
        return self.region

    region_display.short_description = '所在地区'

    def wheel_type_display(self):
        return self.wheel_type if self.wheel_type else '未填写'

    wheel_type_display.short_description = '轮毂类型'

    def wheel_count_display(self):
        return self.wheel_count

    wheel_count_display.short_description = '轮毂数量'

    def ternary_count_display(self):
        return self.ternary_count

    ternary_count_display.short_description = '三元催化器数量'

    def battery_count_display(self):
        return self.battery_count

    battery_count_display.short_description = '铅蓄电池数量'

    def battery_pack_count_display(self):
        return self.battery_pack_count

    battery_pack_count_display.short_description = '电池包数量'

    def engine_count_display(self):
        return self.engine_count

    engine_count_display.short_description = '发动机数量'

    def weight_display(self):
        return f"{self.weight}千克" if self.weight else '未填写'

    weight_display.short_description = '整备质量'

    def can_start_display(self):
        return "能" if self.can_start else "不能"

    can_start_display.short_description = '能否启动'

    def address_display(self):
        return self.address if self.address else '未填写'

    address_display.short_description = '详细地址'

    def remark_display(self):
        return self.remark if self.remark else '无'

    remark_display.short_description = '备注信息'

    def status_history_display(self):
        """状态变更历史显示"""
        history = self.get_status_history_display()
        if history:
            return format_html('<br>'.join([
                f"{item['timestamp'][:16]} {item['old_status_display']} → {item['new_status_display']}"
                for item in history[-5:]  # 显示最近5条
            ]))
        return "无变更历史"

    status_history_display.short_description = '状态变更历史'


class PriceRule(models.Model):
    """
    价格规则模型
    """
    name = models.CharField(max_length=100, verbose_name='规则名称')
    car_type = models.CharField(max_length=50, verbose_name='车辆类型')
    base_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='基础价格')
    weight_factor = models.DecimalField(max_digits=5, decimal_places=2, default=1.0, verbose_name='重量系数')
    condition_factor = models.DecimalField(max_digits=5, decimal_places=2, default=1.0, verbose_name='车况系数')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'recycle_price_rule'
        verbose_name = '价格规则'
        verbose_name_plural = '价格规则'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.car_type})"

    def get_full_info(self):
        """获取完整价格规则信息"""
        return f"{self.name} | 车型: {self.car_type} | 基础价: ¥{self.base_price} | 重量系数: {self.weight_factor} | 车况系数: {self.condition_factor}"


class LocationCache(models.Model):
    """
    位置缓存模型
    """
    latitude = models.DecimalField(max_digits=10, decimal_places=6, verbose_name="纬度")
    longitude = models.DecimalField(max_digits=10, decimal_places=6, verbose_name="经度")
    province = models.CharField(max_length=50, verbose_name="省份")
    city = models.CharField(max_length=50, verbose_name="城市")
    district = models.CharField(max_length=50, verbose_name="区县")
    address = models.CharField(max_length=200, verbose_name="详细地址")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "recycle_location_cache"
        verbose_name = "位置缓存"
        verbose_name_plural = "位置缓存"
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.province}{self.city}{self.district}"

    def get_full_address(self):
        """获取完整地址"""
        return f"{self.province}{self.city}{self.district}{self.address}"


class EvaluationMaterial(models.Model):
    """
    车辆评估材质价格模型
    """
    name = models.CharField(max_length=50, unique=True, verbose_name='材质名称')
    price_per_ton = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='单价（元/吨）')
    factor = models.DecimalField(max_digits=3, decimal_places=2, default=0.56, verbose_name='计算系数')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'recycle_evaluation_material'
        verbose_name = '车辆评估'
        verbose_name_plural = '车辆评估'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.name} - ¥{self.price_per_ton}/吨"
