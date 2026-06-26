# urls.py (添加新的调试和触发URL)

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, error_handlers
from .views import VehicleLicenseResultAPIView, VehicleLicenseDetailAPIView

router = DefaultRouter()
# router.register(r'huawei_configs', views.HuaweiCloudConfigViewSet, basename='huawei_config')
router.register(r'ocr_interfaces', views.OcrInterfaceViewSet, basename='ocr_interface')
router.register(r'certificate_types', views.CertificateTypeViewSet, basename='certificate_type')
router.register(r'recognition_records', views.RecognitionRecordViewSet, basename='recognition_record')
router.register(r'scrap_car_info', views.ScrapCarInfoViewSet, basename='scrap_car_info')

urlpatterns = [
    # 包含路由器生成的URL
    path('', include(router.urls)),
    # 图片上传URL - 微信小程序主要使用
    path('upload_image/', views.ImageUploadView.as_view(), name='upload_image'),
    # 批量图片上传URL
    path('batch_upload/', views.BatchImageUploadView.as_view(), name='batch_upload'),
    # 统计信息URL
    path('statistics/', views.StatisticsView.as_view(), name='statistics'),
    # 识别结果详情URL
    path('recognition_results/<int:record_id>/', views.RecognitionResultView.as_view(), name='recognition_result'),
    # 我的记录URL
    path('recognition_records/my_records/', views.RecognitionRecordViewSet.as_view({'get': 'my_records'}),
         name='my_records'),
    # 重新识别URL
    path('recognition_records/<int:pk>/retry/', views.RecognitionRecordViewSet.as_view({'post': 'retry_recognition'}),
         name='retry_recognition'),

    # 报废车信息相关URL
    path('scrap_car_info/statistics/', views.ScrapCarInfoViewSet.as_view({'get': 'statistics'}),
         name='scrap_car_statistics'),
    path('scrap_car_info/batch_match/', views.ScrapCarInfoViewSet.as_view({'post': 'batch_match'}), name='batch_match'),
    path('scrap_car_info/<int:pk>/manual_match/', views.ScrapCarInfoViewSet.as_view({'post': 'manual_match'}),
         name='manual_match'),

    # 手动触发匹配和调试URL
    path('trigger_matching/<int:record_id>/', views.TriggerMatchingView.as_view(), name='trigger_matching'),
    path('debug_matching/<int:record_id>/', views.DebugMatchingView.as_view(), name='debug_matching'),

    # 重复检测URL
    path('debug_duplicate/<int:record_id>/', views.DebugDuplicateView.as_view(), name='debug_duplicate'),

    path('scrap_car_info/export_excel/',
         views.ScrapCarInfoViewSet.as_view({'get': 'export_excel', 'post': 'export_excel'}), name='export_excel'),
    path('scrap_car_info/export_with_fields/', views.ScrapCarInfoViewSet.as_view({'post': 'export_with_fields'}),
         name='export_with_fields'),
    path('scrap_car_info/available_export_fields/',
         views.ScrapCarInfoViewSet.as_view({'get': 'available_export_fields'}), name='available_export_fields'),

    # CSRF令牌获取
    path('csrf/', views.CSRFProtectedView.as_view(), name='csrf_token'),

    # VIN查询URL
    path('vehicle_license/<int:pk>/query_vin/', views.VehicleLicenseResultViewSet.as_view({'post': 'query_vin'}),
         name='query_vehicle_vin'),

    # 批量VIN查询URL
    path('vehicle_license/batch_query_vin/', views.VehicleLicenseResultViewSet.as_view({'post': 'batch_query_vin'}),
         name='batch_query_vehicle_vin'),

    # 行驶证识别结果API接口 - 供其他系统调用
    path('vehicle_license/results/', VehicleLicenseResultAPIView.as_view(), name='vehicle_license_results'),
    path('vehicle_license/results/<int:result_id>/', VehicleLicenseDetailAPIView.as_view(),
         name='vehicle_license_result_detail'),
    # 车辆搜索API接口
    path('vehicle_license/search/', views.VehicleSearchAPIView.as_view(), name='vehicle_search'),


]

# 错误处理
handler404 = error_handlers.handle_404_error
handler500 = error_handlers.handle_500_error
