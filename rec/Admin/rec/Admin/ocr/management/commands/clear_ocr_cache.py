# ocr/management/commands/clear_ocr_cache.py
from django.core.management.base import BaseCommand
from django.core.cache import cache
from ocr.cache_utils import CacheManager


class Command(BaseCommand):
    help = '清除OCR系统所有缓存'

    def handle(self, *args, **options):
        self.stdout.write('开始清除OCR系统缓存...')

        try:
            # 清除Django默认缓存
            cache.clear()
            self.stdout.write(self.style.SUCCESS('✓ Django缓存已清除'))

            # 清除OCR自定义缓存
            CacheManager.clear_all_cache()
            self.stdout.write(self.style.SUCCESS('✓ OCR缓存已清除'))

            self.stdout.write(self.style.SUCCESS('所有缓存清除完成!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'清除缓存失败: {str(e)}'))