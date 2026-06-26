# points/models.py
import logging
from django.db import models
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class PointsRule(models.Model):
    """
    积分规则定义
    """
    RULE_TYPE_CHOICES = (
        ('sign', '签到'),
        ('task', '任务奖励'),
        ('purchase', '购物奖励'),
        ('recycle', '回收奖励'),
        ('system_bonus', '系统奖励'),
        ('consume', '消费扣除'),
        ('year_end_reset', '年终清零'),
        ('other', '其他'),
    )

    # 绿色生活相关规则类型
    GREEN_LIFE_TYPE_CHOICES = (
        ('transport', '绿色出行'),
        ('food', '光盘行动'),
        ('walk', '低碳行走'),
        ('learning', '低碳学习'),
    )

    # 规则配置字段（JSON格式，存储灵活的配置）
    rule_config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="规则配置（JSON）"
    )

    # 计算公式字段
    calculation_formula = models.TextField(
        blank=True,
        null=True,
        verbose_name="积分计算公式"
    )

    # 变量定义
    variables_config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="变量配置"
    )

    # 步骤配置（用于多步骤任务）
    steps_config = models.JSONField(
        default=list,
        blank=True,
        verbose_name="步骤配置"
    )

    # 触发条件配置
    trigger_conditions = models.JSONField(
        default=list,
        blank=True,
        verbose_name="触发条件"
    )

    rule_id = models.CharField(max_length=50, unique=True, verbose_name="规则ID")
    rule_name = models.CharField(max_length=100, verbose_name="规则名称")
    rule_type = models.CharField(max_length=20, choices=RULE_TYPE_CHOICES, verbose_name="规则类型")
    green_type = models.CharField(max_length=20, choices=GREEN_LIFE_TYPE_CHOICES, blank=True, null=True,
                                  verbose_name="绿色生活类型")

    points_value = models.IntegerField(default=0, verbose_name="积分值")
    points_limit = models.IntegerField(default=0, verbose_name="积分上限（0表示无限制）")
    daily_limit = models.IntegerField(default=0, verbose_name="每日上限")
    monthly_limit = models.IntegerField(default=0, verbose_name="每月上限")

    # 规则条件配置
    condition_type = models.CharField(
        max_length=20,
        choices=(
            ('count', '次数达标'),
            ('amount', '金额达标'),
            ('days', '连续天数'),
            ('steps', '步数达标'),
            ('upload', '上传凭证'),
            ('certificate', '证书认证'),
        ),
        default='count',
        verbose_name="条件类型"
    )
    condition_value = models.IntegerField(default=0, verbose_name="条件值")
    condition_unit = models.CharField(max_length=20, blank=True, null=True, verbose_name="条件单位")

    description = models.TextField(verbose_name="规则描述")
    instructions = models.TextField(blank=True, null=True, verbose_name="操作说明")

    # 绿色生活特定字段
    need_upload = models.BooleanField(default=False, verbose_name="需要上传凭证")
    upload_desc = models.TextField(blank=True, null=True, verbose_name="上传说明")
    certificate_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="证书名称")

    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    sort_order = models.IntegerField(default=0, verbose_name="排序")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "points_rule"
        verbose_name = "积分规则"
        verbose_name_plural = "积分规则"
        ordering = ["sort_order", "rule_name"]

    def __str__(self):
        return f"{self.rule_name} ({self.get_rule_type_display()})"


class PointsRecord(models.Model):
    """
    积分记录
    """
    POINTS_TYPE_CHOICES = (
        ('sign', '签到'),
        ('task', '任务奖励'),
        ('purchase', '购物奖励'),
        ('recycle', '回收奖励'),
        ('system_bonus', '系统奖励'),
        ('consume', '消费扣除'),
        ('year_end_reset', '年终清零'),
        ('order_refund', '订单取消返还'),
        ('other', '其他'),
    )

    # 绿色生活相关类型
    GREEN_LIFE_TYPE_CHOICES = (
        ('transport', '绿色出行'),
        ('food', '光盘行动'),
        ('walk', '低碳行走'),
        ('learning', '低碳学习'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='points_records_new',
        verbose_name="用户"
    )

    # 积分规则关联（新增）
    points_rule = models.ForeignKey(
        PointsRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='records',
        verbose_name="积分规则"
    )

    points_type = models.CharField(max_length=20, choices=POINTS_TYPE_CHOICES, verbose_name="积分类型")
    green_type = models.CharField(max_length=20, choices=GREEN_LIFE_TYPE_CHOICES, blank=True, null=True,
                                  verbose_name="绿色生活类型")

    points_change = models.IntegerField(verbose_name="积分变动")
    current_points = models.IntegerField(verbose_name="变动后积分")

    # 关联信息
    related_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="关联ID")
    order_no = models.CharField(max_length=50, blank=True, null=True, verbose_name="订单号")
    recycle_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="回收记录ID")

    # 绿色生活特定字段
    upload_image = models.ImageField(upload_to='points/uploads/%Y/%m/', blank=True, null=True, verbose_name="上传凭证")
    certificate_image = models.ImageField(upload_to='points/certificates/%Y/%m/', blank=True, null=True,
                                          verbose_name="证书图片")
    steps_count = models.IntegerField(default=0, verbose_name="步数")
    days_count = models.IntegerField(default=0, verbose_name="连续天数")
    is_verified = models.BooleanField(default=False, verbose_name="是否已验证")
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_points_records',
        verbose_name="审核人"
    )
    verified_at = models.DateTimeField(blank=True, null=True, verbose_name="审核时间")

    description = models.TextField(blank=True, null=True, verbose_name="详细说明")
    remark = models.TextField(blank=True, null=True, verbose_name="备注")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "points_record"
        verbose_name = "积分记录"
        verbose_name_plural = "积分记录"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', 'points_type']),
            models.Index(fields=['points_type', 'created_at']),
            models.Index(fields=['green_type', 'is_verified']),
            models.Index(fields=['user', 'green_type', 'created_at']),
            models.Index(fields=['user', 'points_type', 'created_at']),
            models.Index(fields=['created_at', 'points_type']),
        ]

    def __str__(self):
        change_symbol = "+" if self.points_change > 0 else ""
        return f"{self.user.username} {change_symbol}{self.points_change}积分 ({self.get_points_type_display()})"

    def save(self, *args, **kwargs):
        """
        save方法，自动设置验证状态和当前积分
        """
        # 确保 current_points 不为 None
        if self.current_points is None:
            # 如果用户已设置，则计算当前积分
            if self.user_id:
                try:
                    # 重新加载用户以确保获得最新积分
                    if hasattr(self, '_user_cache'):
                        delattr(self, '_user_cache')

                    from user.models import User
                    user = User.objects.get(pk=self.user_id)
                    self.current_points = user.points + self.points_change

                    # 更新用户积分
                    user.points = self.current_points
                    user.save(update_fields=['points', 'updated_at'])
                except Exception as e:
                    logger.error(f"计算 current_points 失败: {e}")
                    # 设置一个合理的默认值
                    self.current_points = self.points_change if self.points_change > 0 else 0
            else:
                # 如果没有用户，设置为积分变动值
                self.current_points = self.points_change if self.points_change > 0 else 0

        # 自动设置验证状态（某些类型不需要验证）
        if not self.pk:
            if self.points_type in ['sign', 'system_bonus']:
                # 签到和系统奖励自动验证
                self.is_verified = True
                self.verified_at = timezone.now()
                self.verified_by = None  # 系统自动验证
            elif self.points_change < 0:
                # 消费类操作自动验证（因为积分足够才能消费）
                self.is_verified = True
                self.verified_at = timezone.now()
                self.verified_by = None  # 系统自动验证

        # 调用父类保存
        super().save(*args, **kwargs)


class UserDailyPoints(models.Model):
    """
    用户每日积分统计
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='daily_points',
        verbose_name="用户"
    )
    date = models.DateField(verbose_name="日期")

    # 各种类型的积分统计
    sign_points = models.IntegerField(default=0, verbose_name="签到积分")
    task_points = models.IntegerField(default=0, verbose_name="任务积分")
    green_points = models.IntegerField(default=0, verbose_name="绿色生活积分")
    purchase_points = models.IntegerField(default=0, verbose_name="购物积分")
    recycle_points = models.IntegerField(default=0, verbose_name="回收积分")
    consume_points = models.IntegerField(default=0, verbose_name="消费积分")

    total_points = models.IntegerField(default=0, verbose_name="总积分")

    # 绿色生活统计
    transport_days = models.IntegerField(default=0, verbose_name="绿色出行天数")
    food_days = models.IntegerField(default=0, verbose_name="光盘行动天数")
    walk_steps = models.IntegerField(default=0, verbose_name="行走步数")
    learning_count = models.IntegerField(default=0, verbose_name="学习次数")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "user_daily_points"
        verbose_name = "用户每日积分统计"
        verbose_name_plural = "用户每日积分统计"
        unique_together = ['user', 'date']
        ordering = ["-date"]

    def __str__(self):
        return f"{self.user.username} - {self.date}"


class PointsTransaction(models.Model):
    """
    积分交易记录
    """
    TRANSACTION_TYPE_CHOICES = (
        ('earn', '获取积分'),
        ('redeem', '兑换商品'),
        ('transfer', '转让积分'),
        ('adjust', '系统调整'),
    )

    STATUS_CHOICES = (
        ('pending', '待处理'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    )

    transaction_no = models.CharField(max_length=50, unique=True, verbose_name="交易流水号")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='points_transactions',
        verbose_name="用户"
    )

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, verbose_name="交易类型")
    points_amount = models.IntegerField(verbose_name="积分数量")

    # 关联商品信息
    product_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="商品ID")
    product_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="商品名称")
    product_points = models.IntegerField(default=0, verbose_name="商品所需积分")

    # 兑换信息
    redeem_address = models.ForeignKey(
        'user.UserAddress',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="收货地址"
    )
    express_no = models.CharField(max_length=100, blank=True, null=True, verbose_name="快递单号")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="状态")
    remark = models.TextField(blank=True, null=True, verbose_name="备注")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="完成时间")

    class Meta:
        db_table = "points_transaction"
        verbose_name = "积分交易记录"
        verbose_name_plural = "积分交易记录"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['transaction_no']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.transaction_no} - {self.user.username} - {self.points_amount}积分"


class UserMonthlySummary(models.Model):
    """
    用户月度积分汇总
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='monthly_summaries',
        verbose_name="用户"
    )
    year = models.IntegerField(verbose_name="年份")
    month = models.IntegerField(verbose_name="月份")

    # 月度统计
    total_earned = models.IntegerField(default=0, verbose_name="本月获得积分")
    total_consumed = models.IntegerField(default=0, verbose_name="本月消费积分")
    ending_balance = models.IntegerField(default=0, verbose_name="月底余额")

    # 绿色生活统计
    green_days_total = models.IntegerField(default=0, verbose_name="绿色生活总天数")
    green_points_total = models.IntegerField(default=0, verbose_name="绿色生活总积分")
    transport_days = models.IntegerField(default=0, verbose_name="绿色出行天数")
    food_days = models.IntegerField(default=0, verbose_name="光盘行动天数")
    walk_points = models.IntegerField(default=0, verbose_name="低碳行走积分")
    learning_points = models.IntegerField(default=0, verbose_name="低碳学习积分")

    # 达标情况
    is_transport_qualified = models.BooleanField(default=False, verbose_name="绿色出行达标")
    is_food_qualified = models.BooleanField(default=False, verbose_name="光盘行动达标")
    is_walk_qualified = models.BooleanField(default=False, verbose_name="低碳行走达标")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "user_monthly_summary"
        verbose_name = "用户月度积分汇总"
        verbose_name_plural = "用户月度积分汇总"
        unique_together = ['user', 'year', 'month']
        ordering = ["-year", "-month"]

    def __str__(self):
        return f"{self.user.username} - {self.year}年{self.month}月"


class Order(PointsTransaction):
    """
    订单代理模型，用于后台管理界面
    仅用于区分积分交易中的兑换订单，不创建新表
    """
    class Meta:
        proxy = True
        verbose_name = "订单"
        verbose_name_plural = "订单管理"

    def __str__(self):
        return f"订单 {self.transaction_no} - {self.user.username}"