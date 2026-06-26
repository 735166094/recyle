from rest_framework import serializers
from .models import Banner, NewsCategory, News


class BannerSerializer(serializers.ModelSerializer):
    """
    轮播图序列化器
    """
    # 返回完整的图片URL而不是相对路径
    image = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = '__all__'

    def get_image(self, obj):
        """
        获取完整的图片URL
        """
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class NewsCategorySerializer(serializers.ModelSerializer):
    """
    新闻分类序列化器
    """

    class Meta:
        model = NewsCategory
        fields = '__all__'


class NewsSerializer(serializers.ModelSerializer):
    """
    新闻资讯序列化器
    """
    category = NewsCategorySerializer(read_only=True)  # 嵌套序列化显示分类详情

    image = serializers.SerializerMethodField()  # 返回完整的图片URL而不是相对路径

    # category_id用于接收分类ID，确保只能选择激活的分类
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=NewsCategory.objects.filter(is_active=True),
        source='category',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = News
        fields = '__all__'

    def get_image(self, obj):
        """
        获取完整的图片URL
        """
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return obj.image_url