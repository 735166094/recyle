from django.contrib import admin

from django.utils.safestring import mark_safe
from .models import Banner, NewsCategory, News


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    """
    轮播图管理后台配置
    """
    # 列表中显示的字段（第一个字段默认是链接字段，需与 list_editable 区分）
    list_display = ['title', 'desc', 'image_preview', 'link', 'order', 'is_active', 'created_at', 'updated_at']
    # 可编辑的字段不能包含 list_display 的默认链接字段，除非显式设置 list_display_links）
    list_editable = ['order', 'title', 'desc', 'is_active']
    # 关键修复：显式指定链接字段（必须是 list_display 中的字段，且不在 list_editable 中）
    list_display_links = ['image_preview']  # 用图片预览作为链接字段，避免与 editable 冲突
    # 只读字段，显示图片预览
    readonly_fields = ['image_preview']

    # 可过滤的字段
    list_filter = ['is_active', 'created_at', 'updated_at']
    # 搜索字段
    search_fields = ['title', 'desc']
    # 每页显示的数量
    list_per_page = 10
    # 排序方式
    ordering = ['order', '-created_at']

    def image_preview(self, obj):
        """
        在列表中显示图片预览
        """
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" style="max-height: 100px; max-width: 200px;" />')
        return "无图片"

    image_preview.short_description = '图片预览'
    image_preview.allow_tags = True


@admin.register(NewsCategory)
class NewsCategoryAdmin(admin.ModelAdmin):
    """
    新闻分类管理后台配置
    """
    list_display = ['id', 'name', 'EngName', 'description', 'is_active', 'show_in_home', 'order', 'created_at',
                    'updated_at']  # 添加id字段
    list_editable = ['is_active', 'show_in_home', ]
    list_display_links = ['id',]  # 使用id作为链接字段
    list_filter = ['updated_at', 'is_active', 'created_at', 'show_in_home']
    search_fields = ['description', 'name', 'EngName']
    list_per_page = 12
    ordering = ['order', '-created_at']

    def activate_categories(self, request, queryset):
        """激活选择的分类"""
        queryset.update(is_active=True)
        self.message_user(request, "已成功激活选择的分类")

    activate_categories.short_description = "激活选择的分类"

    def deactivate_categories(self, request, queryset):
        """禁用选择的分类"""
        queryset.update(is_active=False)
        self.message_user(request, "已成功禁用选择的分类")

    deactivate_categories.short_description = "禁用选择的分类"


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    """
    新闻管理后台配置
    """
    list_display = ['title', 'category', 'image_preview', 'publish_date', 'view_count', 'is_active', 'created_at',
                    'updated_at']
    list_editable = ['category', 'publish_date', 'is_active']
    list_display_links = ['image_preview']  # 使用图片预览作为链接字段
    readonly_fields = ['image_preview', 'view_count', 'created_at', 'updated_at']
    list_filter = ['is_active', 'category', 'publish_date', 'created_at', 'updated_at']
    search_fields = ['title', 'content']
    # search_fields = ['title']
    list_per_page = 10
    ordering = ['-publish_date', '-created_at']
    actions = ['activate_news', 'deactivate_news', 'increase_views']

    fieldsets = [
        (None, {
            'fields': ['title', 'category', 'is_active', 'publish_date']
        }),
        ('内容', {
            'fields': ['content', 'image', 'image_url']
        }),
        ('图片预览', {
            'fields': ['image_preview'],
            'classes': ['collapse']
        }),
        ('统计信息', {
            'fields': ['view_count', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    # 添加 image_preview 方法
    def image_preview(self, obj):
        """
        在列表中显示图片预览
        """
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" style="max-height: 100px; max-width: 200px;" />')
        elif obj.image_url:
            return mark_safe(f'<img src="{obj.image_url}" style="max-height: 100px; max-width: 200px;" />')
        return "无图片"

    image_preview.short_description = '图片预览'
    image_preview.allow_tags = True

    def activate_news(self, request, queryset):
        """激活所选新闻"""
        queryset.update(is_active=True)
        self.message_user(request, "已成功激活所选新闻")

    activate_news.short_description = "激活所选新闻"

    def deactivate_news(self, request, queryset):
        """禁用所选新闻"""
        queryset.update(is_active=False)
        self.message_user(request, "已成功禁用所选新闻")

    deactivate_news.short_description = "禁用所选新闻"

    def increase_views(self, request, queryset):
        """增加所选新闻的访问量"""
        for news in queryset:
            news.view_count += 100  # 一次性增加100访问量
            news.save(update_fields=['view_count'])
        self.message_user(request, "已成功增加所选新闻的访问量")

    increase_views.short_description = "增加访问量(+100)"

    def delete_model(self, request, obj):
        """删除单个模型实例时同时删除图片文件"""
        # 模型层的delete方法已处理图片删除
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """删除查询集时同时删除所有图片文件"""
        # 模型层的delete方法已处理图片删除
        super().delete_queryset(request, queryset)

    # def delete_model(self, request, obj):
    #     """删除单个模型实例时同时删除图片文件"""
    #     if obj.image:
    #         obj.image.delete(save=False)
    #     super().delete_model(request, obj)
    #
    # def delete_queryset(self, request, queryset):
    #     """删除查询集时同时删除所有图片文件"""
    #     for obj in queryset:
    #         if obj.image:
    #             obj.image.delete(save=False)
    #     super().delete_queryset(request, queryset)
