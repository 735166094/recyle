# vin/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .permissions import HasVinQueryPermission
from . import views

router = DefaultRouter()
# router.register(r'configs', views.VinConfigViewSet, basename='vin_config')
router.register(r'results', views.VinQueryResultViewSet, basename='vin_query_result')

urlpatterns = [
    path('', include(router.urls)),

    # VIN查询接口
    path('search/', views.VinSearchView.as_view(), name='vin_search'),

    path('query/', views.VinQueryResultViewSet.as_view({'post': 'query_vin'}), name='vin_query'),
    path('batch_query/', views.VinQueryResultViewSet.as_view({'post': 'batch_query'}), name='vin_batch_query'),

    # 统计信息
    path('statistics/', views.VinQueryResultViewSet.as_view({'get': 'statistics'}), name='vin_statistics'),

    # 重新查询
    path('results/<int:pk>/retry/', views.VinQueryResultViewSet.as_view({'post': 'retry_query'}),
         name='vin_retry_query'),
]