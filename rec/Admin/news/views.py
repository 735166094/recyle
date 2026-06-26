from django.shortcuts import render
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404  # 用于简化获取对象的过程
from django_filters.rest_framework import DjangoFilterBackend
from .models import Banner, NewsCategory, News
from .serializers import BannerSerializer, NewsCategorySerializer, NewsSerializer
from rest_framework.filters import OrderingFilter, SearchFilter


class BannerViewSet(viewsets.ModelViewSet):
    """
    轮播图视图集
    提供轮播图的列表、创建、检索、更新和删除功能
    """
    # 允许所有用户访问
    queryset = Banner.objects.filter(is_active=True).order_by('order')
    serializer_class = BannerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # 允许过滤的字段
    filterset_fields = ['is_active']
    # 允许搜索的字段
    search_fields = ['title']
    # 允许排序的字段
    ordering_fields = ['order', 'created_at']

    def list(self, request, *args, **kwargs):
        """
        获取激活的轮播图列表
        """
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 200,
            'message': '成功',
            'data': serializer.data
        })


class NewsCategoryViewSet(viewsets.ModelViewSet):
    """新闻分类视图集"""
    queryset = NewsCategory.objects.filter(is_active=True)
    serializer_class = NewsCategorySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'EngName', 'description']
    filterset_fields = ['is_active']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    @action(detail=False, methods=['get'])
    def home_categories(self, request):
        """获取在首页显示的新闻分类"""
        categories = self.get_queryset().filter(
            is_active=True,
            show_in_home=True
        ).order_by('order')
        serializer = self.get_serializer(categories, many=True)
        return Response({
            'code': 200,
            'message': '成功',
            'data': serializer.data
        })
class NewsViewSet(viewsets.ModelViewSet):
    """新闻视图集"""
    queryset = News.objects.filter(is_active=True)
    serializer_class = NewsSerializer

    # 使用DjangoFilterBackend进行过滤，SearchFilter进行搜索，OrderingFilter进行排序
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['title', 'description', 'content']
    ordering_fields = ['publish_date', 'view_count', 'created_at']
    ordering = ['-publish_date', '-created_at']

    def get_queryset(self):
        """重写查询集，可根据需求进行筛选"""
        queryset = super().get_queryset() # 获取基础查询集

        # 可根据需要添加更多筛选条件

        return queryset

    def destroy(self, request, *args, **kwargs):
        """重写删除方法，实现物理删除"""
        instance = self.get_object()
        # 物理删除图片
        if instance.image:
            instance.image.delete(save=False)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def increase_view_count(self, request, pk=None):
        """增加新闻访问量"""
        news = self.get_object()
        news.increase_view_count()
        return Response({'view_count': news.view_count})

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """获取最新新闻"""
        # count 表示获取的新闻数量，默认10
        count = request.query_params.get('count', 10)
        try:
            count = int(count)
        except ValueError:
            count = 10

        news = self.get_queryset()[:count]
        serializer = self.get_serializer(news, many=True)
        return Response(serializer.data)
