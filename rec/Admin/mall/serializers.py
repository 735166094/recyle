from rest_framework import serializers
from .models import (
    GlobalSpecTemplate, GlobalSpecOption, ProductCategory,
    Product, ProductSpecGroup, ProductSpecOption, PriceRule,
    ProductSku, ProductReview, Banner, CartItem
)


class GlobalSpecOptionSerializer(serializers.ModelSerializer):
    """全局规格选项序列化器"""

    class Meta:
        model = GlobalSpecOption
        fields = ['id', 'value', 'image', 'color_code', 'base_price_increment', 'sort_order']
        read_only_fields = ['id']


class GlobalSpecTemplateSerializer(serializers.ModelSerializer):
    """全局规格模板序列化器"""
    global_options = GlobalSpecOptionSerializer(many=True, read_only=True)

    class Meta:
        model = GlobalSpecTemplate
        fields = [
            'id', 'name', 'description', 'icon', 'data_type',
            'is_active', 'sort_order', 'global_options', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductCategorySerializer(serializers.ModelSerializer):
    """商品分类序列化器"""
    product_count = serializers.IntegerField(source='products.count', read_only=True)

    class Meta:
        model = ProductCategory
        fields = [
            'id', 'name', 'description', 'image', 'icon', 'sort_order',
            'is_active', 'product_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductSpecOptionSerializer(serializers.ModelSerializer):
    """商品规格选项序列化器"""
    spec_group_name = serializers.CharField(source='spec_group.name', read_only=True)
    spec_group_type = serializers.CharField(source='spec_group.group_type', read_only=True)

    class Meta:
        model = ProductSpecOption
        fields = [
            'id', 'spec_group', 'spec_group_name', 'spec_group_type',
            'value', 'image', 'color_code', 'price_increment', 'price_multiplier',
            'global_option', 'is_available', 'stock_impact', 'sort_order'
        ]
        read_only_fields = ['id']


class ProductSpecGroupSerializer(serializers.ModelSerializer):
    """商品规格组序列化器"""
    options = ProductSpecOptionSerializer(many=True, read_only=True)
    option_count = serializers.IntegerField(source='options.count', read_only=True)

    class Meta:
        model = ProductSpecGroup
        fields = [
            'id', 'product', 'name', 'spec_type', 'global_template',
            'group_type', 'price_weight', 'sort_order', 'options', 'option_count'
        ]
        read_only_fields = ['id']


class PriceRuleSerializer(serializers.ModelSerializer):
    """价格规则序列化器"""
    condition_type_display = serializers.CharField(source='get_condition_type_display', read_only=True)
    adjustment_type_display = serializers.CharField(source='get_adjustment_type_display', read_only=True)

    class Meta:
        model = PriceRule
        fields = [
            'id', 'product', 'name', 'description', 'condition_type', 'condition_type_display',
            'spec_conditions', 'adjustment_type', 'adjustment_type_display', 'adjustment_value',
            'priority', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductSkuSerializer(serializers.ModelSerializer):
    """商品SKU序列化器"""
    spec_display = serializers.SerializerMethodField()
    spec_options = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductSku
        fields = [
            'id', 'product', 'sku_code', 'sku_name', 'spec_options', 'spec_display',
            'base_points_price', 'calculated_price', 'final_price', 'stock', 'sales_count',
            'image', 'is_active', 'is_available', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'calculated_price', 'final_price']

    @staticmethod
    def get_spec_display(obj):
        return obj.get_spec_display()


class ProductReviewSerializer(serializers.ModelSerializer):
    """商品评价序列化器"""
    user_nickname = serializers.CharField(source='user.nickname', read_only=True)
    user_avatar = serializers.CharField(source='user.avatar_url', read_only=True)

    class Meta:
        model = ProductReview
        fields = [
            'id', 'user', 'user_nickname', 'user_avatar', 'rating', 'title',
            'content', 'images', 'is_anonymous', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductListSerializer(serializers.ModelSerializer):
    """商品列表序列化器"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    final_price = serializers.IntegerField(read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)
    has_specs = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'main_image', 'base_points_price', 'original_points',
            'final_price', 'discount_percent', 'is_on_sale', 'stock', 'sales_count',
            'category_name', 'is_recommended', 'is_hot', 'is_new', 'rating',
            'review_count', 'use_global_specs', 'has_specs', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    @staticmethod
    def get_has_specs(obj):
        """检查商品是否有规格"""
        return obj.spec_groups.exists()


class ProductDetailSerializer(serializers.ModelSerializer):
    """商品详情序列化器"""
    spec_groups = ProductSpecGroupSerializer(many=True, read_only=True)
    skus = ProductSkuSerializer(many=True, read_only=True)
    price_rules = PriceRuleSerializer(many=True, read_only=True)
    reviews = ProductReviewSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    final_price = serializers.IntegerField(read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)

    # 规格相关统计
    spec_group_count = serializers.IntegerField(source='spec_groups.count', read_only=True)
    sku_count = serializers.IntegerField(source='skus.count', read_only=True)
    available_sku_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'category', 'category_name',
            'main_image', 'images', 'detail_html', 'detail_images',
            'base_points_price', 'original_points', 'final_price', 'discount_percent',
            'is_on_sale', 'stock', 'sales_count', 'rating', 'review_count',
            'is_recommended', 'is_hot', 'is_new', 'status', 'is_available',
            'use_global_specs', 'price_calculation_method',
            'spec_groups', 'spec_group_count', 'skus', 'sku_count', 'available_sku_count',
            'price_rules', 'reviews',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    @staticmethod
    def get_available_sku_count(obj):
        """获取可用SKU数量"""
        return obj.skus.filter(is_active=True, stock__gt=0).count()


class ProductCreateSerializer(serializers.ModelSerializer):
    """商品创建序列化器"""

    class Meta:
        model = Product
        fields = [
            'name', 'description', 'category', 'main_image', 'images',
            'base_points_price', 'original_points', 'discount_percent', 'is_on_sale',
            'stock', 'detail_html', 'detail_images', 'status', 'sort_order',
            'is_recommended', 'is_hot', 'is_new', 'use_global_specs', 'price_calculation_method'
        ]


class ProductSpecOptionCreateSerializer(serializers.ModelSerializer):
    """商品规格选项创建序列化器"""

    class Meta:
        model = ProductSpecOption
        fields = [
            'spec_group', 'value', 'image', 'color_code', 'price_increment',
            'price_multiplier', 'global_option', 'is_available', 'stock_impact', 'sort_order'
        ]


class ProductSpecGroupCreateSerializer(serializers.ModelSerializer):
    """商品规格组创建序列化器"""
    options = ProductSpecOptionCreateSerializer(many=True, required=False)

    class Meta:
        model = ProductSpecGroup
        fields = [
            'product', 'name', 'spec_type', 'global_template',
            'group_type', 'price_weight', 'sort_order', 'options'
        ]

    def create(self, validated_data):
        options_data = validated_data.pop('options', [])
        spec_group = ProductSpecGroup.objects.create(**validated_data)

        for option_data in options_data:
            ProductSpecOption.objects.create(spec_group=spec_group, **option_data)

        return spec_group


class ProductSkuCreateSerializer(serializers.ModelSerializer):
    """商品SKU创建序列化器"""

    class Meta:
        model = ProductSku
        fields = [
            'product', 'sku_code', 'sku_name', 'spec_options',
            'base_points_price', 'stock', 'image', 'is_active'
        ]

    def create(self, validated_data):
        spec_options = validated_data.pop('spec_options', [])
        sku = ProductSku.objects.create(**validated_data)
        sku.spec_options.set(spec_options)

        # 自动计算价格
        sku.calculated_price, sku.final_price = sku.calculate_price()
        sku.save()

        return sku


class PriceRuleCreateSerializer(serializers.ModelSerializer):
    """价格规则创建序列化器"""

    class Meta:
        model = PriceRule
        fields = [
            'product', 'name', 'description', 'condition_type', 'spec_conditions',
            'adjustment_type', 'adjustment_value', 'priority', 'is_active'
        ]


class BannerSerializer(serializers.ModelSerializer):
    """轮播图序列化器"""
    target_url = serializers.CharField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Banner
        fields = [
            'id', 'title', 'desc', 'image', 'type', 'product', 'product_name',
            'activity_url', 'external_url', 'target_url', 'sort_order', 'is_active',
            'is_valid', 'start_time', 'end_time', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# 专门用于前端规格选择和价格计算的序列化器
class ProductSpecSelectionSerializer(serializers.Serializer):
    """商品规格选择序列化器（用于前端交互）"""
    product_id = serializers.IntegerField()
    selected_specs = serializers.DictField(
        child=serializers.IntegerField(),
        help_text="规格组ID到规格选项ID的映射"
    )

    def validate(self, data):
        product_id = data.get('product_id')
        selected_specs = data.get('selected_specs', {})

        # 验证商品存在
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise serializers.ValidationError("商品不存在")

        # 验证规格组和选项
        for group_id, option_id in selected_specs.items():
            try:
                spec_group = product.spec_groups.get(id=group_id)
                spec_option = spec_group.options.get(id=option_id)

                # 验证选项是否可用
                if not spec_option.is_available:
                    raise serializers.ValidationError(f"规格选项不可用: {spec_option.value}")

            except ProductSpecGroup.DoesNotExist:
                raise serializers.ValidationError(f"规格组不存在: {group_id}")
            except ProductSpecOption.DoesNotExist:
                raise serializers.ValidationError(f"规格选项不存在: {option_id}")

        return data


class CalculatedPriceSerializer(serializers.Serializer):
    """计算价格结果序列化器"""
    product_id = serializers.IntegerField()
    base_price = serializers.IntegerField()
    calculated_price = serializers.IntegerField()
    final_price = serializers.IntegerField()
    selected_specs = serializers.DictField()
    spec_display = serializers.CharField()
    matched_sku = serializers.IntegerField(required=False, allow_null=True)
    is_available = serializers.BooleanField()
    stock = serializers.IntegerField()


class ProductSpecAvailabilitySerializer(serializers.Serializer):
    """规格可用性序列化器"""
    spec_group_id = serializers.IntegerField()
    spec_option_id = serializers.IntegerField()
    is_available = serializers.BooleanField()
    reason = serializers.CharField(required=False, allow_null=True)


class CartItemCreateSerializer(serializers.ModelSerializer):
    """购物车项创建序列化器"""
    product_id = serializers.IntegerField(write_only=True, required=True)
    selected_specs = serializers.DictField(
        child=serializers.IntegerField(),
        required=False,
        default={},
        help_text="选中的规格，格式：{'规格组ID': '规格选项ID'}"
    )

    class Meta:
        model = CartItem
        fields = ['product_id', 'selected_specs', 'quantity']
        read_only_fields = ['user']

    def validate(self, data):
        """验证数据"""
        product_id = data.get('product_id')
        selected_specs = data.get('selected_specs', {})
        quantity = data.get('quantity', 1)

        try:
            product = Product.objects.get(id=product_id, status='active')
        except Product.DoesNotExist:
            raise serializers.ValidationError("商品不存在或已下架")

        # 验证规格选择
        product_sku = None
        if selected_specs:
            # 验证规格组和选项
            for group_id, option_id in selected_specs.items():
                try:
                    spec_group = product.spec_groups.get(id=group_id)
                    spec_option = spec_group.options.get(id=option_id, is_available=True)
                except (ProductSpecGroup.DoesNotExist, ProductSpecOption.DoesNotExist):
                    raise serializers.ValidationError(f"规格选择无效: 组{group_id} 选项{option_id}")

            # 尝试匹配SKU
            spec_groups_count = product.spec_groups.count()
            if len(selected_specs) == spec_groups_count:
                for sku in product.skus.filter(is_active=True):
                    sku_option_ids = set(sku.spec_options.values_list('id', flat=True))
                    selected_option_ids = set(selected_specs.values())
                    if selected_option_ids == sku_option_ids:
                        product_sku = sku
                        break

        # 验证库存
        available_stock = product_sku.stock if product_sku else product.stock
        if available_stock < quantity:
            raise serializers.ValidationError(f"库存不足，当前库存: {available_stock}")

        # 添加到验证后的数据
        data['product'] = product
        data['product_sku'] = product_sku
        return data

    def create(self, validated_data):
        """创建购物车项"""
        user = self.context['request'].user
        product = validated_data['product']
        product_sku = validated_data.get('product_sku')
        selected_specs = validated_data.get('selected_specs', {})
        quantity = validated_data.get('quantity', 1)

        # 检查是否已存在相同的购物车项
        cart_item = None
        if product_sku:
            cart_item = CartItem.objects.filter(
                user=user,
                product_sku=product_sku,
                is_active=True
            ).first()
        else:
            cart_item = CartItem.objects.filter(
                user=user,
                product=product,
                product_sku__isnull=True,
                selected_specs=selected_specs,
                is_active=True
            ).first()

        if cart_item:
            # 更新数量
            new_quantity = cart_item.quantity + quantity
            max_stock = product_sku.stock if product_sku else product.stock

            if new_quantity > max_stock:
                raise serializers.ValidationError(f"超过最大库存，最大可购买: {max_stock}")

            cart_item.quantity = new_quantity
            cart_item.save()
            return cart_item
        else:
            # 创建新的购物车项
            return CartItem.objects.create(
                user=user,
                product=product,
                product_sku=product_sku,
                selected_specs=selected_specs,
                quantity=quantity
            )


class CartItemSerializer(serializers.ModelSerializer):
    """购物车项详情序列化器"""
    product_id = serializers.IntegerField(source='actual_product.id', read_only=True)
    product_name = serializers.CharField(source='actual_product.name', read_only=True)
    product_image = serializers.SerializerMethodField()
    spec_display = serializers.SerializerMethodField()
    price = serializers.IntegerField(source='final_price', read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    stock = serializers.IntegerField(read_only=True)

    class Meta:
        model = CartItem
        fields = [
            'id', 'product_id', 'product_name', 'product_image', 'spec_display',
            'price', 'quantity', 'stock', 'is_available', 'selected_specs',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    @staticmethod
    def get_product_image(obj):
        """获取商品图片"""
        return obj.image  # 使用模型的image属性

    @staticmethod
    def get_spec_display(obj):
        """获取规格显示文本"""
        return obj.spec_display  # 使用模型的spec_display属性


class CartItemUpdateSerializer(serializers.ModelSerializer):
    selected_specs = serializers.DictField(
        child=serializers.IntegerField(),
        required=False,
        help_text="选中的规格，格式：{'规格组ID': '规格选项ID'}"
    )

    class Meta:
        model = CartItem
        fields = ['quantity', 'selected_specs']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("数量必须大于0")
        return value

    def validate_selected_specs(self, value):
        # 可以在这里添加额外的验证，例如检查规格是否存在等
        return value

    def update(self, instance, validated_data):
        quantity = validated_data.get('quantity', instance.quantity)
        selected_specs = validated_data.get('selected_specs')

        # 如果有规格变更，需要重新匹配 SKU
        if selected_specs is not None and selected_specs != instance.selected_specs:
            # 根据新的规格查找匹配的 SKU
            product = instance.product
            if not product:
                raise serializers.ValidationError("商品不存在")

            # 查找匹配的 SKU
            matched_sku = None
            # 获取所有规格组
            spec_groups = product.spec_groups.all()
            if len(selected_specs) == spec_groups.count():
                for sku in product.skus.filter(is_active=True):
                    sku_option_ids = set(sku.spec_options.values_list('id', flat=True))
                    selected_option_ids = set(selected_specs.values())
                    if selected_option_ids == sku_option_ids:
                        matched_sku = sku
                        break

            if not matched_sku:
                raise serializers.ValidationError("未找到匹配的 SKU")

            # 更新 SKU 和规格信息
            instance.product_sku = matched_sku
            instance.selected_specs = selected_specs

        # 更新数量（如果有）
        if quantity != instance.quantity:
            # 验证库存
            max_stock = instance.stock
            if quantity > max_stock:
                raise serializers.ValidationError(f"库存不足，最大可购买: {max_stock}")
            instance.quantity = quantity

        instance.save()
        return instance


class CartCheckoutSerializer(serializers.Serializer):
    """购物车结算序列化器"""
    cart_item_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        help_text="要结算的购物车项ID列表"
    )
    address_id = serializers.IntegerField(required=True, help_text="收货地址ID")
    coupon_id = serializers.IntegerField(required=False, allow_null=True, help_text="优惠券ID")
    remark = serializers.CharField(required=False, allow_blank=True, help_text="备注")
