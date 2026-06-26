# points/views.py
from rest_framework import status, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Sum, Count, Q, F
from django.db import transaction
import logging
import pytz
from datetime import datetime, timedelta, time as datetime_time
from django.utils import timezone

from django.db.models.functions import TruncDate
from .models import PointsRule, PointsRecord, UserDailyPoints, PointsTransaction, UserMonthlySummary
from .serializers import (
    PointsRuleSerializer, PointsRecordSerializer, GreenLifeUploadSerializer,
    PointsTransactionSerializer, MonthlySummarySerializer,
    PointsSummarySerializer, ExchangePointsSerializer
)
from user.models import User, UserAddress
from .services import PointsService

logger = logging.getLogger(__name__)


class PointsRulesView(APIView):
    """积分规则列表API"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        """获取积分规则列表"""
        rules = PointsRule.objects.filter(is_active=True).order_by('sort_order')
        serializer = PointsRuleSerializer(rules, many=True)

        return Response({
            'code': 200,
            'message': '获取积分规则成功',
            'data': serializer.data
        })


class PointsSummaryView(APIView):
    """积分汇总信息API"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        """获取积分汇总信息"""
        user = request.user
        today = timezone.now().date()

        # 转换为本地时间（北京时间）进行计算
        local_tz = pytz.timezone('Asia/Shanghai')
        now_local = timezone.now().astimezone(local_tz)
        today_local = now_local.date()

        # 获取今天UTC时间范围
        start_local = local_tz.localize(
            datetime.combine(today_local, datetime_time.min)
        )
        end_local = local_tz.localize(
            datetime.combine(today_local, datetime_time.max)
        )
        start_utc = start_local.astimezone(pytz.UTC)
        end_utc = end_local.astimezone(pytz.UTC)

        month_start = today_local.replace(day=1)

        # 计算连续签到天数
        continuous_days = DailySignView.calculate_continuous_days_v2(user, today_local)

        # 今日积分统计（使用本地时间）
        today_records = PointsRecord.objects.filter(
            user=user,
            created_at__gte=start_utc,
            created_at__lte=end_utc
        ).aggregate(
            earned=Sum('points_change', filter=Q(points_change__gt=0)),
            consumed=Sum('points_change', filter=Q(points_change__lt=0))
        )

        # 本月积分统计（从本月1日开始）
        month_start_local = local_tz.localize(
            datetime.combine(month_start, datetime_time.min)
        )
        month_start_utc = month_start_local.astimezone(pytz.UTC)

        month_records = PointsRecord.objects.filter(
            user=user,
            created_at__gte=month_start_utc
        ).aggregate(
            earned=Sum('points_change', filter=Q(points_change__gt=0)),
            consumed=Sum('points_change', filter=Q(points_change__lt=0))
        )

        # 绿色生活统计（最近30天）
        thirty_days_ago = today_local - timedelta(days=30)
        thirty_days_local = local_tz.localize(
            datetime.combine(thirty_days_ago, datetime_time.min)
        )
        thirty_days_utc = thirty_days_local.astimezone(pytz.UTC)

        green_stats = PointsRecord.objects.filter(
            user=user,
            green_type__isnull=False,
            points_change__gt=0,  # 只统计获取积分的记录
            created_at__gte=thirty_days_utc
        ).aggregate(
            total_green=Sum('points_change'),
            transport_days=Count('id', filter=Q(green_type='transport')),
            food_days=Count('id', filter=Q(green_type='food')),
            walk_steps=Sum('steps_count', filter=Q(green_type='walk')),
            learning_count=Count('id', filter=Q(green_type='learning'))
        )

        # 绿色生活总天数（去重）
        green_dates = PointsRecord.objects.filter(
            user=user,
            green_type__isnull=False,
            points_change__gt=0,
            created_at__gte=thirty_days_utc
        ).dates('created_at', 'day').distinct().count()

        # 达标状态
        transport_qualified = (green_stats['transport_days'] or 0) >= 15
        food_qualified = (green_stats['food_days'] or 0) >= 15

        data = {
            'total_points': user.points,
            'today_earned': today_records['earned'] or 0,
            'today_consumed': abs(today_records['consumed'] or 0),
            'month_earned': month_records['earned'] or 0,
            'month_consumed': abs(month_records['consumed'] or 0),
            'green_points': green_stats['total_green'] or 0,
            'available_points': user.points,

            'continuous_days': continuous_days,  # 连续签到天数

            'green_days': green_dates,
            'transport_days': green_stats['transport_days'] or 0,
            'food_days': green_stats['food_days'] or 0,
            'walk_steps': green_stats['walk_steps'] or 0,
            'learning_count': green_stats['learning_count'] or 0,

            'transport_qualified': transport_qualified,
            'food_qualified': food_qualified,
            'walk_qualified': (green_stats['walk_steps'] or 0) > 0,  # 有步行记录即为达标
        }

        serializer = PointsSummarySerializer(data)
        return Response({
            'code': 200,
            'message': '获取积分汇总成功',
            'data': serializer.data
        })


class DailySignView(APIView):
    """每日签到API - 严格限制每天只能签到一次"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get_local_date_range():
        """
        获取今天本地日期的UTC时间范围
        例如：北京时间 2025-12-31 的UTC范围是 2025-12-30 16:00:00 到 2025-12-31 16:00:00
        """
        # 获取当前本地时间（北京时间）
        local_tz = pytz.timezone('Asia/Shanghai')
        now_local = timezone.now().astimezone(local_tz)
        today_local = now_local.date()

        # 获取今天开始和结束的本地时间
        start_local = local_tz.localize(
            datetime.combine(today_local, datetime_time.min)
        )
        end_local = local_tz.localize(
            datetime.combine(today_local, datetime_time.max)
        )

        # 转换为UTC时间
        start_utc = start_local.astimezone(pytz.UTC)
        end_utc = end_local.astimezone(pytz.UTC)

        return today_local, start_utc, end_utc

    @staticmethod
    def get_today_sign(user):
        """
        检查用户今天是否已签到（使用精确的时间范围）
        """
        try:
            today_local, start_utc, end_utc = DailySignView.get_local_date_range()

            # 查询在本地今天时间范围内的签到记录
            today_sign = PointsRecord.objects.filter(
                user=user,
                points_type='sign',
                created_at__gte=start_utc,
                created_at__lte=end_utc
            ).first()

            return today_sign, today_local

        except Exception as e:
            logger.error(f"获取今日签到记录失败: {str(e)}")
            return None, None

    @staticmethod
    def get(request):
        """获取今日签到状态"""
        user = request.user

        # 使用时间范围查询
        today_sign, today_local = DailySignView.get_today_sign(user)

        if today_local is None:
            return Response({
                'code': 500,
                'message': '获取签到状态失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 计算连续签到天数（修复版本）
        continuous_days = DailySignView.calculate_continuous_days_v2(user, today_local)

        # 获取签到规则
        sign_rule = PointsRule.objects.filter(
            rule_type='sign',
            is_active=True
        ).first()

        base_points = sign_rule.points_value if sign_rule else 10

        # 下一个奖励（如果今天没签到）
        next_reward = 0
        if not today_sign:
            next_reward = DailySignView.calculate_continuous_reward(continuous_days + 1)

        data = {
            'today_checked': bool(today_sign),
            'checked_time': today_sign.created_at.astimezone(
                pytz.timezone('Asia/Shanghai')
            ).strftime('%H:%M:%S') if today_sign else None,
            'points_earned': today_sign.points_change if today_sign else 0,
            'continuous_days': continuous_days,
            'next_reward': base_points + next_reward,
            'today_points': base_points,
            'extra_points': next_reward,
            'can_sign': not bool(today_sign),
            'message': '今日已签到' if today_sign else '可以签到',
            'today_date': today_local.isoformat(),
            'utc_now': timezone.now().isoformat()
        }

        logger.info(
            f"用户 {user.id} 获取签到状态：已签到={bool(today_sign)}，连续{continuous_days}天，今天日期={today_local}")

        return Response({
            'code': 200,
            'message': '获取签到状态成功',
            'data': data
        })

    @staticmethod
    def post(request):
        """执行每日签到  """
        user = request.user

        # 1. 检查今天是否已签到
        today_sign, today_local = DailySignView.get_today_sign(user)

        if today_local is None:
            return Response({
                'code': 500,
                'message': '系统错误，请稍后重试'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if today_sign:
            logger.warning(f"用户 {user.id} 今天已经签到过，签到时间：{today_sign.created_at}")
            return Response({
                'code': 400,
                'message': '今天已经签到过了',
                'data': {
                    'already_signed': True,
                    'signed_time': today_sign.created_at.astimezone(
                        pytz.timezone('Asia/Shanghai')
                    ).strftime('%Y-%m-%d %H:%M:%S'),
                    'points': today_sign.points_change,
                    'today_date': today_local.isoformat()
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # 2. 获取签到规则
        sign_rule = PointsRule.objects.filter(
            rule_type='sign',
            is_active=True
        ).first()

        if not sign_rule:
            base_points = 10
            logger.warning(f"用户 {user.id} 签到：使用默认规则")
        else:
            base_points = sign_rule.points_value

        # 3. 计算连续签到奖励
        continuous_days = DailySignView.calculate_continuous_days_v2(user, today_local)
        extra_points = DailySignView.calculate_continuous_reward(continuous_days + 1)
        total_points = base_points + extra_points

        try:
            with transaction.atomic():
                # 4. 更新用户积分
                user.points = F('points') + total_points
                user.save(update_fields=['points'])
                user.refresh_from_db()

                # 获取当前UTC时间
                now_utc = timezone.now()

                # 5. 创建签到记录
                points_record = PointsRecord.objects.create(
                    user=user,
                    points_type='sign',
                    points_change=total_points,
                    current_points=user.points,
                    points_rule=sign_rule,
                    description=f"每日签到，获得{base_points}积分" +
                                (f"，连续签到奖励{extra_points}积分" if extra_points > 0 else ""),
                    is_verified=True,
                    verified_at=now_utc
                )

                logger.info(f"创建签到记录：ID={points_record.id}, 时间={now_utc}, 本地日期={today_local}")

                # 6. 更新每日统计
                daily_stats, _ = UserDailyPoints.objects.get_or_create(
                    user=user,
                    date=today_local,  # 使用本地日期
                    defaults={'total_points': user.points}
                )
                daily_stats.sign_points += total_points
                daily_stats.total_points = user.points
                daily_stats.save()

                # 7. 计算新的连续签到天数
                new_continuous_days = continuous_days + 1

                data = {
                    'points': total_points,
                    'base_points': base_points,
                    'extra_points': extra_points,
                    'total_points': user.points,
                    'continuous_days': new_continuous_days,
                    'message': '签到成功' + (f'，连续签到奖励{extra_points}积分' if extra_points > 0 else ''),
                    'already_signed': False,
                    'signed_time': now_utc.astimezone(
                        pytz.timezone('Asia/Shanghai')
                    ).strftime('%Y-%m-%d %H:%M:%S'),
                    'today_date': today_local.isoformat(),
                    'record_id': points_record.id
                }

                logger.info(
                    f"用户 {user.id} 签到成功：获得{total_points}积分，连续{new_continuous_days}天，记录ID={points_record.id}")

                return Response({
                    'code': 200,
                    'message': '签到成功',
                    'data': data
                })

        except Exception as e:
            logger.error(f"用户 {user.id} 签到失败: {str(e)}", exc_info=True)
            return Response({
                'code': 500,
                'message': f'签到失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @staticmethod
    def calculate_continuous_days_v2(user, today_local):
        """
        使用时间范围计算连续签到天数（修复版）
        """
        try:
            # 获取最近7天的本地日期
            dates_to_check = []
            for i in range(7):
                check_date = today_local - timedelta(days=i)
                dates_to_check.append(check_date)

            # 为每个日期获取UTC时间范围
            local_tz = pytz.timezone('Asia/Shanghai')

            continuous_days = 0

            for check_date in dates_to_check:
                # 获取这一天的UTC时间范围
                start_local = local_tz.localize(
                    datetime.combine(check_date, datetime_time.min)
                )
                end_local = local_tz.localize(
                    datetime.combine(check_date, datetime_time.max)
                )

                start_utc = start_local.astimezone(pytz.UTC)
                end_utc = end_local.astimezone(pytz.UTC)

                # 检查这一天是否有签到记录
                has_sign = PointsRecord.objects.filter(
                    user=user,
                    points_type='sign',
                    created_at__gte=start_utc,
                    created_at__lte=end_utc
                ).exists()

                if has_sign:
                    continuous_days += 1
                else:
                    break

            logger.info(f"用户 {user.id} 连续签到计算：今天={today_local}，连续{continuous_days}天")

            return continuous_days

        except Exception as e:
            logger.error(f"计算连续签到天数失败: {str(e)}")
            return 0

    @staticmethod
    def calculate_continuous_reward(continuous_days):
        """计算连续签到奖励"""
        if continuous_days >= 7:
            return 10  # 连续7天奖励10积分
        elif continuous_days >= 3:
            return 5  # 连续3天奖励5积分
        else:
            return 0


class GreenLifeView(APIView):
    """绿色生活API"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        """获取绿色生活规则"""
        green_rules = PointsRule.objects.filter(
            green_type__isnull=False,
            is_active=True
        ).order_by('sort_order')

        serializer = PointsRuleSerializer(green_rules, many=True)

        return Response({
            'code': 200,
            'message': '获取绿色生活规则成功',
            'data': serializer.data
        })

    @staticmethod
    def post(request):
        """提交绿色生活记录"""
        serializer = GreenLifeUploadSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({
                'code': 400,
                'message': '参数错误',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        green_type = serializer.validated_data['green_type']
        user = request.user

        try:
            # 获取对应规则
            rule = PointsRule.objects.get(
                green_type=green_type,
                is_active=True
            )

            today = timezone.now().date()

            # 检查今日是否已提交
            today_records = PointsRecord.objects.filter(
                user=user,
                green_type=green_type,
                created_at__date=today
            )

            if today_records.exists():
                return Response({
                    'code': 400,
                    'message': '今天已经提交过了'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 检查规则限制
            if rule.daily_limit > 0:
                today_count = today_records.count()
                if today_count >= rule.daily_limit:
                    return Response({
                        'code': 400,
                        'message': f'今日已达到{rule.daily_limit}次上限'
                    }, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                # 计算积分
                points = rule.points_value

                # 特殊处理：低碳行走按步数计算
                if green_type == 'walk':
                    steps = serializer.validated_data.get('steps_count', 0)
                    if steps > 0:
                        # 1000步=1分，上限100分
                        walk_points = min(steps // 1000, 100)
                        points = walk_points if rule.points_value == 0 else min(rule.points_value, walk_points)

                # 创建记录
                record = PointsRecord.objects.create(
                    user=user,
                    points_rule=rule,
                    points_type='task',
                    green_type=green_type,
                    points_change=points,
                    upload_image=serializer.validated_data.get('upload_image'),
                    certificate_image=serializer.validated_data.get('certificate_image'),
                    steps_count=serializer.validated_data.get('steps_count', 0),
                    days_count=serializer.validated_data.get('days_count', 0),
                    description=serializer.validated_data.get('description', ''),
                    remark=f"绿色生活：{rule.get_green_type_display()}"
                )

                # 更新每日统计
                daily_stats, _ = UserDailyPoints.objects.get_or_create(
                    user=user,
                    date=today
                )
                daily_stats.green_points += points
                daily_stats.total_points += points

                # 更新具体统计
                if green_type == 'transport':
                    daily_stats.transport_days += 1
                elif green_type == 'food':
                    daily_stats.food_days += 1
                elif green_type == 'walk':
                    daily_stats.walk_steps += serializer.validated_data.get('steps_count', 0)
                elif green_type == 'learning':
                    daily_stats.learning_count += 1

                daily_stats.save()

            return Response({
                'code': 200,
                'message': '提交成功',
                'data': {
                    'points': points,
                    'total_points': user.points
                }
            })

        except PointsRule.DoesNotExist:
            logger.error(f"绿色生活规则不存在: {green_type}")
            return Response({
                'code': 404,
                'message': '该绿色生活规则不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"提交绿色生活记录失败: {str(e)}", exc_info=True)
            return Response({
                'code': 500,
                'message': '提交失败',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PointsRecordsPagination(PageNumberPagination):
    """积分记录分页器"""
    page_size = 20  # 默认每页显示20条
    page_size_query_param = 'page_size'  # 允许客户端指定每页数量
    max_page_size = 100  # 最大每页数量
    page_query_param = 'page'  # 页码参数名


class PointsRecordsView(ListAPIView):
    """积分记录列表API（带分页）"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PointsRecordSerializer
    pagination_class = PointsRecordsPagination  # 使用自定义分页器

    def get_queryset(self):
        """获取查询集，支持过滤"""
        user = self.request.user
        queryset = PointsRecord.objects.filter(user=user)

        # 查询参数过滤
        points_type = self.request.query_params.get('points_type')
        green_type = self.request.query_params.get('green_type')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if points_type:
            queryset = queryset.filter(points_type=points_type)
        if green_type:
            queryset = queryset.filter(green_type=green_type)
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.order_by('-created_at')

    def list(self, request, *args, **kwargs):
        """获取积分记录列表（分页）"""
        try:
            queryset = self.filter_queryset(self.get_queryset())

            # 获取分页数据
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)

                # 获取统计信息
                stats = self.calculate_statistics(queryset)

                return self.get_paginated_response({
                    'code': 200,
                    'message': '获取积分记录成功',
                    'data': serializer.data,
                    'stats': stats,
                    'total_records': queryset.count()
                })

            # 如果没有分页，返回所有数据
            serializer = self.get_serializer(queryset, many=True)
            stats = self.calculate_statistics(queryset)

            return Response({
                'code': 200,
                'message': '获取积分记录成功',
                'data': serializer.data,
                'stats': stats,
                'total_records': queryset.count()
            })

        except Exception as e:
            logger.error(f"获取积分记录异常: {str(e)}", exc_info=True)
            return Response({
                'code': 500,
                'message': '获取积分记录失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def calculate_statistics(self, queryset):
        """计算统计信息"""
        from django.db.models import Sum

        # 总获得积分
        total_earned = queryset.filter(points_change__gt=0).aggregate(
            total=Sum('points_change')
        )['total'] or 0

        # 总消费积分
        total_consumed = abs(queryset.filter(points_change__lt=0).aggregate(
            total=Sum('points_change')
        )['total'] or 0)

        # 今日获得
        today = timezone.now().date()
        today_earned = queryset.filter(
            created_at__date=today,
            points_change__gt=0
        ).aggregate(total=Sum('points_change'))['total'] or 0

        # 今日消费
        today_consumed = abs(queryset.filter(
            created_at__date=today,
            points_change__lt=0
        ).aggregate(total=Sum('points_change'))['total'] or 0)

        return {
            'total_earned': total_earned,
            'total_consumed': total_consumed,
            'today_earned': today_earned,
            'today_consumed': today_consumed,
            'balance': total_earned - total_consumed
        }


class ExchangePointsView(APIView):
    """积分兑换API"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def post(request):
        """积分兑换商品"""
        serializer = ExchangePointsSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({
                'code': 400,
                'message': '参数错误',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        product_id = serializer.validated_data['product_id']
        product_name = serializer.validated_data['product_name']
        product_points = serializer.validated_data['product_points']
        address_id = serializer.validated_data['address_id']
        quantity = serializer.validated_data['quantity']

        total_points = product_points * quantity

        # 检查积分是否足够
        if user.points < total_points:
            return Response({
                'code': 400,
                'message': f'积分不足，需要{total_points}积分，当前有{user.points}积分'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 检查收货地址
        try:
            address = UserAddress.objects.get(id=address_id, user=user)
        except UserAddress.DoesNotExist:
            return Response({
                'code': 404,
                'message': '收货地址不存在'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            with transaction.atomic():
                # 生成交易流水号
                transaction_no = f"PTS{timezone.now().strftime('%Y%m%d%H%M%S')}{user.id:06d}"

                # 创建交易记录
                PointsTransaction.objects.create(
                    transaction_no=transaction_no,
                    user=user,
                    transaction_type='redeem',
                    points_amount=-total_points,
                    product_id=product_id,
                    product_name=product_name,
                    product_points=product_points,
                    redeem_address=address,
                    status='pending',
                    remark=f"兑换{product_name} ×{quantity}"
                )

                # 创建消费记录
                PointsRecord.objects.create(
                    user=user,
                    points_type='consume',
                    points_change=-total_points,
                    related_id=transaction_no,
                    description=f"兑换商品：{product_name} ×{quantity}",
                    remark=f"交易号：{transaction_no}"
                )

            return Response({
                'code': 200,
                'message': '兑换申请已提交',
                'data': {
                    'transaction_no': transaction_no,
                    'points': total_points,
                    'remaining_points': user.points,
                    'status': 'pending'
                }
            })

        except Exception as e:
            logger.error(f"积分兑换失败: {str(e)}", exc_info=True)
            return Response({
                'code': 500,
                'message': '兑换失败',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MonthlySummaryView(APIView):
    """月度汇总API"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        """获取月度汇总信息"""
        user = request.user
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not year or not month:
            # 默认查询最近3个月
            today = timezone.now().date()
            summaries = UserMonthlySummary.objects.filter(
                user=user,
                created_at__date__gte=today - timedelta(days=90)
            ).order_by('-year', '-month')
        else:
            summaries = UserMonthlySummary.objects.filter(
                user=user,
                year=year,
                month=month
            )

        serializer = MonthlySummarySerializer(summaries, many=True)

        return Response({
            'code': 200,
            'message': '获取月度汇总成功',
            'data': serializer.data
        })


class GreenLifeStatsView(APIView):
    """绿色生活统计API"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        """获取绿色生活统计数据"""
        user = request.user

        # 转换为本地时间
        local_tz = pytz.timezone('Asia/Shanghai')
        now_local = timezone.now().astimezone(local_tz)
        today_local = now_local.date()
        month_start = today_local.replace(day=1)

        # 获取本月UTC时间范围
        month_start_local = local_tz.localize(
            datetime.combine(month_start, datetime_time.min)
        )
        month_start_utc = month_start_local.astimezone(pytz.UTC)

        # 本月绿色生活统计
        month_green = PointsRecord.objects.filter(
            user=user,
            green_type__isnull=False,
            points_change__gt=0,
            created_at__gte=month_start_utc
        )

        # 按类型统计
        transport_days = month_green.filter(green_type='transport').count()
        food_days = month_green.filter(green_type='food').count()
        walk_steps = month_green.filter(green_type='walk').aggregate(
            steps=Sum('steps_count')
        )['steps'] or 0
        learning_count = month_green.filter(green_type='learning').count()

        # 达标状态
        is_transport_qualified = transport_days >= 15
        is_food_qualified = food_days >= 15

        data = {
            'month': f"{today_local.year}年{today_local.month}月",
            'transport_days': transport_days,
            'food_days': food_days,
            'walk_steps': walk_steps,
            'learning_count': learning_count,
            'is_transport_qualified': is_transport_qualified,
            'is_food_qualified': is_food_qualified,
            'transport_target': 15,
            'food_target': 15,
            'remaining_transport_days': max(0, 15 - transport_days),
            'remaining_food_days': max(0, 15 - food_days)
        }

        return Response({
            'code': 200,
            'message': '获取绿色生活统计成功',
            'data': data
        })


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def batch_award_points(request):
    """批量奖励积分 """
    user_ids = request.data.get('user_ids', [])
    points = request.data.get('points', 0)
    reason = request.data.get('reason', '系统奖励')

    if not user_ids or points <= 0:
        return Response({
            'code': 400,
            'message': '参数错误'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        users = User.objects.filter(id__in=user_ids, is_active=True)

        with transaction.atomic():
            for user in users:
                PointsRecord.objects.create(
                    user=user,
                    points_type='system_bonus',
                    points_change=points,
                    description=reason
                )

        return Response({
            'code': 200,
            'message': f'成功为{users.count()}位用户发放积分'
        })

    except Exception as e:
        logger.error(f"批量奖励积分失败: {str(e)}", exc_info=True)
        return Response({
            'code': 500,
            'message': '批量奖励积分失败',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserPointsStatusView(APIView):
    """用户积分状态检查API"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        """检查用户各项任务状态"""
        from django.db.models import Sum, Count

        user = request.user
        today = timezone.now().date()

        # 检查今日签到
        today_sign = PointsRecord.objects.filter(
            user=user,
            points_type='sign',
            created_at__date=today
        ).first()

        # 检查今日绿色生活
        green_today = PointsRecord.objects.filter(
            user=user,
            green_type__isnull=False,
            created_at__date=today
        ).values('green_type').distinct()

        # 检查本月达标情况
        month_start = today.replace(day=1)
        green_month = PointsRecord.objects.filter(
            user=user,
            green_type__in=['transport', 'food'],
            points_change__gt=0,
            created_at__date__gte=month_start
        ).values('green_type').annotate(
            days=Count('created_at__date', distinct=True)
        )

        # 构建响应数据
        status_data = {
            'sign': {
                'today_checked': bool(today_sign),
                'checked_time': today_sign.created_at if today_sign else None,
                'points': today_sign.points_change if today_sign else 0
            },
            'green_life': {
                'today_submitted': list(green_today),
                'month_stats': {item['green_type']: item['days'] for item in green_month}
            },
            'points_summary': {
                'total': user.points,
                'available': user.points,
                'today_earned': PointsRecord.objects.filter(
                    user=user,
                    points_change__gt=0,
                    created_at__date=today
                ).aggregate(total=Sum('points_change'))['total'] or 0,
                'today_consumed': abs(PointsRecord.objects.filter(
                    user=user,
                    points_change__lt=0,
                    created_at__date=today
                ).aggregate(total=Sum('points_change'))['total'] or 0)
            }
        }

        return Response({
            'code': 200,
            'message': '获取状态成功',
            'data': status_data
        })


class PointsRankingView(APIView):
    """积分排行榜API"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        """获取积分排行榜"""
        from django.db.models import F, Sum, Count

        ranking_type = request.query_params.get('type', 'total')
        limit = int(request.query_params.get('limit', 20))
        user = request.user

        # 转换为本地时间
        local_tz = pytz.timezone('Asia/Shanghai')
        now_local = timezone.now().astimezone(local_tz)
        today_local = now_local.date()

        # 获取本周一（星期一为一周的开始）
        week_start = today_local - timedelta(days=today_local.weekday())
        month_start = today_local.replace(day=1)

        # 获取UTC时间范围
        week_start_local = local_tz.localize(datetime.combine(week_start, datetime_time.min))
        week_start_utc = week_start_local.astimezone(pytz.UTC)
        month_start_local = local_tz.localize(datetime.combine(month_start, datetime_time.min))
        month_start_utc = month_start_local.astimezone(pytz.UTC)

        # 根据类型获取排行
        if ranking_type == 'total':
            # 总积分排行
            users = User.objects.filter(
                is_active=True
            ).annotate(
                total_points=F('points')
            ).order_by('-total_points')[:limit]

        elif ranking_type == 'month':
            # 本月积分排行
            users = User.objects.filter(
                is_active=True
            ).annotate(
                month_points=Sum('points_records_new__points_change',
                                 filter=Q(points_records_new__created_at__gte=month_start_utc))
            ).order_by('-month_points')[:limit]

        elif ranking_type == 'week':
            # 本周积分排行
            users = User.objects.filter(
                is_active=True
            ).annotate(
                week_points=Sum('points_records_new__points_change',
                                filter=Q(points_records_new__created_at__gte=week_start_utc))
            ).order_by('-week_points')[:limit]

        elif ranking_type == 'green':
            # 绿色生活排行（本月）
            users = User.objects.filter(
                is_active=True
            ).annotate(
                green_points=Sum('points_records_new__points_change',
                                 filter=Q(points_records_new__green_type__isnull=False,
                                          points_records_new__created_at__gte=month_start_utc,
                                          points_records_new__points_change__gt=0)),
                green_days=Count('points_records_new__created_at__date',
                                 filter=Q(points_records_new__green_type__isnull=False,
                                          points_records_new__created_at__gte=month_start_utc),
                                 distinct=True)
            ).order_by('-green_points')[:limit]
        else:
            users = []

        # 获取当前用户排名
        user_rank = PointsRankingView.get_user_rank(user, ranking_type,
                                                    month_start_utc, week_start_utc)

        # 构建响应数据
        ranking_data = []
        for index, user_item in enumerate(users, 1):
            if ranking_type == 'total':
                points = user_item.points
            elif ranking_type == 'month':
                points = user_item.month_points or 0
            elif ranking_type == 'week':
                points = user_item.week_points or 0
            elif ranking_type == 'green':
                points = user_item.green_points or 0
            else:
                points = 0

            ranking_data.append({
                'rank': index,
                'user_id': user_item.id,
                'username': user_item.username,
                'points': points,
                'is_current': user_item.id == user.id
            })

        return Response({
            'code': 200,
            'message': '获取排行榜成功',
            'data': {
                'ranking_type': ranking_type,
                'ranking': ranking_data,
                'user_rank': user_rank,
                'total_users': User.objects.filter(is_active=True).count()
            }
        })

    @staticmethod
    def get_user_rank(user, ranking_type, month_start_utc=None, week_start_utc=None):
        """获取用户排名"""
        from django.db.models import Sum, Q

        if ranking_type == 'total':
            users = User.objects.filter(
                is_active=True,
                points__gt=user.points
            ).count()
            return users + 1

        elif ranking_type == 'month':
            if not month_start_utc:
                return None
            user_month_points = PointsRecord.objects.filter(
                user=user,
                created_at__gte=month_start_utc
            ).aggregate(total=Sum('points_change'))['total'] or 0

            users = User.objects.filter(
                is_active=True
            ).annotate(
                month_points=Sum('points_records_new__points_change',
                                 filter=Q(points_records_new__created_at__gte=month_start_utc))
            ).filter(
                month_points__gt=user_month_points
            ).count()
            return users + 1

        elif ranking_type == 'week':
            if not week_start_utc:
                return None
            user_week_points = PointsRecord.objects.filter(
                user=user,
                created_at__gte=week_start_utc
            ).aggregate(total=Sum('points_change'))['total'] or 0

            users = User.objects.filter(
                is_active=True
            ).annotate(
                week_points=Sum('points_records_new__points_change',
                                filter=Q(points_records_new__created_at__gte=week_start_utc))
            ).filter(
                week_points__gt=user_week_points
            ).count()
            return users + 1

        return None
