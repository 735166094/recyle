from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone
import uuid


class Banner(models.Model):
    """
    轮播图模型
    """
    title = models.CharField(max_length=100, verbose_name="标题")

    desc = models.CharField(max_length=100, blank=True, null=True, verbose_name="描述")
    # 轮播图图片地址
    image = models.ImageField(upload_to='banners/', verbose_name="轮播图图片")
    # 点击轮播图跳转的链接
    link = models.URLField(max_length=500, blank=True, null=True, verbose_name="跳转链接")
    order = models.IntegerField(default=0, verbose_name="排序")  # 轮播图排序（数字越小越靠前）
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'banner'
        verbose_name = "轮播图"
        verbose_name_plural = "首页轮播图管理"
        ordering = ['order', '-created_at']  # 按排序和创建时间排序

    def __str__(self):
        return self.title

    # 重写增删改查方法
    def save(self, *args, **kwargs):
        """
        保存轮播图
        """
        # 可以在这里添加额外的业务逻辑，如图片处理等
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        删除轮播图
        """
        # 删除前可以添加清理逻辑，如删除对应的图片文件
        image_path = self.image.path
        # 调用父类删除方法
        super().delete(*args, **kwargs)


class NewsCategory(models.Model):
    """
    新闻分类模型
    """
    name = models.CharField(max_length=50, verbose_name="分类名称")
    EngName = models.CharField(max_length=50, verbose_name="英文名称")
    description = models.CharField(max_length=100, blank=True, null=True, verbose_name="分类描述")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    show_in_home = models.BooleanField(default=False, verbose_name="在首页显示")  #  字段
    order = models.IntegerField(default=0, verbose_name="首页排序")  # 控制首页显示顺序
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'news_category'
        verbose_name = "新闻分类"
        verbose_name_plural = "新闻分类"
        ordering = ['order', '-created_at']  # 按排序和创建时间排序

    def __str__(self):
        return self.name


class News(models.Model):
    """
    新闻资讯模型
    """
    title = models.CharField(max_length=100, verbose_name="新闻标题")
    category = models.ForeignKey(
        NewsCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="新闻分类"
    )
    image = models.ImageField(
        upload_to='news/images/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="新闻图片"
    )
    image_url = models.URLField(
        blank=True,
        verbose_name="图片链接",
        help_text="如果未上传图片，则显示此链接的图片"
    )
    content = models.TextField(verbose_name="新闻内容")
    source = models.CharField(max_length=50, default="", verbose_name="新闻来源")
    publish_date = models.DateField(default=timezone.now, verbose_name="发布日期")
    view_count = models.PositiveIntegerField(default=0, verbose_name="访问量")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'news'
        verbose_name = "新闻资讯"
        verbose_name_plural = "新闻资讯"
        ordering = ['-publish_date', '-created_at']

    def __str__(self):
        return self.title

    def get_image(self):
        """
        获取图片，优先使用上传的图片
        """
        if self.image:
            return self.image.url
        return self.image_url

    def increase_view_count(self):
        """
        增加访问量
        """
        self.view_count += 1
        self.save(update_fields=['view_count'])

    def delete(self, *args, **kwargs):
        """
        重写删除方法，同时删除物理存储的图片文件
        """
        # 删除前可以添加清理逻辑，如删除对应的图片文件
        if self.image:
            self.image.delete(save=False)

        super().delete(*args, **kwargs)  # 调用父类的删除方法，
