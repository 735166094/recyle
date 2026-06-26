# recycle/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import ScrapCar, PriceRule,LocationCache,EvaluationMaterial
from .serializers import ScrapCarSerializer, ScrapCarListSerializer, PriceRuleSerializer, CarImageUploadSerializer, \
    ScrapCarStatusUpdateSerializer ,LocationSerializer, ReverseGeocodeSerializer,EvaluationMaterialSerializer
from rest_framework.parsers import MultiPartParser, FormParser
import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from datetime import datetime
import requests
import uuid
import logging
from django.db.models import Count
from django.core.paginator import Paginator

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def debug_scrap_cars(request):
    """调试接口：查看报废车数据"""
    try:
        # 限制返回数量，避免数据过大
        scrap_cars = ScrapCar.objects.all().select_related('user').order_by('-submit_time')[:20]

        # 使用列表序列化器
        from .serializers import ScrapCarListSerializer
        serializer = ScrapCarListSerializer(scrap_cars, many=True, context={'request': request})

        # 计算状态统计（基于所有记录，不只是当前页）
        status_stats = {
            'total_count': ScrapCar.objects.count(),
            'pending_count': ScrapCar.objects.filter(status='pending').count(),
            'priced_count': ScrapCar.objects.filter(status='priced').count(),
            'confirmed_count': ScrapCar.objects.filter(status='confirmed').count(),
            'cancelled_count': ScrapCar.objects.filter(status='cancelled').count(),
        }

        return Response({
            'success': True,
            'count': len(scrap_cars),
            'results': serializer.data,
            'status_stats': status_stats,  # 新增状态统计字段
            'message': '调试模式 - 显示最近20条记录'
        })

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


class ScrapCarStatsView(APIView):
    """报废车统计视图"""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get(request):
        """获取用户统计信息"""
        queryset = ScrapCar.objects.filter(user=request.user)

        # 使用聚合查询提高性能
        status_stats = queryset.values('status').annotate(count=Count('id'))

        stats_data = {
            'total_count': queryset.count(),
            'pending_count': 0,
            'priced_count': 0,
            'confirmed_count': 0,
            'cancelled_count': 0,
        }

        # 填充各状态数量
        for stat in status_stats:
            status = stat['status']
            count = stat['count']
            if status == 'pending':
                stats_data['pending_count'] = count
            elif status == 'priced':
                stats_data['priced_count'] = count
            elif status == 'confirmed':
                stats_data['confirmed_count'] = count
            elif status == 'cancelled':
                stats_data['cancelled_count'] = count

        return Response({
            'success': True,
            'data': stats_data
        })

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """用户更新记录状态 """
        scrap_car = self.get_object()
        serializer = ScrapCarStatusUpdateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': '数据验证失败',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        new_status = serializer.validated_data['status']
        reason = serializer.validated_data.get('reason', '')

        # 验证用户只能修改自己的记录
        if scrap_car.user != request.user:
            return Response({
                'success': False,
                'message': '无权操作此记录'
            }, status=status.HTTP_403_FORBIDDEN)

        # 验证状态转换的合法性
        valid_transitions = {
            'priced': ['confirmed', 'cancelled'],
            'pending': ['cancelled']
        }

        current_status = scrap_car.status
        if current_status not in valid_transitions or new_status not in valid_transitions[current_status]:
            return Response({
                'success': False,
                'message': f'不能从{scrap_car.get_status_display()}状态变更为{dict(ScrapCar.STATUS_CHOICES).get(new_status, new_status)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 特殊处理：当状态变为confirmed且最终价格为null时，将预估价格设置为最终价格
            price_updated = False
            if new_status == 'confirmed':
                logger.info(
                    f"确认订单处理: 订单{scrap_car.id}, 当前最终价格: {scrap_car.final_price}, 预估价格: {scrap_car.estimated_price}")

                if scrap_car.final_price is None and scrap_car.estimated_price is not None:
                    scrap_car.final_price = scrap_car.estimated_price
                    price_updated = True
                    logger.info(
                        f"自动填充最终价格: 订单{scrap_car.id}的最终价格从null设置为预估价格{scrap_car.estimated_price}")
                elif scrap_car.final_price is None and scrap_car.estimated_price is None:
                    logger.warning(f"订单{scrap_car.id}的预估价格和最终价格都为空，无法自动填充")
                else:
                    logger.info(f"订单{scrap_car.id}的最终价格已存在: {scrap_car.final_price}")

            # 使用新的状态更新方法
            scrap_car.update_status(new_status, f'用户操作：{reason}', request.user)
            scrap_car.save()

            # 返回更新后的数据
            result_serializer = self.get_serializer(scrap_car)
            return Response({
                'success': True,
                'message': '状态更新成功',
                'data': result_serializer.data,
                'price_updated': price_updated  # 明确返回价格是否更新
            })

        except Exception as e:
            logger.error(f"更新状态失败: {str(e)}")
            return Response({
                'success': False,
                'message': '状态更新失败',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ScrapCarMyRecordsView(APIView):
    """用户报废车记录列表视图 """
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get(request):
        """获取当前用户的回收记录"""
        try:
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            status_filter = request.GET.get('status', None)

            # 基础查询集
            queryset = ScrapCar.objects.filter(user=request.user).select_related('user').order_by('-submit_time')

            # 状态筛选
            if status_filter and status_filter != 'all':
                queryset = queryset.filter(status=status_filter)

            # 手动分页
            paginator = Paginator(queryset, page_size)
            try:
                records = paginator.page(page)
            except:
                records = paginator.page(1)

            serializer = ScrapCarListSerializer(records, many=True, context={'request': request})

            # 计算统计数据（基于所有记录，不只是当前页）- 只在第一页计算
            status_stats = None
            if page == 1:
                user_queryset = ScrapCar.objects.filter(user=request.user)
                status_stats = {
                    'total_count': user_queryset.count(),
                    'pending_count': user_queryset.filter(status='pending').count(),
                    'priced_count': user_queryset.filter(status='priced').count(),
                    'confirmed_count': user_queryset.filter(status='confirmed').count(),
                    'cancelled_count': user_queryset.filter(status='cancelled').count(),
                }

            response_data = {
                'success': True,
                'data': {
                    'records': serializer.data,
                },
                'pagination': {
                    'current_page': page,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_next': records.has_next(),
                    'has_previous': records.has_previous(),
                }
            }

            # 只有在第一页时添加统计信息
            if status_stats:
                response_data['data']['stats'] = status_stats
                response_data['status_stats'] = status_stats

            return Response(response_data)

        except Exception as e:
            logger.error(f"获取用户回收记录失败: {str(e)}")
            return Response({
                'success': False,
                'message': '获取记录失败',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ScrapCarViewSet(viewsets.ModelViewSet):
    """
    报废车回收信息视图集
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']

    def get_queryset(self):
        """用户只能看到自己的记录"""
        return ScrapCar.objects.filter(user=self.request.user).select_related('user').order_by('-submit_time')

    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == 'list':
            return ScrapCarListSerializer
        return ScrapCarSerializer

    def get_serializer_context(self):
        """添加上下文"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        """创建时自动设置用户"""
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        """ 在第一页添加所有记录的状态统计信息"""
        # 先调用父类的list方法获取基础响应
        response = super().list(request, *args, **kwargs)

        # 获取当前页码，默认为第一页
        page = int(request.GET.get('page', 1))

        # 只有在第一页时才添加统计信息，避免重复计算
        if page == 1:
            # 使用聚合查询一次性获取所有状态的数量，更高效
            from django.db.models import Count

            status_counts = ScrapCar.objects.filter(user=request.user).values('status').annotate(count=Count('id'))

            # 初始化统计字典
            status_stats = {
                'total_count': 0,
                'pending_count': 0,
                'priced_count': 0,
                'confirmed_count': 0,
                'cancelled_count': 0,
            }

            # 填充统计信息
            for item in status_counts:
                status = item['status']
                count = item['count']
                status_stats['total_count'] += count

                if status == 'pending':
                    status_stats['pending_count'] = count
                elif status == 'priced':
                    status_stats['priced_count'] = count
                elif status == 'confirmed':
                    status_stats['confirmed_count'] = count
                elif status == 'cancelled':
                    status_stats['cancelled_count'] = count

            # 在响应中添加统计信息
            if response.data and isinstance(response.data, dict):
                response.data['status_stats'] = status_stats

        return response

    def create(self, request, *args, **kwargs):
        """创建报废车信息"""
        logger.info("接收到报废车数据: %s", request.data)

        # 直接使用 request.data，确保字段名称正确
        data = request.data.copy()

        # 打印接收到的数据用于调试
        print("接收到的原始数据:", data)

        # 处理 region 字段（前端发送的是数组，需要转换为字符串）
        if 'region' in data and isinstance(data['region'], list):
            data['region'] = ' '.join(data['region'])

        serializer = self.get_serializer(data=data)

        if not serializer.is_valid():
            logger.error("序列化器验证失败: %s", serializer.errors)
            return Response(
                {
                    'success': False,
                    'message': '数据验证失败',
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 保存时自动设置用户
            serializer.save(user=request.user)

            return Response(
                {
                    'success': True,
                    'message': '提交成功，我们将尽快与您联系',
                    'data': serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error("创建报废车记录时出错: %s", str(e))
            return Response(
                {
                    'success': False,
                    'message': '服务器内部错误',
                    'error': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """用户更新记录状态"""
        scrap_car = self.get_object()
        serializer = ScrapCarStatusUpdateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': '数据验证失败',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        new_status = serializer.validated_data['status']
        reason = serializer.validated_data.get('reason', '')

        # 验证用户只能修改自己的记录
        if scrap_car.user != request.user:
            return Response({
                'success': False,
                'message': '无权操作此记录'
            }, status=status.HTTP_403_FORBIDDEN)

        # 验证状态转换的合法性
        valid_transitions = {
            'priced': ['confirmed', 'cancelled'],
            'pending': ['cancelled']
        }

        current_status = scrap_car.status
        if current_status not in valid_transitions or new_status not in valid_transitions[current_status]:
            return Response({
                'success': False,
                'message': f'不能从{scrap_car.get_status_display()}状态变更为{dict(ScrapCar.STATUS_CHOICES).get(new_status, new_status)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 使用新的状态更新方法
            scrap_car.update_status(new_status, f'用户操作：{reason}', request.user)
            scrap_car.save()

            # 返回更新后的数据
            result_serializer = self.get_serializer(scrap_car)
            return Response({
                'success': True,
                'message': '状态更新成功',
                'data': result_serializer.data
            })

        except Exception as e:
            logger.error(f"更新状态失败: {str(e)}")
            return Response({
                'success': False,
                'message': '状态更新失败',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def detail_info(self, request, pk=None):
        """获取报废车详细信息"""
        try:
            scrap_car = self.get_object()

            # 验证用户只能查看自己的记录
            if scrap_car.user != request.user and not request.user.is_staff:
                return Response({
                    'success': False,
                    'message': '无权查看此记录'
                }, status=status.HTTP_403_FORBIDDEN)

            serializer = self.get_serializer(scrap_car)
            return Response({
                'success': True,
                'data': serializer.data
            })

        except Exception as e:
            logger.error(f"获取详情失败: {str(e)}")
            return Response({
                'success': False,
                'message': '获取详情失败',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CarImageUploadView(APIView):
    """
    车辆图片上传视图
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    @staticmethod
    def post(request, format=None):
        serializer = CarImageUploadSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'error': '图片验证失败',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        image_file = serializer.validated_data['image']

        try:
            # 生成唯一文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            unique_id = uuid.uuid4().hex[:8]
            file_extension = os.path.splitext(image_file.name)[1].lower()
            if not file_extension:
                file_extension = '.jpg'
            filename = f"car_image_{timestamp}_{unique_id}{file_extension}"

            # 保存路径
            save_path = os.path.join('scrap_cars', datetime.now().strftime('%Y/%m'), filename)

            # 保存文件
            saved_path = default_storage.save(save_path, ContentFile(image_file.read()))

            # 构建完整的URL - 修复URL生成逻辑
            if hasattr(settings, 'MEDIA_URL') and settings.MEDIA_URL:
                # 确保MEDIA_URL以/开头
                media_url = settings.MEDIA_URL
                if not media_url.startswith('/'):
                    media_url = '/' + media_url
                if not media_url.endswith('/'):
                    media_url += '/'

                # 构建完整URL
                if request.is_secure():
                    base_url = f'https://{request.get_host()}'
                else:
                    base_url = f'http://{request.get_host()}'

                image_url = f"{base_url}{media_url}{saved_path}"
            else:
                # 如果MEDIA_URL未设置，使用相对路径
                image_url = f"/media/{saved_path}"
                # 如果是相对路径，构建完整URL
                if request.is_secure():
                    base_url = f'https://{request.get_host()}'
                else:
                    base_url = f'http://{request.get_host()}'
                image_url = f"{base_url}{image_url}"

            logger.info(f"图片上传成功: {saved_path}, URL: {image_url}")

            return Response(
                {
                    'success': True,
                    'message': '图片上传成功',
                    'image_url': image_url,
                    'saved_path': saved_path,
                    'filename': filename
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error(f"图片上传错误: {str(e)}")
            return Response(
                {
                    'success': False,
                    'error': '图片上传失败，请稍后重试',
                    'details': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ScrapCarAdminViewSet(viewsets.ModelViewSet):
    """
    管理员报废车管理视图集
    """
    permission_classes = [IsAuthenticated]
    queryset = ScrapCar.objects.all().order_by('-submit_time')
    serializer_class = ScrapCarSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'region']

    def get_queryset(self):
        """管理员可以看到所有记录"""
        if self.request.user.is_staff:
            return ScrapCar.objects.all().select_related('user').order_by('-submit_time')
        return ScrapCar.objects.filter(user=self.request.user).order_by('-submit_time')

    @action(detail=True, methods=['post'])
    def set_price(self, request, pk=None):
        """设置预估价格和最终价格"""
        scrap_car = self.get_object()
        estimated_price = request.data.get('estimated_price')
        final_price = request.data.get('final_price')

        if estimated_price is not None:
            scrap_car.estimated_price = estimated_price
            # 状态更新已在模型的save方法中处理

        if final_price is not None:
            scrap_car.final_price = final_price

        scrap_car.save()

        serializer = self.get_serializer(scrap_car)
        return Response({
            'success': True,
            'message': '价格设置成功',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """更新状态 - 优化：同意时自动填充最终价格"""
        scrap_car = self.get_object()
        new_status = request.data.get('status')
        reason = request.data.get('reason', '')

        if new_status in dict(ScrapCar.STATUS_CHOICES):
            # 特殊处理：当状态变为confirmed且最终价格为null时，将预估价格设置为最终价格
            if new_status == 'confirmed' and scrap_car.final_price is None:
                if scrap_car.estimated_price is not None:
                    scrap_car.final_price = scrap_car.estimated_price
                    logger.info(
                        f"管理员操作-自动填充最终价格: 订单{scrap_car.id}的最终价格设置为预估价格{scrap_car.estimated_price}")

            # 使用新的状态更新方法
            scrap_car.update_status(new_status, f'管理员操作：{reason}', request.user)
            scrap_car.save()

            serializer = self.get_serializer(scrap_car)
            return Response({
                'success': True,
                'message': '状态更新成功',
                'data': serializer.data,
                'price_updated': scrap_car.final_price is not None and new_status == 'confirmed'  # 添加价格更新标志
            })
        else:
            return Response({
                'success': False,
                'message': '无效的状态'
            }, status=status.HTTP_400_BAD_REQUEST)


class PriceRuleViewSet(viewsets.ModelViewSet):
    """
    价格规则视图集
    """
    permission_classes = [IsAuthenticated]
    queryset = PriceRule.objects.filter(is_active=True)
    serializer_class = PriceRuleSerializer

    def get_queryset(self):
        """只有管理员可以管理价格规则"""
        if self.request.user.is_staff:
            return PriceRule.objects.all()
        return PriceRule.objects.filter(is_active=True)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reverse_geocode(request):
    """
    逆地理编码API
    """
    serializer = LocationSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': '参数验证失败',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    latitude = serializer.validated_data['latitude']
    longitude = serializer.validated_data['longitude']

    try:
        # 先检查缓存
        cached_location = LocationCache.objects.filter(
            latitude=latitude,
            longitude=longitude
        ).first()

        if cached_location:
            result_serializer = ReverseGeocodeSerializer(cached_location)
            return Response({
                'success': True,
                'data': result_serializer.data
            })

        # 调用腾讯地图逆地理编码服务
        api_key = getattr(settings, 'TENCENT_MAP_KEY', '')
        if not api_key:
            return Response({
                'success': False,
                'error': '地图服务未配置'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        url = 'https://apis.map.qq.com/ws/geocoder/v1/'
        params = {
            'location': f'{latitude},{longitude}',
            'key': api_key,
            'get_poi': 0
        }

        response = requests.get(url, params=params, timeout=10)
        result = response.json()

        if result.get('status') == 0:
            address_component = result['result']['address_component']
            full_address = result['result']['address']

            # 保存到缓存
            location_cache = LocationCache.objects.create(
                latitude=latitude,
                longitude=longitude,
                province=address_component.get('province', ''),
                city=address_component.get('city', ''),
                district=address_component.get('district', ''),
                address=full_address
            )

            result_serializer = ReverseGeocodeSerializer(location_cache)
            return Response({
                'success': True,
                'data': result_serializer.data
            })
        else:
            return Response({
                'success': False,
                'error': '地址解析失败'
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"逆地理编码异常: {str(e)}")
        return Response({
            'success': False,
            'error': '服务器内部错误'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class EvaluationMaterialViewSet(viewsets.ReadOnlyModelViewSet):
    """
    获取车辆评估材质列表（公开接口）
    """
    permission_classes = [AllowAny]
    queryset = EvaluationMaterial.objects.filter(is_active=True).order_by('sort_order', 'id')
    serializer_class = EvaluationMaterialSerializer