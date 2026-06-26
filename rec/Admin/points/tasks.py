# points/tasks.py
from __future__ import absolute_import, unicode_literals
import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction, models
from django.core.cache import cache
from datetime import timedelta

from django.contrib.auth import get_user_model
from .models import PointsRecord, PointsTransaction, UserMonthlySummary
from .services import PointsCleanup

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task
def cleanup_negative_points_task():
    """
    清理负积分用户任务
    每天凌晨执行，修复积分异常的用户
    """
    try:
        result = PointsCleanup.cleanup_negative_points()
        logger.info(f"负积分清理任务完成: {result}")
        return {
            'status': 'success',
            'message': result,
        }
    except Exception as e:
        logger.error(f"负积分清理任务失败: {str(e)}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(e),
        }


@shared_task
def cleanup_duplicate_points_records_task():
    """
    清理重复的积分记录任务
    每周执行一次，清理重复数据
    """
    try:
        result = PointsCleanup.cleanup_duplicate_records()
        logger.info(f"重复记录清理任务完成: {result}")
        return {
            'status': 'success',
            'message': result,
        }
    except Exception as e:
        logger.error(f"重复记录清理任务失败: {str(e)}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(e),
        }


@shared_task
def generate_monthly_summary_task():
    """
    生成月度积分汇总任务
    每月最后一天执行，统计用户月度积分情况
    """
    try:
        today = timezone.now().date()
        year = today.year
        month = today.month

        # 如果是每月第一天，处理上个月的数据
        if today.day == 1:
            # 获取上个月
            if month == 1:
                year = year - 1
                month = 12
            else:
                month = month - 1

        logger.info(f"开始生成月度汇总: {year}年{month}月")

        processed_count = 0
        with transaction.atomic():
            # 获取所有活跃用户
            users = User.objects.filter(is_active=True)

            for user in users:
                try:
                    # 获取本月积分记录
                    month_records = PointsRecord.objects.filter(
                        user=user,
                        created_at__year=year,
                        created_at__month=month
                    )

                    # 计算统计
                    total_earned = sum(r.points_change for r in month_records if r.points_change > 0)
                    total_consumed = sum(abs(r.points_change) for r in month_records if r.points_change < 0)

                    # 绿色生活统计
                    green_records = month_records.filter(green_type__isnull=False)
                    green_points_total = sum(r.points_change for r in green_records if r.points_change > 0)

                    # 具体类型统计
                    transport_days = green_records.filter(green_type='transport').count()
                    food_days = green_records.filter(green_type='food').count()
                    walk_points = sum(
                        r.points_change for r in green_records.filter(green_type='walk') if r.points_change > 0)
                    learning_points = sum(
                        r.points_change for r in green_records.filter(green_type='learning') if r.points_change > 0)

                    # 绿色生活总天数（去重）
                    green_days_total = green_records.values('created_at__date').distinct().count()

                    # 创建或更新月度汇总
                    UserMonthlySummary.objects.update_or_create(
                        user=user,
                        year=year,
                        month=month,
                        defaults={
                            'total_earned': total_earned,
                            'total_consumed': total_consumed,
                            'ending_balance': user.points,
                            'green_days_total': green_days_total,
                            'green_points_total': green_points_total,
                            'transport_days': transport_days,
                            'food_days': food_days,
                            'walk_points': walk_points,
                            'learning_points': learning_points,
                            'is_transport_qualified': transport_days >= 15,
                            'is_food_qualified': food_days >= 15,
                            'is_walk_qualified': walk_points > 0,
                        }
                    )

                    processed_count += 1

                    if processed_count % 100 == 0:
                        logger.info(f"已处理{processed_count}个用户的月度汇总")

                except Exception as e:
                    logger.error(f"处理用户月度汇总失败: user_id={user.id}, error={str(e)}")
                    continue

        logger.info(f"月度汇总任务完成，共处理{processed_count}个用户")
        return {
            'status': 'success',
            'processed_count': processed_count,
            'year': year,
            'month': month
        }

    except Exception as e:
        logger.error(f"月度汇总任务失败: {str(e)}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(e)
        }


@shared_task
def process_expired_points_transactions_task():
    """
    处理过期积分交易任务
    每天执行，清理超时未处理的交易
    """
    try:
        # 找出超过24小时未处理的交易
        expired_time = timezone.now() - timedelta(hours=24)
        expired_transactions = PointsTransaction.objects.filter(
            status='pending',
            created_at__lt=expired_time
        )

        expired_count = expired_transactions.count()

        if expired_count > 0:
            logger.info(f"发现{expired_count}笔过期交易，开始处理")

            processed_count = 0
            for transaction in expired_transactions:
                try:
                    # 如果是兑换交易，取消并返还积分
                    if transaction.transaction_type == 'redeem' and transaction.points_amount < 0:
                        # 返还积分
                        points_change = abs(transaction.points_amount)

                        # 创建积分返还记录
                        PointsRecord.objects.create(
                            user=transaction.user,
                            points_type='system_bonus',
                            points_change=points_change,
                            description=f"交易超时取消，返还积分: {transaction.transaction_no}",
                            related_id=transaction.transaction_no
                        )

                    # 更新交易状态为已取消
                    transaction.status = 'cancelled'
                    transaction.remark = f"系统自动取消，原因：超时未处理"
                    transaction.save()

                    processed_count += 1

                except Exception as e:
                    logger.error(f"处理过期交易失败: transaction_no={transaction.transaction_no}, error={str(e)}")
                    continue

            logger.info(f"已处理{processed_count}笔过期交易")
            return {
                'status': 'success',
                'expired_count': expired_count,
                'processed_count': processed_count
            }
        else:
            return {
                'status': 'success',
                'message': '没有发现过期交易'
            }

    except Exception as e:
        logger.error(f"处理过期交易任务失败: {str(e)}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(e)
        }


@shared_task
def cleanup_old_points_records_task():
    """
    清理旧的积分记录任务
    每季度执行一次，归档历史数据
    """
    try:
        # 清理3年前的积分记录（保留核心字段，删除详细数据）
        cutoff_date = timezone.now() - timedelta(days=365 * 3)

        old_records = PointsRecord.objects.filter(
            created_at__lt=cutoff_date
        )

        record_count = old_records.count()

        if record_count > 0:
            logger.info(f"发现{record_count}条3年前积分记录，开始清理")

            # 保留核心字段，清空大字段
            updated_count = old_records.update(
                upload_image=None,
                certificate_image=None,
                description="历史记录已归档",
                remark="数据已清理归档"
            )

            logger.info(f"已清理{updated_count}条历史记录")
            return {
                'status': 'success',
                'record_count': record_count,
                'updated_count': updated_count
            }
        else:
            return {
                'status': 'success',
                'message': '没有需要清理的历史记录'
            }

    except Exception as e:
        logger.error(f"清理历史记录任务失败: {str(e)}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(e)
        }


@shared_task
def sync_green_life_achievements_task():
    """
    同步绿色生活成就任务
    每天凌晨执行，更新用户达标状态
    """
    try:
        today = timezone.now().date()
        month_start = today.replace(day=1)

        # 更新所有活跃用户的月度达标状态
        users = User.objects.filter(is_active=True)

        updated_count = 0
        for user in users:
            try:
                # 获取本月绿色生活统计
                month_green = PointsRecord.objects.filter(
                    user=user,
                    green_type__isnull=False,
                    points_change__gt=0,
                    created_at__date__gte=month_start
                )

                transport_days = month_green.filter(green_type='transport').count()
                food_days = month_green.filter(green_type='food').count()

                # 更新用户达标状态（可以存储在用户模型或缓存中）
                # 这里简化处理，实际可以根据需求存储

                updated_count += 1

                if updated_count % 100 == 0:
                    logger.info(f"已同步{updated_count}个用户的绿色生活成就")

            except Exception as e:
                logger.error(f"同步用户绿色生活成就失败: user_id={user.id}, error={str(e)}")
                continue

        logger.info(f"绿色生活成就同步完成，共处理{updated_count}个用户")
        return {
            'status': 'success',
            'updated_count': updated_count,
            'date': today.strftime('%Y-%m-%d')
        }

    except Exception as e:
        logger.error(f"绿色生活成就同步任务失败: {str(e)}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(e)
        }


@shared_task
def batch_award_points_task(user_ids, points, reason, award_type='system_bonus'):
    """
    批量奖励积分任务（异步执行）

    Args:
        user_ids: 用户ID列表
        points: 奖励积分
        reason: 奖励原因
        award_type: 奖励类型
    """
    try:
        from .services import PointsService

        if not user_ids or points <= 0:
            return {
                'status': 'failed',
                'error': '参数错误'
            }

        users = User.objects.filter(id__in=user_ids, is_active=True)
        success_count = 0
        failed_users = []

        for user in users:
            try:
                # 使用原子操作更新积分
                success, points_record, error_msg = PointsService.atomic_update_points(
                    user=user,
                    points_change=points,
                    points_type=award_type,
                    description=reason
                )

                if success:
                    success_count += 1
                else:
                    failed_users.append({
                        'user_id': user.id,
                        'error': error_msg
                    })

                # 每处理10个用户记录一次
                if (success_count + len(failed_users)) % 10 == 0:
                    logger.info(f"批量奖励积分进度: {success_count}成功, {len(failed_users)}失败")

            except Exception as e:
                logger.error(f"批量奖励积分失败: user_id={user.id}, error={str(e)}")
                failed_users.append({
                    'user_id': user.id,
                    'error': str(e)
                })
                continue

        result = {
            'status': 'success',
            'total_users': len(users),
            'success_count': success_count,
            'failed_count': len(failed_users),
            'failed_users': failed_users if failed_users else None
        }

        logger.info(f"批量奖励积分任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"批量奖励积分任务失败: {str(e)}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(e)
        }


@shared_task
def generate_points_report_task(start_date, end_date, report_type='daily'):
    """
    生成积分报表任务

    Args:
        start_date: 开始日期
        end_date: 结束日期
        report_type: 报表类型（daily, weekly, monthly）
    """
    try:
        from datetime import datetime

        start = datetime.strptime(start_date, '%Y-%m-%d').date() if isinstance(start_date, str) else start_date
        end = datetime.strptime(end_date, '%Y-%m-%d').date() if isinstance(end_date, str) else end_date

        logger.info(f"开始生成积分报表: {start} 到 {end}, 类型: {report_type}")

        # 统计每日积分数据
        daily_stats = PointsRecord.objects.filter(
            created_at__date__range=[start, end]
        ).extra(
            select={'date': 'DATE(created_at)'}
        ).values('date').annotate(
            total_earned=models.Sum('points_change', filter=models.Q(points_change__gt=0)),
            total_consumed=models.Sum('points_change', filter=models.Q(points_change__lt=0)),
            user_count=models.Count('user_id', distinct=True),
            record_count=models.Count('id')
        ).order_by('date')

        # 用户活跃度统计
        active_users = User.objects.filter(
            is_active=True,
            points_records_new__created_at__date__range=[start, end]
        ).annotate(
            total_earned=models.Sum('points_records_new__points_change',
                                    filter=models.Q(points_records_new__points_change__gt=0)),
            record_count=models.Count('points_records_new')
        ).order_by('-total_earned')[:100]  # 前100名活跃用户

        # 绿色生活统计
        green_stats = PointsRecord.objects.filter(
            green_type__isnull=False,
            created_at__date__range=[start, end]
        ).values('green_type').annotate(
            total_points=models.Sum('points_change'),
            user_count=models.Count('user_id', distinct=True),
            record_count=models.Count('id')
        )

        report_data = {
            'period': {
                'start_date': start.strftime('%Y-%m-%d'),
                'end_date': end.strftime('%Y-%m-%d'),
                'report_type': report_type
            },
            'summary': {
                'total_earned': sum(stat['total_earned'] or 0 for stat in daily_stats),
                'total_consumed': sum(abs(stat['total_consumed'] or 0) for stat in daily_stats),
                'total_users': len(active_users),
                'total_records': sum(stat['record_count'] for stat in daily_stats)
            },
            'daily_stats': list(daily_stats),
            'top_users': [
                {
                    'user_id': user.id,
                    'username': user.username,
                    'total_earned': user.total_earned or 0,
                    'record_count': user.record_count
                }
                for user in active_users
            ],
            'green_life_stats': list(green_stats),
            'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # 保存报表到数据库或文件
        logger.info(f"积分报表生成完成: {len(daily_stats)}天数据, {len(active_users)}个活跃用户")

        return {
            'status': 'success',
            'report_data': report_data,
        }

    except Exception as e:
        logger.error(f"生成积分报表失败: {str(e)}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(e),
        }


# 新增任务 - 积分到期提醒
@shared_task
def send_points_expiry_reminders_task():
    """
    发送积分到期提醒任务
    每天执行，检查即将到期的积分
    """
    try:
        from datetime import datetime, timedelta

        # 计算到期日期（7天后到期）
        expiry_date = timezone.now().date() + timedelta(days=7)
        one_year_ago = expiry_date - timedelta(days=365)

        # 查找即将到期的积分记录
        expiring_records = PointsRecord.objects.filter(
            created_at__date=one_year_ago,
            points_change__gt=0
        ).select_related('user')

        expiring_users = {}
        for record in expiring_records:
            user_id = record.user_id
            if user_id not in expiring_users:
                expiring_users[user_id] = {
                    'user': record.user,
                    'points': 0,
                    'expiry_date': expiry_date
                }
            expiring_users[user_id]['points'] += record.points_change

        # 发送提醒
        reminded_count = 0
        for user_data in expiring_users.values():
            try:
                user = user_data['user']
                points = user_data['points']
                expiry_date = user_data['expiry_date']

                # 这里可以集成消息推送系统
                # 例如：发送微信模板消息、站内信等

                # 记录日志
                logger.info(f"积分到期提醒: user_id={user.id}, points={points}, expiry_date={expiry_date}")

                reminded_count += 1

            except Exception as e:
                logger.error(f"发送到期提醒失败: user_id={user.id}, error={str(e)}")
                continue

        return {
            'status': 'success',
            'reminded_count': reminded_count,
            'expiring_users_count': len(expiring_users),
            'execution_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    except Exception as e:
        logger.error(f"积分到期提醒任务失败: {str(e)}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(e)
        }


# 新增任务 - 重置每日签到成就
@shared_task
def reset_daily_sign_achievements_task():
    """
    重置每日签到成就任务
    每天凌晨执行，更新连续签到状态
    """
    try:
        from datetime import datetime, timedelta

        yesterday = timezone.now().date() - timedelta(days=1)

        # 获取所有用户昨日的签到状态
        yesterday_signs = PointsRecord.objects.filter(
            points_type='sign',
            created_at__date=yesterday
        ).values('user_id')

        signed_user_ids = set(item['user_id'] for item in yesterday_signs)

        # 获取所有活跃用户
        all_users = User.objects.filter(is_active=True).values_list('id', flat=True)

        # 找出昨日未签到的用户
        not_signed_users = set(all_users) - signed_user_ids

        # 这里可以记录用户的连续签到中断，或者更新用户成就
        # 实际业务逻辑根据需求实现

        logger.info(
            f"连续签到重置检查: 总用户{len(all_users)}, 昨日签到{len(signed_user_ids)}, 未签到{len(not_signed_users)}")

        return {
            'status': 'success',
            'total_users': len(all_users),
            'signed_yesterday': len(signed_user_ids),
            'not_signed': len(not_signed_users),
            'date': yesterday.strftime('%Y-%m-%d')
        }

    except Exception as e:
        logger.error(f"重置签到成就任务失败: {str(e)}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(e)
        }


# 新增任务 - 更新月度积分排行榜
@shared_task
def update_monthly_points_rankings_task():
    """
    更新月度积分排行榜任务
    每月最后一天执行
    """
    try:
        today = timezone.now().date()
        year = today.year
        month = today.month

        # 如果是每月第一天，处理上个月的数据
        if today.day == 1:
            if month == 1:
                year = year - 1
                month = 12
            else:
                month = month - 1

        logger.info(f"开始更新月度积分排行榜: {year}年{month}月")

        # 计算月度积分排行
        from django.db.models import Sum

        # 获取本月积分排名前100的用户
        top_users = User.objects.filter(
            is_active=True,
            points_records_new__created_at__year=year,
            points_records_new__created_at__month=month
        ).annotate(
            month_points=Sum('points_records_new__points_change')
        ).order_by('-month_points')[:100]

        # 保存排行榜数据（可以存入缓存或数据库）
        ranking_data = []
        for rank, user in enumerate(top_users, 1):
            ranking_data.append({
                'rank': rank,
                'user_id': user.id,
                'username': user.username,
                'month_points': user.month_points or 0,
            })

        # 存入缓存（7天有效期）
        cache_key = f'points:monthly_ranking:{year}:{month}'
        cache.set(cache_key, ranking_data, timeout=60 * 60 * 24 * 7)

        logger.info(f"月度积分排行榜更新完成，共{len(ranking_data)}位用户上榜")

        return {
            'status': 'success',
            'ranking_data': ranking_data[:10],  # 只返回前10名
            'year': year,
            'month': month,
            'total_users': len(ranking_data)
        }

    except Exception as e:
        logger.error(f"更新月度积分排行榜失败: {str(e)}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(e)
        }
