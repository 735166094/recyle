from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'banner', views.BannerViewSet, basename='banner')
router.register(r'news_categories', views.NewsCategoryViewSet, basename='news_categories')
router.register(r'news', views.NewsViewSet, basename='news')

urlpatterns = router.urls
