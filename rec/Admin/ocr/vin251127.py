# vin.py
import hashlib
import requests
import json
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class VinResponseParser:
    """
    VIN API响应解析器 - 完整字段解析版
    """

    def __init__(self, response_data: Dict[str, Any]):
        """
        初始化解析器

        Args:
            response_data: API返回的JSON数据
        """
        self.raw_data = response_data
        self.data = response_data.get('data', {})

    @property
    def code(self) -> int:
        """返回状态码"""
        return self.raw_data.get('code', -1)

    @property
    def message(self) -> str:
        """返回消息"""
        return self.raw_data.get('msg', '')

    @property
    def is_success(self) -> bool:
        """是否成功"""
        return self.code == 1

    # 基本信息属性 - 根级别字段
    @property
    def model_year_from_vin(self) -> str:
        """VIN生产年份"""
        return self.data.get('model_year_from_vin', '')

    @property
    def epc(self) -> str:
        """品牌对应的Epc标识"""
        return self.data.get('epc', '')

    @property
    def epc_cn(self) -> str:
        """品牌中文名"""
        return self.data.get('epc_cn', '')

    @property
    def my_model_std_id(self) -> str:
        """已废弃，已改为epc_id"""
        return self.data.get('my_model_std_id', '')

    @property
    def epc_id(self) -> str:
        """某原厂epc下面的细分车型id"""
        return self.data.get('epc_id', '')

    @property
    def matching_mode(self) -> str:
        """匹配模式，包括exact_match（精准匹配），inexact_match（非精准匹配）"""
        return self.data.get('matching_mode', '')

    @property
    def brand(self) -> str:
        """品牌"""
        return self.data.get('brand', '')

    @property
    def gonggao_no(self) -> str:
        """车辆公告编号"""
        return self.data.get('gonggao_no', '')

    @property
    def build_date(self) -> str:
        """生产日期"""
        return self.data.get('build_date', '')

    # 车型列表相关方法
    def get_model_list(self) -> List[Dict[str, Any]]:
        """获取通俗车型信息列表"""
        return self.data.get('model_list', [])

    def get_first_model(self) -> Optional[Dict[str, Any]]:
        """获取第一个车型信息"""
        model_list = self.get_model_list()
        return model_list[0] if model_list else None

    def get_model_by_id(self, model_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取车型信息"""
        for model in self.get_model_list():
            if model.get('Id') == model_id:
                return model
        return None

    @staticmethod
    def get_model_images(model: Dict[str, Any]) -> List[str]:
        """获取车型图片URL列表"""
        img_address = model.get('Img_adress', '')
        if not img_address:
            return []

        base_url = "http://resource.17vin.com/img/car/all/"
        img_paths = [path.strip() for path in img_address.split(',')]
        return [f"{base_url}{path}" for path in img_paths if path]

    # 原厂车型信息
    def get_original_epc_list(self) -> List[Dict[str, Any]]:
        """获取原厂车型信息列表"""
        return self.data.get('model_original_epc_list', [])

    def get_original_attributes(self, language: str = 'zh') -> List[Dict[str, Any]]:
        """获取原厂车型属性（支持中英文）"""
        epc_list = self.get_original_epc_list()
        if not epc_list:
            return []

        attributes = epc_list[0].get('CarAttributes', [])
        return [attr for attr in attributes if attr.get('Language') == language]

    # 公告列表信息
    def get_gonggao_list(self) -> List[Dict[str, Any]]:
        """获取公告列表信息"""
        return self.data.get('model_gonggao_list', [])

    # 进口车型信息
    def get_import_list(self) -> List[Dict[str, Any]]:
        """获取进口车型信息列表"""
        return self.data.get('model_import_list', [])

    # 格式化输出方法
    def print_basic_info(self):
        """打印基本信息"""
        print("=" * 50)
        print("VIN查询结果 - 基本信息")
        print("=" * 50)
        print(f"状态: {'成功' if self.is_success else '失败'} - {self.message}")
        print(f"品牌: {self.brand}")
        print(f"EPC标识: {self.epc}")
        print(f"EPC中文名: {self.epc_cn}")
        print(f"EPC ID: {self.epc_id}")
        print(f"my_model_std_id(已废弃): {self.my_model_std_id}")
        print(f"生产年份: {self.model_year_from_vin}")
        print(f"生产日期: {self.build_date}")
        print(f"匹配模式: {self.matching_mode}")
        print(f"公告编号: {self.gonggao_no}")

    def print_model_info(self, detailed: bool = True):
        """打印车型信息

        Args:
            detailed: 是否显示详细信息
        """
        model_list = self.get_model_list()
        if not model_list:
            print("\n未找到车型信息")
            return

        print(f"\n找到 {len(model_list)} 个匹配车型:")
        print("=" * 80)

        for i, model in enumerate(model_list, 1):
            print(f"\n车型 {i}:")
            print("-" * 40)

            # 基本信息
            print("【基本信息】")
            print(f"  车型ID: {model.get('Id', '')}")
            print(f"  JS ID: {model.get('Js_id', '')}")
            print(f"  车型详细配置KEY: {model.get('model_detail_key', '')}")
            print(f"  公告编号: {model.get('Gonggao_no', '')}")
            print(f"  分组ID: {model.get('Group_id', '')}")
            print(f"  EPC标识: {model.get('Epc', '')}")
            print(f"  EPC ID: {model.get('Epc_id', '')}")
            print(f"  车型年份: {model.get('Model_year', '')}")

            # 车型描述
            print("【车型描述】")
            print(f"  车型详细说明: {model.get('Model_detail', '')}")
            print(f"  车型英文说明: {model.get('Model_detial_en', '')}")
            print(f"  厂家: {model.get('Factory', '')}")
            print(f"  品牌: {model.get('Brand', '')}")
            print(f"  车型: {model.get('Model', '')}")
            print(f"  车系: {model.get('Series', '')}")
            print(f"  销售版本: {model.get('Sales_version', '')}")

            # 动力系统
            print("【动力系统】")
            print(f"  排量: {model.get('Cc', '')}")
            print(f"  发动机: {model.get('Engine_no', '')}")
            print(f"  进气形式: {model.get('Air_intake', '')}")
            print(f"  燃油类型: {model.get('Fuel_type', '')}")

            # 传动系统
            print("【传动系统】")
            print(f"  变速箱: {model.get('Transmission_detail', '')}")
            print(f"  档位数: {model.get('Gear_num', '')}")
            print(f"  驱动方式: {model.get('Driving_mode', '')}")
            print(f"  变速箱代码: {model.get('Trans_code', '')}")

            # 车身信息
            print("【车身信息】")
            print(f"  底盘代码: {model.get('Chassis_code', '')}")
            print(f"  车门数: {model.get('Door_num', '')}")
            print(f"  座位数: {model.get('Seat_num', '')}")
            print(f"  车身类型: {model.get('Body_type', '')}")

            # 生产信息
            print("【生产信息】")
            print(f"  上市年份: {model.get('Date_begin', '')}")
            print(f"  停产日期: {model.get('Date_end', '')}")
            print(f"  参考价格: {model.get('Price', '')}元")

            # 其他信息
            print("【其他信息】")
            print(f"  汽车之家ID: {model.get('Autohome_id', '')}")
            print(f"  XS ID: {model.get('Xs_id', '')}")
            print(f"  URL Make: {model.get('UrlMake', '')}")

            # 显示图片
            images = self.get_model_images(model)
            if images:
                print(f"  图片数量: {len(images)}")
                for j, img_url in enumerate(images[:3], 1):  # 只显示前3张
                    print(f"    图片 {j}: {img_url}")
                if len(images) > 3:
                    print(f"    ... 还有 {len(images) - 3} 张图片")

    def print_original_epc_info(self):
        """打印原厂EPC信息"""
        epc_list = self.get_original_epc_list()
        if not epc_list:
            print("\n未找到原厂车型信息")
            return

        print("\n" + "=" * 50)
        print("原厂车型信息")
        print("=" * 50)

        for epc in epc_list:
            print(f"\nEPC ID: {epc.get('Epc_id', '')}")

            attributes = epc.get('CarAttributes', [])
            if attributes:
                # 按语言分组
                zh_attributes = [attr for attr in attributes if attr.get('Language') == 'zh']
                en_attributes = [attr for attr in attributes if attr.get('Language') == 'en']

                if zh_attributes:
                    print("\n【中文配置】")
                    for attr in zh_attributes:
                        is_major = "★" if attr.get('IsMajorAttribute') else " "
                        print(f"  {is_major} {attr.get('Col_name', '')}: {attr.get('Col_value', '')}")

                if en_attributes:
                    print("\n【英文配置】")
                    for attr in en_attributes:
                        is_major = "★" if attr.get('IsMajorAttribute') else " "
                        print(f"  {is_major} {attr.get('Col_name', '')}: {attr.get('Col_value', '')}")

    def print_gonggao_info(self):
        """打印公告信息"""
        gonggao_list = self.get_gonggao_list()
        if not gonggao_list:
            print("\n未找到公告信息")
            return

        print("\n" + "=" * 50)
        print("公告信息")
        print("=" * 50)

        for i, gonggao in enumerate(gonggao_list, 1):
            print(f"\n公告 {i}:")
            print("-" * 30)

            # 基本信息
            print("【基本信息】")
            print(f"  公告型号: {gonggao.get('F4', '')}")
            print(f"  公告批次: {gonggao.get('F5', '')}")
            print(f"  品牌: {gonggao.get('F6', '')}")
            print(f"  类型: {gonggao.get('F7', '')}")
            print(f"  额定质量: {gonggao.get('F8', '')}")
            print(f"  总质量: {gonggao.get('F9', '')}kg")
            print(f"  燃料种类: {gonggao.get('F11', '')}")
            print(f"  排放标准: {gonggao.get('F12', '')}")

            # 底盘参数
            print("【底盘参数】")
            print(f"  轴数: {gonggao.get('F13', '')}")
            print(f"  轴距: {gonggao.get('F14', '')}")
            print(f"  轴荷: {gonggao.get('F15', '')}")
            print(f"  弹簧片数: {gonggao.get('F16', '')}")
            print(f"  轮胎数: {gonggao.get('F17', '')}")
            print(f"  轮胎规格: {gonggao.get('F18', '')}")

            # 尺寸参数
            print("【尺寸参数】")
            print(f"  接近离去角: {gonggao.get('F19', '')}")
            print(f"  前悬后悬: {gonggao.get('F20', '')}")
            print(f"  前轮距: {gonggao.get('F21', '')}")
            print(f"  后轮距: {gonggao.get('F22', '')}")
            print(f"  整车长: {gonggao.get('F23', '')}")
            print(f"  整车宽: {gonggao.get('F24', '')}")
            print(f"  整车高: {gonggao.get('F25', '')}")
            print(f"  货厢长: {gonggao.get('F26', '')}")
            print(f"  货厢宽: {gonggao.get('F27', '')}")
            print(f"  货厢高: {gonggao.get('F28', '')}")

            # 性能参数
            print("【性能参数】")
            print(f"  最高车速: {gonggao.get('F29', '')}km/h")
            print(f"  额定载客: {gonggao.get('F30', '')}")
            print(f"  驾驶室准乘人数: {gonggao.get('F31', '')}")
            print(f"  转向形式: {gonggao.get('F32', '')}")
            print(f"  准拖挂车总质量: {gonggao.get('F33', '')}")
            print(f"  载质量利用系数: {gonggao.get('F34', '')}")
            print(f"  半挂车鞍座最大承载质量: {gonggao.get('F35', '')}")

            # 企业信息
            print("【企业信息】")
            print(f"  企业名称: {gonggao.get('F36', '')}")
            print(f"  企业地址: {gonggao.get('F37', '')}")
            print(f"  电话号码: {gonggao.get('F38', '')}")
            print(f"  传真号码: {gonggao.get('F39', '')}")
            print(f"  邮政编码: {gonggao.get('F40', '')}")

            # 底盘信息
            print("【底盘信息】")
            print(f"  底盘1: {gonggao.get('F41', '')}")
            print(f"  底盘2: {gonggao.get('F42', '')}")
            print(f"  底盘3: {gonggao.get('F43', '')}")
            print(f"  底盘4: {gonggao.get('F44', '')}")
            print(f"  备注: {gonggao.get('F45', '')}")

            # 发动机信息
            engines = gonggao.get('Engines', [])
            if engines:
                print("【发动机信息】")
                for j, engine in enumerate(engines, 1):
                    print(f"  发动机 {j}:")
                    print(f"    型号: {engine.get('Engine_no', '')}")
                    print(f"    排量: {engine.get('Cc', '')}cc")
                    print(f"    功率: {engine.get('Kw', '')}kW")
                    print(f"    厂家: {engine.get('Factory', '')}")

    def print_import_info(self):
        """打印进口车型信息"""
        import_list = self.get_import_list()
        if not import_list:
            print("\n未找到进口车型信息")
            return

        print("\n" + "=" * 50)
        print("进口车型信息")
        print("=" * 50)

        for i, import_car in enumerate(import_list, 1):
            print(f"\n进口车型 {i}:")
            print("-" * 30)

            print(f"  EPC标识: {import_car.get('Epc', '')}")
            print(f"  品牌: {import_car.get('Make_cn', '')}")
            print(f"  车型: {import_car.get('Model_cn', '')}")
            print(f"  车身类型: {import_car.get('Body_style_cn', '')}")
            print(f"  排量: {import_car.get('Cc_cn', '')}")
            print(f"  发动机: {import_car.get('Engine_cn', '')}")
            print(f"  变速箱说明: {import_car.get('Trim_cn', '')}")
            print(f"  变速箱: {import_car.get('Transmission_cn', '')}")
            print(f"  驱动方式: {import_car.get('Driveline_cn', '')}")
            print(f"  乘坐标准: {import_car.get('Seating_standard_cn', '')}")
            print(f"  长度: {import_car.get('Length_cn', '')}")
            print(f"  宽度: {import_car.get('Width_cn', '')}")
            print(f"  高度: {import_car.get('Height_cn', '')}")

    def print_summary(self, detailed: bool = True):
        """打印完整摘要信息

        Args:
            detailed: 是否显示详细信息
        """
        self.print_basic_info()
        self.print_model_info(detailed)

        # 根据匹配模式决定显示哪些信息
        if self.matching_mode == 'exact_match':
            self.print_original_epc_info()
        else:
            self.print_gonggao_info()
            self.print_import_info()

    def get_all_data(self) -> Dict[str, Any]:
        """获取所有解析后的数据"""
        return {
            'basic_info': {
                'code': self.code,
                'message': self.message,
                'is_success': self.is_success,
                'model_year_from_vin': self.model_year_from_vin,
                'epc': self.epc,
                'epc_cn': self.epc_cn,
                'my_model_std_id': self.my_model_std_id,
                'epc_id': self.epc_id,
                'matching_mode': self.matching_mode,
                'brand': self.brand,
                'gonggao_no': self.gonggao_no,
                'build_date': self.build_date
            },
            'model_list': self.get_model_list(),
            'original_epc_list': self.get_original_epc_list(),
            'gonggao_list': self.get_gonggao_list(),
            'import_list': self.get_import_list(),
            'raw_data': self.raw_data  # 包含原始完整数据
        }

    def export_to_json(self, filename: str):
        """导出所有数据到JSON文件"""
        all_data = self.get_all_data()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"数据已导出到: {filename}")

    def extract_vehicle_name(self, model_index: int = 0) -> str:
        """
        提取车辆名称
        格式：品牌 + 系列 + 排量（如：江淮骏铃 骏铃E3 2.156L）

        Args:
            model_index: 车型列表中的索引，默认取第一个

        Returns:
            str: 格式化后的车辆名称
        """
        try:
            model_list = self.get_model_list()
            if not model_list or model_index >= len(model_list):
                return ""

            model = model_list[model_index]

            # 获取品牌、系列、排量信息
            brand = model.get('Brand', '').strip() or self.brand or ''
            series = model.get('Series', '').strip()
            cc_str = model.get('Cc', '').strip()

            # 处理排量：将cc转换为L
            engine_displacement = ''
            if cc_str:
                try:
                    # 尝试将cc转换为升
                    cc_value = float(cc_str)
                    if cc_value > 0:
                        # 转换为升，保留3位小数
                        liters = cc_value / 1000.0
                        # 格式化为2.156L样式
                        if liters.is_integer():
                            engine_displacement = f"{int(liters)}.0L"
                        else:
                            # 保留3位小数，但去除末尾的0
                            formatted = f"{liters:.3f}".rstrip('0').rstrip('.')
                            engine_displacement = f"{formatted}L"
                except (ValueError, TypeError):
                    # 如果转换失败，直接使用原值
                    engine_displacement = f"{cc_str}L"

            # 构建车辆名称
            parts = []
            if brand:
                parts.append(brand)
            if series:
                parts.append(series)
            if engine_displacement:
                parts.append(engine_displacement)

            if parts:
                return ' '.join(parts)

            # 如果上述方法都无法提取，返回Model_detail
            model_detail = model.get('Model_detail', '').strip()
            if model_detail:
                return model_detail

            return ""

        except Exception as e:
            logger.error(f"提取车辆名称失败: {str(e)}")
            return ""

    def extract_production_year(self, model_index: int = 0) -> str:
        """
        提取生产年份
        格式：2013款

        Args:
            model_index: 车型列表中的索引，默认取第一个

        Returns:
            str: 生产年份
        """
        try:
            model_list = self.get_model_list()
            if not model_list or model_index >= len(model_list):
                return ""

            model = model_list[model_index]

            # 尝试从Model_detail中提取年份
            model_detail = model.get('Model_detail', '').strip()
            if model_detail:
                # 查找年份模式，如：2013款、2015款等
                import re
                year_match = re.search(r'(\d{4})款', model_detail)
                if year_match:
                    return f"{year_match.group(1)}款"

            # 使用Model_year字段
            model_year = model.get('Model_year', '').strip()
            if model_year:
                return f"{model_year}款"

            # 使用VIN生产年份
            if self.model_year_from_vin:
                return f"{self.model_year_from_vin}款"

            return ""

        except Exception as e:
            logger.error(f"提取生产年份失败: {str(e)}")
            return ""

    def extract_vehicle_names_with_years(self, max_models: int = 3) -> list:
        """
        提取多个车型的车辆名称和生产年份

        Args:
            max_models: 最大提取数量

        Returns:
            list: 包含车辆名称和生产年份的字典列表
        """
        try:
            model_list = self.get_model_list()
            if not model_list:
                return []

            results = []
            for i, model in enumerate(model_list[:max_models]):
                brand = model.get('Brand', '').strip() or self.brand or ''
                series = model.get('Series', '').strip()
                cc_str = model.get('Cc', '').strip()

                # 处理排量
                engine_displacement = ''
                if cc_str:
                    try:
                        cc_value = float(cc_str)
                        if cc_value > 0:
                            liters = cc_value / 1000.0
                            if liters.is_integer():
                                engine_displacement = f"{int(liters)}.0L"
                            else:
                                formatted = f"{liters:.3f}".rstrip('0').rstrip('.')
                                engine_displacement = f"{formatted}L"
                    except (ValueError, TypeError):
                        engine_displacement = f"{cc_str}L"

                # 构建车辆名称
                parts = []
                if brand:
                    parts.append(brand)
                if series:
                    parts.append(series)
                if engine_displacement:
                    parts.append(engine_displacement)

                vehicle_name = ' '.join(parts) if parts else model.get('Model_detail', '').strip()

                # 提取生产年份
                production_year = ''
                model_detail = model.get('Model_detail', '').strip()
                if model_detail:
                    import re
                    year_match = re.search(r'(\d{4})款', model_detail)
                    if year_match:
                        production_year = f"{year_match.group(1)}款"

                if not production_year:
                    model_year = model.get('Model_year', '').strip()
                    production_year = f"{model_year}款" if model_year else ""

                results.append({
                    'vehicle_name': vehicle_name,
                    'production_year': production_year,
                    'model_detail': model.get('Model_detail', ''),
                    'brand': brand,
                    'series': series,
                    'cc': cc_str
                })

            return results

        except Exception as e:
            logger.error(f"提取车辆信息失败: {str(e)}")
            return []


# API客户端保持不变
class VinAPIWithParser:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.base_url = "http://api.17vin.com:8080/"

    def _compute_md5(self, text: str) -> str:
        """计算MD5哈希值"""
        return hashlib.md5(text.encode('utf-8')).hexdigest().lower()

    def _generate_token(self, vin: str) -> str:
        """生成API token"""
        url_parameters = f"/?vin={vin}"
        user_md5 = self._compute_md5(self.username)
        pass_md5 = self._compute_md5(self.password)
        return self._compute_md5(user_md5 + pass_md5 + url_parameters)

    def query_vin(self, vin: str, timeout: int = 10) -> VinResponseParser:
        """
        查询VIN信息并返回解析器对象

        Args:
            vin: 车辆VIN码
            timeout: 请求超时时间

        Returns:
            VinResponseParser: 响应解析器对象
        """
        token = self._generate_token(vin)

        params = {
            'vin': vin,
            'user': self.username,
            'token': token
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=timeout)
            response.raise_for_status()

            response_data = response.json()
            return VinResponseParser(response_data)

        except requests.exceptions.RequestException as e:
            # 返回一个错误响应的解析器
            error_data = {
                'code': -1,
                'msg': f'请求错误: {str(e)}',
                'data': {}
            }
            return VinResponseParser(error_data)
        except json.JSONDecodeError as e:
            error_data = {
                'code': -1,
                'msg': f'JSON解析错误: {str(e)}',
                'data': {}
            }
            return VinResponseParser(error_data)


# VIN配置管理器
class VinConfigManager:
    """VIN配置管理器 - 从数据库获取配置"""

    @staticmethod
    def get_active_config():
        """获取激活的VIN配置"""
        try:
            from .models import VinConfig
            config = VinConfig.objects.filter(is_active=True).first()
            if config:
                logger.info(f"获取到VIN配置: {config.name}")
            else:
                logger.warning("未找到激活的VIN配置")
            return config
        except Exception as e:
            logger.error(f"获取VIN配置失败: {str(e)}")
            return None

    @staticmethod
    def get_config_by_id(config_id):
        """根据ID获取VIN配置"""
        try:
            from .models import VinConfig
            config = VinConfig.objects.filter(id=config_id, is_active=True).first()
            if config:
                logger.info(f"获取到指定VIN配置: {config.name}")
            else:
                logger.warning(f"未找到ID为 {config_id} 的激活VIN配置")
            return config
        except Exception as e:
            logger.error(f"获取指定VIN配置失败: {str(e)}")
            return None

    @staticmethod
    def create_api_client(config=None):
        """创建VIN API客户端"""
        if config is None:
            config = VinConfigManager.get_active_config()

        if not config:
            raise ValueError("未找到有效的VIN配置")

        # 确保使用VinConfig中的用户名和密码
        if not config.username or not config.password:
            raise ValueError("VIN配置中的用户名或密码为空")

        return VinAPIWithParser(config.username, config.password)  # 这里正确使用了VinConfig的凭据

    @staticmethod
    def query_vin_with_config(vin_code, config=None, timeout=10, debug=False):
        """使用配置查询VIN码"""
        try:
            api_client = VinConfigManager.create_api_client(config)
            return api_client.query_vin(vin_code, timeout)
        except Exception as e:
            logger.error(f"使用配置查询VIN失败: {str(e)}")
            error_data = {
                'code': -1,
                'msg': f'配置错误: {str(e)}',
                'data': {}
            }
            parser = VinResponseParser(error_data)
            return parser


# 使用示例
if __name__ == "__main__":
    # 配置您的用户名和密码
    USERNAME = "USERNAME"  # 请替换为实际用户名
    PASSWORD = "PASSWORD"  # 请替换为实际密码

    # 创建API客户端
    api = VinAPIWithParser(USERNAME, PASSWORD)

    # 查询VIN
    vin_code = "LCN643DTXD0000288"  # 替换为实际VIN码
    parser = api.query_vin(vin_code)

    # 打印完整信息
    if parser.is_success:
        print("查询成功!")
        parser.print_summary(detailed=True)

        # 导出数据到JSON文件
        parser.export_to_json(f"vin_result_{vin_code}.json")

        # 显示匹配模式说明
        print("\n" + "=" * 50)
        print("匹配模式说明")
        print("=" * 50)
        if parser.matching_mode == 'exact_match':
            print("精准匹配 - 显示原厂车型详细信息")
        else:
            print("非精准匹配 - 显示公告和进口车型信息")
            print("备注:")
            print("  - model_gonggao_list只有在非精准解码才会有信息，比如上汽通用")
            print("  - model_import_list只有在非精准解码进口epc才会有信息，比如法拉利")

    else:
        print(f"查询失败: {parser.message}")
