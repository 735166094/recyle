import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from .models import RecognitionRecord, ScrapCarInfo, VehicleLicenseResult
from .signals import MatchEngine
from .duplicate_utils import DuplicateManager
from .utils import enrich_vehicle_license_with_vin
from .vin_tasks import query_vin_for_vehicle_result_task
from .utils import enrich_vehicle_license_with_vin

logger = logging.getLogger(__name__)


@shared_task
def batch_process_unmatched_records():
    """批量处理未匹配记录 - 每日凌晨执行"""
    try:
        logger.info("开始批量处理未匹配记录")

        # 查找最近30天内未匹配的行驶证记录
        unmatched_vehicle_records = RecognitionRecord.objects.filter(
            certificate_type__type_code='vehicle_license',
            recognition_status=True,
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).exclude(
            scrap_car_vehicle_records__match_status='matched'
        ).select_related('vehicle_result')

        processed_count = 0
        matched_count = 0

        for vehicle_record in unmatched_vehicle_records:
            try:
                with transaction.atomic():
                    scrap_info = MatchEngine.create_or_update_scrap_car_info(vehicle_record)
                    if scrap_info and scrap_info.match_status == 'matched':
                        matched_count += 1
                    processed_count += 1

            except Exception as e:
                logger.error(f"处理记录 {vehicle_record.id} 失败: {str(e)}")
                continue

        logger.info(f"批量处理完成: 处理 {processed_count} 条记录, 匹配 {matched_count} 条记录")
        return {
            'processed_count': processed_count,
            'matched_count': matched_count,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"批量处理任务失败: {str(e)}")
        return {'error': str(e)}


@shared_task
def auto_mark_duplicates_task():
    """自动标记重复记录任务"""
    try:
        marked_count = DuplicateManager.auto_mark_duplicates()
        return {
            'marked_count': marked_count,
            'timestamp': timezone.now().isoformat()
        }
    except Exception as e:
        logger.error(f"自动标记重复记录任务失败: {str(e)}")
        return {'error': str(e)}


@shared_task
def auto_merge_duplicates_task():
    """自动合并重复记录任务"""
    try:
        merged_count = DuplicateManager.auto_merge_duplicates()
        return {
            'merged_count': merged_count,
            'timestamp': timezone.now().isoformat()
        }
    except Exception as e:
        logger.error(f"自动合并重复记录任务失败: {str(e)}")
        return {'error': str(e)}


@shared_task
def cleanup_duplicates_task():
    """清理重复记录任务"""
    try:
        deleted_count = DuplicateManager.cleanup_duplicates()
        return {
            'deleted_count': deleted_count,
            'timestamp': timezone.now().isoformat()
        }
    except Exception as e:
        logger.error(f"清理重复记录任务失败: {str(e)}")
        return {'error': str(e)}


@shared_task
def get_duplicate_statistics_task():
    """获取重复记录统计任务"""
    try:
        statistics = DuplicateManager.get_duplicate_statistics()
        return statistics
    except Exception as e:
        logger.error(f"获取重复记录统计任务失败: {str(e)}")
        return {'error': str(e)}


@shared_task
def cleanup_old_scrap_car_info():
    """清理过期的报废车信息记录 - 保留最近90天"""
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=90)
        deleted_count, _ = ScrapCarInfo.objects.filter(
            created_at__lt=cutoff_date,
            match_status='unmatched'
        ).delete()

        logger.info(f"清理过期报废车信息记录: 删除 {deleted_count} 条")
        return {'deleted_count': deleted_count}

    except Exception as e:
        logger.error(f"清理任务失败: {str(e)}")
        return {'error': str(e)}


@shared_task
def auto_merge_duplicates_task():
    """自动合并重复记录任务"""
    try:
        from .duplicate_utils import DuplicateManager
        merged_count = DuplicateManager.auto_merge_duplicates()
        return {
            'merged_count': merged_count,
            'timestamp': timezone.now().isoformat()
        }
    except Exception as e:
        logger.error(f"自动合并重复记录任务失败: {str(e)}")
        return {'error': str(e)}


@shared_task
def get_duplicate_statistics_task():
    """获取重复记录统计任务"""
    try:
        from .duplicate_utils import DuplicateManager
        statistics = DuplicateManager.get_duplicate_statistics()
        return statistics
    except Exception as e:
        logger.error(f"获取重复记录统计任务失败: {str(e)}")
        return {'error': str(e)}


@shared_task
def batch_query_vin_for_vehicle_records_task():
    """批量查询行驶证的VIN信息 """
    try:
        logger.info("开始批量查询行驶证的VIN信息")

        # 查找有VIN码但没有车辆名称或生产年份的行驶证记录
        vehicle_results = VehicleLicenseResult.objects.filter(
            vin__isnull=False,
            vin__gt='',  # 确保VIN不为空字符串
        ).filter(
            Q(vehicle_name__isnull=True) | Q(vehicle_name='') |
            Q(production_year__isnull=True) | Q(production_year='')
        ).order_by('-created_at')[:100]  # 每次处理100条

        processed_count = 0
        success_count = 0

        for vehicle_result in vehicle_results:
            try:
                success = enrich_vehicle_license_with_vin(vehicle_result)
                if success:
                    success_count += 1
                processed_count += 1

            except Exception as e:
                logger.error(f"处理行驶证 {vehicle_result.id} 失败: {str(e)}")
                continue

        logger.info(f"批量VIN查询完成: 处理 {processed_count} 条记录, 成功 {success_count} 条")
        return {
            'processed_count': processed_count,
            'success_count': success_count,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"批量VIN查询任务失败: {str(e)}")
        return {'error': str(e)}


@shared_task
def periodic_duplicate_cleanup():
    """定期清理重复记录"""
    try:
        from .duplicate_utils import DuplicateManager

        logger.info("=== 开始定期清理重复记录 ===")

        # 1. 自动合并重复记录
        merged_count = DuplicateManager.auto_merge_duplicates()

        # 2. 获取重复统计信息
        statistics = DuplicateManager.get_duplicate_statistics()

        logger.info(f"定期清理完成: 合并 {merged_count} 条记录")
        logger.info(f"重复统计: {statistics}")

        return {
            'merged_count': merged_count,
            'statistics': statistics,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"定期清理重复记录失败: {str(e)}")
        return {'error': str(e)}


