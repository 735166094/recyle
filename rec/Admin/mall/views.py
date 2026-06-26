from . import models
from rest_framework.request import Request
from typing import Optional
from django.db.models import Sum, Q, Count, Prefetch
from rest_framework import status, permissions, viewsets, mixins
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.decorators import api_view, permission_classes, action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.permissions import IsAuthenticated
from .models import (
    ProductCategory, Product, ProductSpecGroup, ProductSpecOption,
    PriceRule, ProductSku, Banner, GlobalSpecTemplate, CartItem
)
from .serializers import (
    ProductCategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateSerializer,
    ProductSpecGroupSerializer,
    ProductSpecOptionSerializer,
    ProductSkuSerializer,
    PriceRuleSerializer,
    BannerSerializer,
    ProductSpecSelectionSerializer,
    CalculatedPriceSerializer,
    GlobalSpecTemplateSerializer,
    CartItemSerializer,
    CartItemCreateSerializer,
    CartItemUpdateSerializer,
    CartCheckoutSerializer,
)


class ProductCategoryListView(ListAPIView):
    """商品分类列表API"""
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductCategorySerializer
    queryset = ProductCategory.objects.filter(is_active=True).order_by('sort_order')


class ProductListView(ListAPIView):
    """商品列表API"""
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'status', 'is_recommended', 'is_hot', 'is_new', 'use_global_specs']
    search_fields = ['name', 'description']
    ordering_fields = ['base_points_price', 'sales_count', 'rating', 'created_at', 'sort_order']
    ordering = ['-sort_order', '-created_at']

    def get_queryset(self):
        queryset = Product.objects.filter(status='active').prefetch_related('skus')

        # 添加类型提示，告诉IDE这个request是DRF的Request对象
        request: Request = self.request

        # 只显示有库存的商品
        in_stock = request.query_params.get('in_stock')
        if in_stock == 'true':
            queryset = queryset.filter(stock__gt=0)

        # 价格区间过滤
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(base_points_price__gte=min_price)
        if max_price:
            queryset = queryset.filter(base_points_price__lte=max_price)

        # 规格过滤
        has_specs = request.query_params.get('has_specs')
        if has_specs == 'true':
            queryset = queryset.filter(spec_groups__isnull=False).distinct()
        elif has_specs == 'false':
            queryset = queryset.filter(spec_groups__isnull=True)

        # 分类过滤（多个分类ID）
        category_ids = request.query_params.get('categories')
        if category_ids:
            try:
                # 支持逗号分隔的多个分类ID
                ids = [int(id.strip()) for id in category_ids.split(',') if id.strip()]
                if ids:
                    queryset = queryset.filter(category_id__in=ids)
            except (ValueError, AttributeError):
                pass

        # 推荐/热销/新品过滤
        is_recommended = request.query_params.get('is_recommended')
        if is_recommended == 'true':
            queryset = queryset.filter(is_recommended=True)
        elif is_recommended == 'false':
            queryset = queryset.filter(is_recommended=False)

        is_hot = request.query_params.get('is_hot')
        if is_hot == 'true':
            queryset = queryset.filter(is_hot=True)
        elif is_hot == 'false':
            queryset = queryset.filter(is_hot=False)

        is_new = request.query_params.get('is_new')
        if is_new == 'true':
            queryset = queryset.filter(is_new=True)
        elif is_new == 'false':
            queryset = queryset.filter(is_new=False)

        return queryset

    def list(self, request, *args, **kwargs):
        """重写list方法以自定义响应格式"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 200,
            'message': '获取商品列表成功',
            'data': {
                'results': serializer.data,
                'count': queryset.count()
            }
        })


class ProductDetailView(RetrieveAPIView):
    """商品详情API"""
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductDetailSerializer

    def get_queryset(self):
        return Product.objects.filter(status='active').prefetch_related(
            'spec_groups__options',
            'skus__spec_options',
            'price_rules',
            'reviews'
        )


class ProductCreateView(APIView):
    """商品创建API"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def post(request):
        serializer = ProductCreateSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save()
            return Response({
                'code': 201,
                'message': '商品创建成功',
                'data': ProductDetailSerializer(product).data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'code': 400,
            'message': '商品创建失败',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ProductSpecGroupsView(APIView):
    """商品规格组管理API"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request, product_id):
        """获取商品的规格组列表"""
        try:
            product = Product.objects.get(id=product_id)
            spec_groups = product.spec_groups.all()
            serializer = ProductSpecGroupSerializer(spec_groups, many=True)
            return Response({
                'code': 200,
                'message': '获取规格组成功',
                'data': serializer.data
            })
        except Product.DoesNotExist:
            return Response({
                'code': 404,
                'message': '商品不存在'
            }, status=status.HTTP_404_NOT_FOUND)

    @staticmethod
    def post(request, product_id):
        """为商品创建规格组"""
        try:
            product = Product.objects.get(id=product_id)
            serializer = ProductSpecGroupSerializer(data=request.data)
            if serializer.is_valid():
                spec_group = serializer.save(product=product)
                return Response({
                    'code': 201,
                    'message': '规格组创建成功',
                    'data': ProductSpecGroupSerializer(spec_group).data
                }, status=status.HTTP_201_CREATED)

            return Response({
                'code': 400,
                'message': '规格组创建失败',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Product.DoesNotExist:
            return Response({
                'code': 404,
                'message': '商品不存在'
            }, status=status.HTTP_404_NOT_FOUND)


class CalculatePriceView(APIView):
    """计算商品价格API"""
    permission_classes = [permissions.AllowAny]

    @staticmethod
    def post(request):
        """根据选择的规格计算商品价格"""
        # 使用 request.data 而不是 request.query_params（POST请求使用data）
        serializer = ProductSpecSelectionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'code': 400,
                'message': '参数错误',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        product_id = data['product_id']
        selected_specs = data['selected_specs']

        try:
            product = Product.objects.get(id=product_id)

            # 获取选中的规格选项
            selected_options = ProductSpecOption.objects.filter(
                id__in=selected_specs.values()
            ).select_related('spec_group')

            # 计算基础价格
            base_price = product.base_points_price
            total_increment = 0
            total_multiplier = 1.0

            spec_display_parts = []

            for option in selected_options:
                if option.is_available:
                    total_increment += option.price_increment
                    total_multiplier *= float(option.price_multiplier)
                    spec_display_parts.append(f"{option.spec_group.name}:{option.value}")

            # 计算价格
            calculated_price = int(base_price * total_multiplier) + total_increment
            final_price = calculated_price

            # 查找匹配的SKU
            matched_sku = None
            is_available = True
            stock = product.stock

            # 如果选择了所有规格组，尝试匹配SKU
            spec_groups_count = product.spec_groups.count()
            if len(selected_specs) == spec_groups_count:
                # 查找完全匹配的SKU
                for sku in product.skus.filter(is_active=True):
                    sku_option_ids = set(sku.spec_options.values_list('id', flat=True))
                    selected_option_ids = set(selected_specs.values())

                    if selected_option_ids == sku_option_ids:
                        matched_sku = sku
                        is_available = sku.is_available
                        stock = sku.stock
                        # 使用SKU的最终价格
                        final_price = sku.final_price
                        break

            # 应用价格规则
            if matched_sku:
                final_price = matched_sku.final_price

            spec_display = " ".join(spec_display_parts)

            result_data = {
                'product_id': product_id,
                'base_price': base_price,
                'calculated_price': calculated_price,
                'final_price': final_price,
                'selected_specs': selected_specs,
                'spec_display': spec_display,
                'matched_sku': matched_sku.id if matched_sku else None,
                'is_available': is_available,
                'stock': stock
            }

            result_serializer = CalculatedPriceSerializer(result_data)

            return Response({
                'code': 200,
                'message': '价格计算成功',
                'data': result_serializer.data
            })

        except Product.DoesNotExist:
            return Response({
                'code': 404,
                'message': '商品不存在'
            }, status=status.HTTP_404_NOT_FOUND)


class CheckSpecAvailabilityView(APIView):
    """检查规格可用性API"""
    permission_classes = [permissions.AllowAny]

    @staticmethod
    def post(request, product_id):
        """检查规格组合的可用性"""
        try:
            product = Product.objects.get(id=product_id)
            # POST请求使用request.data
            selected_specs = request.data.get('selected_specs', {})

            # 获取当前选中的规格选项
            selected_option_ids = list(selected_specs.values())
            selected_options = ProductSpecOption.objects.filter(
                id__in=selected_option_ids
            )

            # 获取所有规格组
            spec_groups = product.spec_groups.all()

            availability_info = []

            for spec_group in spec_groups:
                group_options = spec_group.options.filter(is_available=True)

                for option in group_options:
                    # 临时选择当前选项
                    temp_specs = selected_specs.copy()
                    temp_specs[spec_group.id] = option.id

                    # 检查是否存在包含这些规格的可用SKU
                    is_available = ProductSku.objects.filter(
                        product=product,
                        is_active=True,
                        stock__gt=0,
                        spec_options__id__in=temp_specs.values()
                    ).annotate(
                        match_count=Count('spec_options',
                                          filter=Q(spec_options__id__in=temp_specs.values()))
                    ).filter(match_count=len(temp_specs)).exists()

                    availability_info.append({
                        'spec_group_id': spec_group.id,
                        'spec_option_id': option.id,
                        'is_available': is_available,
                        'reason': '无可用SKU' if not is_available else None
                    })

            return Response({
                'code': 200,
                'message': '规格可用性检查完成',
                'data': availability_info
            })

        except Product.DoesNotExist:
            return Response({
                'code': 404,
                'message': '商品不存在'
            }, status=status.HTTP_404_NOT_FOUND)


class GlobalSpecTemplatesView(ListAPIView):
    """全局规格模板列表API"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GlobalSpecTemplateSerializer
    queryset = GlobalSpecTemplate.objects.filter(is_active=True).order_by('sort_order')


class ApplyGlobalSpecTemplateView(APIView):
    """应用全局规格模板到商品API"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def post(request, product_id):
        """将全局规格模板应用到商品"""
        try:
            product = Product.objects.get(id=product_id)
            template_id = request.data.get('template_id')

            if not template_id:
                return Response({
                    'code': 400,
                    'message': '请提供模板ID'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                template = GlobalSpecTemplate.objects.get(id=template_id, is_active=True)
            except GlobalSpecTemplate.DoesNotExist:
                return Response({
                    'code': 404,
                    'message': '规格模板不存在'
                }, status=status.HTTP_404_NOT_FOUND)

            # 创建规格组
            spec_group = ProductSpecGroup.objects.create(
                product=product,
                spec_type='global',
                global_template=template,
                group_type='main',
                name=template.name
            )

            # 创建规格选项
            for global_option in template.global_options.all():
                ProductSpecOption.objects.create(
                    spec_group=spec_group,
                    global_option=global_option,
                    value=global_option.value,
                    image=global_option.image,
                    color_code=global_option.color_code,
                    price_increment=global_option.base_price_increment,
                    sort_order=global_option.sort_order
                )

            # 更新商品使用全局规格标志
            product.use_global_specs = True
            product.save()

            return Response({
                'code': 200,
                'message': '全局规格模板应用成功',
                'data': ProductSpecGroupSerializer(spec_group).data
            })

        except Product.DoesNotExist:
            return Response({
                'code': 404,
                'message': '商品不存在'
            }, status=status.HTTP_404_NOT_FOUND)


class HotProductsView(ListAPIView):
    """热销商品列表API"""
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        # 添加类型提示消除警告
        request: Request = self.request

        # 支持分页参数
        page_size = request.query_params.get('page_size', '10')
        page = request.query_params.get('page', '1')

        try:
            page_size = int(page_size)
        except (ValueError, TypeError):
            page_size = 10

        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1

        queryset = Product.objects.filter(
            status='active',
            is_hot=True,
            stock__gt=0
        ).order_by('-sales_count')

        # 限制返回数量
        limit = request.query_params.get('limit')
        if limit:
            try:
                limit = int(limit)
                queryset = queryset[:limit]
            except (ValueError, TypeError):
                pass
        else:
            # 使用page_size进行分页
            start_index = (page - 1) * page_size
            end_index = page * page_size
            queryset = queryset[start_index:end_index]

        return queryset

    def list(self, request, *args, **kwargs):
        """重写list方法以返回所有热销商品"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # 获取总数量用于分页信息
        total_count = Product.objects.filter(
            status='active',
            is_hot=True,
            stock__gt=0
        ).count()

        return Response({
            'code': 200,
            'message': '获取热销商品成功',
            'data': {
                'results': serializer.data,
                'count': queryset.count(),
                'total_count': total_count
            }
        })


class NewProductsView(ListAPIView):
    """新品商品列表API"""
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        # 支持分页参数
        page_size = self.request.query_params.get('page_size', 10)
        try:
            page_size = int(page_size)
        except (ValueError, TypeError):
            page_size = 10

        queryset = Product.objects.filter(
            status='active',
            is_new=True,
            stock__gt=0
        ).order_by('-created_at')

        # 限制返回数量
        limit = self.request.query_params.get('limit')
        if limit:
            try:
                limit = int(limit)
                queryset = queryset[:limit]
            except (ValueError, TypeError):
                pass

        return queryset

    def list(self, request, *args, **kwargs):
        """重写list方法"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 200,
            'message': '获取新品商品成功',
            'data': {
                'results': serializer.data,
                'count': queryset.count()
            }
        })


class RecommendedProductsView(ListAPIView):
    """推荐商品列表API"""
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        # 支持分页参数
        page_size = self.request.query_params.get('page_size', 10)
        try:
            page_size = int(page_size)
        except (ValueError, TypeError):
            page_size = 10

        queryset = Product.objects.filter(
            status='active',
            is_recommended=True,
            stock__gt=0
        ).order_by('-sort_order')

        # 限制返回数量
        limit = self.request.query_params.get('limit')
        if limit:
            try:
                limit = int(limit)
                queryset = queryset[:limit]
            except (ValueError, TypeError):
                pass

        return queryset

    def list(self, request, *args, **kwargs):
        """重写list方法"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 200,
            'message': '获取推荐商品成功',
            'data': {
                'results': serializer.data,
                'count': queryset.count()
            }
        })


class BannerListView(ListAPIView):
    """轮播图列表API"""
    permission_classes = [permissions.AllowAny]
    serializer_class = BannerSerializer

    def get_queryset(self):
        from django.utils import timezone
        now = timezone.now()

        # 过滤有效的轮播图
        queryset = Banner.objects.filter(
            is_active=True
        ).filter(
            models.Q(start_time__isnull=True) | models.Q(start_time__lte=now)
        ).filter(
            models.Q(end_time__isnull=True) | models.Q(end_time__gte=now)
        ).order_by('sort_order', '-created_at')

        return queryset

    def list(self, request, *args, **kwargs):
        """重写list方法以返回统一格式"""
        queryset = self.filter_queryset(self.get_queryset())

        # 检查是否分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # 不分页的情况
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'code': 200,
            'message': '获取轮播图成功',
            'data': {
                'results': serializer.data,
                'count': queryset.count()
            }
        })


class ProductSkusView(ListAPIView):
    """商品SKU列表API"""
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductSkuSerializer

    def get_queryset(self):
        product_id = self.kwargs.get('product_id')
        return ProductSku.objects.filter(
            product_id=product_id,
            is_active=True
        ).prefetch_related('spec_options')


class ProductPriceRulesView(ListAPIView):
    """商品价格规则列表API"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PriceRuleSerializer

    def get_queryset(self):
        product_id = self.kwargs.get('product_id')
        return PriceRule.objects.filter(
            product_id=product_id,
            is_active=True
        ).order_by('priority')


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def product_spec_summary(request, product_id):
    """获取商品规格摘要API"""
    try:
        product = Product.objects.get(id=product_id)

        # 获取规格组信息
        spec_groups = product.spec_groups.all()
        spec_summary = []

        for group in spec_groups:
            options = group.options.filter(is_available=True)
            spec_summary.append({
                'id': group.id,
                'name': group.name,
                'group_type': group.group_type,
                'options_count': options.count(),
                'has_images': any(opt.image for opt in options),
                'has_colors': any(opt.color_code for opt in options)
            })

        # 获取SKU统计
        total_skus = product.skus.count()
        available_skus = product.skus.filter(is_active=True, stock__gt=0).count()

        return Response({
            'code': 200,
            'message': '获取规格摘要成功',
            'data': {
                'product_id': product_id,
                'product_name': product.name,
                'use_global_specs': product.use_global_specs,
                'spec_groups': spec_summary,
                'sku_stats': {
                    'total': total_skus,
                    'available': available_skus
                }
            }
        })

    except Product.DoesNotExist:
        return Response({
            'code': 404,
            'message': '商品不存在'
        }, status=status.HTTP_404_NOT_FOUND)


class CartItemViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin,
                      mixins.DestroyModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """购物车项视图集"""
    permission_classes = [IsAuthenticated]
    pagination_class = None  # 购物车不分页

    def get_serializer_class(self):
        if self.action == 'create':
            return CartItemCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CartItemUpdateSerializer
        elif self.action == 'retrieve':
            return CartItemSerializer
        return CartItemSerializer

    def get_queryset(self):
        """获取当前用户的购物车项"""
        queryset = CartItem.objects.filter(
            user=self.request.user,
            is_active=True
        ).select_related(
            'product', 'product_sku'
        ).order_by('-created_at')

        # 过滤可用商品
        available_only = self.request.query_params.get('available_only')
        if available_only == 'true':
            queryset = queryset.filter(
                Q(product__status='active', product__stock__gt=0) |
                Q(product_sku__is_active=True, product_sku__stock__gt=0)
            )

        return queryset

    def list(self, request, *args, **kwargs):
        """获取购物车列表"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # 计算统计信息
        total_quantity = queryset.aggregate(
            total=Sum('quantity')
        )['total'] or 0

        total_price = 0
        available_items = []
        unavailable_items = []

        for item in queryset:
            item_price = item.final_price * item.quantity
            total_price += item_price

            item_data = {
                'id': item.id,
                'product_name': item.actual_product.name,
                'quantity': item.quantity,
                'price': item.final_price,
                'is_available': item.is_available,
                'reason': '库存不足' if item.stock < item.quantity else '商品已下架'
            }

            if item.is_available:
                available_items.append(item_data)
            else:
                unavailable_items.append(item_data)

        return Response({
            'code': 200,
            'message': '获取购物车成功',
            'data': {
                'items': serializer.data,
                'stats': {
                    'total_quantity': total_quantity,
                    'total_price': total_price,
                    'item_count': queryset.count()
                },
                'available_items': available_items,
                'unavailable_items': unavailable_items
            }
        })

    def perform_create(self, serializer):
        """创建购物车项"""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def count(self, request):
        """获取购物车商品总数"""
        total_count = self.get_queryset().aggregate(
            total_quantity=Sum('quantity')
        )['total_quantity'] or 0

        return Response({
            'code': 200,
            'message': '获取购物车数量成功',
            'data': {
                'total_count': total_count
            }
        })

    @action(detail=False, methods=['post'])
    def batch_update(self, request):
        """批量更新购物车项"""
        cart_updates = request.data.get('updates', [])

        if not cart_updates:
            return Response({
                'code': 400,
                'message': '请提供要更新的购物车项'
            }, status=status.HTTP_400_BAD_REQUEST)

        updated_items = []
        failed_items = []

        for update in cart_updates:
            cart_item_id = update.get('id')
            quantity = update.get('quantity')

            if not cart_item_id or not quantity:
                continue

            try:
                cart_item = CartItem.objects.get(
                    id=cart_item_id,
                    user=request.user,
                    is_active=True
                )

                if quantity <= 0:
                    cart_item.delete()
                    continue

                # 验证库存
                max_stock = cart_item.stock
                if quantity > max_stock:
                    failed_items.append({
                        'id': cart_item_id,
                        'reason': f'库存不足，最大可购买: {max_stock}'
                    })
                    continue

                cart_item.quantity = quantity
                cart_item.save()
                updated_items.append(cart_item_id)

            except CartItem.DoesNotExist:
                failed_items.append({
                    'id': cart_item_id,
                    'reason': '购物车项不存在'
                })
                continue

        return Response({
            'code': 200,
            'message': '批量更新完成',
            'data': {
                'updated_items': updated_items,
                'failed_items': failed_items
            }
        })

    @action(detail=False, methods=['post'])
    def batch_delete(self, request):
        """批量删除购物车项"""
        cart_item_ids = request.data.get('ids', [])

        if not cart_item_ids:
            return Response({
                'code': 400,
                'message': '请选择要删除的商品'
            }, status=status.HTTP_400_BAD_REQUEST)

        deleted_count, _ = CartItem.objects.filter(
            id__in=cart_item_ids,
            user=request.user
        ).delete()

        return Response({
            'code': 200,
            'message': f'成功删除{deleted_count}件商品'
        })

    @action(detail=False, methods=['post'])
    def clear(self, request):
        """清空购物车"""
        deleted_count, _ = CartItem.objects.filter(
            user=request.user,
            is_active=True
        ).delete()

        return Response({
            'code': 200,
            'message': f'已清空购物车，共删除{deleted_count}件商品'
        })

    # mall/views.py (修改部分)
    @action(detail=False, methods=['post'])
    def checkout(self, request):
        """购物车结算"""
        serializer = CartCheckoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'code': 400,
                'message': '参数错误',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        cart_item_ids = data['cart_item_ids']
        address_id = data.get('address_id')

        # 获取要结算的购物车项
        cart_items = CartItem.objects.filter(
            id__in=cart_item_ids,
            user=request.user
        )

        if not cart_items.exists():
            return Response({
                'code': 400,
                'message': '没有找到要结算的商品'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 验证所有购物车项是否可用
        unavailable_items = []
        for item in cart_items:
            if not item.is_available:
                unavailable_items.append({
                    'id': item.id,
                    'product_name': item.actual_product.name,
                    'reason': '库存不足' if item.stock < item.quantity else '商品已下架'
                })

        if unavailable_items:
            return Response({
                'code': 400,
                'message': '部分商品不可用',
                'data': {
                    'unavailable_items': unavailable_items
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # 判断是否需要地址：检查购物车中是否有实体商品
        needs_address = False
        for item in cart_items:
            product = item.actual_product
            # 这里需要根据商品类型判断是否是实体商品
            # 假设商品模型中有 is_physical 字段来判断是否是实体商品
            # 或者使用 category 来判断某些分类是虚拟商品
            # 如果没有明确的字段，可以暂时使用商品分类判断

            # 方法1: 如果商品有 is_physical 字段
            # if hasattr(product, 'is_physical') and product.is_physical:
            #     needs_address = True
            #     break

            # 方法2: 如果某些分类是虚拟商品
            # 假设分类ID为 1,2 的是虚拟商品（如优惠券、虚拟卡券等）
            # if product.category and product.category.id not in [1, 2]:
            #     needs_address = True
            #     break

            # 方法3: 默认情况下，假设所有商品都需要地址
            # 为了兼容现有代码，暂时设置所有商品都需要地址
            # 等您确定虚拟商品的标识方式后，再修改这里的逻辑
            needs_address = True
            break

        # 如果需要地址，验证收货地址
        address = None
        if needs_address:
            if not address_id:
                return Response({
                    'code': 400,
                    'message': '实体商品需要收货地址'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                from user.models import UserAddress
                address = UserAddress.objects.get(id=address_id, user=request.user, is_default=True)
            except UserAddress.DoesNotExist:
                return Response({
                    'code': 404,
                    'message': '收货地址不存在或不是默认地址'
                }, status=status.HTTP_404_NOT_FOUND)

        # 计算总金额
        total_price = sum(item.final_price * item.quantity for item in cart_items)
        total_quantity = sum(item.quantity for item in cart_items)

        # 创建订单逻辑
        # 这里可以添加创建订单的代码
        # 注意：创建订单时，如果是虚拟商品，订单中的地址信息可以为空

        # 返回结算信息
        response_data = {
            'code': 200,
            'message': '结算信息获取成功',
            'data': {
                'cart_items': CartItemSerializer(cart_items, many=True).data,
                'address': {
                    'id': address.id if address else None,
                    'name': address.receiver_name if address else None,
                    'phone': address.receiver_phone if address else None,
                    'full_address': f"{address.province}{address.city}{address.district}{address.detail_address}" if address else None
                } if address else None,
                'total_price': total_price,
                'total_quantity': total_quantity,
                'needs_address': needs_address,  # 告诉前端是否需要地址
                'remark': data.get('remark', '')
            }
        }

        return Response(response_data)

    def retrieve(self, request, *args, **kwargs):
        """获取单个购物车项详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response({
            'code': 200,
            'message': '获取购物车项详情成功',
            'data': serializer.data
        })


class CartStatsView(APIView):
    """购物车统计API"""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get(request):
        """获取购物车统计信息"""
        cart_items = CartItem.objects.filter(
            user=request.user,
            is_active=True
        )

        # 使用正确的 Sum 函数
        total_quantity = cart_items.aggregate(
            total=Sum('quantity')
        )['total'] or 0

        total_price = 0
        for item in cart_items:
            total_price += item.final_price * item.quantity

        return Response({
            'code': 200,
            'message': '获取购物车统计成功',
            'data': {
                'total_quantity': total_quantity,
                'total_price': total_price,
                'item_count': cart_items.count()
            }
        })
