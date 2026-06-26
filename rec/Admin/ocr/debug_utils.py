import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def debug_ocr_result(ocr_result, record_id):
    """调试OCR识别结果"""
    try:
        if hasattr(ocr_result, 'to_dict'):
            result_dict = ocr_result.to_dict()
        else:
            result_dict = str(ocr_result)

        logger.info(f"=== OCR识别结果调试 ===")
        logger.info(f"记录ID: {record_id}")
        logger.info(f"时间: {datetime.now()}")
        logger.info(f"结果类型: {type(ocr_result)}")
        logger.info(f"结果数据: {result_dict}")
        logger.info(f"=== 调试结束 ===")

        return result_dict
    except Exception as e:
        logger.error(f"调试OCR结果失败: {str(e)}")
        return None


def debug_id_card_processing(id_card_result):
    """调试身份证处理过程"""
    try:
        logger.info(f"=== 身份证处理调试 ===")
        logger.info(f"身份证结果对象: {id_card_result}")
        if id_card_result:
            logger.info(f"姓名: {id_card_result.name}")
            logger.info(f"身份证号: {id_card_result.number}")
            logger.info(f"签发机关: {id_card_result.issue_authority}")
            logger.info(f"有效期: {id_card_result.valid_from} - {id_card_result.valid_to}")
            logger.info(f"面类型: {id_card_result.side}")
        logger.info(f"=== 身份证调试结束 ===")
    except Exception as e:
        logger.error(f"调试身份证处理失败: {str(e)}")


def debug_id_card_auto_classification(result_list, record_id):
    """调试智能分类身份证识别结果"""
    try:
        logger.info(f"=== 智能分类身份证识别调试 ===")
        logger.info(f"记录ID: {record_id}")
        logger.info(f"结果数量: {len(result_list)}")

        for i, item in enumerate(result_list):
            logger.info(f"项目 {i + 1}:")
            logger.info(f"  类型: {item.get('type')}")
            logger.info(f"  状态: {item.get('status')}")
            logger.info(f"  内容: {item.get('content')}")
            logger.info(f"  位置: {item.get('location')}")

        logger.info(f"=== 调试结束 ===")

    except Exception as e:
        logger.error(f"调试智能分类身份证结果失败: {str(e)}")


def debug_matching_status(record_id):
    """调试匹配状态"""
    try:
        from .models import RecognitionRecord, ScrapCarInfo
        from .signals import MatchEngine

        logger.info(f"=== 匹配状态调试 ===")
        logger.info(f"记录ID: {record_id}")

        # 获取记录
        record = RecognitionRecord.objects.get(id=record_id)
        logger.info(
            f"记录信息: 用户={record.user.username}, 类型={record.certificate_type.type_code if record.certificate_type else 'None'}, 状态={record.recognition_status}")

        if record.certificate_type and record.certificate_type.type_code == 'vehicle_license':
            # 检查行驶证结果
            if hasattr(record, 'vehicle_result'):
                vehicle_result = record.vehicle_result
                logger.info(f"行驶证结果: 车主={vehicle_result.owner_name}, 车牌={vehicle_result.number}")

                # 查找匹配记录
                id_card_record, business_record = MatchEngine.find_matching_records_recent(record, days=3)
                logger.info(
                    f"找到匹配: 身份证={id_card_record.id if id_card_record else '无'}, 营业执照={business_record.id if business_record else '无'}")

                # 计算匹配分数
                match_score, match_rules = MatchEngine.calculate_match_score(record, id_card_record, business_record)
                logger.info(f"匹配分数: {match_score}, 规则: {match_rules}")

                # 检查是否已存在报废车信息
                scrap_info = ScrapCarInfo.objects.filter(vehicle_record=record).first()
                if scrap_info:
                    logger.info(f"已存在报废车信息: ID={scrap_info.id}, 状态={scrap_info.match_status}")
                else:
                    logger.info("未找到对应的报废车信息")
            else:
                logger.info("无行驶证识别结果")

        elif record.certificate_type and record.certificate_type.type_code in ['id_card', 'business_license']:
            # 检查相关行驶证记录
            start_date = timezone.now() - timezone.timedelta(days=3)
            vehicle_records = RecognitionRecord.objects.filter(
                user=record.user,
                certificate_type__type_code='vehicle_license',
                recognition_status=True,
                created_at__gte=start_date
            )
            logger.info(f"找到 {len(vehicle_records)} 个相关行驶证记录")

            for vehicle_record in vehicle_records:
                if hasattr(vehicle_record, 'vehicle_result'):
                    logger.info(f"行驶证记录 {vehicle_record.id}: 车主={vehicle_record.vehicle_result.owner_name}")

        logger.info(f"=== 调试结束 ===")

    except Exception as e:
        logger.error(f"匹配状态调试失败: {str(e)}")
