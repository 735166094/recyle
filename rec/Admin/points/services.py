# points/services.py
from django.db import transaction, models
from django.core.cache import cache
from django.utils import timezone
from django_redis import get_redis_connection
import uuid
import hashlib
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from .models import PointsRule, PointsRecord, UserDailyPoints, PointsTransaction
from user.models import User

logger = logging.getLogger(__name__)


class PointsService:
    """积分操作服务类 - 确保原子性和安全性"""

    REDIS_KEY_PREFIX = "points:lock:"
    IDEMPOTENCY_KEY_PREFIX = "points:idempotent:"
    CACHE_TIMEOUT = 300  # 5分钟

    @classmethod
    def acquire_lock(cls, user_id, operation_type, timeout=10):
        """
        获取分布式锁

        Args:
            user_id: 用户ID
            operation_type: 操作类型（sign、green_life、exchange等）
            timeout: 锁超时时间（秒）

        Returns:
            lock_key: 锁键，成功时返回，失败时返回None
        """
        redis_conn = get_redis_connection("default")
        lock_key = f"{cls.REDIS_KEY_PREFIX}{user_id}:{operation_type}"

        # 使用SETNX + EXPIRE实现分布式锁
        lock_value = str(uuid.uuid4())

        # Redis 2.6.12+ 支持 SET NX EX
        acquired = redis_conn.set(
            lock_key,
            lock_value,
            nx=True,
            ex=timeout
        )

        if acquired:
            return lock_key
        return None

    @classmethod
    def release_lock(cls, lock_key):
        """释放锁"""
        redis_conn = get_redis_connection("default")
        redis_conn.delete(lock_key)

    @classmethod
    def generate_idempotency_key(cls, user_id, operation_type, data):
        """
        生成幂等性键

        Args:
            user_id: 用户ID
            operation_type: 操作类型
            data: 操作数据

        Returns:
            idempotency_key: 幂等性键
        """
        data_str = json.dumps(data, sort_keys=True)
        key_string = f"{user_id}:{operation_type}:{data_str}"
        return hashlib.md5(key_string.encode()).hexdigest()

    @classmethod
    def check_and_set_idempotency(cls, idempotency_key, result_data=None):
        """
        检查并设置幂等性

        Args:
            idempotency_key: 幂等性键
            result_data: 如果已存在，返回的结果数据

        Returns:
            (exists, cached_result): 是否存在，缓存的结果
        """
        cache_key = f"{cls.IDEMPOTENCY_KEY_PREFIX}{idempotency_key}"
        cached = cache.get(cache_key)

        if cached is not None:
            return True, cached

        # 设置缓存，24小时过期
        if result_data:
            cache.set(cache_key, result_data, timeout=86400)

        return False, None


    @classmethod
    def atomic_update_points(cls, user, points_change, **record_data):
        """
        原子性更新用户积分
        """
        try:
            with transaction.atomic():
                # 使用select_for_update锁定用户行
                locked_user = User.objects.select_for_update().get(pk=user.pk)

                # 检查积分是否足够（如果是消费）
                if points_change < 0 and locked_user.points + points_change < 0:
                    return False, None, "积分不足"

                # 使用F表达式原子性更新积分
                from django.db.models import F
                locked_user.points = F('points') + points_change
                locked_user.save(update_fields=['points', 'updated_at'])

                # 重新获取更新后的积分值
                locked_user.refresh_from_db()

                # 创建积分记录
                points_record = PointsRecord(
                    user=locked_user,
                    points_change=points_change,
                    current_points=locked_user.points,
                    **{k: v for k, v in record_data.items()
                       if k in ['points_rule', 'points_type', 'green_type', 'upload_image',
                                'certificate_image', 'steps_count', 'days_count', 'description',
                                'remark', 'related_id', 'order_no', 'recycle_id', 'is_verified',
                                'verified_at', 'verified_by']}
                )
                points_record.save()

                return True, points_record, None

        except Exception as e:
            logger.error(f"原子性更新积分失败: {str(e)}", exc_info=True)
            return False, None, f"积分更新失败: {str(e)}"

    @classmethod
    def daily_sign(cls, user, request_data=None):
        """
        安全的每日签到 - 确保每天只能签到一次
        """
        # 获取分布式锁
        lock_key = cls.acquire_lock(user.id, "sign")
        if not lock_key:
            return False, None, "系统繁忙，请稍后重试"

        try:
            # 获取今天的日期（确保使用服务器时间）
            today = timezone.now().date()

            # 检查今天是否已签到（严格检查）
            today_sign_exists = PointsRecord.objects.filter(
                user=user,
                points_type='sign',
                created_at__date=today
            ).exists()

            if today_sign_exists:
                # 获取今天的具体签到记录
                today_sign = PointsRecord.objects.filter(
                    user=user,
                    points_type='sign',
                    created_at__date=today
                ).first()

                result = {
                    'points': today_sign.points_change if today_sign else 0,
                    'total_points': user.points,
                    'message': '今天已经签到过了',
                    'already_signed': True,
                    'signed_time': today_sign.created_at if today_sign else None
                }
                return True, result, None

            # 获取签到规则
            sign_rule = PointsRule.objects.filter(
                rule_type='sign',
                is_active=True
            ).first()

            if not sign_rule:
                # 使用默认规则
                base_points = 10
                logger.warning(f"用户 {user.id} 签到：使用默认规则")
            else:
                base_points = sign_rule.points_value

            # 计算连续签到奖励
            continuous_days = cls.get_continuous_days(user)
            extra_points = cls.calculate_continuous_reward(continuous_days + 1)

            total_points = base_points + extra_points

            # 原子性更新积分
            success, points_record, error_msg = cls.atomic_update_points(
                user=user,
                points_change=total_points,
                points_rule=sign_rule,
                points_type='sign',
                description=f"每日签到，获得{base_points}积分" +
                            (f"，连续签到奖励{extra_points}积分" if extra_points > 0 else ""),
                is_verified=True,
                verified_at=timezone.now()
            )

            if not success:
                return False, None, error_msg

            # 更新每日统计
            try:
                daily_stats, created = UserDailyPoints.objects.get_or_create(
                    user=user,
                    date=today,
                    defaults={
                        'sign_points': total_points,
                        'total_points': user.points
                    }
                )

                if not created:
                    daily_stats.sign_points += total_points
                    daily_stats.total_points = user.points
                    daily_stats.save()
            except Exception as e:
                logger.error(f"更新每日统计失败: {str(e)}")
                # 不影响主要签到流程

            result = {
                'points': total_points,
                'base_points': base_points,
                'extra_points': extra_points,
                'total_points': user.points,
                'message': '签到成功' + (f'，连续签到奖励{extra_points}积分' if extra_points > 0 else ''),
                'already_signed': False,
                'continuous_days': continuous_days + 1,
                'signed_time': timezone.now()
            }

            return True, result, None

        finally:
            cls.release_lock(lock_key)

    @classmethod
    def get_continuous_days(cls, user):
        """获取连续签到天数"""
        try:
            # 获取最近7天的签到记录
            seven_days_ago = timezone.now().date() - timedelta(days=7)
            sign_records = PointsRecord.objects.filter(
                user=user,
                points_type='sign',
                created_at__date__gte=seven_days_ago
            ).order_by('-created_at').values_list('created_at__date', flat=True).distinct()

            # 计算连续天数
            continuous_days = 0
            current_date = timezone.now().date()

            for i in range(1, 8):  # 检查最近7天
                check_date = current_date - timedelta(days=i - 1)
                if check_date in sign_records:
                    continuous_days += 1
                else:
                    break

            return continuous_days
        except Exception as e:
            logger.error(f"计算连续签到天数失败: {str(e)}")
            return 0

    @classmethod
    def calculate_continuous_reward(cls, continuous_days):
        """计算连续签到奖励"""
        # 连续签到奖励规则
        if continuous_days >= 7:
            return 10  # 连续7天奖励10积分
        elif continuous_days >= 3:
            return 5  # 连续3天奖励5积分
        else:
            return 0

    @classmethod
    def submit_green_life(cls, user, green_type, data):
        """
        安全的绿色生活提交

        Args:
            user: 用户对象
            green_type: 绿色生活类型
            data: 提交数据

        Returns:
            (success, data, error_message)
        """
        # 生成幂等性键
        idempotency_key = cls.generate_idempotency_key(
            user.id, f"green_life_{green_type}", data
        )

        # 检查幂等性
        exists, cached_result = cls.check_and_set_idempotency(idempotency_key)
        if exists:
            return True, cached_result, None

        # 获取分布式锁
        lock_key = cls.acquire_lock(user.id, f"green_life_{green_type}")
        if not lock_key:
            return False, None, "系统繁忙，请稍后重试"

        try:
            today = timezone.now().date()

            # 检查今天是否已提交
            today_records = PointsRecord.objects.filter(
                user=user,
                green_type=green_type,
                created_at__date=today
            )

            if today_records.exists():
                result = {
                    'points': 0,
                    'total_points': user.points,
                    'message': '今天已经提交过了'
                }

                cls.check_and_set_idempotency(idempotency_key, result)
                return True, result, None

            # 获取规则
            rule = PointsRule.objects.filter(
                green_type=green_type,
                is_active=True
            ).first()

            if not rule:
                return False, None, "该绿色生活规则不存在"

            # 检查规则限制
            if rule.daily_limit > 0:
                today_count = today_records.count()
                if today_count >= rule.daily_limit:
                    result = {
                        'points': 0,
                        'total_points': user.points,
                        'message': f'今日已达到{rule.daily_limit}次上限'
                    }

                    cls.check_and_set_idempotency(idempotency_key, result)
                    return True, result, None

            # 计算积分
            points = rule.points_value

            # 特殊处理：低碳行走
            if green_type == 'walk':
                steps = data.get('steps_count', 0)
                if steps > 0:
                    walk_points = min(steps // 1000, 100)
                    points = walk_points if rule.points_value == 0 else min(rule.points_value, walk_points)

            # 原子性更新积分
            success, points_record, error_msg = cls.atomic_update_points(
                user=user,
                points_change=points,
                points_rule=rule,
                points_type='task',
                green_type=green_type,
                upload_image=data.get('upload_image'),
                certificate_image=data.get('certificate_image'),
                steps_count=data.get('steps_count', 0),
                days_count=data.get('days_count', 0),
                description=data.get('description', ''),
                remark=f"绿色生活：{rule.get_green_type_display()}"
            )

            if not success:
                return False, None, error_msg

            # 更新每日统计
            daily_stats, _ = UserDailyPoints.objects.get_or_create(
                user=user,
                date=today
            )
            daily_stats.green_points += points
            daily_stats.total_points += points

            if green_type == 'transport':
                daily_stats.transport_days += 1
            elif green_type == 'food':
                daily_stats.food_days += 1
            elif green_type == 'walk':
                daily_stats.walk_steps += data.get('steps_count', 0)
            elif green_type == 'learning':
                daily_stats.learning_count += 1

            daily_stats.save()

            result = {
                'points': points,
                'total_points': user.points,
                'message': '提交成功'
            }

            # 缓存结果
            cls.check_and_set_idempotency(idempotency_key, result)

            return True, result, None

        finally:
            cls.release_lock(lock_key)

    @classmethod
    def exchange_points(cls, user, product_data, address_id, quantity=1):
        """
        安全的积分兑换

        Args:
            user: 用户对象
            product_data: 商品信息
            address_id: 收货地址ID
            quantity: 数量

        Returns:
            (success, data, error_message)
        """
        from user.models import UserAddress

        # 生成幂等性键
        idempotency_key = cls.generate_idempotency_key(
            user.id, "exchange", {
                **product_data,
                'address_id': address_id,
                'quantity': quantity
            }
        )

        # 检查幂等性
        exists, cached_result = cls.check_and_set_idempotency(idempotency_key)
        if exists:
            return True, cached_result, None

        # 获取分布式锁
        lock_key = cls.acquire_lock(user.id, "exchange")
        if not lock_key:
            return False, None, "系统繁忙，请稍后重试"

        try:
            # 检查收货地址
            try:
                address = UserAddress.objects.get(id=address_id, user=user)
            except UserAddress.DoesNotExist:
                return False, None, "收货地址不存在"

            total_points = product_data['product_points'] * quantity

            # 原子性更新积分（消费）
            success, points_record, error_msg = cls.atomic_update_points(
                user=user,
                points_change=-total_points,
                points_type='consume',
                description=f"兑换商品：{product_data['product_name']} ×{quantity}",
                related_id=f"product_{product_data['product_id']}"
            )

            if not success:
                return False, None, error_msg

            # 生成交易记录
            transaction_no = f"PTS{timezone.now().strftime('%Y%m%d%H%M%S')}{user.id:06d}"

            PointsTransaction.objects.create(
                transaction_no=transaction_no,
                user=user,
                transaction_type='redeem',
                points_amount=-total_points,
                product_id=product_data['product_id'],
                product_name=product_data['product_name'],
                product_points=product_data['product_points'],
                redeem_address=address,
                status='pending',
                remark=f"兑换{product_data['product_name']} ×{quantity}"
            )

            result = {
                'transaction_no': transaction_no,
                'points': total_points,
                'remaining_points': user.points,
                'status': 'pending',
                'message': '兑换申请已提交'
            }

            # 缓存结果
            cls.check_and_set_idempotency(idempotency_key, result)

            return True, result, None

        finally:
            cls.release_lock(lock_key)

    @classmethod
    def get_points_summary_cached(cls, user_id):
        """
        获取缓存的积分汇总信息
        """
        cache_key = f"points:summary:{user_id}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return cached_data

        # 重新计算并缓存
        from points.views import PointsSummaryView
        user = User.objects.get(id=user_id)

        # 这里简化处理，实际应调用视图中的逻辑
        today = timezone.now().date()
        month_start = today.replace(day=1)

        # ... 计算逻辑 ...

        # 缓存5分钟
        cache.set(cache_key, cached_data, timeout=cls.CACHE_TIMEOUT)

        return cached_data

    @classmethod
    def clear_user_cache(cls, user_id):
        """清除用户相关缓存"""
        cache_keys = [
            f"points:summary:{user_id}",
            f"user_points_{user_id}",
            f"daily_stats_{user_id}_{timezone.now().date()}",
        ]
        for key in cache_keys:
            cache.delete(key)


class PointsValidator:
    """积分验证器"""

    @staticmethod
    def validate_points_change(user, points_change, operation_type):
        """
        验证积分变动合法性

        Args:
            user: 用户对象
            points_change: 积分变动值
            operation_type: 操作类型

        Returns:
            (is_valid, error_message)
        """
        # 检查积分是否为整数
        if not isinstance(points_change, int):
            return False, "积分必须是整数"

        # 检查用户是否活跃
        if not user.is_active:
            return False, "用户账户已被禁用"

        # 根据操作类型进行验证
        if operation_type in ['consume', 'redeem']:
            # 消费类操作：不能为负数，且不能超过用户当前积分
            if points_change >= 0:
                return False, "消费积分必须为负数"

            if user.points + points_change < 0:
                return False, "积分不足"

        elif operation_type in ['sign', 'task', 'purchase', 'recycle']:
            # 获取积分操作：必须为正数
            if points_change <= 0:
                return False, "获取积分必须为正数"

            # 检查积分上限（如果有）
            # TODO: 可以根据规则配置上限

        return True, None

    @staticmethod
    def validate_green_life_data(green_type, data):
        """
        验证绿色生活数据

        Args:
            green_type: 绿色生活类型
            data: 提交数据

        Returns:
            (is_valid, error_message)
        """
        if green_type == 'walk':
            steps = data.get('steps_count', 0)
            if steps < 1000:
                return False, "步数需达到1000步以上"
            if steps > 100000:
                return False, "步数异常，请检查"

        elif green_type in ['transport', 'food']:
            if not data.get('upload_image'):
                return False, "请上传凭证图片"

        elif green_type == 'learning':
            if not data.get('certificate_image'):
                return False, "请上传证书图片"

        return True, None


class PointsCleanup:
    """积分数据清理工具"""

    @staticmethod
    def cleanup_negative_points():
        """
        清理异常的负积分记录
        """
        # 找出导致用户积分为负的记录
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT pr.id, pr.user_id, pr.points_change, u.points
                FROM points_record pr
                JOIN user_info u ON pr.user_id = u.id
                WHERE u.points < 0
                ORDER BY pr.created_at DESC
                LIMIT 100
            """)

            rows = cursor.fetchall()

            for row in rows:
                record_id, user_id, points_change, current_points = row

                # 记录异常
                logger.warning(
                    f"发现负积分用户: user_id={user_id}, "
                    f"record_id={record_id}, "
                    f"points_change={points_change}, "
                    f"current_points={current_points}"
                )

        # 修复负积分用户（设置为0）
        User.objects.filter(points__lt=0).update(points=0)

        return f"已修复 {User.objects.filter(points__lt=0).count()} 个负积分用户"

    @staticmethod
    def cleanup_duplicate_records():
        """
        清理重复的积分记录（基于相同用户、类型、时间）
        """
        from django.db.models import Count

        # 找出完全重复的记录
        duplicates = PointsRecord.objects.values(
            'user_id', 'points_type', 'green_type', 'points_change', 'created_at__date'
        ).annotate(
            count=Count('id')
        ).filter(
            count__gt=1
        )

        for dup in duplicates:
            # 保留第一条，删除其他重复记录
            records = PointsRecord.objects.filter(
                user_id=dup['user_id'],
                points_type=dup['points_type'],
                green_type=dup['green_type'],
                points_change=dup['points_change'],
                created_at__date=dup['created_at__date']
            ).order_by('id')

            if records.count() > 1:
                # 保留第一条
                keep_record = records.first()
                # 删除其他
                records.exclude(id=keep_record.id).delete()

        return f"已清理 {duplicates.count()} 组重复记录"
