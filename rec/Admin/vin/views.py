# vin/views.py
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import exceptions

from . import permissions
from .models import VinConfig, VinQueryResult
from .serializers import (
    VinConfigSerializer, VinQueryResultSerializer,
    VinQueryRequestSerializer, VinQueryStatisticsSerializer,
    VinBatchQuerySerializer
)
from .vin import VinConfigManager

logger = logging.getLogger(__name__)


class BaseViewSet(viewsets.ModelViewSet):
    """基础视图集"""

    def perform_create(self, serializer):
        instance = serializer.save()
        logger.info(f"用户 {self.request.user.username} 创建了 {self._get_model_name()}: {instance.id}")

    def perform_update(self, serializer):
        instance = serializer.save()
        logger.info(f"用户 {self.request.user.username} 更新了 {self._get_model_name()}: {instance.id}")

    def perform_destroy(self, instance):
        instance.delete()
        logger.info(f"用户 {self.request.user.username} 删除了 {self._get_model_name()}: {instance.id}")

    def _get_model_name(self):
        return self.queryset.model.__name__ if self.queryset else '记录'


class VinConfigViewSet(BaseViewSet):
    """VIN配置视图集"""
    queryset = VinConfig.objects.all()
    serializer_class = VinConfigSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return VinConfig.objects.all()
        else:
            return VinConfig.objects.filter(is_active=True)


class VinQueryResultViewSet(BaseViewSet):
    """VIN查询结果视图集"""

    serializer_class = VinQueryResultSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['query_status', 'brand', 'config_used']
    search_fields = ['vin_code', 'brand', 'model_name']
    ordering_fields = ['query_time', 'processing_time', 'model_count']
    ordering = ['-query_time']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            queryset = VinQueryResult.objects.all()
        else:
            queryset = VinQueryResult.objects.filter(user=user)
        return queryset.select_related('config_used', 'user').order_by('-query_time')

    @action(detail=False, methods=['post'])
    def query_vin(self, request):
        """执行VIN查询"""
        try:
            serializer = VinQueryRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            vin_code = serializer.validated_data['vin_code']
            config_id = serializer.validated_data.get('config_id')
            save_result = serializer.validated_data.get('save_result', True)

            start_time = timezone.now()

            # 获取VIN配置
            if config_id:
                config = VinConfigManager.get_config_by_id(config_id)
            else:
                config = VinConfigManager.get_active_config()

            if not config:
                return Response(
                    {"error": "未找到有效的VIN配置"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 执行VIN查询
            parser = VinConfigManager.query_vin_with_config(vin_code, config)
            processing_time = (timezone.now() - start_time).total_seconds()

            response_data = {
                'success': parser.is_success,
                'vin_code': vin_code,
                'processing_time': processing_time,
                'config_used': {
                    'id': config.id,
                    'name': config.name
                } if config else None
            }

            if parser.is_success:
                all_data = self._extract_complete_data_from_parser(parser)

                # 保存查询结果
                if save_result:
                    vin_result = VinQueryResult(
                        vin_code=vin_code,
                        config_used=config,
                        user=request.user,
                        query_status='success',
                        processing_time=processing_time,
                        **all_data
                    )
                    vin_result.save()
                    response_data['saved_result_id'] = vin_result.id

                response_data.update({
                    'basic_info': all_data['basic_info'],
                    'model_list': self._format_model_list_for_response(all_data['model_list']),
                    'original_attributes': all_data['original_attributes'],
                    'gonggao_list': all_data['gonggao_list'],
                    'import_list': all_data['import_list'],
                    'statistics': {
                        'model_count': len(all_data['model_list']),
                        'original_attributes_count': len(all_data['original_attributes']),
                        'gonggao_count': len(all_data['gonggao_list']),
                        'import_count': len(all_data['import_list']),
                        'has_images': any(model.get('Img_adress') for model in all_data['model_list'])
                    }
                })

            else:
                response_data['error_message'] = parser.message

                if save_result:
                    vin_result = VinQueryResult(
                        vin_code=vin_code,
                        config_used=config,
                        user=request.user,
                        query_status='failed',
                        error_message=parser.message,
                        processing_time=processing_time,
                        raw_response_data=parser.raw_data
                    )
                    vin_result.save()
                    response_data['saved_result_id'] = vin_result.id

            return Response(response_data)

        except Exception as e:
            logger.error(f"VIN查询失败: {str(e)}")
            return Response(
                {"error": f"VIN查询失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @staticmethod
    def _extract_complete_data_from_parser(parser):
        """从解析器提取完整数据"""
        try:
            data = parser.raw_data.get('data', {})

            # 提取车型名称
            model_name = ''
            model_list = data.get('model_list', [])
            if model_list and len(model_list) > 0:
                first_model = model_list[0]
                model_name = first_model.get('Model_detail', '') or first_model.get('Model', '')

            # 提取原厂属性
            original_attributes = []
            original_epc_list = data.get('model_original_epc_list', [])
            for epc in original_epc_list:
                car_attrs = epc.get('CarAttributes', [])
                for attr in car_attrs:
                    if attr.get('Language') == 'zh':
                        original_attributes.append(attr)

            return {
                'brand': parser.brand,
                'model_year': parser.model_year_from_vin,
                'build_date': parser.build_date,
                'model_name': model_name,
                'model_list': parser.get_model_list(),
                'original_epc_list': parser.get_original_epc_list(),
                'original_attributes': original_attributes,
                'gonggao_list': parser.get_gonggao_list(),
                'import_list': parser.get_import_list(),
                'raw_response_data': parser.raw_data,
                'basic_info': {
                    'brand': parser.brand,
                    'model_name': model_name,
                    'model_year': parser.model_year_from_vin,
                    'build_date': parser.build_date,
                }
            }
        except Exception as e:
            logger.error(f"提取解析器数据失败: {str(e)}")
            # 返回简化版本
            model_name = ''
            model_list = parser.get_model_list()
            if model_list and len(model_list) > 0:
                first_model = model_list[0]
                model_name = first_model.get('Model_detail', '') or first_model.get('Model', '')

            return {
                'brand': parser.brand,
                'model_year': parser.model_year_from_vin,
                'build_date': parser.build_date,
                'model_name': model_name,
                'model_list': model_list,
                'original_epc_list': parser.get_original_epc_list(),
                'original_attributes': parser.get_original_attributes('zh'),
                'gonggao_list': parser.get_gonggao_list(),
                'import_list': parser.get_import_list(),
                'raw_response_data': parser.raw_data,
                'basic_info': {
                    'brand': parser.brand,
                    'model_name': model_name,
                    'model_year': parser.model_year_from_vin,
                    'build_date': parser.build_date,
                }
            }

    @staticmethod
    def _format_model_list_for_response(model_list):
        """格式化车型列表用于API响应"""
        formatted_models = []
        for model in model_list:
            formatted_model = {
                'model_detail': model.get('Model_detail', ''),
                'model_name': model.get('Model', ''),
                'factory': model.get('Factory', ''),
                'brand': model.get('Brand', ''),
                'series': model.get('Series', ''),
                'sales_version': model.get('Sales_version', ''),
                'cc': model.get('Cc', ''),
                'engine_no': model.get('Engine_no', ''),
                'price': model.get('Price', ''),
                'transmission_detail': model.get('Transmission_detail', ''),
                'fuel_type': model.get('Fuel_type', ''),
                'body_type': model.get('Body_type', ''),
                'images': VinQueryResultViewSet._get_model_images(model)
            }
            formatted_models.append(formatted_model)
        return formatted_models

    @staticmethod
    def _get_model_images(model):
        """获取车型图片URL列表"""
        try:
            img_address = model.get('Img_adress', '')
            if not img_address:
                return []

            base_url = "http://resource.17vin.com/img/car/all/"
            img_paths = [path.strip() for path in img_address.split(',')]
            return [f"{base_url}{path}" for path in img_paths if path]
        except Exception as e:
            logger.error(f"获取车型图片失败: {str(e)}")
            return []

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """获取VIN查询统计信息"""
        from django.db.models import Avg
        user = request.user

        if user.is_staff:
            queryset = VinQueryResult.objects.all()
        else:
            queryset = VinQueryResult.objects.filter(user=user)

        # 基础统计
        total_queries = queryset.count()
        success_queries = queryset.filter(query_status='success').count()
        failed_queries = queryset.filter(query_status='failed').count()

        # 时间范围统计
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        today_queries = queryset.filter(query_time__date=today).count()
        week_queries = queryset.filter(query_time__date__gte=week_ago).count()
        month_queries = queryset.filter(query_time__date__gte=month_ago).count()

        # 热门品牌
        popular_brands = queryset.filter(
            query_status='success', brand__isnull=False
        ).exclude(brand='').values('brand').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        # 热门车型
        popular_models = queryset.filter(
            query_status='success', model_name__isnull=False
        ).exclude(model_name='').values('model_name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        # 查询趋势（最近7天）
        query_trends = []
        for i in range(7):
            date = today - timedelta(days=i)
            count = queryset.filter(query_time__date=date).count()
            query_trends.append({
                'date': date.isoformat(),
                'count': count
            })

        # 数据完整性统计
        has_images_count = queryset.filter(has_images=True).count()
        has_vehicle_info_count = queryset.filter(has_vehicle_info=True).count()
        avg_processing_time = queryset.aggregate(avg_time=Avg('processing_time'))['avg_time'] or 0

        statistics_data = {
            'total_queries': total_queries,
            'success_queries': success_queries,
            'failed_queries': failed_queries,
            'success_rate': round((success_queries / total_queries * 100) if total_queries > 0 else 0, 2),
            'today_queries': today_queries,
            'week_queries': week_queries,
            'month_queries': month_queries,
            'popular_brands': list(popular_brands),
            'popular_models': list(popular_models),
            'query_trends': list(reversed(query_trends)),
            'data_quality': {
                'has_images_count': has_images_count,
                'has_vehicle_info_count': has_vehicle_info_count,
                'has_images_rate': round((has_images_count / success_queries * 100) if success_queries > 0 else 0, 2),
                'has_vehicle_info_rate': round(
                    (has_vehicle_info_count / success_queries * 100) if success_queries > 0 else 0, 2),
                'avg_processing_time': round(avg_processing_time, 2)
            }
        }

        serializer = VinQueryStatisticsSerializer(statistics_data)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def retry_query(self, request, pk=None):
        """重新执行VIN查询"""
        try:
            vin_result = self.get_object()

            config = vin_result.config_used
            if not config:
                config = VinConfigManager.get_active_config()

            if not config:
                return Response(
                    {"error": "未找到有效的VIN配置"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            start_time = timezone.now()
            parser = VinConfigManager.query_vin_with_config(vin_result.vin_code, config)
            processing_time = (timezone.now() - start_time).total_seconds()

            if parser.is_success:
                all_data = self._extract_complete_data_from_parser(parser)

                vin_result.query_status = 'success'
                vin_result.error_message = None
                vin_result.processing_time = processing_time

                # 更新所有字段
                for field, value in all_data.items():
                    if hasattr(vin_result, field):
                        setattr(vin_result, field, value)

                message = "VIN查询重试成功"
            else:
                vin_result.query_status = 'failed'
                vin_result.error_message = parser.message
                vin_result.processing_time = processing_time
                vin_result.raw_response_data = parser.raw_data

                message = f"VIN查询重试失败: {parser.message}"

            vin_result.save()

            serializer = self.get_serializer(vin_result)
            return Response({
                'success': parser.is_success,
                'message': message,
                'data': serializer.data
            })

        except Exception as e:
            logger.error(f"VIN查询重试失败: {str(e)}")
            return Response(
                {"error": f"VIN查询重试失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def batch_query(self, request):
        """批量VIN查询"""
        try:
            serializer = VinBatchQuerySerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            vin_codes = serializer.validated_data['vin_codes']
            config_id = serializer.validated_data.get('config_id')
            save_results = serializer.validated_data.get('save_results', True)

            if config_id:
                config = VinConfigManager.get_config_by_id(config_id)
            else:
                config = VinConfigManager.get_active_config()

            if not config:
                return Response(
                    {"error": "未找到有效的VIN配置"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            results = []
            success_count = 0

            for vin_code in vin_codes:
                try:
                    parser = VinConfigManager.query_vin_with_config(vin_code, config)

                    result_data = {
                        'vin_code': vin_code,
                        'success': parser.is_success,
                        'error_message': parser.message if not parser.is_success else None
                    }

                    if parser.is_success:
                        success_count += 1
                        all_data = self._extract_complete_data_from_parser(parser)
                        result_data.update({
                            'brand': parser.brand,
                            'model_year': parser.model_year_from_vin,
                            'model_name': all_data.get('model_name', ''),
                            'basic_info': all_data['basic_info']
                        })

                    if save_results and parser.is_success:
                        vin_result = VinQueryResult(
                            vin_code=vin_code,
                            config_used=config,
                            user=request.user,
                            query_status='success',
                            processing_time=0,
                            **all_data
                        )
                        vin_result.save()
                        result_data['saved_result_id'] = vin_result.id

                    results.append(result_data)

                except Exception as e:
                    results.append({
                        'vin_code': vin_code,
                        'success': False,
                        'error_message': str(e)
                    })

            return Response({
                'total_count': len(vin_codes),
                'success_count': success_count,
                'failed_count': len(vin_codes) - success_count,
                'success_rate': round((success_count / len(vin_codes)) * 100, 2),
                'results': results
            })

        except Exception as e:
            logger.error(f"批量VIN查询失败: {str(e)}")
            return Response(
                {"error": f"批量VIN查询失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VinSearchView(APIView):
    """VIN查询视图 - 微信小程序专用接口"""

    # 直接设置权限类
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        """
        自定义权限检查
        """
        # 首先调用父类的权限检查（检查是否认证）
        super().check_permissions(request)

        # 如果不是POST请求，直接通过
        if request.method != 'POST':
            return

        # 检查用户是否认证（父类已检查，这里做额外验证）
        if not request.user or not request.user.is_authenticated:
            logger.error("VIN查询权限检查失败: 用户未认证")
            raise exceptions.PermissionDenied("请先登录")

        # 记录用户信息用于调试
        user_info = {
            'id': request.user.id,
            'username': request.user.username,
            'is_staff': request.user.is_staff,
            'is_superuser': request.user.is_superuser,
            'is_staff_member': getattr(request.user, 'is_staff_member', False),
            'ocr_user_type': getattr(request.user, 'ocr_user_type', 'unknown'),
            'staff_role': getattr(request.user, 'staff_role', ''),
            'staff_id': getattr(request.user, 'staff_id', ''),
            'is_active': request.user.is_active
        }
        logger.info(f"VIN查询 - 用户权限检查信息: {user_info}")

        # 检查用户类型 - 更灵活的检查
        ocr_user_type = getattr(request.user, 'ocr_user_type', 'unknown')

        # 扩展允许的用户类型
        allowed_user_types = ['employee', 'admin', 'manager', 'wechat', 'unknown']  # 添加 'unknown' 和 'wechat'

        # 1. 如果用户类型在允许列表中，检查用户状态
        if ocr_user_type in allowed_user_types:
            # 检查用户是否激活
            if not request.user.is_active:
                logger.error(f"VIN查询权限检查失败: 用户账号未激活")
                raise exceptions.PermissionDenied("用户账号未激活")

            logger.info(f"VIN查询权限检查通过: 用户类型 {ocr_user_type}")
            return

        # 2. 如果是超级管理员，直接通过
        if request.user.is_superuser:
            logger.info("VIN查询权限检查通过: 超级管理员")
            return

        # 3. 如果是普通员工（is_staff），检查是否有VIN查询权限
        if request.user.is_staff:
            # 检查是否有VIN查询权限（通过用户组或权限）
            has_perm = request.user.has_perm('vin.can_query_vin') or \
                       request.user.has_perm('vin.query_vin') or \
                       request.user.groups.filter(name__in=['VIN查询', '员工']).exists()

            if has_perm:
                logger.info("VIN查询权限检查通过: 具有VIN查询权限的员工")
                return
            else:
                logger.error("VIN查询权限检查失败: 员工没有VIN查询权限")
                raise exceptions.PermissionDenied("您没有VIN查询权限")

        # 4. 默认拒绝其他用户
        logger.error(f"VIN查询权限检查失败: 用户类型 {ocr_user_type} 不允许访问")
        raise exceptions.PermissionDenied("您没有权限进行VIN查询")

    def post(self, request):
        try:
            # 记录用户信息用于调试
            user_info = {
                'id': request.user.id,
                'username': request.user.username,
                'is_staff': request.user.is_staff,
                'is_superuser': request.user.is_superuser,
                'is_staff_member': getattr(request.user, 'is_staff_member', False),
                'ocr_user_type': getattr(request.user, 'ocr_user_type', 'unknown'),
                'is_active': request.user.is_active
            }
            logger.info(f"VIN查询请求接收 - 用户信息: {user_info}")

            # 检查请求数据
            vin_code = request.data.get('vin') or request.data.get('vin_code', '').strip().upper()

            if not vin_code:
                logger.warning("VIN查询失败: VIN码为空")
                return Response(
                    {"message": "VIN码不能为空"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 验证VIN码格式
            if len(vin_code) != 17:
                logger.warning(f"VIN查询失败: VIN码长度错误 {len(vin_code)}")
                return Response(
                    {"message": "VIN码应为17位字符"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            import re
            if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin_code):
                logger.warning(f"VIN查询失败: VIN码格式不正确 {vin_code}")
                return Response(
                    {"message": "VIN码格式不正确"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"开始查询VIN码: {vin_code}")

            # 获取VIN配置
            config = VinConfigManager.get_active_config()
            if not config:
                logger.error("VIN查询失败: 未找到激活的VIN配置")
                return Response(
                    {"message": "系统配置不可用，请联系管理员"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 执行VIN查询
            start_time = timezone.now()
            parser = VinConfigManager.query_vin_with_config(vin_code, config)
            processing_time = (timezone.now() - start_time).total_seconds()

            response_data = {
                'success': parser.is_success,
                'vin_code': vin_code,
                'processing_time': round(processing_time, 2),
                'timestamp': timezone.now().isoformat()
            }

            if parser.is_success:
                logger.info(f"VIN查询成功: {vin_code}")

                # 提取车型名称
                model_name = ''
                model_list = parser.get_model_list()
                if model_list and len(model_list) > 0:
                    first_model = model_list[0]
                    model_name = first_model.get('Model_detail', '') or first_model.get('Model', '')

                basic_info = {
                    'brand': parser.brand or '',
                    'model_name': model_name or '',
                    'model_year': parser.model_year_from_vin or '',
                    'build_date': parser.build_date or '',
                }

                model_list = parser.get_model_list()[:5]
                formatted_models = []
                for model in model_list:
                    formatted_model = {
                        'model_detail': model.get('Model_detail', ''),
                        'model_name': model.get('Model', ''),
                        'factory': model.get('Factory', ''),
                        'series': model.get('Series', ''),
                        'sales_version': model.get('Sales_version', ''),
                        'cc': model.get('Cc', ''),
                        'engine_no': model.get('Engine_no', ''),
                        'price': model.get('Price', ''),
                        'transmission': model.get('Transmission_detail', ''),
                        'fuel_type': model.get('Fuel_type', ''),
                        'body_type': model.get('Body_type', ''),
                        'images': self._get_model_images(model)
                    }
                    formatted_models.append(formatted_model)

                original_attributes = parser.get_original_attributes('zh')
                main_attributes = []
                for attr in original_attributes[:8]:
                    if attr.get('IsMajorAttribute'):
                        main_attributes.append({
                            'name': attr.get('Col_name', ''),
                            'value': attr.get('Col_value', '')
                        })

                response_data.update({
                    'basic_info': basic_info,
                    'models': formatted_models,
                    'model_count': len(parser.get_model_list()),
                    'main_attributes': main_attributes,
                    'has_images': any(model.get('Img_adress') for model in model_list),
                })

                # 根据配置决定是否保存查询结果
                if config.save_miniprogram_results:
                    self._save_query_result(
                        request.user, vin_code, config, parser,
                        processing_time, True, None
                    )
                    response_data['saved_to_database'] = True
                else:
                    response_data['saved_to_database'] = False

            else:
                error_msg = parser.message or '未知错误'
                logger.warning(f"VIN查询失败: {vin_code} - {error_msg}")
                response_data['message'] = error_msg

                # 失败时也根据配置决定是否保存
                if config.save_miniprogram_results:
                    self._save_query_result(
                        request.user, vin_code, config, parser,
                        processing_time, False, parser.message
                    )
                    response_data['saved_to_database'] = True
                else:
                    response_data['saved_to_database'] = False

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"VIN查询异常: {str(e)}", exc_info=True)
            return Response(
                {"message": f"查询失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @staticmethod
    def _get_model_images(model):
        """获取车型图片URL列表"""
        try:
            img_address = model.get('Img_adress', '')
            if not img_address:
                return []

            base_url = "http://resource.17vin.com/img/car/all/"
            img_paths = [path.strip() for path in img_address.split(',')]
            return [f"{base_url}{path}" for path in img_paths if path]
        except Exception as e:
            logger.error(f"获取车型图片失败: {str(e)}")
            return []

    def _save_query_result(self, user, vin_code, config, parser, processing_time, is_success, error_message):
        """保存查询结果到数据库"""
        try:
            if is_success:
                # 提取车型名称
                model_name = ''
                model_list = parser.get_model_list()
                if model_list and len(model_list) > 0:
                    first_model = model_list[0]
                    model_name = first_model.get('Model_detail', '') or first_model.get('Model', '')

                vin_result = VinQueryResult(
                    vin_code=vin_code,
                    config_used=config,
                    user=user,
                    query_status='success',
                    processing_time=processing_time,
                    brand=parser.brand or '',
                    model_year=parser.model_year_from_vin or '',
                    build_date=parser.build_date or '',
                    model_name=model_name,
                    model_list=parser.get_model_list(),
                    original_epc_list=parser.get_original_epc_list(),
                    original_attributes=parser.get_original_attributes('zh'),
                    gonggao_list=parser.get_gonggao_list(),
                    import_list=parser.get_import_list(),
                    raw_response_data=parser.raw_data
                )
                vin_result.save()
                logger.info(f"保存VIN查询结果成功: {vin_code}")
            else:
                vin_result = VinQueryResult(
                    vin_code=vin_code,
                    config_used=config,
                    user=user,
                    query_status='failed',
                    error_message=error_message,
                    processing_time=processing_time,
                    raw_response_data=parser.raw_data if hasattr(parser, 'raw_data') else {}
                )
                vin_result.save()
                logger.info(f"保存VIN查询失败结果: {vin_code}")
        except Exception as e:
            logger.error(f"保存VIN查询结果失败: {str(e)}")
