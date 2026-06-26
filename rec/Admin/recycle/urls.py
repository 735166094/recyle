# recycle/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'scrap_cars', views.ScrapCarViewSet, basename='scrap_car')
router.register(r'admin/scrap_cars', views.ScrapCarAdminViewSet, basename='admin_scrap_car')
router.register(r'price_rules', views.PriceRuleViewSet, basename='price_rule')
router.register(r'evaluation_materials', views.EvaluationMaterialViewSet, basename='evaluation_material')

urlpatterns = [
    path('', include(router.urls)),
    path('upload_car_image/', views.CarImageUploadView.as_view(), name='upload_car_image'),
    path('reverse_geocode/', views.reverse_geocode, name='reverse_geocode'),

    # 确保这些路径是正确的
    path('scrap_cars/stats/', views.ScrapCarStatsView.as_view(), name='scrap_cars_stats'),
    path('scrap_cars/my_records/', views.ScrapCarMyRecordsView.as_view(), name='scrap_cars_my_records'),

    # 调试接口
    path('debug/scrap_cars/', views.debug_scrap_cars, name='debug_scrap_cars'),
]
