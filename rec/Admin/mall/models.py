from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from user.models import User


class GlobalSpecTemplate(models.Model):
    """
    全局规格模板
    用于存储公共规格，可在多个商品间复用
    """
    name = models.CharField(max_length=50, verbose_name="规格名称")
    description = models.TextField(blank=True, null=True, verbose_name="规格描述")
    icon = models.CharField(max_length=50, blank=True, null=True, verbose_name="图标类名")
    data_type = models.CharField(
        max_length=20,
        choices=(
            ('text', '文本'),
            ('color', '颜色'),
            ('image', '图片'),
            ('mixed', '混合'),
        ),
        default='text',
        verbose_name="数据类型"
    )
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    sort_order = models.IntegerField(default=0, verbose_name="排序")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "global_spec_template"
        verbose_name = "全局规格模板"
        verbose_name_plural = "全局规格模板"
        ordering = ["sort_order", "-created_at"]

    def __str__(self):
        return self.name


class GlobalSpecOption(models.Model):
    """
    全局规格选项模板
    """
    spec_template = models.ForeignKey(
        GlobalSpecTemplate,
        on_delete=models.CASCADE,
        related_name='global_options',
        verbose_name="规格模板"
    )
    value = models.CharField(max_length=50, verbose_name="选项值")
    image = models.URLField(blank=True, null=True, verbose_name="选项图片")
    color_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="颜色代码")
    base_price_increment = models.IntegerField(default=0, verbose_name="基础价格增量")
    sort_order = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = "global_spec_option"
        verbose_name = "全局规格选项"
        verbose_name_plural = "全局规格选项"
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.spec_template.name}: {self.value}"


class ProductCategory(models.Model):
    """
    商品类别
    """
    name = models.CharField(max_length=50, verbose_name="类别名称")
    description = models.TextField(blank=True, null=True, verbose_name="分类描述")
    image = models.URLField(blank=True, null=True, verbose_name="分类图片")
    icon = models.CharField(
        max_length=50,
        default='icon-defaults',
        verbose_name="图标类名",
        help_text="小程序图标字体类名，如：icon-car, icon-electronic"
    )
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "product_category"
        verbose_name = "商品类别"
        verbose_name_plural = "商品类别"
        ordering = ["sort_order", "-created_at"]

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    商品模型
    """
    PRODUCT_STATUS_CHOICES = (
        ('active', '热销中'), ('inactive', '下架'), ('sold_out', '售罄'), ('restocking', '补货中'))

    name = models.CharField(max_length=200, verbose_name="商品名称")
    description = models.TextField(blank=True, null=True, verbose_name="商品描述")
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products',
        verbose_name="商品分类"
    )

    # 商品图片（多张）
    main_image = models.URLField(verbose_name="主图")
    images = models.JSONField(default=list, blank=True, verbose_name="商品图集")

    # 积分价格
    base_points_price = models.IntegerField(verbose_name="基础积分价格")
    original_points = models.IntegerField(default=0, verbose_name="原价积分")

    # 折扣信息
    discount_percent = models.IntegerField(default=0, verbose_name="折扣百分比")
    is_on_sale = models.BooleanField(default=False, verbose_name="是否打折")

    # 库存信息
    stock = models.IntegerField(default=0, verbose_name="库存数量")
    sales_count = models.IntegerField(default=0, verbose_name="销量")

    # 商品详情
    detail_html = models.TextField(blank=True, null=True, verbose_name="商品详情HTML")
    detail_images = models.JSONField(default=list, blank=True, verbose_name="详情图片")

    # 状态
    status = models.CharField(max_length=20, choices=PRODUCT_STATUS_CHOICES, default='active', verbose_name="商品状态")

    # 排序和推荐
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    is_recommended = models.BooleanField(default=False, verbose_name="是否推荐")
    is_hot = models.BooleanField(default=False, verbose_name="是否热销")
    is_new = models.BooleanField(default=False, verbose_name="是否新品")

    # 评价信息
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0, verbose_name="评分")
    review_count = models.IntegerField(default=0, verbose_name="评价数量")

    # 规格配置
    use_global_specs = models.BooleanField(default=False, verbose_name="使用全局规格")
    price_calculation_method = models.CharField(
        max_length=20,
        choices=(('additive', '累加计算'), ('fixed', '固定价格'), ('custom', '自定义规则'),),
        default='additive',
        verbose_name="价格计算方式"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "product"
        verbose_name = "商品"
        verbose_name_plural = "商品"
        ordering = ["-sort_order", "-created_at"]

    def __str__(self):
        return self.name

    @property
    def is_available(self):
        """商品是否可购买"""
        return self.status == 'active' and self.stock > 0

    @property
    def points_price(self):
        """兼容旧字段，返回基础价格"""
        return self.base_points_price

    @property
    def final_price(self):
        """最终价格（考虑折扣）"""
        if self.is_on_sale and self.discount_percent > 0:
            return int(self.base_points_price * (100 - self.discount_percent) / 100)
        return self.base_points_price

    def update_rating(self):
        """更新商品评分"""
        reviews = self.reviews.filter(is_active=True)
        if reviews.exists():
            self.rating = reviews.aggregate(avg_rating=models.Avg('rating'))['avg_rating']
            self.review_count = reviews.count()
            self.save()

    def get_available_skus(self):
        """获取可用SKU"""
        return self.skus.filter(is_active=True, stock__gt=0)


class ProductSpecGroup(models.Model):
    """
    商品规格组
    支持全局规格和私有规格
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='spec_groups',
        verbose_name="商品"
    )
    name = models.CharField(max_length=50, verbose_name="规格组名称")

    # 规格类型：全局规格或私有规格
    spec_type = models.CharField(
        max_length=20,
        choices=(
            ('global', '全局规格'),
            ('private', '私有规格'),
        ),
        default='private',
        verbose_name="规格类型"
    )

    # 关联全局规格模板（如果是全局规格）
    global_template = models.ForeignKey(
        GlobalSpecTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='product_spec_groups',
        verbose_name="全局规格模板"
    )

    # 规格组类型
    group_type = models.CharField(
        max_length=20,
        choices=(
            ('main', '主规格'),
            ('secondary', '次规格'),
            ('display', '展示规格'),
        ),
        default='main',
        verbose_name="规格组类型",
        help_text="主规格影响价格，次规格辅助选择，展示规格仅用于展示"
    )

    # 价格计算权重（主规格权重更高）
    price_weight = models.IntegerField(default=1, verbose_name="价格权重")

    sort_order = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        verbose_name = "商品规格组"
        verbose_name_plural = verbose_name
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    def save(self, *args, **kwargs):
        """保存时自动设置名称（如果是全局规格）"""
        if self.spec_type == 'global' and self.global_template:
            self.name = self.global_template.name
        super().save(*args, **kwargs)


class ProductSpecOption(models.Model):
    """
    商品规格选项
    支持全局规格选项和私有规格选项
    """
    spec_group = models.ForeignKey(
        ProductSpecGroup,
        on_delete=models.CASCADE,
        related_name='options',
        verbose_name="规格组"
    )

    # 规格值
    value = models.CharField(max_length=50, verbose_name="规格值")
    image = models.URLField(blank=True, null=True, verbose_name="规格图片")
    color_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="颜色代码")

    # 价格调整
    price_increment = models.IntegerField(default=0, verbose_name="价格增量")
    price_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.0,
        verbose_name="价格乘数",
        help_text="例如：1.1表示价格增加10%"
    )

    # 关联全局规格选项（如果是全局规格）
    global_option = models.ForeignKey(
        GlobalSpecOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='product_spec_options',
        verbose_name="全局规格选项"
    )

    # 可用性控制
    is_available = models.BooleanField(default=True, verbose_name="是否可用")
    stock_impact = models.BooleanField(default=True, verbose_name="影响库存")

    sort_order = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        verbose_name = "商品规格选项"
        verbose_name_plural = verbose_name
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.spec_group.name}: {self.value}"

    def save(self, *args, **kwargs):
        """保存时自动同步全局规格选项数据"""
        if self.spec_group.spec_type == 'global' and self.global_option:
            # 同步全局规格选项的数据
            self.value = self.global_option.value
            if not self.image and self.global_option.image:
                self.image = self.global_option.image
            if not self.color_code and self.global_option.color_code:
                self.color_code = self.global_option.color_code
            # 使用全局规格的基础价格增量
            if self.price_increment == 0:
                self.price_increment = self.global_option.base_price_increment
        super().save(*args, **kwargs)


class PriceRule(models.Model):
    """
    价格规则
    支持复杂的价格计算规则
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='price_rules',
        verbose_name="商品"
    )
    name = models.CharField(max_length=100, verbose_name="规则名称")
    description = models.TextField(blank=True, null=True, verbose_name="规则描述")

    # 规则条件
    condition_type = models.CharField(
        max_length=20,
        choices=(
            ('spec_combination', '规格组合'),
            ('quantity', '数量范围'),
            ('user_group', '用户分组'),
        ),
        default='spec_combination',
        verbose_name="条件类型"
    )

    # 规格条件（JSON格式存储规格组合）
    spec_conditions = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="规格条件",
        help_text="JSON格式：{'规格组ID': '规格选项ID'}"
    )

    # 价格调整方式
    adjustment_type = models.CharField(
        max_length=20,
        choices=(
            ('fixed', '固定价格'),
            ('increment', '价格增量'),
            ('multiplier', '价格乘数'),
            ('percentage', '百分比调整'),
        ),
        default='increment',
        verbose_name="调整方式"
    )

    adjustment_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="调整值"
    )

    # 优先级（数字越小优先级越高）
    priority = models.IntegerField(default=1, verbose_name="优先级")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "price_rule"
        verbose_name = "价格规则"
        verbose_name_plural = "价格规则"
        ordering = ['priority', '-created_at']

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    def save(self, *args, **kwargs):
        """保存时验证规格条件并更新相关SKU"""
        is_new = self.pk is None

        # 验证规格条件格式
        if self.condition_type == 'spec_combination' and self.spec_conditions:
            self._validate_spec_conditions()

        super().save(*args, **kwargs)

        # 如果是现有规则且已激活，更新相关SKU
        if not is_new and self.is_active:
            self.update_related_skus()

    def _validate_spec_conditions(self):
        """验证规格条件格式"""
        if not isinstance(self.spec_conditions, dict):
            raise ValueError("规格条件必须是JSON字典格式")

        # 验证规格组和选项存在 - 修复：使用下划线忽略未使用的变量
        for group_id, option_id in self.spec_conditions.items():
            try:
                spec_group = ProductSpecGroup.objects.get(id=group_id, product=self.product)
                _ = ProductSpecOption.objects.get(id=option_id, spec_group=spec_group)
            except (ProductSpecGroup.DoesNotExist, ProductSpecOption.DoesNotExist):
                raise ValueError(f"规格条件无效: 规格组 {group_id} 或选项 {option_id} 不存在")

    def get_affected_skus(self):
        """获取受此规则影响的SKU """
        if self.condition_type != 'spec_combination' or not self.spec_conditions:
            return ProductSku.objects.none()

        # 使用数据库查询来获取受影响的SKU
        from django.db.models import Q

        # 构建查询条件：SKU必须包含所有规则中指定的规格选项
        query = Q(product=self.product)

        for group_id, option_id in self.spec_conditions.items():
            # 使用多对多关系的查询
            query &= Q(spec_options__id=option_id)

        # 使用distinct()避免重复
        return ProductSku.objects.filter(query).distinct()

    def get_affected_skus_count(self):
        """获取受影响的SKU数量"""
        return self.get_affected_skus().count()

    def update_related_skus(self):
        """更新所有相关SKU的价格 """
        affected_skus = self.get_affected_skus()
        updated_count = 0

        for sku in affected_skus:
            # 重新计算价格并保存
            calculated_price, final_price = sku.calculate_price()
            sku.calculated_price = calculated_price
            sku.final_price = final_price
            sku.save(update_fields=['calculated_price', 'final_price', 'updated_at'])
            updated_count += 1

        return updated_count

    def _matches_sku_conditions(self, sku):
        """检查SKU是否匹配规则条件"""
        if self.condition_type == 'spec_combination':
            sku_option_ids = set(sku.spec_options.values_list('id', flat=True))
            rule_option_ids = set(self.spec_conditions.values())

            return rule_option_ids.issubset(sku_option_ids)

        return False

    def clean(self):
        """验证规则数据"""
        super().clean()

        if self.condition_type == 'spec_combination' and self.spec_conditions:
            # 验证规格条件格式
            if not isinstance(self.spec_conditions, dict):
                raise ValidationError("规格条件必须是JSON字典格式")  # 使用 Django 的 ValidationError

            # 验证规格组和选项存在且属于同一个商品
            for group_id, option_id in self.spec_conditions.items():
                try:
                    spec_group = ProductSpecGroup.objects.get(
                        id=group_id,
                        product=self.product
                    )
                    ProductSpecOption.objects.get(
                        id=option_id,
                        spec_group=spec_group
                    )
                except (ProductSpecGroup.DoesNotExist, ProductSpecOption.DoesNotExist):
                    raise ValidationError(f"规格条件无效: 规格组 {group_id} 或选项 {option_id} 不存在")


class ProductSku(models.Model):
    """
    商品SKU（规格组合）
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='skus',
        verbose_name="商品"
    )

    sku_code = models.CharField(max_length=100, blank=True, null=True, verbose_name="SKU编码")
    sku_name = models.CharField(max_length=200, verbose_name="SKU名称")

    # 规格组合
    spec_options = models.ManyToManyField(
        ProductSpecOption,
        related_name='skus',
        verbose_name="规格选项"
    )

    # 价格信息
    base_points_price = models.IntegerField(verbose_name="基础积分价格")
    calculated_price = models.IntegerField(verbose_name="计算后价格")
    final_price = models.IntegerField(verbose_name="最终价格")

    # 库存信息
    stock = models.IntegerField(default=0, verbose_name="库存")
    sales_count = models.IntegerField(default=0, verbose_name="销量")

    # 图片信息
    image = models.URLField(blank=True, null=True, verbose_name="SKU图片")

    # 状态
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")  # 新增更新时间字段

    class Meta:
        db_table = "product_sku"
        verbose_name = "商品规格"
        verbose_name_plural = "商品规格"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} - {self.sku_name}"

    def get_spec_display(self):
        """获取规格显示文本"""
        options = self.spec_options.all()
        return " ".join([f"{opt.spec_group.name}:{opt.value}" for opt in options])

    def calculate_price(self, spec_options=None):
        """计算SKU价格：考虑基础价格和所有规格选项的价格调整 """
        # 如果没有传入spec_options，使用当前的spec_options
        if spec_options is None:
            spec_options = self.spec_options.all()

        base_price = self.product.base_points_price

        # 累加所有规格选项的价格调整
        total_increment = 0
        total_multiplier = 1.0

        for option in spec_options:
            if option.is_available:
                total_increment += option.price_increment
                total_multiplier *= float(option.price_multiplier)

        # 计算价格：基础价格 × 乘数 + 增量
        calculated_price = int(base_price * total_multiplier) + total_increment

        # 应用价格规则 - 按优先级顺序
        applied_rules = PriceRule.objects.filter(
            product=self.product,
            is_active=True,
            condition_type='spec_combination'
        ).order_by('priority')

        final_price = calculated_price

        for rule in applied_rules:
            if self._matches_rule_condition(rule, spec_options):
                final_price = self._apply_price_rule(calculated_price, rule)
                break  # 只应用最高优先级的匹配规则

        return calculated_price, final_price

    def _matches_rule_condition(self, rule, spec_options=None):
        """检查SKU是否匹配价格规则条件 """
        if spec_options is None:
            spec_options = self.spec_options.all()

        if rule.condition_type == 'spec_combination':
            if not rule.spec_conditions:
                return False

            # 检查规格组合匹配 - 修复：确保所有条件都满足
            sku_option_ids = set(option.id for option in spec_options)

            # 规则中的选项ID需要全部存在于SKU的选项ID中
            rule_option_ids = set()
            for option_id in rule.spec_conditions.values():
                # 确保选项ID是整数
                try:
                    rule_option_ids.add(int(option_id))
                except (ValueError, TypeError):
                    continue

            return rule_option_ids.issubset(sku_option_ids)

        return False

    @staticmethod
    def _apply_price_rule(current_price, rule):
        """应用价格规则 """
        try:
            adjustment_value = float(rule.adjustment_value)
        except (ValueError, TypeError):
            return current_price

        if rule.adjustment_type == 'fixed':
            return int(adjustment_value)
        elif rule.adjustment_type == 'increment':
            return int(current_price + adjustment_value)
        elif rule.adjustment_type == 'multiplier':
            return int(current_price * adjustment_value)
        elif rule.adjustment_type == 'percentage':
            # 百分比调整：+10% 表示乘以1.1，-10% 表示乘以0.9
            return int(current_price * (1 + adjustment_value / 100))

        return current_price

    @classmethod
    def recalculate_all_skus_for_product(cls, product):
        """重新计算商品的所有SKU价格"""
        skus = cls.objects.filter(product=product)
        updated_count = 0

        for sku in skus:
            try:
                calculated_price, final_price = sku.calculate_price()
                if (sku.calculated_price != calculated_price or
                        sku.final_price != final_price):
                    sku.calculated_price = calculated_price
                    sku.final_price = final_price
                    sku.save(update_fields=['calculated_price', 'final_price', 'updated_at'])
                    updated_count += 1
            except Exception as e:
                print(f"重新计算SKU {sku.id} 价格失败: {e}")

        return updated_count

    def save(self, *args, **kwargs):
        """保存时避免访问多对多关系"""
        # 只有在有ID的情况下才计算价格（避免在创建时访问多对多关系）
        if self.pk and 'skip_price_calculation' not in kwargs:
            try:
                # 只有在spec_options已经设置的情况下才计算价格
                if self.spec_options.exists():
                    self.calculated_price, self.final_price = self.calculate_price()
            except (ValueError, AttributeError):
                # 如果访问多对多关系失败，跳过价格计算
                pass

        # 如果没有设置基础价格，使用商品的基础价格
        if not self.base_points_price and self.product:
            self.base_points_price = self.product.base_points_price

        # 移除skip_price_calculation参数
        if 'skip_price_calculation' in kwargs:
            kwargs.pop('skip_price_calculation')

        super().save(*args, **kwargs)

    def recalculate_price(self):
        """手动重新计算价格"""
        if self.spec_options.exists():
            self.calculated_price, self.final_price = self.calculate_price()
            self.save(update_fields=['calculated_price', 'final_price', 'updated_at'])

    @property
    def is_available(self):
        """SKU是否可用"""
        return self.is_active and self.stock > 0

    @classmethod
    def create_with_specs(cls, product, sku_code, sku_name, spec_options, **kwargs):
        """
        创建SKU并设置规格选项的辅助方法
        避免在保存前访问多对多关系
        """
        # 计算基础价格
        base_price = kwargs.get('base_points_price', product.base_points_price)

        # 计算价格
        calculated_price, final_price = cls._calculate_price_for_options(
            product, spec_options, base_price
        )

        # 创建SKU对象
        sku = cls(
            product=product,
            sku_code=sku_code,
            sku_name=sku_name,
            base_points_price=base_price,
            calculated_price=calculated_price,
            final_price=final_price,
            **{k: v for k, v in kwargs.items() if k != 'base_points_price'}
        )

        # 先保存获取ID（跳过价格计算）
        sku.save(skip_price_calculation=True)

        # 设置多对多关系 - 修复：添加类型提示或忽略警告
        sku.spec_options.set(spec_options)  # type: ignore

        return sku

    @classmethod
    def _calculate_price_for_options(cls, product, spec_options, base_price):
        """为给定的规格选项计算价格"""
        # 累加所有规格选项的价格调整
        total_increment = 0
        total_multiplier = 1.0

        for option in spec_options:
            if option.is_available:
                total_increment += option.price_increment
                total_multiplier *= float(option.price_multiplier)

        # 计算价格：基础价格 × 乘数 + 增量
        calculated_price = int(base_price * total_multiplier) + total_increment

        # 应用价格规则
        applied_rules = PriceRule.objects.filter(
            product=product,
            is_active=True
        ).order_by('priority')

        final_price = calculated_price

        for rule in applied_rules:
            if cls._matches_rule_condition_for_options(rule, spec_options):
                final_price = cls._apply_price_rule(final_price, rule)

        return calculated_price, final_price

    @staticmethod
    def _matches_rule_condition_for_options(rule, spec_options):
        """检查规格选项是否匹配价格规则条件"""
        if rule.condition_type == 'spec_combination':
            if not rule.spec_conditions:
                return False

            # 检查规格组合匹配
            option_ids = set(option.id for option in spec_options)
            rule_option_ids = set(rule.spec_conditions.values())

            return rule_option_ids.issubset(option_ids)

        return False


class ProductReview(models.Model):
    """
    商品评价
    """
    RATING_CHOICES = (
        (1, '1星'),
        (2, '2星'),
        (3, '3星'),
        (4, '4星'),
        (5, '5星'),
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="商品"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='product_reviews',
        verbose_name="用户"
    )
    rating = models.IntegerField(choices=RATING_CHOICES, verbose_name="评分")
    title = models.CharField(max_length=100, blank=True, null=True, verbose_name="评价标题")
    content = models.TextField(verbose_name="评价内容")
    images = models.JSONField(default=list, blank=True, verbose_name="评价图片")
    is_anonymous = models.BooleanField(default=False, verbose_name="匿名评价")
    is_active = models.BooleanField(default=True, verbose_name="是否显示")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="评价时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "product_review"
        verbose_name = "商品评价"
        verbose_name_plural = "商品评价"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.rating}星"


class Banner(models.Model):
    """
    商品页面轮播图
    """
    BANNER_TYPE_CHOICES = (
        ('product', '商品'),
        ('activity', '活动'),
        ('url', '外部链接'),
    )

    title = models.CharField(max_length=100, verbose_name="轮播图标题")
    image = models.URLField(verbose_name="轮播图图片")
    desc = models.CharField(max_length=100, blank=True, null=True, verbose_name="描述")
    type = models.CharField(max_length=20, choices=BANNER_TYPE_CHOICES, default='product', verbose_name="链接类型")
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='banners',
        verbose_name="关联商品"
    )
    activity_url = models.URLField(blank=True, null=True, verbose_name="活动链接")
    external_url = models.URLField(blank=True, null=True, verbose_name="外部链接")
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    start_time = models.DateTimeField(blank=True, null=True, verbose_name="开始时间")
    end_time = models.DateTimeField(blank=True, null=True, verbose_name="结束时间")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "mall_banner"
        verbose_name = "轮播图"
        verbose_name_plural = "轮播图"
        ordering = ["sort_order", "-created_at"]

    def __str__(self):
        return self.title

    @property
    def target_url(self):
        """获取目标链接"""
        if self.type == 'product' and self.product:
            return f"/pages/mall/goodsdetail/goodsdetail?id={self.product.id}"
        elif self.type == 'activity' and self.activity_url:
            return self.activity_url
        elif self.type == 'url' and self.external_url:
            return self.external_url
        return "#"

    @property
    def is_valid(self):
        """检查轮播图是否在有效期内"""
        from django.utils import timezone
        now = timezone.now()
        if self.start_time and now < self.start_time:
            return False
        if self.end_time and now > self.end_time:
            return False
        return self.is_active


class CartItem(models.Model):
    """
    购物车项模型
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items', verbose_name="用户")

    # 商品SKU或商品（如果商品没有规格，直接使用商品）
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items', verbose_name="商品",
                                null=True, blank=True)

    product_sku = models.ForeignKey(ProductSku, on_delete=models.CASCADE, related_name='cart_items',
                                    verbose_name="商品SKU", null=True, blank=True)

    # 规格选择信息（JSON格式，用于记录选中的规格）
    selected_specs = models.JSONField(default=dict, blank=True, verbose_name="选中的规格",
                                      help_text="JSON格式：{'规格组ID': '规格选项ID'}")

    quantity = models.PositiveIntegerField(default=1, verbose_name="数量")
    is_active = models.BooleanField(default=True, verbose_name="是否有效")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="加入时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "cart_item"
        verbose_name = "购物车项"
        verbose_name_plural = "购物车项"
        unique_together = ['user', 'product_sku']
        ordering = ["-created_at"]

    def __str__(self):
        if self.product_sku:
            return f"{self.user.username} - {self.product_sku.sku_name} x {self.quantity}"
        else:
            return f"{self.user.username} - {self.product.name} x {self.quantity}"

    @property
    def actual_product(self):
        """获取实际商品"""
        if self.product_sku:
            return self.product_sku.product
        return self.product

    @property
    def final_price(self):
        """获取最终价格"""
        if self.product_sku:
            return self.product_sku.final_price
        return self.product.final_price

    @property
    def spec_display(self):
        """获取规格显示文本"""
        if self.product_sku:
            return self.product_sku.get_spec_display()

        # 如果选择了规格但未生成SKU，从selected_specs生成显示文本
        if self.selected_specs:
            spec_texts = []
            for group_id, option_id in self.selected_specs.items():
                try:
                    spec_group = ProductSpecGroup.objects.get(id=group_id)
                    option = ProductSpecOption.objects.get(id=option_id)
                    spec_texts.append(f"{spec_group.name}:{option.value}")
                except (ProductSpecGroup.DoesNotExist, ProductSpecOption.DoesNotExist):
                    continue
            return " ".join(spec_texts)

        return "默认规格"

    @property
    def image(self):
        """获取图片"""
        if self.product_sku and self.product_sku.image:
            return self.product_sku.image
        return self.actual_product.main_image

    @property
    def is_available(self):
        """检查是否可用"""
        if self.product_sku:
            return self.product_sku.is_available and self.product_sku.stock >= self.quantity
        return self.actual_product.is_available and self.actual_product.stock >= self.quantity

    @property
    def stock(self):
        """获取库存"""
        if self.product_sku:
            return self.product_sku.stock
        return self.actual_product.stock

    def clean(self):
        """验证数据"""
        from django.core.exceptions import ValidationError

        # 确保要么有product，要么有product_sku
        if not self.product and not self.product_sku:
            raise ValidationError("必须指定商品或商品SKU")

        # 如果同时指定了product和product_sku，确保product_sku属于product
        if self.product and self.product_sku and self.product_sku.product != self.product:
            raise ValidationError("商品SKU不属于指定的商品")

        # 验证数量
        if self.quantity <= 0:
            raise ValidationError("数量必须大于0")

        # 验证库存
        if self.stock < self.quantity:
            raise ValidationError(f"库存不足，当前库存: {self.stock}")

    def save(self, *args, **kwargs):
        """保存前验证库存和规格"""
        from django.core.exceptions import ValidationError

        # 如果只有product没有product_sku，确保selected_specs为空或匹配
        if self.product and not self.product_sku and self.selected_specs:
            # 尝试查找匹配的SKU
            try:
                # 查找匹配的SKU
                sku = self.find_matching_sku()
                if sku:
                    self.product_sku = sku
            except ProductSku.DoesNotExist:
                pass

        # 验证数量
        if self.quantity <= 0:
            raise ValidationError("商品数量必须大于0")

        # 验证库存
        available_stock = self.stock
        if self.quantity > available_stock:
            raise ValidationError(f"库存不足，最多可购买 {available_stock} 件")

        # 确保用户不能操作其他用户的购物车
        if self.pk:
            original = CartItem.objects.get(pk=self.pk)
            if original.user != self.user:
                raise ValidationError("不能修改其他用户的购物车")

        super().save(*args, **kwargs)

    def find_matching_sku(self):
        """根据selected_specs查找匹配的SKU"""
        if not self.selected_specs or not self.product:
            return None

        # 获取所有相关SKU
        skus = self.product.skus.filter(is_active=True)

        for sku in skus:
            sku_option_ids = set(sku.spec_options.values_list('id', flat=True))
            selected_option_ids = set(self.selected_specs.values())

            if sku_option_ids == selected_option_ids:
                return sku

        return None

    @property
    def total_price(self):
        """计算该购物车项总价"""
        return self.final_price * self.quantity

    def to_dict(self):
        """转换为字典格式"""
        product = self.actual_product
        return {
            'id': self.id,
            'user_id': self.user_id,
            'product_id': product.id if product else None,
            'product_sku_id': self.product_sku.id if self.product_sku else None,
            'product_name': product.name if product else '未知商品',
            'spec_display': self.spec_display,
            'product_image': self.image,
            'price': self.final_price,
            'quantity': self.quantity,
            'stock': self.stock,
            'is_available': self.is_available,
            'selected_specs': self.selected_specs,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
