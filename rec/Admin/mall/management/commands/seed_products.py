import os
import random
import itertools
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from mall.models import (
    GlobalSpecTemplate, GlobalSpecOption,
    ProductCategory, Product, ProductSpecGroup, ProductSpecOption,
    PriceRule, ProductSku, Banner
)


class Command(BaseCommand):
    help = '生成虚拟商品数据（支持增强型规格模型）'

    def handle(self, *args, **options):
        self.stdout.write('开始生成虚拟商品数据...')

        # 使用事务确保数据一致性
        with transaction.atomic():
            # 1. 创建全局规格模板
            self.stdout.write('创建全局规格模板...')
            global_specs = self.create_global_spec_templates()

            # 2. 创建商品分类
            self.stdout.write('创建商品分类...')
            categories = self.create_product_categories()

            # 3. 创建商品
            self.stdout.write('创建商品和规格...')
            products = self.create_products_with_specs(categories, global_specs)

            # 4. 创建价格规则
            self.stdout.write('创建价格规则...')
            self.create_price_rules(products)

            # 5. 创建轮播图
            self.stdout.write('创建轮播图...')
            self.create_banners(products)

            # 6. 验证价格规则效果
            self.stdout.write('验证价格规则效果...')
            self.validate_price_rules(products)

        self.stdout.write(
            self.style.SUCCESS('虚拟数据生成完成！')
        )

    def create_global_spec_templates(self):
        """创建全局规格模板"""
        global_specs_data = [
            {
                'name': '颜色',
                'description': '商品颜色规格',
                'data_type': 'color',
                'icon': 'icon-color',
                'options': [
                    {'value': '深空黑', 'color_code': '#2C3E50', 'base_price_increment': 0},
                    {'value': '月光银', 'color_code': '#BDC3C7', 'base_price_increment': 200},
                    {'value': '玫瑰金', 'color_code': '#E8C4C4', 'base_price_increment': 500},
                    {'value': '宝石蓝', 'color_code': '#3498DB', 'base_price_increment': 300},
                    {'value': '烈焰红', 'color_code': '#E74C3C', 'base_price_increment': 400},
                ]
            },
            {
                'name': '存储容量',
                'description': '设备存储容量规格',
                'data_type': 'text',
                'icon': 'icon-storage',
                'options': [
                    {'value': '64GB', 'base_price_increment': 0},
                    {'value': '128GB', 'base_price_increment': 800},
                    {'value': '256GB', 'base_price_increment': 1500},
                    {'value': '512GB', 'base_price_increment': 2500},
                    {'value': '1TB', 'base_price_increment': 4000},
                ]
            },
            {
                'name': '尺寸',
                'description': '服装鞋包尺寸规格',
                'data_type': 'text',
                'icon': 'icon-size',
                'options': [
                    {'value': 'S', 'base_price_increment': 0},
                    {'value': 'M', 'base_price_increment': 0},
                    {'value': 'L', 'base_price_increment': 0},
                    {'value': 'XL', 'base_price_increment': 100},
                    {'value': 'XXL', 'base_price_increment': 200},
                ]
            },
            {
                'name': '版本',
                'description': '产品版本规格',
                'data_type': 'text',
                'icon': 'icon-version',
                'options': [
                    {'value': '标准版', 'base_price_increment': 0},
                    {'value': '专业版', 'base_price_increment': 1000},
                    {'value': '旗舰版', 'base_price_increment': 2000},
                    {'value': '尊享版', 'base_price_increment': 3500},
                ]
            },
            {
                'name': '材质',
                'description': '商品材质规格',
                'data_type': 'text',
                'icon': 'icon-material',
                'options': [
                    {'value': '塑料', 'base_price_increment': -500},
                    {'value': '金属', 'base_price_increment': 0},
                    {'value': '皮革', 'base_price_increment': 800},
                    {'value': '实木', 'base_price_increment': 1200},
                    {'value': '碳纤维', 'base_price_increment': 2000},
                ]
            }
        ]

        global_specs = {}
        for i, spec_data in enumerate(global_specs_data):
            spec_template, created = GlobalSpecTemplate.objects.get_or_create(
                name=spec_data['name'],
                defaults={
                    'description': spec_data['description'],
                    'data_type': spec_data['data_type'],
                    'icon': spec_data['icon'],
                    'sort_order': i * 10,
                    'is_active': True
                }
            )

            # 创建规格选项
            for j, option_data in enumerate(spec_data['options']):
                GlobalSpecOption.objects.get_or_create(
                    spec_template=spec_template,
                    value=option_data['value'],
                    defaults={
                        'color_code': option_data.get('color_code'),
                        'base_price_increment': option_data['base_price_increment'],
                        'sort_order': j * 10
                    }
                )

            global_specs[spec_data['name']] = spec_template
            self.stdout.write(f'创建全局规格: {spec_template.name}')

        return global_specs

    def create_product_categories(self):
        """创建商品分类"""
        categories_data = [
            {'name': '数码家电', 'description': '手机、电脑、家电等数码产品', 'icon': 'icon-electronic'},
            {'name': '家居生活', 'description': '家居用品、厨房用具等', 'icon': 'icon-home'},
            {'name': '美妆个护', 'description': '化妆品、护肤品等', 'icon': 'icon-beauty'},
            {'name': '服装鞋包', 'description': '服装、鞋类、箱包等', 'icon': 'icon-clothes'},
            {'name': '食品饮料', 'description': '零食、饮料、生鲜等', 'icon': 'icon-food'},
            {'name': '运动户外', 'description': '运动装备、户外用品等', 'icon': 'icon-sport'},
            {'name': '虚拟商品', 'description': '代金券、兑换券等虚拟商品', 'icon': 'icon-virtual'},
        ]

        categories = []
        for i, cat_data in enumerate(categories_data):
            category, created = ProductCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'icon': cat_data['icon'],
                    'image': f'https://picsum.photos/200/200?random={random.randint(1, 100)}',
                    'sort_order': i * 10,
                    'is_active': True
                }
            )
            categories.append(category)
            self.stdout.write(f'创建分类: {category.name}')

        return categories

    def create_products_with_specs(self, categories, global_specs):
        """创建商品及其规格"""
        products_data = [
            # 数码家电 - 8个商品
            {
                'name': '苹果iPhone 15 Pro',
                'category': categories[0],
                'base_points_price': 99900,
                'original_points': 109900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 2
                    },
                    {
                        'global_template': global_specs['存储容量'],
                        'group_type': 'main',
                        'price_weight': 3
                    }
                ]
            },
            {
                'name': '华为Mate 60 Pro',
                'category': categories[0],
                'base_points_price': 79900,
                'original_points': 89900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 2
                    },
                    {
                        'global_template': global_specs['版本'],
                        'group_type': 'main',
                        'price_weight': 3
                    }
                ]
            },
            {
                'name': '小米智能扫地机器人',
                'category': categories[0],
                'base_points_price': 29900,
                'original_points': 39900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    },
                    {
                        'global_template': global_specs['版本'],
                        'group_type': 'main',
                        'price_weight': 2
                    }
                ]
            },
            {
                'name': '三星Galaxy S24 Ultra',
                'category': categories[0],
                'base_points_price': 89900,
                'original_points': 99900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 2
                    },
                    {
                        'global_template': global_specs['存储容量'],
                        'group_type': 'main',
                        'price_weight': 3
                    }
                ]
            },
            {
                'name': '苹果MacBook Pro 14英寸',
                'category': categories[0],
                'base_points_price': 159900,
                'original_points': 179900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    },
                    {
                        'global_template': global_specs['存储容量'],
                        'group_type': 'main',
                        'price_weight': 3
                    }
                ]
            },
            {
                'name': '索尼PlayStation 5',
                'category': categories[0],
                'base_points_price': 45900,
                'original_points': 49900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    },
                    {
                        'global_template': global_specs['版本'],
                        'group_type': 'main',
                        'price_weight': 2
                    }
                ]
            },
            {
                'name': '戴尔XPS 13笔记本电脑',
                'category': categories[0],
                'base_points_price': 89900,
                'original_points': 99900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    },
                    {
                        'global_template': global_specs['存储容量'],
                        'group_type': 'main',
                        'price_weight': 2
                    }
                ]
            },
            {
                'name': '大疆DJI Mini 4 Pro无人机',
                'category': categories[0],
                'base_points_price': 69900,
                'original_points': 79900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    },
                    {
                        'global_template': global_specs['版本'],
                        'group_type': 'main',
                        'price_weight': 2
                    }
                ]
            },

            # 家居生活 - 7个商品
            {
                'name': '高级瑜伽垫套装',
                'category': categories[1],
                'base_points_price': 3900,
                'original_points': 4900,
                'use_global_specs': False,
                'spec_config': [
                    {
                        'name': '材质',
                        'group_type': 'main',
                        'price_weight': 2,
                        'private_options': [
                            {'value': 'TPE材质', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': 'NBR材质', 'price_increment': -500, 'price_multiplier': 1.0},
                            {'value': '天然橡胶', 'price_increment': 1000, 'price_multiplier': 1.0},
                        ]
                    },
                    {
                        'name': '厚度',
                        'group_type': 'secondary',
                        'price_weight': 1,
                        'private_options': [
                            {'value': '6mm', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '8mm', 'price_increment': 300, 'price_multiplier': 1.0},
                            {'value': '10mm', 'price_increment': 600, 'price_multiplier': 1.0},
                        ]
                    }
                ]
            },
            {
                'name': '智能空气净化器',
                'category': categories[1],
                'base_points_price': 12900,
                'original_points': 15900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    },
                    {
                        'global_template': global_specs['版本'],
                        'group_type': 'main',
                        'price_weight': 2
                    }
                ]
            },
            {
                'name': '北欧简约沙发',
                'category': categories[1],
                'base_points_price': 29900,
                'original_points': 35900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 2
                    },
                    {
                        'global_template': global_specs['材质'],
                        'group_type': 'main',
                        'price_weight': 3
                    }
                ]
            },
            {
                'name': '智能咖啡机',
                'category': categories[1],
                'base_points_price': 15900,
                'original_points': 19900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    },
                    {
                        'global_template': global_specs['版本'],
                        'group_type': 'main',
                        'price_weight': 2
                    }
                ]
            },
            {
                'name': '多功能料理锅',
                'category': categories[1],
                'base_points_price': 8900,
                'original_points': 11900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    },
                    {
                        'global_template': global_specs['版本'],
                        'group_type': 'main',
                        'price_weight': 1
                    }
                ]
            },
            {
                'name': '乳胶记忆枕',
                'category': categories[1],
                'base_points_price': 2900,
                'original_points': 3900,
                'use_global_specs': False,
                'spec_config': [
                    {
                        'name': '尺寸',
                        'group_type': 'main',
                        'price_weight': 1,
                        'private_options': [
                            {'value': '标准款', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '加宽款', 'price_increment': 500, 'price_multiplier': 1.0},
                        ]
                    },
                    {
                        'name': '高度',
                        'group_type': 'secondary',
                        'price_weight': 1,
                        'private_options': [
                            {'value': '低枕', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '中枕', 'price_increment': 200, 'price_multiplier': 1.0},
                            {'value': '高枕', 'price_increment': 400, 'price_multiplier': 1.0},
                        ]
                    }
                ]
            },
            {
                'name': '智能体重秤',
                'category': categories[1],
                'base_points_price': 1900,
                'original_points': 2900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    }
                ]
            },

            # 美妆个护 - 6个商品
            {
                'name': '雅诗兰黛小棕瓶精华',
                'category': categories[2],
                'base_points_price': 8900,
                'original_points': 10900,
                'use_global_specs': False,
                'spec_config': [
                    {
                        'name': '容量',
                        'group_type': 'main',
                        'price_weight': 2,
                        'private_options': [
                            {'value': '30ml', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '50ml', 'price_increment': 3000, 'price_multiplier': 1.0},
                            {'value': '75ml', 'price_increment': 5000, 'price_multiplier': 1.0},
                        ]
                    }
                ]
            },
            {
                'name': '兰蔻清滢柔肤水',
                'category': categories[2],
                'base_points_price': 4900,
                'original_points': 5900,
                'use_global_specs': False,
                'spec_config': [
                    {
                        'name': '肤质',
                        'group_type': 'main',
                        'price_weight': 1,
                        'private_options': [
                            {'value': '干性肤质', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '油性肤质', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '混合肤质', 'price_increment': 0, 'price_multiplier': 1.0},
                        ]
                    },
                    {
                        'name': '容量',
                        'group_type': 'secondary',
                        'price_weight': 2,
                        'private_options': [
                            {'value': '200ml', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '400ml', 'price_increment': 2000, 'price_multiplier': 1.0},
                        ]
                    }
                ]
            },
            {
                'name': '香奈儿可可小姐香水',
                'category': categories[2],
                'base_points_price': 12900,
                'original_points': 14900,
                'use_global_specs': False,
                'spec_config': [
                    {
                        'name': '容量',
                        'group_type': 'main',
                        'price_weight': 2,
                        'private_options': [
                            {'value': '35ml', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '50ml', 'price_increment': 3000, 'price_multiplier': 1.0},
                            {'value': '100ml', 'price_increment': 6000, 'price_multiplier': 1.0},
                        ]
                    }
                ]
            },
            {
                'name': '资生堂红妍肌活精华',
                'category': categories[2],
                'base_points_price': 9900,
                'original_points': 11900,
                'use_global_specs': False,
                'spec_config': [
                    {
                        'name': '容量',
                        'group_type': 'main',
                        'price_weight': 2,
                        'private_options': [
                            {'value': '30ml', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '50ml', 'price_increment': 3500, 'price_multiplier': 1.0},
                            {'value': '75ml', 'price_increment': 5500, 'price_multiplier': 1.0},
                        ]
                    }
                ]
            },
            {
                'name': 'SK-II神仙水',
                'category': categories[2],
                'base_points_price': 15900,
                'original_points': 18900,
                'use_global_specs': False,
                'spec_config': [
                    {
                        'name': '容量',
                        'group_type': 'main',
                        'price_weight': 2,
                        'private_options': [
                            {'value': '75ml', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '160ml', 'price_increment': 5000, 'price_multiplier': 1.0},
                            {'value': '230ml', 'price_increment': 8000, 'price_multiplier': 1.0},
                        ]
                    }
                ]
            },
            {
                'name': '迪奥烈艳蓝金唇膏',
                'category': categories[2],
                'base_points_price': 3900,
                'original_points': 4900,
                'use_global_specs': False,
                'spec_config': [
                    {
                        'name': '色号',
                        'group_type': 'main',
                        'price_weight': 1,
                        'private_options': [
                            {'value': '999正红色', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '772豆沙色', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '720栗红色', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '840枫叶色', 'price_increment': 0, 'price_multiplier': 1.0},
                        ]
                    }
                ]
            },

            # 服装鞋包 - 8个商品
            {
                'name': 'Nike运动鞋',
                'category': categories[3],
                'base_points_price': 12900,
                'original_points': 15900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 2
                    },
                    {
                        'global_template': global_specs['尺寸'],
                        'group_type': 'main',
                        'price_weight': 1
                    }
                ]
            },
            {
                'name': 'Adidas运动外套',
                'category': categories[3],
                'base_points_price': 8900,
                'original_points': 11900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    },
                    {
                        'global_template': global_specs['尺寸'],
                        'group_type': 'main',
                        'price_weight': 1
                    }
                ]
            },
            {
                'name': '优衣库HEATTECH保暖内衣',
                'category': categories[3],
                'base_points_price': 2900,
                'original_points': 3900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    },
                    {
                        'global_template': global_specs['尺寸'],
                        'group_type': 'main',
                        'price_weight': 1
                    }
                ]
            },
            {
                'name': 'ZARA女士连衣裙',
                'category': categories[3],
                'base_points_price': 5900,
                'original_points': 7900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    },
                    {
                        'global_template': global_specs['尺寸'],
                        'group_type': 'main',
                        'price_weight': 1
                    }
                ]
            },
            {
                'name': '李宁篮球鞋',
                'category': categories[3],
                'base_points_price': 6900,
                'original_points': 8900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    },
                    {
                        'global_template': global_specs['尺寸'],
                        'group_type': 'main',
                        'price_weight': 1
                    }
                ]
            },
            {
                'name': '新秀丽旅行箱',
                'category': categories[3],
                'base_points_price': 12900,
                'original_points': 15900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    },
                    {
                        'global_template': global_specs['尺寸'],
                        'group_type': 'main',
                        'price_weight': 2
                    }
                ]
            },
            {
                'name': 'Coach女士手提包',
                'category': categories[3],
                'base_points_price': 19900,
                'original_points': 24900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 2
                    },
                    {
                        'global_template': global_specs['材质'],
                        'group_type': 'main',
                        'price_weight': 2
                    }
                ]
            },
            {
                'name': 'Under Armour运动裤',
                'category': categories[3],
                'base_points_price': 4900,
                'original_points': 6900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    },
                    {
                        'global_template': global_specs['尺寸'],
                        'group_type': 'main',
                        'price_weight': 1
                    }
                ]
            },

            # 食品饮料 - 7个商品
            {
                'name': '进口黑巧克力礼盒',
                'category': categories[4],
                'base_points_price': 2900,
                'original_points': 3900,
                'use_global_specs': False,
                'spec_config': [
                    {
                        'name': '可可含量',
                        'group_type': 'main',
                        'price_weight': 1,
                        'private_options': [
                            {'value': '70%', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '85%', 'price_increment': 500, 'price_multiplier': 1.0},
                            {'value': '95%', 'price_increment': 800, 'price_multiplier': 1.0},
                        ]
                    },
                    {
                        'name': '净含量',
                        'group_type': 'secondary',
                        'price_weight': 2,
                        'private_options': [
                            {'value': '200g', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '400g', 'price_increment': 1500, 'price_multiplier': 1.0},
                        ]
                    }
                ]
            },
            {
                'name': '意大利进口咖啡豆',
                'category': categories[4],
                'base_points_price': 1900,
                'original_points': 2900,
                'use_global_specs': False,
                'spec_config': [
                    {
                        'name': '烘焙程度',
                        'group_type': 'main',
                        'price_weight': 1,
                        'private_options': [
                            {'value': '浅度烘焙', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '中度烘焙', 'price_increment': 200, 'price_multiplier': 1.0},
                            {'value': '深度烘焙', 'price_increment': 400, 'price_multiplier': 1.0},
                        ]
                    },
                    {
                        'name': '包装规格',
                        'group_type': 'secondary',
                        'price_weight': 2,
                        'private_options': [
                            {'value': '250g', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '500g', 'price_increment': 1500, 'price_multiplier': 1.0},
                            {'value': '1kg', 'price_increment': 2500, 'price_multiplier': 1.0},
                        ]
                    }
                ]
            },
            {
                'name': '日本进口抹茶粉',
                'category': categories[4],
                'base_points_price': 3900,
                'original_points': 4900,
                'use_global_specs': False,
                'spec_config': [
                    {
                        'name': '等级',
                        'group_type': 'main',
                        'price_weight': 2,
                        'private_options': [
                            {'value': '料理级', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '饮用级', 'price_increment': 1000, 'price_multiplier': 1.0},
                            {'value': '茶道级', 'price_increment': 2000, 'price_multiplier': 1.0},
                        ]
                    },
                    {
                        'name': '净含量',
                        'group_type': 'secondary',
                        'price_weight': 1,
                        'private_options': [
                            {'value': '50g', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '100g', 'price_increment': 1500, 'price_multiplier': 1.0},
                        ]
                    }
                ]
            },
            {
                'name': '新西兰进口蜂蜜',
                'category': categories[4],
                'base_points_price': 4900,
                'original_points': 5900,
                'use_global_specs': False,
                'spec_config': [
                    {
                        'name': '蜂蜜种类',
                        'group_type': 'main',
                        'price_weight': 2,
                        'private_options': [
                            {'value': '麦卢卡蜂蜜UMF5+', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '麦卢卡蜂蜜UMF10+', 'price_increment': 2000, 'price_multiplier': 1.0},
                            {'value': '麦卢卡蜂蜜UMF15+', 'price_increment': 4000, 'price_multiplier': 1.0},
                        ]
                    },
                    {
                        'name': '净含量',
                        'group_type': 'secondary',
                        'price_weight': 1,
                        'private_options': [
                            {'value': '250g', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '500g', 'price_increment': 2000, 'price_multiplier': 1.0},
                        ]
                    }
                ]
            },
            {
                'name': '法国进口红酒',
                'category': categories[4],
                'base_points_price': 8900,
                'original_points': 10900,
                'use_global_specs': False,
                'spec_config': [
                    {
                        'name': '年份',
                        'group_type': 'main',
                        'price_weight': 2,
                        'private_options': [
                            {'value': '2018年', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '2015年', 'price_increment': 2000, 'price_multiplier': 1.0},
                            {'value': '2012年', 'price_increment': 4000, 'price_multiplier': 1.0},
                        ]
                    },
                    {
                        'name': '产区',
                        'group_type': 'secondary',
                        'price_weight': 1,
                        'private_options': [
                            {'value': '波尔多', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '勃艮第', 'price_increment': 3000, 'price_multiplier': 1.0},
                        ]
                    }
                ]
            },
            {
                'name': '有机坚果大礼包',
                'category': categories[4],
                'base_points_price': 3900,
                'original_points': 4900,
                'use_global_specs': False,
                'spec_config': [
                    {
                        'name': '礼包类型',
                        'group_type': 'main',
                        'price_weight': 2,
                        'private_options': [
                            {'value': '经典款', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '豪华款', 'price_increment': 1500, 'price_multiplier': 1.0},
                            {'value': '尊享款', 'price_increment': 3000, 'price_multiplier': 1.0},
                        ]
                    }
                ]
            },
            {
                'name': '精品茶叶礼盒',
                'category': categories[4],
                'base_points_price': 5900,
                'original_points': 7900,
                'use_global_specs': False,
                'spec_config': [
                    {
                        'name': '茶叶种类',
                        'group_type': 'main',
                        'price_weight': 2,
                        'private_options': [
                            {'value': '龙井茶', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '铁观音', 'price_increment': 1000, 'price_multiplier': 1.0},
                            {'value': '大红袍', 'price_increment': 2000, 'price_multiplier': 1.0},
                        ]
                    },
                    {
                        'name': '包装规格',
                        'group_type': 'secondary',
                        'price_weight': 1,
                        'private_options': [
                            {'value': '100g', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '200g', 'price_increment': 1500, 'price_multiplier': 1.0},
                        ]
                    }
                ]
            },

            # 运动户外 - 6个商品
            {
                'name': '专业瑜伽垫',
                'category': categories[5],
                'base_points_price': 3900,
                'original_points': 4900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    },
                    {
                        'global_template': global_specs['材质'],
                        'group_type': 'main',
                        'price_weight': 2
                    }
                ]
            },
            {
                'name': '登山杖',
                'category': categories[5],
                'base_points_price': 2900,
                'original_points': 3900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['材质'],
                        'group_type': 'main',
                        'price_weight': 2
                    },
                    {
                        'global_template': global_specs['版本'],
                        'group_type': 'main',
                        'price_weight': 1
                    }
                ]
            },
            {
                'name': '健身哑铃套装',
                'category': categories[5],
                'base_points_price': 5900,
                'original_points': 7900,
                'use_global_specs': False,
                'spec_config': [
                    {
                        'name': '重量组合',
                        'group_type': 'main',
                        'price_weight': 2,
                        'private_options': [
                            {'value': '5kg*2', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '10kg*2', 'price_increment': 2000, 'price_multiplier': 1.0},
                            {'value': '15kg*2', 'price_increment': 3500, 'price_multiplier': 1.0},
                        ]
                    },
                    {
                        'name': '材质',
                        'group_type': 'secondary',
                        'price_weight': 1,
                        'private_options': [
                            {'value': '包胶', 'price_increment': 0, 'price_multiplier': 1.0},
                            {'value': '电镀', 'price_increment': 1000, 'price_multiplier': 1.0},
                        ]
                    }
                ]
            },
            {
                'name': '户外帐篷',
                'category': categories[5],
                'base_points_price': 12900,
                'original_points': 15900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    },
                    {
                        'global_template': global_specs['版本'],
                        'group_type': 'main',
                        'price_weight': 2
                    }
                ]
            },
            {
                'name': '骑行头盔',
                'category': categories[5],
                'base_points_price': 3900,
                'original_points': 4900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    },
                    {
                        'global_template': global_specs['尺寸'],
                        'group_type': 'main',
                        'price_weight': 1
                    }
                ]
            },
            {
                'name': '游泳眼镜',
                'category': categories[5],
                'base_points_price': 1900,
                'original_points': 2900,
                'use_global_specs': True,
                'spec_config': [
                    {
                        'global_template': global_specs['颜色'],
                        'group_type': 'main',
                        'price_weight': 1
                    },
                    {
                        'global_template': global_specs['版本'],
                        'group_type': 'main',
                        'price_weight': 1
                    }
                ]
            },

            # 虚拟商品 - 5个商品
            {
                'name': '星巴克代金券',
                'category': categories[6],
                'base_points_price': 500,
                'original_points': 600,
                'use_global_specs': False,
                'spec_config': []
            },
            {
                'name': '视频网站会员月卡',
                'category': categories[6],
                'base_points_price': 2500,
                'original_points': 3000,
                'use_global_specs': False,
                'spec_config': []
            },
            {
                'name': '在线课程学习卡',
                'category': categories[6],
                'base_points_price': 9900,
                'original_points': 11900,
                'use_global_specs': False,
                'spec_config': []
            },
            {
                'name': '游戏点券',
                'category': categories[6],
                'base_points_price': 1000,
                'original_points': 1200,
                'use_global_specs': False,
                'spec_config': []
            },
            {
                'name': '电子书阅读券',
                'category': categories[6],
                'base_points_price': 1500,
                'original_points': 1800,
                'use_global_specs': False,
                'spec_config': []
            },
        ]

        products = []
        for prod_data in products_data:
            # 创建商品
            product = Product.objects.create(
                name=prod_data['name'],
                category=prod_data['category'],
                description=f'{prod_data["name"]}的详细描述，这是一款优质的商品，采用先进工艺制造，性能卓越，深受用户喜爱。',
                main_image=f'https://picsum.photos/400/400?random={random.randint(100, 200)}',
                images=[
                    f'https://picsum.photos/400/400?random={random.randint(201, 300)}',
                    f'https://picsum.photos/400/400?random={random.randint(301, 400)}',
                    f'https://picsum.photos/400/400?random={random.randint(401, 500)}',
                ],
                base_points_price=prod_data['base_points_price'],
                original_points=prod_data['original_points'],
                discount_percent=random.randint(0, 30),
                is_on_sale=random.choice([True, False]),
                stock=random.randint(50, 200),
                sales_count=random.randint(0, 500),
                detail_html=f'<h1>{prod_data["name"]}</h1><p>这是{prod_data["name"]}的详细商品介绍，包含产品特性、使用方法、注意事项等详细信息。</p>',
                detail_images=[
                    f'https://picsum.photos/600/400?random={random.randint(501, 600)}',
                    f'https://picsum.photos/600/400?random={random.randint(601, 700)}',
                ],
                status='active',
                sort_order=random.randint(1, 100),
                is_recommended=random.choice([True, False]),
                is_hot=random.choice([True, False]),
                is_new=random.choice([True, False]),
                rating=round(random.uniform(3.5, 5.0), 1),
                review_count=random.randint(0, 200),
                use_global_specs=prod_data['use_global_specs'],
                price_calculation_method='additive'
            )
            products.append(product)
            self.stdout.write(f'创建商品: {product.name}')

            # 创建规格组和规格选项
            if prod_data['spec_config']:
                spec_groups = self.create_product_specs(product, prod_data['spec_config'], global_specs)

                # 创建SKU（规格组合）
                self.create_product_skus(product, spec_groups)

        return products

    def create_product_specs(self, product, spec_config, global_specs):
        """为商品创建规格组和选项"""
        spec_groups = []

        for i, group_config in enumerate(spec_config):
            if product.use_global_specs and 'global_template' in group_config:
                # 使用全局规格
                spec_group = ProductSpecGroup.objects.create(
                    product=product,
                    spec_type='global',
                    global_template=group_config['global_template'],
                    group_type=group_config['group_type'],
                    price_weight=group_config['price_weight'],
                    sort_order=i
                )

                # 从全局规格模板创建选项
                global_options = group_config['global_template'].global_options.all()
                for global_option in global_options:
                    ProductSpecOption.objects.create(
                        spec_group=spec_group,
                        global_option=global_option,
                        value=global_option.value,
                        color_code=global_option.color_code,
                        price_increment=global_option.base_price_increment,
                        sort_order=global_option.sort_order
                    )

            else:
                # 使用私有规格
                spec_group = ProductSpecGroup.objects.create(
                    product=product,
                    name=group_config['name'],
                    spec_type='private',
                    group_type=group_config['group_type'],
                    price_weight=group_config['price_weight'],
                    sort_order=i
                )

                # 创建私有规格选项
                for j, option_data in enumerate(group_config['private_options']):
                    ProductSpecOption.objects.create(
                        spec_group=spec_group,
                        value=option_data['value'],
                        price_increment=option_data['price_increment'],
                        price_multiplier=option_data['price_multiplier'],
                        sort_order=j
                    )

            spec_groups.append(spec_group)
            self.stdout.write(f'  创建规格组: {spec_group.name}')

        return spec_groups

    def create_product_skus(self, product, spec_groups):
        """为商品创建SKU - 完全修复版本"""
        if not spec_groups:
            # 没有规格的商品，创建一个默认SKU
            sku = ProductSku.objects.create(
                product=product,
                sku_code=f"{product.id}_DEFAULT",
                sku_name="默认规格",
                base_points_price=product.base_points_price,
                calculated_price=product.base_points_price,
                final_price=product.base_points_price,
                stock=random.randint(10, 100),
                sales_count=random.randint(0, 50),
                image=product.main_image
            )
            self.stdout.write(f'  创建默认SKU: {sku.sku_name}')
            return

        # 生成所有可能的规格组合
        all_options = [list(group.options.all()) for group in spec_groups]
        all_combinations = list(itertools.product(*all_options))

        # 为每个组合创建SKU（限制数量避免过多）
        for combination in all_combinations[:min(8, len(all_combinations))]:
            spec_names = [f"{opt.spec_group.name}:{opt.value}" for opt in combination]
            sku_name = " ".join(spec_names)

            # 生成SKU编码
            sku_code = f"{product.id}_{'_'.join([str(opt.id) for opt in combination])}"

            # 使用新的create_with_specs方法创建SKU
            try:
                sku = ProductSku.create_with_specs(
                    product=product,
                    sku_code=sku_code,
                    sku_name=sku_name,
                    spec_options=combination,
                    base_points_price=product.base_points_price,
                    stock=random.randint(5, 50),
                    sales_count=random.randint(0, 20),
                    image=f'https://picsum.photos/300/300?random={random.randint(701, 800)}'
                )
                self.stdout.write(f'  创建SKU: {sku.sku_name} - 价格: {sku.final_price}积分')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  创建SKU失败: {sku_name}, 错误: {str(e)}'))

    def create_price_rules(self, products):
        """创建价格规则 - 完全重写版本"""
        for product in products:
            # 只为有规格的商品创建价格规则
            if not product.spec_groups.exists():
                continue

            self.stdout.write(f'\n为商品 [{product.name}] 创建价格规则:')

            # 获取商品的所有规格组
            spec_groups = list(product.spec_groups.all())

            # 创建更实际的价格规则
            rules_created = self._create_realistic_price_rules(product, spec_groups)

            if rules_created:
                # 重新计算所有SKU价格以确保规则生效
                updated_count = self._recalculate_all_skus_for_product(product)
                self.stdout.write(f'  重新计算了 {updated_count} 个SKU的价格')

    def _create_realistic_price_rules(self, product, spec_groups):
        """创建实际可用的价格规则"""
        rules_created = 0

        # 规则1：特定热门颜色优惠（如月光银9折）
        color_group = next((g for g in spec_groups if '颜色' in g.name), None)
        if color_group:
            # 找到月光银选项
            silver_option = color_group.options.filter(value='月光银').first()
            if silver_option:
                rule = PriceRule.objects.create(
                    product=product,
                    name='月光银特惠',
                    description='月光银色号享受特别优惠',
                    condition_type='spec_combination',
                    spec_conditions={str(color_group.id): silver_option.id},
                    adjustment_type='percentage',
                    adjustment_value=-10,  # 9折
                    priority=1,
                    is_active=True
                )
                self.stdout.write(f'  创建规则: {rule.name} - 月光银9折')
                rules_created += 1

        # 规则2：大容量存储优惠（如512GB及以上8.5折）
        storage_group = next((g for g in spec_groups if '存储容量' in g.name), None)
        if storage_group:
            # 找到512GB和1TB选项
            large_storage_options = storage_group.options.filter(
                value__in=['512GB', '1TB']
            )
            for option in large_storage_options:
                rule = PriceRule.objects.create(
                    product=product,
                    name=f'{option.value}大容量特惠',
                    description=f'{option.value}存储容量享受大容量优惠',
                    condition_type='spec_combination',
                    spec_conditions={str(storage_group.id): option.id},
                    adjustment_type='percentage',
                    adjustment_value=-15,  # 8.5折
                    priority=2,
                    is_active=True
                )
                self.stdout.write(f'  创建规则: {rule.name} - {option.value} 8.5折')
                rules_created += 1

        # 规则3：高端版本组合优惠（如尊享版+特定颜色）
        version_group = next((g for g in spec_groups if '版本' in g.name), None)
        if version_group and color_group:
            premium_option = version_group.options.filter(value='尊享版').first()
            premium_color_option = color_group.options.filter(value='玫瑰金').first()

            if premium_option and premium_color_option:
                rule = PriceRule.objects.create(
                    product=product,
                    name='尊享玫瑰金组合',
                    description='尊享版+玫瑰金颜色组合特惠',
                    condition_type='spec_combination',
                    spec_conditions={
                        str(version_group.id): premium_option.id,
                        str(color_group.id): premium_color_option.id
                    },
                    adjustment_type='percentage',
                    adjustment_value=-12,  # 8.8折
                    priority=3,
                    is_active=True
                )
                self.stdout.write(f'  创建规则: {rule.name} - 尊享版+玫瑰金 8.8折')
                rules_created += 1

        # 规则4：清仓特价（基础配置）
        if color_group and storage_group:
            # 基础颜色 + 基础存储
            base_color = color_group.options.order_by('price_increment').first()
            base_storage = storage_group.options.order_by('price_increment').first()

            if base_color and base_storage:
                rule = PriceRule.objects.create(
                    product=product,
                    name='基础配置清仓',
                    description='基础颜色和存储配置清仓特价',
                    condition_type='spec_combination',
                    spec_conditions={
                        str(color_group.id): base_color.id,
                        str(storage_group.id): base_storage.id
                    },
                    adjustment_type='fixed',
                    adjustment_value=product.base_points_price * 0.8,  # 固定8折价
                    priority=4,
                    is_active=True
                )
                self.stdout.write(f'  创建规则: {rule.name} - 基础配置固定8折价')
                rules_created += 1

        return rules_created

    def _recalculate_all_skus_for_product(self, product):
        """重新计算商品的所有SKU价格"""
        skus = ProductSku.objects.filter(product=product)
        updated_count = 0

        for sku in skus:
            try:
                calculated_price, final_price = sku.calculate_price()
                if (sku.calculated_price != calculated_price or
                        sku.final_price != final_price):
                    sku.calculated_price = calculated_price
                    sku.final_price = final_price
                    sku.save(update_fields=['calculated_price', 'final_price', 'updated_at'])
                    updated_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"重新计算SKU {sku.id} 价格失败: {e}"))

        return updated_count

    def validate_price_rules(self, products):
        """验证价格规则效果 - 修复版本"""
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('验证价格规则效果')
        self.stdout.write('=' * 50)

        for product in products:
            if not product.price_rules.exists():
                continue

            self.stdout.write(f'\n商品: {product.name}')
            self.stdout.write('-' * 30)

            # 显示所有价格规则
            active_rules = product.price_rules.filter(is_active=True).order_by('priority')
            for rule in active_rules:
                affected_count = rule.get_affected_skus().count()
                self.stdout.write(f'规则: {rule.name} (优先级: {rule.priority})')
                self.stdout.write(f'  条件: {rule.spec_conditions}')
                self.stdout.write(f'  调整: {rule.get_adjustment_type_display()} {rule.adjustment_value}')
                self.stdout.write(f'  影响SKU数量: {affected_count}')

                # 显示受影响的SKU示例
                if affected_count > 0:
                    sample_skus = rule.get_affected_skus()[:2]  # 只显示前2个
                    for sku in sample_skus:
                        base_price = sku.calculated_price
                        final_price = sku.final_price
                        if base_price > 0:
                            discount = ((base_price - final_price) / base_price) * 100
                            self.stdout.write(f'    SKU: {sku.sku_name}')
                            self.stdout.write(f'      原价: {base_price} → 现价: {final_price} (优惠: {discount:.1f}%)')

            # 显示价格范围
            skus = product.skus.all()
            if skus:
                prices = [sku.final_price for sku in skus]
                min_price = min(prices)
                max_price = max(prices)
                avg_price = sum(prices) / len(prices)

                self.stdout.write(f'\n价格统计:')
                self.stdout.write(f'  最低价: {min_price}')
                self.stdout.write(f'  最高价: {max_price}')
                self.stdout.write(f'  平均价: {avg_price:.0f}')
                self.stdout.write(f'  价格区间: {max_price - min_price}')

    def create_banners(self, products):
        """创建轮播图"""
        banners_data = [
            {'title': '新品上市', 'type': 'product', 'product': products[0]},
            {'title': '热销推荐', 'type': 'product', 'product': products[1]},
            {'title': '智能家居', 'type': 'product', 'product': products[2]},
            {'title': '运动装备', 'type': 'product', 'product': products[3]},
            {'title': '限时特惠', 'type': 'activity', 'activity_url': '/pages/activity/special'},
        ]

        for i, banner_data in enumerate(banners_data):
            banner = Banner.objects.create(
                title=banner_data['title'],
                desc=f'{banner_data["title"]}活动描述',
                image=f'https://picsum.photos/750/300?random={random.randint(801, 900)}',
                type=banner_data['type'],
                product=banner_data.get('product'),
                activity_url=banner_data.get('activity_url'),
                external_url=banner_data.get('external_url'),
                sort_order=i * 10,
                is_active=True,
                start_time=timezone.now(),
                end_time=timezone.now() + timezone.timedelta(days=30)
            )
            self.stdout.write(f'创建轮播图: {banner.title}')
