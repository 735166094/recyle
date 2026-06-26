# duplicate_utils.py
import logging
from django.utils import timezone
from .models import ScrapCarInfo

logger = logging.getLogger(__name__)


class DuplicateManager:
    """重复数据管理工具类"""

    @staticmethod
    def _calculate_completeness_score(record):
        """计算记录的数据完整性分数 """
        score = 0

        # 基础字段检查
        fields_to_check = [
            'owner_name', 'identification_number', 'vehicle_number',
            'vin', 'brand', 'vehicle_model', 'engine_no'
        ]

        for field in fields_to_check:
            value = getattr(record, field, '')
            if value and str(value).strip():
                score += 2  # 提高基础字段的权重

        # 匹配状态加分
        if record.match_status == 'matched':
            score += 3
        elif record.match_status == 'manual_review':
            score += 1

        # 匹配分数加分
        if record.match_score >= 80:
            score += 3
        elif record.match_score >= 50:
            score += 2
        elif record.match_score > 0:
            score += 1

        # 关联记录加分
        if record.id_card_record and record.business_record:
            score += 4
        elif record.id_card_record:
            score += 2
        elif record.business_record:
            score += 2

        # 额外字段检查
        extra_fields = ['address', 'use_character', 'register_date', 'energy_type']
        for field in extra_fields:
            value = getattr(record, field, '')
            if value and str(value).strip():
                score += 1

        return score

    @staticmethod
    def check_and_handle_duplicates(new_record):
        """
        检查并处理重复记录
        """
        try:
            logger.info(f"=== 开始检查重复记录 ===")
            logger.info(f"新记录ID: {new_record.id}")
            logger.info(
                f"新记录关键字段 - 车主: '{new_record.owner_name}', 车牌: '{new_record.vehicle_number}', VIN: '{new_record.vin}'")

            # 查找重复记录
            duplicate_records = ScrapCarInfo.find_duplicate_records(new_record)
            logger.info(f"找到 {duplicate_records.count()} 条潜在重复记录")

            if not duplicate_records.exists():
                logger.info("未发现重复记录，创建新记录")
                return False, new_record, 'created'

            # 显示所有重复记录的详细信息
            for i, dup in enumerate(duplicate_records):
                logger.info(
                    f"重复记录 {i + 1}: ID={dup.id}, 车主='{dup.owner_name}', 车牌='{dup.vehicle_number}', VIN='{dup.vin}'")

            # 按创建时间排序，找到最新的重复记录
            latest_duplicate = duplicate_records.order_by('-created_at').first()
            logger.info(f"选择最新的重复记录进行比对: ID={latest_duplicate.id}")

            # 详细比较数据完整性
            new_score = DuplicateManager._calculate_completeness_score(new_record)
            old_score = DuplicateManager._calculate_completeness_score(latest_duplicate)
            logger.info(f"数据完整性得分 - 新记录: {new_score}, 旧记录: {old_score}")

            # 比较创建时间
            logger.info(f"创建时间 - 新记录: {new_record.created_at}, 旧记录: {latest_duplicate.created_at}")

            if DuplicateManager._is_record_more_complete(new_record, latest_duplicate):
                logger.info("新记录数据更完整，将替换旧记录")
                # 用新记录替换旧记录
                if new_record.replace_duplicate_record(latest_duplicate):
                    # 删除新创建的记录（因为数据已经合并到旧记录中）
                    new_record_pk = new_record.pk
                    new_record.delete()
                    logger.info(f"成功替换重复记录: 保留记录={latest_duplicate.id}, 删除新记录={new_record_pk}")
                    return True, latest_duplicate, 'replaced'
                else:
                    logger.error("替换重复记录失败，保留新记录")
                    return True, new_record, 'skipped'
            else:
                logger.info("现有记录数据更完整，跳过新记录")
                # 删除新记录，保留现有记录
                new_record_pk = new_record.pk
                new_record.delete()
                return True, latest_duplicate, 'skipped'

        except Exception as e:
            logger.error(f"检查处理重复记录时发生错误: {str(e)}", exc_info=True)
            return False, new_record, 'created'

    @staticmethod
    def _is_record_more_complete(record1, record2):
        """判断记录1是否比记录2更完整"""
        try:
            # 检查是否有 created_at 字段
            created_at1 = record1.created_at if hasattr(record1, 'created_at') else None
            created_at2 = record2.created_at if hasattr(record2, 'created_at') else None

            # 如果有一个为 None，处理特殊情况
            if created_at1 is None and created_at2 is None:
                is_newer = False
            elif created_at1 is None:
                is_newer = False  # 没有创建时间，认为不是更新的
            elif created_at2 is None:
                is_newer = True  # 另一个没有创建时间，这个有，认为是更新的
            else:
                # 两个都有创建时间，正常比较
                is_newer = created_at1 > created_at2

            # 比较数据完整性
            completeness_score1 = DuplicateManager._calculate_completeness_score(record1)
            completeness_score2 = DuplicateManager._calculate_completeness_score(record2)

            # 判断哪个记录更完整
            is_more_complete = completeness_score1 > completeness_score2

            # 如果完整性相同，使用创建时间判断
            if completeness_score1 == completeness_score2:
                return is_newer

            return is_more_complete

        except Exception as e:
            logger.error(f"判断记录完整性失败: {str(e)}")
            return False

    @staticmethod
    def _get_record_key(record):
        """
        生成记录的唯一键用于重复检测
        """
        key_parts = []

        # 清理字符串的辅助函数
        def clean_string(s):
            if not s:
                return ""
            return str(s).strip().upper().replace(' ', '').replace('-', '').replace('_', '')

        vin = clean_string(record.vin)
        vehicle_number = clean_string(record.vehicle_number)
        owner_name = clean_string(record.owner_name)
        brand = clean_string(record.brand)
        vehicle_model = clean_string(record.vehicle_model)
        engine_no = clean_string(record.engine_no)

        logger.info(f"生成键的字段 - VIN: '{vin}', 车牌: '{vehicle_number}', 车主: '{owner_name}'")

        # 优先级1: VIN码（最准确）
        if vin and len(vin) >= 5:  # VIN码通常有17位，但至少需要5位才能有效
            key_parts.append(f"VIN:{vin}")
            logger.info(f"使用VIN生成键: {vin}")

        # 优先级2: 车牌号码
        elif vehicle_number and len(vehicle_number) >= 4:
            key_parts.append(f"VEHICLE:{vehicle_number}")
            logger.info(f"使用车牌生成键: {vehicle_number}")

        # 优先级3: 车主+品牌+型号组合
        elif (owner_name and len(owner_name) >= 2 and
              brand and len(brand) >= 2 and
              vehicle_model and len(vehicle_model) >= 2):
            combo_key = f"COMBO:{owner_name}_{brand}_{vehicle_model}"
            key_parts.append(combo_key)
            logger.info(f"使用组合生成键: {combo_key}")

        # 优先级4: 发动机号
        elif engine_no and len(engine_no) >= 4:
            key_parts.append(f"ENGINE:{engine_no}")
            logger.info(f"使用发动机号生成键: {engine_no}")

        else:
            # 如果没有足够的关键字段，使用ID作为后备（这样就不会与其他记录重复）
            key_parts.append(f"ID:{record.id}")
            logger.info(f"使用ID生成键: {record.id}")

        final_key = "|".join(key_parts)
        logger.info(f"最终生成的键: {final_key}")
        return final_key

    @staticmethod
    def auto_merge_duplicates():
        """
        自动合并系统中的重复记录
        """
        try:
            logger.info("=== 开始自动合并重复记录 ===")
            merged_count = 0
            deleted_count = 0

            # 获取所有记录，按创建时间降序排序（新的在前）
            all_records = ScrapCarInfo.objects.all().order_by('-created_at')
            logger.info(f"总记录数: {all_records.count()}")

            processed_records = {}
            records_to_delete = set()

            for record in all_records:
                # 如果记录已经在删除列表中，跳过
                if record.id in records_to_delete:
                    continue

                record_key = DuplicateManager._get_record_key(record)
                logger.info(f"处理记录: ID={record.id}, 键={record_key}")

                if record_key in processed_records:
                    # 找到重复记录，合并它们
                    existing_record = processed_records[record_key]
                    logger.info(f"发现重复记录: 当前记录ID={record.id}, 已处理记录ID={existing_record.id}")

                    # 检查哪个记录更完整
                    if DuplicateManager._is_record_more_complete(record, existing_record):
                        # 当前记录更完整，用当前记录替换现有记录
                        logger.info(f"当前记录 {record.id} 更完整，将替换已处理记录 {existing_record.id}")

                        # 复制当前记录的数据到现有记录
                        if DuplicateManager._copy_record_data(record, existing_record):
                            records_to_delete.add(record.id)
                            processed_records[record_key] = existing_record  # 保持引用为现有记录
                            merged_count += 1
                            logger.info(f"成功合并: 保留={existing_record.id}, 删除={record.id}")
                        else:
                            logger.error(f"复制记录数据失败")
                    else:
                        # 现有记录更完整，删除当前记录
                        logger.info(f"已处理记录 {existing_record.id} 更完整，将删除当前记录 {record.id}")
                        records_to_delete.add(record.id)
                        merged_count += 1
                        logger.info(f"合并完成: 保留={existing_record.id}, 删除={record.id}")
                else:
                    # 没有重复，添加到已处理记录中
                    processed_records[record_key] = record
                    logger.info(f"记录 {record.id} 无重复，添加到已处理记录")

            # 执行批量删除
            if records_to_delete:
                deleted_count = ScrapCarInfo.objects.filter(id__in=records_to_delete).delete()[0]
                logger.info(f"实际删除记录数: {deleted_count}")

            logger.info(f"自动合并完成: 共处理 {merged_count} 条记录, 实际删除 {deleted_count} 条记录")
            return merged_count

        except Exception as e:
            logger.error(f"自动合并重复记录失败: {str(e)}", exc_info=True)
            return 0

    @staticmethod
    def _copy_record_data(source_record, target_record):
        """
        将源记录的数据复制到目标记录
        """
        try:
            # 复制基础字段
            target_record.owner_name = source_record.owner_name
            target_record.identification_number = source_record.identification_number
            target_record.address = source_record.address
            target_record.vin = source_record.vin
            target_record.vehicle_number = source_record.vehicle_number
            target_record.vehicle_type = source_record.vehicle_type
            target_record.use_character = source_record.use_character
            target_record.brand = source_record.brand
            target_record.vehicle_model = source_record.vehicle_model
            target_record.engine_no = source_record.engine_no
            target_record.approved_passengers = source_record.approved_passengers
            target_record.register_date = source_record.register_date
            target_record.energy_type = source_record.energy_type
            target_record.unladen_mass = source_record.unladen_mass
            target_record.remarks = source_record.remarks

            # 复制关联记录（如果源记录有更好的关联）
            if source_record.vehicle_record and not target_record.vehicle_record:
                target_record.vehicle_record = source_record.vehicle_record
            if source_record.id_card_record and not target_record.id_card_record:
                target_record.id_card_record = source_record.id_card_record
            if source_record.business_record and not target_record.business_record:
                target_record.business_record = source_record.business_record

            # 复制匹配信息（如果源记录匹配状态更好）
            if source_record.match_status == 'matched' and target_record.match_status != 'matched':
                target_record.match_status = source_record.match_status
                target_record.match_score = source_record.match_score
                target_record.match_rules = source_record.match_rules
                target_record.matched_at = source_record.matched_at
            elif source_record.match_score > target_record.match_score:
                target_record.match_status = source_record.match_status
                target_record.match_score = source_record.match_score
                target_record.match_rules = source_record.match_rules
                if source_record.matched_at:
                    target_record.matched_at = source_record.matched_at

            target_record.save()
            logger.info(f"成功复制记录数据: 从 {source_record.id} 到 {target_record.id}")
            return True

        except Exception as e:
            logger.error(f"复制记录数据失败: {str(e)}")
            return False

    @staticmethod
    def get_duplicate_statistics():
        """
        获取重复记录统计信息

        Returns:
            dict: 统计信息
        """
        try:
            total_records = ScrapCarInfo.objects.count()

            # 检测潜在的重复记录组
            potential_duplicates = 0
            records_by_key = {}

            for record in ScrapCarInfo.objects.all():
                record_key = DuplicateManager._get_record_key(record)
                if record_key in records_by_key:
                    records_by_key[record_key].append(record)
                else:
                    records_by_key[record_key] = [record]

            # 统计有重复的组
            duplicate_groups = 0
            for key, records in records_by_key.items():
                if len(records) > 1 and not key.startswith('id:'):
                    duplicate_groups += 1
                    potential_duplicates += len(records)

            return {
                'total_records': total_records,
                'potential_duplicates': potential_duplicates,
                'duplicate_groups': duplicate_groups,
                'unique_records': total_records - potential_duplicates + duplicate_groups
            }

        except Exception as e:
            logger.error(f"获取重复记录统计失败: {str(e)}")
            return {}

    @staticmethod
    def find_and_merge_duplicates_on_save(new_record):
        """在保存时查找并合并重复记录"""
        try:
            logger.info(f"=== 保存时去重检查 ===")
            logger.info(
                f"新记录关键字段 - 车主: '{new_record.owner_name}', 车牌: '{new_record.vehicle_number}', VIN: '{new_record.vin}'")

            # 查找重复记录
            duplicate_records = ScrapCarInfo.find_duplicate_records(new_record)
            logger.info(f"找到 {duplicate_records.count()} 条潜在重复记录")

            if not duplicate_records.exists():
                logger.info("未发现重复记录，创建新记录")
                return False, new_record, 'created'

            # 显示所有重复记录的详细信息
            for i, dup in enumerate(duplicate_records):
                logger.info(
                    f"重复记录 {i + 1}: ID={dup.id}, 车主='{dup.owner_name}', 车牌='{dup.vehicle_number}', VIN='{dup.vin}'")

            # 按创建时间排序，找到最新的重复记录
            latest_duplicate = duplicate_records.order_by('-created_at').first()
            logger.info(f"选择最新的重复记录进行比对: ID={latest_duplicate.id}")

            # 详细比较数据完整性
            new_score = DuplicateManager._calculate_completeness_score(new_record)
            old_score = DuplicateManager._calculate_completeness_score(latest_duplicate)
            logger.info(f"数据完整性得分 - 新记录: {new_score}, 旧记录: {old_score}")

            if DuplicateManager._is_record_more_complete(new_record, latest_duplicate):
                logger.info("新记录数据更完整，将替换旧记录")
                # 用新记录替换旧记录
                if new_record.replace_duplicate_record(latest_duplicate):
                    logger.info(f"成功替换重复记录: 保留记录={latest_duplicate.id}")
                    return True, latest_duplicate, 'replaced'
                else:
                    logger.error("替换重复记录失败，保留新记录")
                    return True, new_record, 'skipped'
            else:
                logger.info("现有记录数据更完整，跳过新记录")
                return True, latest_duplicate, 'skipped'

        except Exception as e:
            logger.error(f"保存时去重检查失败: {str(e)}", exc_info=True)
            return False, new_record, 'created'
