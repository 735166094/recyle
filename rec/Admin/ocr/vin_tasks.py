# vin_tasks.py
import logging
from celery import shared_task
from django.utils import timezone
from .models import VehicleLicenseResult
from .utils import enrich_vehicle_license_with_vin

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def query_vin_for_vehicle_result_task(self, vehicle_result_id, model_index: int = 0):
    """
    为行驶证结果查询VIN信息的异步任务

    Args:
        vehicle_result_id: VehicleLicenseResult的ID
        model_index: 车型列表中的索引，默认取第一个
    """
    try:
        logger.info(f"开始处理VIN查询任务，行驶证结果ID: {vehicle_result_id}")

        # 获取行驶证结果
        vehicle_result = VehicleLicenseResult.objects.get(id=vehicle_result_id)

        if not vehicle_result.vin:
            logger.warning(f"行驶证结果 {vehicle_result_id} 没有VIN码，跳过查询")
            return False

        # 查询VIN信息
        success = enrich_vehicle_license_with_vin(vehicle_result, model_index)

        if success:
            logger.info(f"VIN查询任务完成，行驶证结果ID: {vehicle_result_id}, "
                        f"车辆名称: {vehicle_result.vehicle_name}, "
                        f"生产年份: {vehicle_result.production_year}")
        else:
            logger.warning(f"VIN查询任务失败，行驶证结果ID: {vehicle_result_id}")

        return success

    except VehicleLicenseResult.DoesNotExist:
        logger.error(f"行驶证结果不存在，ID: {vehicle_result_id}")
        return False

    except Exception as e:
        logger.error(f"VIN查询任务异常: {str(e)}")

        # 重试逻辑
        try:
            self.retry(countdown=2 ** self.request.retries, exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"VIN查询任务达到最大重试次数，行驶证结果ID: {vehicle_result_id}")
            return False
