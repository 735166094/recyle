# points/management/commands/seed_points_rules.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from points.models import PointsRule


class Command(BaseCommand):
    """初始化积分规则种子数据"""
    help = '初始化积分规则种子数据'

    def handle(self, *args, **options):
        self.stdout.write('开始创建积分规则种子数据...')

        # 清空现有规则（可选）
        # PointsRule.objects.all().delete()

        # 1. 签到规则
        self.create_sign_rule()

        # 2. 绿色生活规则
        self.create_green_life_rules()

        # 3. 其他积分规则
        self.create_other_rules()

        self.stdout.write(self.style.SUCCESS('积分规则种子数据创建完成！'))

    def create_sign_rule(self):
        """创建签到规则"""
        rule, created = PointsRule.objects.update_or_create(
            rule_id='SIGN_DAILY',
            defaults={
                'rule_name': '每日签到',
                'rule_type': 'sign',
                'green_type': None,
                'points_value': 1,
                'points_limit': 0,
                'daily_limit': 1,
                'monthly_limit': 31,
                'condition_type': 'days',
                'condition_value': 1,
                'condition_unit': '天',
                'description': '每日签到奖励，连续签到有额外奖励',
                'instructions': '1. 每天登录小程序\n2. 点击签到按钮\n3. 获得相应积分',
                'need_upload': False,
                'upload_desc': None,
                'certificate_name': None,
                'is_active': True,
                'sort_order': 10,
            }
        )
        status = '创建' if created else '更新'
        self.stdout.write(f'{status}签到规则: {rule.rule_name}')

    def create_green_life_rules(self):
        """创建绿色生活规则"""
        green_rules = [
            {
                'rule_id': 'GREEN_TRANSPORT',
                'rule_name': '绿色出行',
                'rule_type': 'task',
                'green_type': 'transport',
                'points_value': 1,
                'points_limit': 0,
                'daily_limit': 1,
                'monthly_limit': 31,
                'condition_type': 'upload',
                'condition_value': 1,
                'condition_unit': '次',
                'description': '使用公共交通、共享单车、步行等方式出行',
                'instructions': '1. 上传绿色出行凭证\n2. 等待审核\n3. 审核通过获得积分',
                'need_upload': True,
                'upload_desc': '请上传公交/地铁票、共享单车截图、步行轨迹等凭证',
                'certificate_name': None,
                'is_active': True,
                'sort_order': 20,
            },
            {
                'rule_id': 'GREEN_FOOD',
                'rule_name': '光盘行动',
                'rule_type': 'task',
                'green_type': 'food',
                'points_value': 1,
                'points_limit': 0,
                'daily_limit': 1,
                'monthly_limit': 31,
                'condition_type': 'upload',
                'condition_value': 1,
                'condition_unit': '次',
                'description': '用餐光盘，不浪费食物',
                'instructions': '1. 上传光盘照片\n2. 等待审核\n3. 审核通过获得积分',
                'need_upload': True,
                'upload_desc': '请上传餐后光盘照片，需清晰可见',
                'certificate_name': None,
                'is_active': True,
                'sort_order': 30,
            },
            {
                'rule_id': 'GREEN_WALK',
                'rule_name': '低碳行走',
                'rule_type': 'task',
                'green_type': 'walk',
                'points_value': 0,  # 按步数计算
                'points_limit': 100,
                'daily_limit': 1,
                'monthly_limit': 31,
                'condition_type': 'steps',
                'condition_value': 10000,
                'condition_unit': '步',
                'description': '每日步行10000步以上，每10000步可获得1积分，每日最高10积分',
                'instructions': '1. 记录当日步数\n2. 提交步数截图\n3. 系统自动计算积分',
                'need_upload': True,
                'upload_desc': '请上传微信运动、手机健康等步数截图',
                'certificate_name': None,
                'is_active': True,
                'sort_order': 40,
            },
            {
                'rule_id': 'GREEN_LEARNING',
                'rule_name': '低碳学习',
                'rule_type': 'task',
                'green_type': 'learning',
                'points_value': 2,
                'points_limit': 0,
                'daily_limit': 1,
                'monthly_limit': 5,
                'condition_type': 'certificate',
                'condition_value': 1,
                'condition_unit': '次',
                'description': '学习低碳环保知识，完成学习获得证书',
                'instructions': '1. 完成低碳学习课程\n2. 上传学习证书\n3. 审核通过获得积分',
                'need_upload': True,
                'upload_desc': '请上传学习证书截图',
                'certificate_name': '低碳学习证书',
                'is_active': True,
                'sort_order': 50,
            },
        ]

        for rule_data in green_rules:
            rule, created = PointsRule.objects.update_or_create(
                rule_id=rule_data['rule_id'],
                defaults=rule_data
            )
            status = '创建' if created else '更新'
            self.stdout.write(f'{status}绿色生活规则: {rule.rule_name} ({rule.get_green_type_display()})')

    def create_other_rules(self):
        """创建其他积分规则"""
        other_rules = [
            {
                'rule_id': 'RECYCLE_REWARD',
                'rule_name': '回收奖励',
                'rule_type': 'recycle',
                'green_type': None,
                'points_value': 5,
                'points_limit': 0,
                'daily_limit': 0,
                'monthly_limit': 500,
                'condition_type': 'amount',
                'condition_value': 1,
                'condition_unit': '次',
                'description': '成功完成回收订单，根据回收价值获得积分',
                'instructions': '1. 提交回收订单\n2. 完成回收交易\n3. 系统自动发放积分',
                'need_upload': False,
                'upload_desc': None,
                'certificate_name': None,
                'is_active': True,
                'sort_order': 60,
            },
            {
                'rule_id': 'SYSTEM_BONUS',
                'rule_name': '系统奖励',
                'rule_type': 'system_bonus',
                'green_type': None,
                'points_value': 0,  # 根据具体情况
                'points_limit': 0,
                'daily_limit': 0,
                'monthly_limit': 0,
                'condition_type': 'count',
                'condition_value': 1,
                'condition_unit': '次',
                'description': '系统活动、补偿、推广等奖励',
                'instructions': '由系统管理员发放',
                'need_upload': False,
                'upload_desc': None,
                'certificate_name': None,
                'is_active': True,
                'sort_order': 80,
            },
            {
                'rule_id': 'CONSUME_DEDUCT',
                'rule_name': '积分兑换',
                'rule_type': 'consume',
                'green_type': None,
                'points_value': -1,  # 负数表示扣除
                'points_limit': 0,
                'daily_limit': 0,
                'monthly_limit': 0,
                'condition_type': 'count',
                'condition_value': 1,
                'condition_unit': '次',
                'description': '积分商城兑换商品',
                'instructions': '1. 选择兑换商品\n2. 使用积分支付\n3. 积分相应扣除',
                'need_upload': False,
                'upload_desc': None,
                'certificate_name': None,
                'is_active': True,
                'sort_order': 90,
            },
            {
                'rule_id': 'YEAR_END_RESET',
                'rule_name': '年终清零',
                'rule_type': 'year_end_reset',
                'green_type': None,
                'points_value': 0,
                'points_limit': 0,
                'daily_limit': 0,
                'monthly_limit': 0,
                'condition_type': 'days',
                'condition_value': 365,
                'condition_unit': '天',
                'description': '每年年底过期积分清零',
                'instructions': '系统自动执行，每年12月31日清零过期积分',
                'need_upload': False,
                'upload_desc': None,
                'certificate_name': None,
                'is_active': True,
                'sort_order': 100,
            },
        ]

        for rule_data in other_rules:
            rule, created = PointsRule.objects.update_or_create(
                rule_id=rule_data['rule_id'],
                defaults=rule_data
            )
            status = '创建' if created else '更新'
            self.stdout.write(f'{status}其他规则: {rule.rule_name}')
