# recycle_admin/celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

# 设置默认Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ocr_admin.settings')

app = Celery('ocr_admin')

# 使用Django的设置文件配置Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# 从所有已注册的Django应用中发现任务
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


# 配置定时任务
app.conf.beat_schedule = {
    # OCR 相关任务
    'batch-process-unmatched-records': {
        'task': 'ocr.tasks.batch_process_unmatched_records',
        'schedule': crontab(hour=2, minute=0),  # 每天凌晨2点
        'options': {'queue': 'periodic'}
    },
    'cleanup-old-scrap-car-info': {
        'task': 'ocr.tasks.cleanup_old_scrap_car_info',
        'schedule': crontab(hour=3, minute=0, day_of_month='1'),  # 每月1号凌晨3点
        'options': {'queue': 'periodic'}
    },

    # ============ 积分系统定时任务 ============

    # 1. 清理负积分用户（每天凌晨4点）
    'cleanup-negative-points-daily': {
        'task': 'points.tasks.cleanup_negative_points_task',
        'schedule': crontab(hour=4, minute=0),
        'options': {'queue': 'periodic'},
    },

    # 2. 清理重复积分记录（每周一凌晨1点）
    'cleanup-duplicate-points-weekly': {
        'task': 'points.tasks.cleanup_duplicate_points_records_task',
        'schedule': crontab(day_of_week='monday', hour=1, minute=0),
        'options': {'queue': 'periodic'},
    },

    # 3. 生成月度积分汇总（每月1号凌晨0:10执行，处理上个月数据）
    'generate-monthly-summary': {
        'task': 'points.tasks.generate_monthly_summary_task',
        'schedule': crontab(day_of_month=1, hour=0, minute=10),
        'options': {'queue': 'periodic'},
    },

    # 4. 处理过期积分交易（每天凌晨3点）
    'process-expired-transactions-daily': {
        'task': 'points.tasks.process_expired_points_transactions_task',
        'schedule': crontab(hour=3, minute=0),
        'options': {'queue': 'periodic'},
    },

    # 5. 同步绿色生活成就（每天凌晨5点）
    'sync-green-life-achievements-daily': {
        'task': 'points.tasks.sync_green_life_achievements_task',
        'schedule': crontab(hour=5, minute=0),
        'options': {'queue': 'periodic'},
    },

    # 6. 清理旧积分记录（每季度第一天凌晨2点）
    'cleanup-old-points-records-quarterly': {
        'task': 'points.tasks.cleanup_old_points_records_task',
        'schedule': crontab(month_of_year='1,4,7,10', day_of_month='1', hour=2, minute=0),
        'options': {'queue': 'periodic'},
    },

    # 7. 发送积分到期提醒（每天上午9点）
    'send-points-expiry-reminders': {
        'task': 'points.tasks.send_points_expiry_reminders_task',
        'schedule': crontab(hour=9, minute=0),
        'options': {'queue': 'periodic'},
    },

    # 8. 重置每日签到成就（每天凌晨0:05）
    'reset-daily-sign-achievements': {
        'task': 'points.tasks.reset_daily_sign_achievements_task',
        'schedule': crontab(hour=0, minute=5),
        'options': {'queue': 'periodic'},
    },

    # 9. 更新月度积分排行榜（每月1号凌晨0:30执行）
    'update-monthly-points-rankings': {
        'task': 'points.tasks.update_monthly_points_rankings_task',
        'schedule': crontab(day_of_month=1, hour=0, minute=30),
        'options': {'queue': 'periodic'},
    },
}