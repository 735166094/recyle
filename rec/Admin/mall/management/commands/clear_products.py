from django.core.management.base import BaseCommand
from django.db import transaction
from mall.models import (
    ProductCategory, Product, ProductSku, ProductReview, Banner,
    ProductSpecGroup, ProductSpecOption, PriceRule,
    GlobalSpecTemplate, GlobalSpecOption
)


class Command(BaseCommand):
    help = '清空商品相关表数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制清空，不进行确认提示',
        )
        parser.add_argument(
            '--skip-categories',
            action='store_true',
            help='跳过清空商品分类',
        )
        parser.add_argument(
            '--skip-global-specs',
            action='store_true',
            help='跳过清空全局规格模板',
        )
        parser.add_argument(
            '--recalculate-prices',
            action='store_true',
            help='清空后重新计算所有SKU价格（实验功能）',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        skip_categories = options.get('skip_categories', False)
        skip_global_specs = options.get('skip_global_specs', False)
        recalculate_prices = options.get('recalculate_prices', False)

        if not force:
            # 显示将要删除的数据统计
            self.show_data_stats(skip_categories, skip_global_specs)

            # 确认提示
            confirm = input(
                '\n⚠️  警告：此操作将永久删除所有商品相关数据！\n'
                '请输入 "YES" 确认执行清空操作: '
            )
            if confirm != 'YES':
                self.stdout.write(self.style.WARNING('操作已取消'))
                return

        # 在事务中执行删除操作
        with transaction.atomic():
            try:
                self.clear_data(skip_categories, skip_global_specs)

                # 如果启用价格重新计算，在清空后执行
                if recalculate_prices:
                    self.recalculate_remaining_prices()

                self.stdout.write(
                    self.style.SUCCESS('商品数据清空完成！')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'清空数据时发生错误: {str(e)}')
                )
                raise

    def recalculate_remaining_prices(self):
        """重新计算剩余SKU的价格（用于测试）"""
        self.stdout.write('重新计算剩余SKU价格...')

        # 这里只是示例，实际清空后没有SKU了
        # 在实际使用中，这个功能可以用于修复价格数据
        try:
            from mall.models import ProductSku
            sku_count = ProductSku.objects.count()
            if sku_count > 0:
                # 调用SKU类的静态方法重新计算所有价格
                updated_count = 0
                for sku in ProductSku.objects.all():
                    sku.calculated_price, sku.final_price = sku.calculate_price()
                    sku.save(update_fields=['calculated_price', 'final_price', 'updated_at'])
                    updated_count += 1
                self.stdout.write(f'重新计算了 {updated_count} 个SKU的价格')
            else:
                self.stdout.write('没有需要重新计算价格的SKU')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'价格重新计算失败: {str(e)}'))

    def show_data_stats(self, skip_categories=False, skip_global_specs=False):
        """显示数据统计"""
        stats = {}

        # 基础模型统计
        stats['Product'] = Product.objects.count()
        stats['ProductSku'] = ProductSku.objects.count()
        stats['ProductReview'] = ProductReview.objects.count()
        stats['Banner'] = Banner.objects.count()
        stats['ProductSpecGroup'] = ProductSpecGroup.objects.count()
        stats['ProductSpecOption'] = ProductSpecOption.objects.count()
        stats['PriceRule'] = PriceRule.objects.count()

        # 可选模型统计
        if not skip_categories:
            stats['ProductCategory'] = ProductCategory.objects.count()

        if not skip_global_specs:
            stats['GlobalSpecTemplate'] = GlobalSpecTemplate.objects.count()
            stats['GlobalSpecOption'] = GlobalSpecOption.objects.count()

        self.stdout.write('当前数据统计:')
        for model_name, count in stats.items():
            self.stdout.write(f'  {model_name}: {count} 条记录')

    def clear_data(self, skip_categories=False, skip_global_specs=False):
        """清空数据的具体实现"""
        self.stdout.write('开始清空商品数据...')

        # 按依赖关系顺序清空数据
        # 1. 先清空有外键依赖的表

        # 商品评价
        review_count = ProductReview.objects.count()
        ProductReview.objects.all().delete()
        self.stdout.write(f'删除 ProductReview: {review_count} 条记录')

        # 价格规则
        price_rule_count = PriceRule.objects.count()
        PriceRule.objects.all().delete()
        self.stdout.write(f'删除 PriceRule: {price_rule_count} 条记录')

        # SKU与规格选项的多对多关系会自动处理，先清空SKU
        sku_count = ProductSku.objects.count()
        ProductSku.objects.all().delete()
        self.stdout.write(f'删除 ProductSku: {sku_count} 条记录')

        # 规格选项
        spec_option_count = ProductSpecOption.objects.count()
        ProductSpecOption.objects.all().delete()
        self.stdout.write(f'删除 ProductSpecOption: {spec_option_count} 条记录')

        # 规格组
        spec_group_count = ProductSpecGroup.objects.count()
        ProductSpecGroup.objects.all().delete()
        self.stdout.write(f'删除 ProductSpecGroup: {spec_group_count} 条记录')

        # 轮播图
        banner_count = Banner.objects.count()
        Banner.objects.all().delete()
        self.stdout.write(f'删除 Banner: {banner_count} 条记录')

        # 商品
        product_count = Product.objects.count()
        Product.objects.all().delete()
        self.stdout.write(f'删除 Product: {product_count} 条记录')

        # 商品分类（可选删除）
        if not skip_categories:
            category_count = ProductCategory.objects.count()
            ProductCategory.objects.all().delete()
            self.stdout.write(f'删除 ProductCategory: {category_count} 条记录')
        else:
            self.stdout.write('跳过删除 ProductCategory')

        # 全局规格选项
        if not skip_global_specs:
            global_option_count = GlobalSpecOption.objects.count()
            GlobalSpecOption.objects.all().delete()
            self.stdout.write(f'删除 GlobalSpecOption: {global_option_count} 条记录')

            # 全局规格模板
            global_template_count = GlobalSpecTemplate.objects.count()
            GlobalSpecTemplate.objects.all().delete()
            self.stdout.write(f'删除 GlobalSpecTemplate: {global_template_count} 条记录')
        else:
            self.stdout.write('跳过删除全局规格模板和选项')

        # 重置自增ID（可选，如果需要的话）
        self.reset_auto_increment(skip_categories, skip_global_specs)

    def reset_auto_increment(self, skip_categories=False, skip_global_specs=False):
        """重置自增ID（MySQL特定）"""
        from django.db import connection

        if connection.vendor == 'mysql':
            with connection.cursor() as cursor:
                # 基础表
                tables = [
                    'product',
                    'product_sku',
                    'product_review',
                    'mall_banner',
                    'mall_productspecgroup',
                    'mall_productspecoption',
                    'price_rule',
                ]

                # 可选表
                if not skip_categories:
                    tables.append('product_category')

                if not skip_global_specs:
                    tables.extend(['global_spec_template', 'global_spec_option'])

                for table in tables:
                    try:
                        cursor.execute(f'ALTER TABLE {table} AUTO_INCREMENT = 1')
                        self.stdout.write(f'重置 {table} 自增ID')
                    except Exception as e:
                        self.stdout.write(f'重置 {table} 自增ID失败: {str(e)}')
        else:
            self.stdout.write('当前数据库不是MySQL，跳过自增ID重置')


class CommandWithConfirmation(BaseCommand):
    """
    带有详细确认的清空命令
    这个类提供了更详细的确认流程，可以选择性地清空不同类型的数据
    """
    help = '交互式清空商品相关表数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--products-only',
            action='store_true',
            help='只清空商品数据，保留分类和规格模板',
        )
        parser.add_argument(
            '--force-all',
            action='store_true',
            help='强制清空所有数据，不进行交互确认',
        )

    def handle(self, *args, **options):
        products_only = options.get('products_only', False)
        force_all = options.get('force_all', False)

        if force_all:
            # 直接清空所有数据
            base_command = Command()
            base_command.handle(force=True, skip_categories=False, skip_global_specs=False)
            return

        if products_only:
            # 只清空商品相关数据
            base_command = Command()
            base_command.handle(force=True, skip_categories=True, skip_global_specs=True)
            return

        # 交互式选择
        self.interactive_clear()

    def interactive_clear(self):
        """交互式清空数据"""
        self.stdout.write(self.style.WARNING('=' * 50))
        self.stdout.write(self.style.WARNING('商品数据清空工具'))
        self.stdout.write(self.style.WARNING('=' * 50))

        # 显示当前数据统计
        base_command = Command()
        base_command.show_data_stats(skip_categories=False, skip_global_specs=False)

        self.stdout.write('\n请选择要清空的数据范围:')
        self.stdout.write('1. 清空所有商品数据（包括分类和规格模板）')
        self.stdout.write('2. 只清空商品数据（保留分类和规格模板）')
        self.stdout.write('3. 取消操作')

        choice = input('\n请输入选择 (1/2/3): ').strip()

        if choice == '1':
            confirm = input('确定要清空所有商品数据吗？请输入 "CONFIRM_ALL": ')
            if confirm == 'CONFIRM_ALL':
                base_command.handle(force=True, skip_categories=False, skip_global_specs=False)
            else:
                self.stdout.write(self.style.WARNING('操作已取消'))
        elif choice == '2':
            confirm = input('确定要清空商品数据（保留分类和规格模板）吗？请输入 "CONFIRM_PRODUCTS": ')
            if confirm == 'CONFIRM_PRODUCTS':
                base_command.handle(force=True, skip_categories=True, skip_global_specs=True)
            else:
                self.stdout.write(self.style.WARNING('操作已取消'))
        else:
            self.stdout.write(self.style.WARNING('操作已取消'))
