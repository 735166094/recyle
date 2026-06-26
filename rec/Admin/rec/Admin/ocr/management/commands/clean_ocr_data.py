# ocr/management/commands/clean_ocr_data.py
import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.cache import cache
from ocr.models import (
    HuaweiCloudConfig, OcrInterface, CertificateType,
    RecognitionRecord, VehicleLicenseResult, IdCardResult, BusinessLicenseResult
)
from ocr.cache_utils import CacheManager


class Command(BaseCommand):
    help = '清理OCR系统数据，为重新初始化做准备'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-images',
            action='store_true',
            help='保留图片文件，只清理数据库记录',
        )
        parser.add_argument(
            '--keep-config',
            action='store_true',
            help='保留华为云配置',
        )

    def handle(self, *args, **options):
        keep_images = options.get('keep_images')
        keep_config = options.get('keep_config')

        self.stdout.write('开始清理OCR系统数据...')

        # 清除所有缓存
        self.clear_cache()

        # 删除识别记录和相关文件
        self.clear_recognition_records(keep_images)

        # 删除证件类型
        self.clear_certificate_types()

        # 删除OCR接口
        self.clear_ocr_interfaces()

        # 删除华为云配置（可选）
        if not keep_config:
            self.clear_huawei_configs()

        self.stdout.write(
            self.style.SUCCESS('OCR系统数据清理完成!')
        )

    def clear_cache(self):
        """清除所有缓存"""
        try:
            cache.clear()
            CacheManager.clear_all_cache()
            self.stdout.write(self.style.SUCCESS('✓ 缓存已清除'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 清除缓存失败: {str(e)}'))

    def clear_recognition_records(self, keep_images):
        """清理识别记录和相关文件"""
        try:
            # 统计记录数量
            total_records = RecognitionRecord.objects.count()
            self.stdout.write(f'找到 {total_records} 条识别记录')

            # 删除相关的结果记录
            VehicleLicenseResult.objects.all().delete()
            IdCardResult.objects.all().delete()
            BusinessLicenseResult.objects.all().delete()
            self.stdout.write('✓ 相关结果记录已删除')

            # 删除识别记录和图片文件
            deleted_count = 0
            for record in RecognitionRecord.objects.all():
                # 删除图片文件
                if not keep_images and record.image:
                    try:
                        if os.path.isfile(record.image.path):
                            os.remove(record.image.path)
                            self.stdout.write(f'  删除图片文件: {record.image.path}')
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'  删除图片失败: {str(e)}'))

                # 删除数据库记录
                record.delete()
                deleted_count += 1

            self.stdout.write(self.style.SUCCESS(f'✓ 识别记录已删除: {deleted_count}/{total_records}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 清理识别记录失败: {str(e)}'))

    def clear_certificate_types(self):
        """清理证件类型"""
        try:
            count = CertificateType.objects.count()
            CertificateType.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ 证件类型已删除: {count} 个'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 清理证件类型失败: {str(e)}'))

    def clear_ocr_interfaces(self):
        """清理OCR接口"""
        try:
            count = OcrInterface.objects.count()
            OcrInterface.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ OCR接口已删除: {count} 个'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 清理OCR接口失败: {str(e)}'))

    def clear_huawei_configs(self):
        """清理华为云配置"""
        try:
            count = HuaweiCloudConfig.objects.count()
            HuaweiCloudConfig.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ 华为云配置已删除: {count} 个'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 清理华为云配置失败: {str(e)}'))