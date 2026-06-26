import logging
import datetime
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.core.cache import cache
from django.db.models import Q
from .models import RecognitionRecord, ScrapCarInfo

logger = logging.getLogger(__name__)


class MatchEngine:
    """匹配引擎 """

    @staticmethod
    def normalize_name(name):
        """标准化姓名，去除空格和特殊字符"""
        if not name:
            return ""
        # 去除所有空格和特殊字符，转换为小写
        return ''.join(str(name).split()).lower()

    @staticmethod
    def exact_name_match(name1, name2):
        """精确姓名匹配"""
        if not name1 or not name2:
            return False
        return MatchEngine.normalize_name(name1) == MatchEngine.normalize_name(name2)

    @staticmethod
    def find_best_match(vehicle_record, candidate_records, record_type):
        """查找最佳匹配记录"""
        if not candidate_records:
            return None

        # 获取行驶证车主姓名
        vehicle_owner = ""
        if hasattr(vehicle_record, 'vehicle_result') and vehicle_record.vehicle_result.owner_name:
            vehicle_owner = vehicle_record.vehicle_result.owner_name

        if not vehicle_owner:
            return None

        # 过滤出姓名匹配的记录
        matched_records = []
        for record in candidate_records:
            if record_type == 'id_card' and hasattr(record, 'id_card_result'):
                id_name = record.id_card_result.name
                if id_name and MatchEngine.exact_name_match(vehicle_owner, id_name):
                    matched_records.append(record)
            elif record_type == 'business_license' and hasattr(record, 'business_result'):
                business_name = record.business_result.name
                if business_name and MatchEngine.exact_name_match(vehicle_owner, business_name):
                    matched_records.append(record)

        if not matched_records:
            return None

        # 按时间最接近排序（与车辆记录时间差最小）
        vehicle_time = vehicle_record.created_at
        matched_records.sort(
            key=lambda x: abs((x.created_at - vehicle_time).total_seconds())
        )

        best_match = matched_records[0]
        logger.info(
            f"找到最佳{record_type}匹配: {best_match.id}, 时间差: {abs((best_match.created_at - vehicle_time).total_seconds())}秒")

        return best_match

    @staticmethod
    def find_matching_records_recent(vehicle_record, days=3):
        """为行驶证记录查找最近N天的匹配记录"""
        try:
            if not hasattr(vehicle_record, 'vehicle_result'):
                logger.warning(f"行驶证记录 {vehicle_record.id} 没有关联的识别结果")
                return None, None

            vehicle_result = vehicle_record.vehicle_result
            vehicle_owner = vehicle_result.owner_name

            if not vehicle_owner:
                logger.warning(f"行驶证记录 {vehicle_record.id} 没有车主姓名")
                return None, None

            # 获取最近N天的日期范围
            end_date = timezone.now()
            start_date = end_date - timezone.timedelta(days=days)

            logger.info(f"为车辆记录 {vehicle_record.id} 查找{start_date.date()}到{end_date.date()}的匹配记录")

            # 查找最近的身份证记录（同一用户）
            id_card_candidates = RecognitionRecord.objects.filter(
                user=vehicle_record.user,
                certificate_type__type_code='id_card',
                recognition_status=True,
                created_at__range=(start_date, end_date)
            ).select_related('id_card_result').order_by('-created_at')

            id_card_record = MatchEngine.find_best_match(
                vehicle_record, id_card_candidates, 'id_card'
            )

            # 查找最近的营业执照记录（同一用户）
            business_candidates = RecognitionRecord.objects.filter(
                user=vehicle_record.user,
                certificate_type__type_code='business_license',
                recognition_status=True,
                created_at__range=(start_date, end_date)
            ).select_related('business_result').order_by('-created_at')

            business_record = MatchEngine.find_best_match(
                vehicle_record, business_candidates, 'business_license'
            )

            logger.info(f"匹配结果 - 身份证: {id_card_record.id if id_card_record else '无'}, "
                        f"营业执照: {business_record.id if business_record else '无'}")

            return id_card_record, business_record

        except Exception as e:
            logger.error(f"查找匹配记录失败: {str(e)}")
            return None, None

    @staticmethod
    def calculate_match_score(vehicle_record, id_card_record, business_record):
        """计算匹配分数"""
        score = 0
        match_rules = []

        try:
            if not hasattr(vehicle_record, 'vehicle_result'):
                return 0, []

            vehicle_result = vehicle_record.vehicle_result
            vehicle_owner = vehicle_result.owner_name

            if not vehicle_owner:
                return 0, []

            # 身份证匹配
            if id_card_record and hasattr(id_card_record, 'id_card_result'):
                id_card_result = id_card_record.id_card_result
                id_card_name = id_card_result.name

                if id_card_name and MatchEngine.exact_name_match(vehicle_owner, id_card_name):
                    score += 50
                    match_rules.append('身份证姓名匹配')
                    logger.info(f"身份证匹配成功: {vehicle_owner} == {id_card_name}")

            # 营业执照匹配
            if business_record and hasattr(business_record, 'business_result'):
                business_result = business_record.business_result
                business_name = business_result.name

                if business_name and MatchEngine.exact_name_match(vehicle_owner, business_name):
                    score += 50
                    match_rules.append('营业执照企业名称匹配')
                    logger.info(f"营业执照匹配成功: {vehicle_owner} == {business_name}")

            # 额外加分项
            if score > 0:
                # 所有证件识别成功
                if vehicle_record.recognition_status and \
                        (not id_card_record or id_card_record.recognition_status) and \
                        (not business_record or business_record.recognition_status):
                    score += 20
                    match_rules.append('所有证件识别成功')

                # 证件在同一用户下
                user_ids = {vehicle_record.user_id}
                if id_card_record:
                    user_ids.add(id_card_record.user_id)
                if business_record:
                    user_ids.add(business_record.user_id)

                if len(user_ids) == 1:
                    score += 10
                    match_rules.append('同一用户上传')

            logger.info(f"匹配分数计算完成: {score}分, 规则: {match_rules}")

        except Exception as e:
            logger.error(f"计算匹配分数失败: {str(e)}")

        return score, match_rules

    @staticmethod
    def create_or_update_scrap_car_info(vehicle_record):
        """创建或更新报废车信息 """
        try:
            logger.info(f"开始为车辆记录 {vehicle_record.id} 创建或更新报废车信息")

            # 查找匹配记录
            id_card_record, business_record = MatchEngine.find_matching_records_recent(vehicle_record, days=3)

            # 计算匹配分数
            match_score, match_rules = MatchEngine.calculate_match_score(
                vehicle_record, id_card_record, business_record
            )

            # 确定匹配状态
            if match_score >= 50:
                match_status = 'matched'
                matched_at = timezone.now()
            elif match_score > 0:
                match_status = 'manual_review'
                matched_at = None
            else:
                match_status = 'unmatched'
                matched_at = None

            logger.info(f"匹配状态: {match_status}, 分数: {match_score}")

            # 验证是否应该创建记录
            should_create = match_score > 0 or (id_card_record or business_record)

            if not should_create:
                logger.info(f"车辆记录 {vehicle_record.id} 无有效匹配，跳过创建报废车信息")
                return None

            # 创建报废车信息对象（但先不保存到数据库）
            scrap_info = ScrapCarInfo(
                vehicle_record=vehicle_record,
                id_card_record=id_card_record,
                business_record=business_record,
                match_status=match_status,
                match_score=match_score,
                match_rules=match_rules,
                matched_at=matched_at
            )

            # 填充数据
            scrap_info._populate_from_related_records()

            # 验证数据有效性
            if not scrap_info._has_valid_data():
                logger.warning(f"创建报废车信息记录数据不完整，跳过创建")
                return None

            # 关键修改：在保存前进行去重检查
            logger.info(f"=== 进行去重检查 ===")
            logger.info(
                f"准备创建的记录关键字段 - 车主: '{scrap_info.owner_name}', 车牌: '{scrap_info.vehicle_number}', VIN: '{scrap_info.vin}'")

            # 查找重复记录
            duplicate_records = ScrapCarInfo.find_duplicate_records(scrap_info)

            if duplicate_records.exists():
                logger.info(f"找到 {duplicate_records.count()} 条潜在重复记录")

                # 按创建时间排序，找到最新的重复记录
                latest_duplicate = duplicate_records.order_by('-created_at').first()
                logger.info(
                    f"最新重复记录: ID={latest_duplicate.id}, 车主='{latest_duplicate.owner_name}', 车牌='{latest_duplicate.vehicle_number}', VIN='{latest_duplicate.vin}'")

                # 比较数据完整性
                from .duplicate_utils import DuplicateManager

                new_score = DuplicateManager._calculate_completeness_score(scrap_info)
                old_score = DuplicateManager._calculate_completeness_score(latest_duplicate)
                logger.info(f"数据完整性得分 - 新记录: {new_score}, 旧记录: {old_score}")

                if DuplicateManager._is_record_more_complete(scrap_info, latest_duplicate):
                    # 新记录更完整，替换旧记录
                    logger.info("新记录数据更完整，将替换旧记录")

                    # 复制新记录的数据到旧记录
                    if latest_duplicate.replace_duplicate_record(scrap_info):
                        logger.info(f"成功替换重复记录: 保留记录={latest_duplicate.id}")
                        return latest_duplicate
                    else:
                        logger.error("替换重复记录失败")
                        # 创建新记录
                        scrap_info.save()
                        return scrap_info
                else:
                    # 旧记录更完整，跳过新记录
                    logger.info("现有记录数据更完整，跳过新记录")
                    return latest_duplicate
            else:
                # 没有重复记录，创建新记录
                logger.info("无重复记录，创建新记录")
                scrap_info.save()
                return scrap_info

        except Exception as e:
            logger.error(f"创建报废车信息失败: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def trigger_matching_for_record(record):
        """为单个记录触发匹配"""
        try:
            if not record.recognition_status:
                logger.info(f"记录 {record.id} 识别未成功，跳过匹配")
                return None

            certificate_type = record.certificate_type.type_code if record.certificate_type else None

            logger.info(f"开始匹配处理: 记录ID {record.id}, 类型: {certificate_type}")

            if certificate_type == 'vehicle_license':
                # 行驶证记录 - 直接创建匹配
                result = MatchEngine.create_or_update_scrap_car_info(record)
                if result:
                    logger.info(f"行驶证记录匹配成功，创建报废车信息: {result.id}")
                else:
                    logger.info(f"行驶证记录无匹配: {record.id}")
                return result

            elif certificate_type in ['id_card', 'business_license']:
                # 身份证或营业执照记录 - 查找相关的行驶证记录
                start_date = timezone.now() - timezone.timedelta(days=3)
                vehicle_records = RecognitionRecord.objects.filter(
                    user=record.user,
                    certificate_type__type_code='vehicle_license',
                    recognition_status=True,
                    created_at__gte=start_date
                ).select_related('vehicle_result')

                results = []
                for vehicle_record in vehicle_records:
                    scrap_info = MatchEngine.create_or_update_scrap_car_info(vehicle_record)
                    if scrap_info:
                        results.append(scrap_info)

                logger.info(f"为{record.certificate_type}记录 {record.id} 触发了 {len(results)} 个匹配")
                return results

            logger.info(f"记录类型 {certificate_type} 不支持匹配")
            return None

        except Exception as e:
            logger.error(f"触发匹配失败: {str(e)}")
            return None


@receiver(post_save, sender=RecognitionRecord)
def handle_new_recognition_record(sender, instance, created, **kwargs):
    """处理新识别记录 """
    try:
        # 只处理识别成功的记录
        if not instance.recognition_status:
            logger.info(f"记录 {instance.id} 识别未成功，跳过匹配处理")
            return

        # 只处理行驶证、身份证、营业执照
        if not instance.certificate_type or \
                instance.certificate_type.type_code not in ['vehicle_license', 'id_card', 'business_license']:
            logger.info(f"记录 {instance.id} 类型不支持匹配")
            return

        logger.info(f"开始处理新识别记录匹配: 记录ID {instance.id}, 类型: {instance.certificate_type.type_code}")

        # 检查是否已经处理过匹配（通过缓存标记）
        cache_key = f"match_processed_{instance.id}"
        if cache.get(cache_key):
            logger.info(f"记录 {instance.id} 已经处理过匹配，跳过")
            return

        # 设置缓存标记，防止重复处理
        cache.set(cache_key, True, 60)  # 60秒内不再处理

        # 使用事务确保数据一致性
        with transaction.atomic():
            result = MatchEngine.trigger_matching_for_record(instance)

            if result:
                if isinstance(result, list):
                    logger.info(f"匹配处理完成: 为记录 {instance.id} 创建了 {len(result)} 个匹配")
                else:
                    logger.info(f"匹配处理完成: 创建了报废车信息记录 {result.id}")
            else:
                logger.info(f"匹配处理完成: 记录 {instance.id} 无匹配")

    except Exception as e:
        logger.error(f"处理新识别记录失败: {str(e)}")
