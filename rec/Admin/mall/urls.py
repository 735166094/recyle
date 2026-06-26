from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

urlpatterns = [
    # 商品分类
    path('categories/', views.ProductCategoryListView.as_view(), name='product_categories'),

    # 商品列表和详情
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),

    # 商品规格管理
    path('products/<int:product_id>/spec_groups/', views.ProductSpecGroupsView.as_view(), name='product_spec_groups'),
    path('products/<int:product_id>/spec_summary/', views.product_spec_summary, name='product_spec_summary'),
    path('products/<int:product_id>/skus/', views.ProductSkusView.as_view(), name='product_skus'),
    path('products/<int:product_id>/price_rules/', views.ProductPriceRulesView.as_view(), name='product_price_rules'),

    # 价格计算和规格可用性检查
    path('products/calculate_price/', views.CalculatePriceView.as_view(), name='calculate_price'),
    path('products/<int:product_id>/check_availability/', views.CheckSpecAvailabilityView.as_view(),
         name='check_spec_availability'),

    # 全局规格模板
    path('global_spec_templates/', views.GlobalSpecTemplatesView.as_view(), name='global_spec_templates'),
    path('products/<int:product_id>/apply_global_spec/', views.ApplyGlobalSpecTemplateView.as_view(),
         name='apply_global_spec'),

    # 推荐、热销和新品商品
    path('products/recommended/', views.RecommendedProductsView.as_view(), name='recommended_products'),
    path('products/hot/', views.HotProductsView.as_view(), name='hot_products'),
    path('products/new/', views.NewProductsView.as_view(), name='new_products'),

    # 轮播图
    path('banners/', views.BannerListView.as_view(), name='banner_list'),

    path('cart/stats/', views.CartStatsView.as_view(), name='cart_stats'),

]

router = DefaultRouter()
router.register(r'cart', views.CartItemViewSet, basename='cart')

urlpatterns += router.urls
