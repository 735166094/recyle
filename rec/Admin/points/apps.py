# points/apps.py
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class PointsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "points"
    verbose_name = "积分管理"

    def ready(self):
        """
        应用就绪时执行
        注意：这里不能直接导入 tasks，因为 Django 启动时可能还没有完全初始化
        """
        try:
            # 使用 import_module 来避免循环导入
            from django.utils.module_loading import import_string

            # 检查 Celery 是否可用
            try:
                from recycle_admin.celery import shared_task

                # 导入信号处理器
                import points.signals
                logger.info("Points 应用信号处理器加载成功")

                # 尝试导入任务（但不执行）
                import points.tasks
                logger.info("Points 应用任务模块加载成功")

            except ImportError:
                logger.warning("Celery 不可用，跳过任务导入")

        except Exception as e:
            logger.error(f"Points 应用初始化失败: {str(e)}", exc_info=True)