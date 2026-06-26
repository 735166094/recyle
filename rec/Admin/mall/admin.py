from django.contrib import admin
from django.utils.html import format_html
from .models import (
    GlobalSpecTemplate, GlobalSpecOption, ProductCategory,
    Product, ProductSpecGroup, ProductSpecOption, PriceRule,
    ProductSku, ProductReview, Banner, CartItem
)


class GlobalSpecOptionInline(admin.TabularInline):
    """全局规格选项内联编辑"""
    model = GlobalSpecOption
    extra = 1
    fields = ('value', 'image', 'color_code', 'base_price_increment', 'sort_order')
    ordering = ('sort_order',)


@admin.register(GlobalSpecTemplate)
class GlobalSpecTemplateAdmin(admin.ModelAdmin):
    """全局规格模板管理界面"""
    list_display = ('name', 'data_type', 'is_active', 'option_count', 'sort_order', 'created_at')
    list_filter = ('data_type', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    list_editable = ('sort_order', 'is_active')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [GlobalSpecOptionInline]

    fieldsets = (
        ('基本信息', {'fields': ('name', 'description', 'data_type')}),
        ('显示配置', {'fields': ('icon', 'sort_order', 'is_active')}),
        ('时间信息', {'fields': ('created_at', 'updated_at')}),
    )

    def option_count(self, obj):
        return obj.global_options.count()

    option_count.short_description = '选项数量'


@admin.register(GlobalSpecOption)
class GlobalSpecOptionAdmin(admin.ModelAdmin):
    """全局规格选项管理界面"""
    list_display = ('spec_template', 'value', 'color_code', 'base_price_increment', 'sort_order')
    list_filter = ('spec_template',)
    search_fields = ('spec_template__name', 'value')
    list_editable = ('base_price_increment', 'sort_order')
    ordering = ('spec_template', 'sort_order')

    fieldsets = (
        ('基本信息', {'fields': ('spec_template', 'value')}),
        ('显示信息', {'fields': ('image', 'color_code')}),
        ('价格配置', {'fields': ('base_price_increment',)}),
        ('排序配置', {'fields': ('sort_order',)}),
    )


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    """商品类别管理界面"""
    list_display = ('name', 'icon', 'sort_order', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    list_editable = ('sort_order', 'is_active')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('基本信息', {'fields': ('name', 'description', 'image')}),
        ('图标配置', {
            'fields': ('icon',),
            'description': '设置小程序图标字体类名，常用图标：<br>'
                           'icon-car (汽车), icon-defaults (默认)'
        }),
        ('配置信息', {'fields': ('sort_order', 'is_active')}),
    )


class ProductSpecOptionInline(admin.TabularInline):
    """商品规格选项内联编辑"""
    model = ProductSpecOption
    extra = 1
    fields = ('value', 'image', 'color_code', 'price_increment', 'price_multiplier',
              'is_available', 'sort_order')
    ordering = ('sort_order',)


@admin.register(ProductSpecGroup)
class ProductSpecGroupAdmin(admin.ModelAdmin):
    """商品规格组管理界面"""
    list_display = ('product', 'name', 'spec_type', 'group_type', 'price_weight', 'sort_order')
    list_filter = ('spec_type', 'group_type', 'product')
    search_fields = ('product__name', 'name')
    list_editable = ('sort_order', 'price_weight')
    inlines = [ProductSpecOptionInline]

    fieldsets = (
        ('基本信息', {'fields': ('product', 'spec_type', 'global_template')}),
        ('规格配置', {'fields': ('name', 'group_type', 'price_weight')}),
        ('排序配置', {'fields': ('sort_order',)}),
    )

    def get_form(self, request, obj=None, **kwargs):
        """动态过滤全局规格模板"""
        form = super().get_form(request, obj, **kwargs)
        if 'global_template' in form.base_fields:
            form.base_fields['global_template'].queryset = GlobalSpecTemplate.objects.filter(is_active=True)
        return form


class PriceRuleInline(admin.TabularInline):
    """价格规则内联编辑"""
    model = PriceRule
    extra = 1
    fields = ('name', 'condition_type', 'adjustment_type', 'adjustment_value', 'priority', 'is_active')
    ordering = ('priority',)


class ProductSpecGroupInline(admin.TabularInline):
    """商品规格组内联编辑"""
    model = ProductSpecGroup
    extra = 1
    fields = ('name', 'spec_type', 'global_template', 'group_type', 'price_weight', 'sort_order')
    ordering = ('sort_order',)


class ProductSkuInline(admin.TabularInline):
    """商品SKU内联编辑"""
    model = ProductSku
    extra = 1
    fields = ('sku_code', 'sku_name', 'spec_options', 'base_points_price', 'calculated_price',
              'final_price', 'stock', 'image', 'is_active')
    filter_horizontal = ('spec_options',)
    readonly_fields = ('calculated_price', 'final_price')


class ProductReviewInline(admin.TabularInline):
    """商品评价内联编辑"""
    model = ProductReview
    extra = 0
    fields = ('user', 'rating', 'title', 'is_active')
    readonly_fields = ('created_at',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """商品管理界面"""
    list_display = ('name', 'category', 'base_points_price', 'final_price', 'stock',
                    'status', 'is_recommended', 'is_hot', 'is_new', 'use_global_specs', 'created_at')
    list_filter = ('category', 'status', 'is_recommended', 'is_hot', 'is_new',
                   'use_global_specs', 'price_calculation_method', 'created_at')
    search_fields = ('name', 'description')
    list_editable = ('status', 'is_recommended', 'is_hot', 'is_new', 'use_global_specs')
    readonly_fields = ('created_at', 'updated_at', 'sales_count', 'rating', 'review_count')
    inlines = [ProductSpecGroupInline, PriceRuleInline, ProductSkuInline, ProductReviewInline]

    fieldsets = (
        ('基本信息', {'fields': ('name', 'description', 'category')}),
        ('图片信息', {'fields': ('main_image', 'images', 'detail_images')}),
        ('价格信息', {'fields': ('base_points_price', 'original_points', 'discount_percent', 'is_on_sale')}),
        ('规格配置', {
            'fields': ('use_global_specs', 'price_calculation_method'),
            'description': '使用全局规格可以复用公共规格模板，提高管理效率'
        }),
        ('库存销量', {'fields': ('stock', 'sales_count')}),
        ('商品详情', {'fields': ('detail_html',)}),
        ('评价信息', {'fields': ('rating', 'review_count')}),
        ('状态配置', {'fields': ('status', 'sort_order', 'is_recommended', 'is_hot', 'is_new')}),
        ('时间信息', {'fields': ('created_at', 'updated_at')}),
    )

    def final_price(self, obj):
        return obj.final_price

    final_price.short_description = '最终价格'

    def save_related(self, request, form, formsets, change):
        """保存关联对象后，自动处理全局规格"""
        super().save_related(request, form, formsets, change)

        # 如果商品启用了全局规格，自动创建对应的规格组和选项
        if form.instance.use_global_specs:
            self._sync_global_specs(form.instance)


@admin.register(PriceRule)
class PriceRuleAdmin(admin.ModelAdmin):
    """价格规则管理界面"""
    list_display = ('product', 'name', 'condition_type', 'adjustment_type',
                    'adjustment_value', 'priority', 'is_active', 'created_at')
    list_filter = ('condition_type', 'adjustment_type', 'is_active', 'created_at')
    search_fields = ('product__name', 'name', 'description')
    list_editable = ('priority', 'is_active')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('基本信息', {'fields': ('product', 'name', 'description')}),
        ('规则条件', {'fields': ('condition_type', 'spec_conditions')}),
        ('价格调整', {'fields': ('adjustment_type', 'adjustment_value')}),
        ('优先级配置', {'fields': ('priority', 'is_active')}),
        ('时间信息', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(ProductSku)
class ProductSkuAdmin(admin.ModelAdmin):
    """商品SKU管理界面"""
    list_display = ('product', 'sku_name', 'get_spec_display', 'base_points_price',
                    'calculated_price', 'final_price', 'stock', 'is_active')
    list_filter = ('product', 'is_active')
    search_fields = ('product__name', 'sku_name', 'sku_code')
    list_editable = ('stock', 'is_active')
    filter_horizontal = ('spec_options',)
    readonly_fields = ('created_at', 'calculated_price', 'final_price')

    fieldsets = (
        ('基本信息', {'fields': ('product', 'sku_code', 'sku_name')}),
        ('规格配置', {'fields': ('spec_options',)}),
        ('价格信息', {'fields': ('base_points_price', 'calculated_price', 'final_price')}),
        ('库存信息', {'fields': ('stock', 'sales_count')}),
        ('图片信息', {'fields': ('image',)}),
        ('状态配置', {'fields': ('is_active',)}),
        ('时间信息', {'fields': ('created_at',)}),
    )

    def get_spec_display(self, obj):
        return obj.get_spec_display()

    get_spec_display.short_description = '规格组合'

    def save_model(self, request, obj, form, change):
        """保存时自动计算价格"""
        if not obj.calculated_price or not obj.final_price:
            obj.calculated_price, obj.final_price = obj.calculate_price()
        super().save_model(request, obj, form, change)


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    """商品评价管理界面"""
    list_display = ('product', 'user', 'rating', 'title', 'is_active', 'created_at')
    list_filter = ('rating', 'is_active', 'is_anonymous', 'created_at')
    search_fields = ('product__name', 'user__username', 'title', 'content')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('基本信息', {'fields': ('product', 'user')}),
        ('评价内容', {'fields': ('rating', 'title', 'content', 'images')}),
        ('显示设置', {'fields': ('is_anonymous', 'is_active')}),
        ('时间信息', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    """轮播图管理界面"""
    list_display = ('title', 'type', 'product', 'desc', 'sort_order', 'is_active', 'is_valid_display', 'created_at')
    list_filter = ('type', 'is_active', 'created_at')
    search_fields = ('title',)
    list_editable = ('sort_order', 'is_active')
    readonly_fields = ('created_at', 'updated_at', 'is_valid_display')
    list_display_links = ('title', 'type', 'product', 'desc',)

    fieldsets = (
        ('基本信息', {'fields': ('title', 'desc', 'image')}),
        ('链接配置', {'fields': ('type', 'product', 'activity_url', 'external_url')}),
        ('时间设置', {'fields': ('start_time', 'end_time')}),
        ('显示配置', {'fields': ('sort_order', 'is_active', 'is_valid_display')}),
        ('时间信息', {'fields': ('created_at', 'updated_at')}),
    )

    def is_valid_display(self, obj):
        """显示是否有效（只读字段）"""
        return obj.is_valid

    is_valid_display.boolean = True
    is_valid_display.short_description = '是否有效'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """购物车项管理界面"""
    list_display = ('user', 'get_product_name', 'spec_display', 'quantity',
                    'final_price', 'is_available', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'user')
    search_fields = ('user__username', 'user__phone', 'product__name', 'product_sku__sku_name')
    list_editable = ('quantity', 'is_active')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('用户信息', {'fields': ('user',)}),
        ('商品信息', {'fields': ('product', 'product_sku', 'selected_specs')}),
        ('购物车信息', {'fields': ('quantity', 'is_active')}),
        ('时间信息', {'fields': ('created_at', 'updated_at')}),
    )

    def get_product_name(self, obj):
        if obj.product_sku:
            return f"{obj.product_sku.product.name} - {obj.product_sku.sku_name}"
        return obj.product.name if obj.product else "未知商品"

    get_product_name.short_description = '商品名称'

    def final_price(self, obj):
        return obj.final_price

    final_price.short_description = '单价'

    def spec_display(self, obj):
        return obj.spec_display

    spec_display.short_description = '规格'

    def is_available(self, obj):
        return obj.is_available

    is_available.boolean = True
    is_available.short_description = '是否可用'


