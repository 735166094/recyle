# points/signals.py
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from .models import PointsRecord, UserDailyPoints, UserMonthlySummary, PointsRule
import logging
from .services import PointsService

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=PointsRecord)
def validate_points_change(sender, instance, **kwargs):
    """
    在保存前验证积分变动
    """
    # 1. 自动检查规则限制
    if instance.points_rule:
        rule = instance.points_rule
        today = timezone.now().date()

        # 检查每日上限
        if rule.daily_limit > 0:
            today_count = PointsRecord.objects.filter(
                user=instance.user,
                points_rule=rule,
                created_at__date=today
            ).count()
            if today_count >= rule.daily_limit:
                raise ValueError(f"今日已达到{rule.daily_limit}次上限")

    # 2. 验证积分变动值
    if instance.points_change == 0:
        raise ValueError("积分变动值不能为0")

    # 3. 自动设置描述（如果未提供）
    if not instance.description and instance.points_rule:
        instance.description = f"{instance.points_rule.rule_name}，获得{instance.points_change}积分"


@receiver(post_save, sender=PointsRecord)
def update_user_points(sender, instance, created, **kwargs):
    """
    更新用户总积分（实时）
    """
    if created:
        try:
            # 使用数据库事务确保一致性
            with transaction.atomic():
                # 更新用户积分
                instance.user.points = instance.current_points
                instance.user.save(update_fields=['points', 'updated_at'])

                logger.info(f"用户{instance.user.username}积分更新: {instance.current_points}")

        except Exception as e:
            logger.error(f"更新用户积分失败: {str(e)}", exc_info=True)


@receiver(post_save, sender=PointsRecord)
def update_related_stats(sender, instance, created, **kwargs):
    """
    更新相关统计数据（每日、月度）
    """
    if created:
        try:
            update_daily_stats(instance)
            update_monthly_summary(instance)
            clear_cache(instance.user)

        except Exception as e:
            logger.error(f"更新统计数据失败: {str(e)}", exc_info=True)


def update_daily_stats(record):
    """更新每日统计"""
    date = record.created_at.date()

    # 获取或创建每日统计
    daily_stats, _ = UserDailyPoints.objects.get_or_create(
        user=record.user,
        date=date,
        defaults={'total_points': 0}
    )

    # 根据类型更新相应字段
    if record.points_change > 0:
        update_earned_stats(daily_stats, record)
    else:
        update_consumed_stats(daily_stats, record)

    # 更新总积分
    daily_stats.total_points = record.current_points
    daily_stats.save()


def update_earned_stats(daily_stats, record):
    """更新获取积分统计"""
    # 签到积分
    if record.points_type == 'sign':
        daily_stats.sign_points += record.points_change

    # 任务积分
    elif record.points_type == 'task':
        daily_stats.task_points += record.points_change

        # 绿色生活积分
        if record.green_type:
            daily_stats.green_points += record.points_change

            # 具体类型统计
            if record.green_type == 'transport':
                daily_stats.transport_days += 1
            elif record.green_type == 'food':
                daily_stats.food_days += 1
            elif record.green_type == 'walk':
                daily_stats.walk_steps += record.steps_count or 0
            elif record.green_type == 'learning':
                daily_stats.learning_count += 1

    # 购物奖励
    elif record.points_type == 'purchase':
        daily_stats.purchase_points += record.points_change

    # 回收奖励
    elif record.points_type == 'recycle':
        daily_stats.recycle_points += record.points_change


def update_consumed_stats(daily_stats, record):
    """更新消费积分统计"""
    daily_stats.consume_points += abs(record.points_change)


def update_monthly_summary(record):
    """更新月度汇总"""
    year = record.created_at.year
    month = record.created_at.month

    # 获取或创建月度汇总
    summary, _ = UserMonthlySummary.objects.get_or_create(
        user=record.user,
        year=year,
        month=month,
        defaults={'ending_balance': 0}
    )

    # 更新积分统计
    if record.points_change > 0:
        summary.total_earned += record.points_change
        update_green_life_stats(summary, record)
    else:
        summary.total_consumed += abs(record.points_change)

    # 更新余额和达标状态
    summary.ending_balance = record.current_points
    update_qualification_status(summary)

    summary.save()


def update_green_life_stats(summary, record):
    """更新绿色生活统计"""
    if record.green_type:
        summary.green_points_total += record.points_change

        # 更新天数统计（去重）
        if record.green_type in ['transport', 'food']:
            unique_dates = PointsRecord.objects.filter(
                user=record.user,
                green_type=record.green_type,
                points_change__gt=0,
                created_at__year=summary.year,
                created_at__month=summary.month
            ).dates('created_at', 'day').count()

            if record.green_type == 'transport':
                summary.transport_days = unique_dates
            elif record.green_type == 'food':
                summary.food_days = unique_dates

        # 更新其他统计
        elif record.green_type == 'walk':
            summary.walk_points += record.points_change
        elif record.green_type == 'learning':
            summary.learning_points += record.points_change

        # 更新绿色生活总天数
        summary.green_days_total = PointsRecord.objects.filter(
            user=record.user,
            green_type__isnull=False,
            points_change__gt=0,
            created_at__year=summary.year,
            created_at__month=summary.month
        ).dates('created_at', 'day').count()


def update_qualification_status(summary):
    """更新达标状态"""
    summary.is_transport_qualified = summary.transport_days >= 15
    summary.is_food_qualified = summary.food_days >= 15
    summary.is_walk_qualified = summary.walk_points > 0


def clear_cache(user):
    """清除缓存"""
    # 清除用户积分缓存
    cache.delete(f'user_points_{user.id}')

    # 清除每日统计缓存
    today = timezone.now().date()
    cache.delete(f'daily_stats_{user.id}_{today}')

    # 清除月度汇总缓存
    cache.delete(f'monthly_summary_{user.id}_{today.year}_{today.month}')


@receiver(post_delete, sender=PointsRecord)
def revert_stats_on_delete(sender, instance, **kwargs):
    """
    删除积分记录时，回滚统计数据
    """
    try:
        # 回滚用户积分
        instance.user.points = instance.current_points - instance.points_change
        instance.user.save(update_fields=['points'])

        # 删除相关统计（可以由定时任务重新计算）
        logger.info(f"删除了积分记录，用户积分回滚到: {instance.user.points}")

    except Exception as e:
        logger.error(f"回滚积分统计数据失败: {str(e)}", exc_info=True)


@receiver(post_save, sender=PointsRule)
def clear_rule_cache(sender, instance, **kwargs):
    """
    积分规则更新时，清除相关缓存
    """
    # 清除所有规则缓存
    cache.delete('active_points_rules')
    cache.delete(f'points_rule_{instance.rule_id}')

    # 如果有绿色生活相关规则，清除绿色生活缓存
    if instance.green_type:
        cache.delete('green_life_rules')


@receiver(pre_save, sender=PointsRecord)
def auto_verify_simple_types(sender, instance, **kwargs):
    """
    自动验证简单的积分类型
    """
    if not instance.pk:  # 只对新记录
        # 自动验证的类型
        auto_verify_types = ['sign', 'system_bonus']

        if instance.points_type in auto_verify_types:
            instance.is_verified = True
            instance.verified_at = timezone.now()
            instance.verified_by = None

        # 消费类操作也自动验证
        elif instance.points_change < 0:
            instance.is_verified = True
            instance.verified_at = timezone.now()
            instance.verified_by = None
