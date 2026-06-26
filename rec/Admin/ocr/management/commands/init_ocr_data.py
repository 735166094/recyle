# init_ocr_data.py
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from ocr.models import HuaweiCloudConfig, OcrInterface, CertificateType


class Command(BaseCommand):
    help = '初始化OCR系统基础数据'

    def create_directories(self):
        """创建必要的目录结构"""
        directories = [
            os.path.join(settings.MEDIA_ROOT, 'ocr_images'),
            os.path.join(settings.MEDIA_ROOT, 'avatars'),
            os.path.join(settings.MEDIA_ROOT, 'temp'),
            os.path.join(settings.BASE_DIR, 'logs'),
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            self.stdout.write(f'创建目录: {directory}')


    def handle(self, *args, **options):
        self.stdout.write('开始初始化OCR系统基础数据...')

        # 创建必要的目录
        directories = [
            os.path.join(settings.MEDIA_ROOT, 'ocr_images'),
            os.path.join(settings.MEDIA_ROOT, 'avatars'),
            os.path.join(settings.MEDIA_ROOT, 'temp'),
            os.path.join(settings.BASE_DIR, 'logs'),
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            self.stdout.write(f'创建目录: {directory}')

        # 创建默认的华为云配置
        huawei_config, created = HuaweiCloudConfig.objects.get_or_create(
            name='华为云（默认）',
            defaults={
                'ak': 'HPUAMZXHGV8KJ4OF8E2V',
                'sk': '8yfgguAqENJPLIvba9XX0ZQ6ih6p2BjGdsIHRbLs',
                'region': 'cn-north-4',
                'is_active': True
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('创建默认华为云配置'))
        else:
            self.stdout.write('华为云配置已存在')

        # 创建OCR接口
        interfaces_data = [
            {
                'name': '通用文字识别',
                'interface_type': 'general_text',
                'description': '识别图片中的文字信息',
            },
            {
                'name': '身份证识别',
                'interface_type': 'id_card',
                'description': '识别身份证正反面信息',
            },
            {
                'name': '行驶证识别',
                'interface_type': 'vehicle_license',
                'description': '识别行驶证主页和副页信息',
            },
            {
                'name': '营业执照识别',
                'interface_type': 'business_license',
                'description': '识别营业执照信息',
            },
            {
                'name': '智能分类识别',
                'interface_type': 'auto_classification',
                'description': '自动分类并识别证件类型',
            },
        ]

        for interface_data in interfaces_data:
            interface, created = OcrInterface.objects.get_or_create(
                name=interface_data['name'],
                defaults={
                    'interface_type': interface_data['interface_type'],
                    'description': interface_data['description'],
                    'huawei_config': huawei_config,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'创建接口: {interface_data["name"]}'))
            else:
                self.stdout.write(f'接口已存在: {interface_data["name"]}')

        # 创建证件类型 - 确保创建4个类型
        certificate_types_data = [
            {
                'name': '身份证',
                'type_code': 'id_card',
                'interface_type': 'auto_classification',  # 使用智能分类接口
                'keywords': '居民身份证,公民身份号码,身份证',
            },
            {
                'name': '行驶证',
                'type_code': 'vehicle_license',
                'interface_type': 'vehicle_license',
                'keywords': '中华人民共和国机动车行驶证,行驶证,车辆识别代号',
            },
            {
                'name': '营业执照',
                'type_code': 'business_license',
                'interface_type': 'business_license',
                'keywords': '营业执照,企业名称,法定代表人',
            },
            {
                'name': '智能分类识别',
                'type_code': 'auto',
                'interface_type': 'auto_classification',
                'keywords': '自动识别,智能分类',
            },
        ]

        created_count = 0
        for cert_data in certificate_types_data:
            # 找到对应的接口
            interface = OcrInterface.objects.filter(
                interface_type=cert_data['interface_type'],
                is_active=True
            ).first()

            if interface:
                cert_type, created = CertificateType.objects.get_or_create(
                    name=cert_data['name'],
                    defaults={
                        'type_code': cert_data['type_code'],
                        'interface': interface,
                        'keywords': cert_data['keywords'],
                        'is_active': True
                    }
                )
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'创建证件类型: {cert_data["name"]}'))
                else:
                    # 更新已存在的证件类型
                    cert_type.type_code = cert_data['type_code']
                    cert_type.interface = interface
                    cert_type.keywords = cert_data['keywords']
                    cert_type.is_active = True
                    cert_type.save()
                    self.stdout.write(f'更新证件类型: {cert_data["name"]}')
            else:
                self.stdout.write(self.style.ERROR(f'未找到接口: {cert_data["interface_type"]}'))

        self.stdout.write(
            self.style.SUCCESS(f'共处理 {len(certificate_types_data)} 个证件类型，创建 {created_count} 个新类型'))

        # 验证最终数据
        total_active = CertificateType.objects.filter(is_active=True).count()
        self.stdout.write(self.style.SUCCESS(f'OCR系统基础数据初始化完成! 当前有 {total_active} 个激活的证件类型'))
