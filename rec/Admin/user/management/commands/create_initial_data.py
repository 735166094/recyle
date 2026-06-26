from django.core.management.base import BaseCommand
from user.models import User, EmployeeApp
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '创建初始测试数据'

    def handle(self, *args, **options):
        self.stdout.write('开始创建初始测试数据...')

        # 1. 创建测试员工账号
        test_employee_data = {
            'username': 'test_employee',
            'staff_id': 'EMP001',
            'employee_id': 'EMP001',
            'real_name': '测试员工',
            'department': '技术部',
            'position': '测试工程师',
            'phone': '13800138000',
            'email': 'test@company.com',
            'is_staff_member': True,
            'ocr_user_type': 'employee',
            'is_active': True
        }

        try:
            # 先检查是否已存在
            existing_user = User.objects.filter(staff_id='EMP001').first()
            if existing_user:
                # 更新密码为默认密码
                existing_user.set_password('111@chery')
                existing_user.save()
                self.stdout.write(self.style.SUCCESS(f'更新员工账号: {existing_user.staff_id}'))
            else:
                # 创建新员工
                user = User.objects.create(**test_employee_data)
                user.set_password('111@chery')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'创建员工账号: {user.staff_id}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'创建员工账号失败: {str(e)}'))

        # 2. 创建测试管理员账号
        admin_employee_data = {
            'username': 'admin_employee',
            'staff_id': 'ADMIN001',
            'employee_id': 'ADMIN001',
            'real_name': '管理员',
            'department': '信息部',
            'position': '系统管理员',
            'phone': '13900139000',
            'email': 'admin@company.com',
            'is_staff_member': True,
            'is_staff': True,
            'is_superuser': True,
            'ocr_user_type': 'admin',
            'is_active': True
        }

        try:
            # 先检查是否已存在
            existing_admin = User.objects.filter(staff_id='ADMIN001').first()
            if existing_admin:
                # 更新密码为默认密码
                existing_admin.set_password('111@chery')
                existing_admin.save()
                self.stdout.write(self.style.SUCCESS(f'更新管理员账号: {existing_admin.staff_id}'))
            else:
                # 创建新管理员
                admin_user = User.objects.create(**admin_employee_data)
                admin_user.set_password('111@chery')
                admin_user.save()
                self.stdout.write(self.style.SUCCESS(f'创建管理员账号: {admin_user.staff_id}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'创建管理员账号失败: {str(e)}'))

        # 3. 创建应用系统（根据新的模型结构）
        default_apps = [
            # OCR系统 - 内部应用
            {
                'app_id': 'ocr_system',
                'app_name': 'OCR识别系统',
                'app_desc': '证件识别与管理',
                'icon_class': 'iconfont icon-OCR',
                'open_type': 'internal',
                'internal_path': 'pages/ocr/index/index',
                'app_url': '',  # 可以为空，使用internal_path
                'webview_url': '',  # 外部网页地址，内部应用不需要
                'miniapp_path': '',  # 小程序路径，内部应用不需要
                'access_roles': ['admin', 'manager', 'employee'],  # 可访问的角色
                'require_auth': True,
                'app_config': {
                    'version': '1.0.0',
                    'theme': 'default',
                    'permissions': ['view', 'upload', 'download']
                },
                'is_active': True,
                'sort_order': 1
            },
            # 地磅系统 - 内部应用（待开发）
            {
                'app_id': 'scale_system',
                'app_name': '地磅系统',
                'app_desc': '货物称重与管理',
                'icon_class': 'iconfont icon-dibang',
                'open_type': 'internal',
                'internal_path': 'pages/under_construction/under_construction',
                'app_url': '',  # 可以为空，使用internal_path
                'webview_url': '',  # 外部网页地址
                'miniapp_path': '',  # 小程序路径
                'access_roles': ['admin', 'manager', 'warehouse'],  # 仓库角色
                'require_auth': True,
                'app_config': {
                    'version': '0.1.0',
                    'status': 'developing',
                    'message': '系统开发中'
                },
                'is_active': True,
                'sort_order': 2
            },
            # 用车系统 - 内部应用（待开发）
            {
                'app_id': 'car_system',
                'app_name': '用车系统',
                'app_desc': '车辆调度与预约',
                'icon_class': 'iconfont icon-car',
                'open_type': 'internal',
                'internal_path': 'pages/under_construction/under_construction',
                'app_url': '',  # 可以为空，使用internal_path
                'webview_url': '',  # 外部网页地址
                'miniapp_path': '',  # 小程序路径
                'access_roles': ['admin', 'manager', 'employee'],  # 所有员工
                'require_auth': True,
                'app_config': {
                    'version': '0.1.0',
                    'status': 'developing',
                    'message': '系统开发中'
                },
                'is_active': True,
                'sort_order': 3
            },
            # 住房系统 - 内部应用（待开发）
            {
                'app_id': 'house_system',
                'app_name': '住房系统',
                'app_desc': '宿舍分配与管理',
                'icon_class': 'iconfont icon-house',
                'open_type': 'internal',
                'internal_path': 'pages/under_construction/under_construction',
                'app_url': '',  # 可以为空，使用internal_path
                'webview_url': '',  # 外部网页地址
                'miniapp_path': '',  # 小程序路径
                'access_roles': ['admin', 'hr', 'employee'],  # HR和员工
                'require_auth': True,
                'app_config': {
                    'version': '0.1.0',
                    'status': 'developing',
                    'message': '系统开发中'
                },
                'is_active': True,
                'sort_order': 4
            },
            # 订餐系统 - 内部应用（待开发）
            {
                'app_id': 'food_system',
                'app_name': '订餐系统',
                'app_desc': '食堂预订与点餐',
                'icon_class': 'iconfont icon-food',
                'open_type': 'internal',
                'internal_path': 'pages/under_construction/under_construction',
                'app_url': '',  # 可以为空，使用internal_path
                'webview_url': '',  # 外部网页地址
                'miniapp_path': '',  # 小程序路径
                'access_roles': ['admin', 'employee'],  # 所有员工
                'require_auth': True,
                'app_config': {
                    'version': '0.1.0',
                    'status': 'developing',
                    'message': '系统开发中'
                },
                'is_active': True,
                'sort_order': 5
            },
            # 人事系统 - WebView外部应用（示例）
            {
                'app_id': 'hr_system',
                'app_name': '人事系统',
                'app_desc': '人力资源管理系统',
                'icon_class': 'iconfont icon-hr',
                'open_type': 'webview',
                'internal_path': '',  # 内部应用不需要
                'app_url': 'https://hr.company.com',
                'webview_url': 'https://hr.company.com',
                'miniapp_path': '',  # 小程序路径
                'access_roles': ['admin', 'hr', 'manager'],  # 仅HR和管理员
                'require_auth': True,
                'app_config': {
                    'version': '3.1.0',
                    'features': ['attendance', 'salary', 'performance']
                },
                'is_active': True,
                'sort_order': 6
            }
        ]

        created_count = 0
        updated_count = 0

        for app_data in default_apps:
            app_id = app_data['app_id']

            # 检查应用是否已存在
            existing_app = EmployeeApp.objects.filter(app_id=app_id).first()

            if existing_app:
                # 更新现有应用
                for key, value in app_data.items():
                    if hasattr(existing_app, key):
                        setattr(existing_app, key, value)
                existing_app.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'更新应用: {existing_app.app_name} ({app_id})')
                )
            else:
                # 创建新应用
                try:
                    app = EmployeeApp.objects.create(**app_data)
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'创建应用: {app.app_name} ({app_id})')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'创建应用失败 {app_id}: {str(e)}')
                    )

        self.stdout.write(
            self.style.SUCCESS(f'初始数据创建完成！')
        )
        self.stdout.write(
            self.style.SUCCESS(f'统计: 创建 {created_count} 个新应用, 更新 {updated_count} 个现有应用')
        )

        # 4. 输出使用说明
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('初始账号信息:'))
        self.stdout.write('员工账号: EMP001 / 111@chery')
        self.stdout.write('管理员账号: ADMIN001 / 111@chery')
        self.stdout.write(self.style.SUCCESS('OCR系统路径: pages/ocr/index/index'))
        self.stdout.write('=' * 50)