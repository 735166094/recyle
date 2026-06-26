import os
import re
import base64
import logging
from datetime import datetime
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkocr.v1.region.ocr_region import OcrRegion
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkocr.v1 import *

# 配置日志
logger = logging.getLogger(__name__)


class HuaweiOcrClient:
    """华为云OCR接口调用客户端"""

    def __init__(self, ak, sk, region="cn-north-4"):
        """初始化客户端"""
        self.ak = ak
        self.sk = sk
        self.region = region
        self.client = self._create_client()

    def _create_client(self):
        """创建OCR客户端"""
        try:
            credentials = BasicCredentials(self.ak, self.sk)
            client = OcrClient.new_builder() \
                .with_credentials(credentials) \
                .with_region(OcrRegion.value_of(self.region)) \
                .build()
            logger.info(f"华为云OCR客户端创建成功，区域: {self.region}")
            return client
        except Exception as e:
            logger.error(f"创建华为云OCR客户端失败: {str(e)}")
            raise

    @staticmethod
    def encode_image_to_base64(image_path):
        """将图片文件编码为base64格式"""
        try:
            if not os.path.exists(image_path):
                logger.error(f"图片文件不存在: {image_path}")
                return None

            with open(image_path, 'rb') as f:
                image_data = f.read()
                encoded = base64.b64encode(image_data).decode('utf-8')
                logger.info(f"图片编码成功，大小: {len(encoded)} 字符")
                return encoded
        except Exception as e:
            logger.error(f"图片编码失败: {str(e)}")
            return None

    def recognize_general_text(self, image_path):
        """调用通用文字识别接口"""
        try:
            logger.info(f"开始通用文字识别: {image_path}")
            image_base64 = self.encode_image_to_base64(image_path)
            if not image_base64:
                return None

            request = RecognizeGeneralTextRequest()
            request.body = GeneralTextRequestBody(image=image_base64)
            response = self.client.recognize_general_text(request)
            logger.info("通用文字识别成功")
            return response
        except exceptions.ClientRequestException as e:
            logger.error(f"通用文字识别请求错误: {e.status_code} - {e.error_msg}")
            return None
        except Exception as e:
            logger.error(f"通用文字识别发生错误: {str(e)}")
            return None

    def recognize_id_card(self, image_path, side="double_side"):
        """调用身份证识别接口

        Args:
            image_path: 图片文件路径
            side: 身份证正反面，front-人像面，back-国徽面 double_side（正反面）
        """
        try:
            logger.info(f"开始身份证识别: {image_path}, 面: {side}")
            image_base64 = self.encode_image_to_base64(image_path)
            if not image_base64:
                return None

            request = RecognizeIdCardRequest()
            request.body = IdCardRequestBody(
                image=image_base64,
                side=side
            )
            response = self.client.recognize_id_card(request)
            logger.info(f"身份证识别成功 - 面: {side}")
            return response
        except exceptions.ClientRequestException as e:
            logger.error(f"身份证识别请求错误: {e.status_code} - {e.error_msg}")
            return None
        except Exception as e:
            logger.error(f"身份证识别发生错误: {str(e)}")
            return None

    def recognize_vehicle_license(self, image_path):
        """调用行驶证识别接口"""
        try:
            image_base64 = self.encode_image_to_base64(image_path)
            if not image_base64:
                return None

            request = RecognizeVehicleLicenseRequest()
            request.body = VehicleLicenseRequestBody(
                image=image_base64,
                side="double_side"  # 明确指定双面识别
            )
            response = self.client.recognize_vehicle_license(request)
            logger.info("行驶证识别成功")
            return response
        except exceptions.ClientRequestException as e:
            logger.error(f"行驶证识别请求错误: {e.error_msg}")
            return None
        except Exception as e:
            logger.error(f"行驶证识别发生错误: {str(e)}")
            return None

    def recognize_business_license(self, image_path):
        """调用营业执照识别接口"""
        try:
            image_base64 = self.encode_image_to_base64(image_path)
            if not image_base64:
                return None

            request = RecognizeBusinessLicenseRequest()
            request.body = BusinessLicenseRequestBody(image=image_base64)
            response = self.client.recognize_business_license(request)
            logger.info("营业执照识别成功")
            return response
        except exceptions.ClientRequestException as e:
            logger.error(f"营业执照识别请求错误: {e.error_msg}")
            return None
        except Exception as e:
            logger.error(f"营业执照识别发生错误: {str(e)}")
            return None

    def recognize_auto_classification(self, image_path):
        """调用智能分类识别接口"""
        try:
            image_base64 = self.encode_image_to_base64(image_path)
            if not image_base64:
                return None

            request = RecognizeAutoClassificationRequest()
            request.body = AutoClassificationRequestBody(image=image_base64)
            response = self.client.recognize_auto_classification(request)
            logger.info("智能分类识别成功")
            return response
        except exceptions.ClientRequestException as e:
            logger.error(f"智能分类识别请求错误: {e.error_msg}")
            return None
        except Exception as e:
            logger.error(f"智能分类识别发生错误: {str(e)}")
            return None

    def recognize_auto_classification(self, image_path):
        """调用智能分类识别接口 - 用于身份证识别"""
        try:
            logger.info(f"开始智能分类识别: {image_path}")
            image_base64 = self.encode_image_to_base64(image_path)
            if not image_base64:
                return None

            request = RecognizeAutoClassificationRequest()
            request.body = AutoClassificationRequestBody(
                image=image_base64
            )
            response = self.client.recognize_auto_classification(request)
            logger.info("智能分类识别成功")
            return response
        except exceptions.ClientRequestException as e:
            logger.error(f"智能分类识别请求错误: {e.error_msg}")
            return None
        except Exception as e:
            logger.error(f"智能分类识别发生错误: {str(e)}")
            return None

    def extract_id_card_from_auto_classification(result):
        """从智能分类识别结果中提取身份证信息"""
        try:
            if not result or not hasattr(result, 'result'):
                return None

            result_dict = result.to_dict()
            result_list = result_dict.get('result', [])

            id_card_data = {
                'front': {},  # 人像面
                'back': {}  # 国徽面
            }

            for item in result_list:
                item_type = item.get('type', '')
                content = item.get('content', {})
                status = item.get('status', {})

                # 检查识别状态
                if status.get('error_code') != 'AIS.0000':
                    continue

                if item_type == 'id_card_portrait_side':
                    # 人像面信息
                    id_card_data['front'] = {
                        'name': content.get('name'),
                        'gender': content.get('sex'),
                        'ethnicity': content.get('ethnicity'),
                        'birth': content.get('birth'),
                        'address': content.get('address'),
                        'number': content.get('number'),
                        'side': 'front'
                    }

                elif item_type == 'id_card_emblem_side':
                    # 国徽面信息
                    id_card_data['back'] = {
                        'issue_authority': content.get('issue'),
                        'valid_from': content.get('valid_from'),
                        'valid_to': content.get('valid_to'),
                        'side': 'back'
                    }

            return id_card_data

        except Exception as e:
            logger.error(f"提取身份证信息失败: {str(e)}")
            return None


def extract_all_text(result):
    """从通用文字识别结果中提取所有文本内容"""
    all_text = []
    if not result or not hasattr(result, 'result'):
        return all_text
    try:
        if hasattr(result.result, 'words_block_list'):
            for block in result.result.words_block_list:
                if hasattr(block, 'words'):
                    all_text.append(block.words)
    except Exception as e:
        logger.error(f"提取文本时出错: {str(e)}")
    return all_text


def remove_spaces(text):
    """去除文本中的所有空格"""
    return text.replace(" ", "") if text else ""


def classify_document(all_text):
    """根据文本内容对文档进行分类 """
    if not all_text:
        return "unknown"

    full_text = remove_spaces(" ".join(all_text))

    # 定义关键词（去除空格）
    target_id = remove_spaces("公民身份号码")
    target_driving = remove_spaces("中华人民共和国机动车行驶证")
    target_business = remove_spaces("营业执照")
    target_vehicle = remove_spaces("车辆识别代号")
    target_license = remove_spaces("机动车行驶证")

    # 新增更多关键词以提高识别准确性
    id_card_keywords = [
        remove_spaces("公民身份号码"),
        remove_spaces("居民身份证"),
        remove_spaces("姓名"),
        remove_spaces("性别"),
        remove_spaces("民族"),
        remove_spaces("出生"),
        remove_spaces("住址"),
    ]

    vehicle_keywords = [
        remove_spaces("中华人民共和国机动车行驶证"),
        remove_spaces("机动车行驶证"),
        remove_spaces("车辆识别代号"),
        remove_spaces("发动机号码"),
        remove_spaces("号牌号码"),
        remove_spaces("车辆类型"),
        remove_spaces("所有人"),
    ]

    business_keywords = [
        remove_spaces("营业执照"),
        remove_spaces("企业名称"),
        remove_spaces("法定代表人"),
        remove_spaces("注册资本"),
        remove_spaces("成立日期"),
        remove_spaces("经营范围"),
        remove_spaces("注册号"),
    ]

    # 计算关键词匹配数量
    id_card_matches = sum(1 for keyword in id_card_keywords if keyword in full_text)
    vehicle_matches = sum(1 for keyword in vehicle_keywords if keyword in full_text)
    business_matches = sum(1 for keyword in business_keywords if keyword in full_text)

    # 基于匹配数量进行分类
    if business_matches >= 2:
        return "business_license"
    elif vehicle_matches >= 2:
        return "vehicle_license"
    elif id_card_matches >= 2:
        return "id_card"
    else:
        return "unknown"


def enhanced_classify_document(all_text):
    """文档分类 - 支持更多证件类型"""
    if not all_text:
        return "unknown"

    full_text = remove_spaces(" ".join(all_text)).lower()

    # 身份证关键词
    id_keywords = [
        remove_spaces("公民身份号码"),
        remove_spaces("居民身份证"),
        remove_spaces("姓名"),
        remove_spaces("性别"),
        remove_spaces("民族"),
        remove_spaces("出生"),
        remove_spaces("住址"),
        remove_spaces("签发机关"),
        remove_spaces("有效期限"),
    ]

    # 行驶证关键词
    vehicle_keywords = [
        remove_spaces("中华人民共和国机动车行驶证"),
        remove_spaces("机动车行驶证"),
        remove_spaces("车辆识别代号"),
        remove_spaces("发动机号码"),
        remove_spaces("号牌号码"),
        remove_spaces("车辆类型"),
        remove_spaces("所有人"),
        remove_spaces("使用性质"),
        remove_spaces("注册日期"),
        remove_spaces("发证日期"),
    ]

    # 营业执照关键词
    business_keywords = [
        remove_spaces("营业执照"),
        remove_spaces("企业名称"),
        remove_spaces("法定代表人"),
        remove_spaces("注册资本"),
        remove_spaces("成立日期"),
        remove_spaces("经营范围"),
        remove_spaces("注册号"),
        remove_spaces("统一社会信用代码"),
        remove_spaces("住所"),
        remove_spaces("营业期限"),
    ]

    # 计算匹配分数
    id_score = sum(3 for keyword in id_keywords if keyword in full_text)
    vehicle_score = sum(3 for keyword in vehicle_keywords if keyword in full_text)
    business_score = sum(3 for keyword in business_keywords if keyword in full_text)

    # 添加简单关键词匹配（分数较低）
    if "身份证" in full_text:
        id_score += 2
    if "行驶证" in full_text:
        vehicle_score += 2
    if "营业执照" in full_text:
        business_score += 2

    # 根据分数决定类型
    scores = {
        "id_card": id_score,
        "vehicle_license": vehicle_score,
        "business_license": business_score
    }

    max_type = max(scores, key=scores.get)
    return max_type if scores[max_type] > 3 else "unknown"


def query_vin_for_vehicle_info(vin_code, model_index: int = 0):
    """
    查询VIN码获取车辆信息

    Args:
        vin_code: VIN码
        model_index: 车型列表中的索引，默认取第一个

    Returns:
        dict: 包含车辆信息的字典
    """
    try:
        # 导入VIN模块
        from .vin251127 import VinConfigManager

        # 获取VIN配置
        config = VinConfigManager.get_active_config()
        if not config:
            logger.error("未找到激活的VIN配置")
            return None

        # 查询VIN
        parser = VinConfigManager.query_vin_with_config(vin_code, config)
        if not parser or not parser.is_success:
            logger.error(f"VIN查询失败: {parser.message if parser else '解析器为空'}")
            return None

        # 提取车辆信息
        vehicle_info = {
            'vin': vin_code,
            'brand': parser.brand,
            'model_year': parser.model_year_from_vin,
            'build_date': parser.build_date,
            'success': True,
            'message': parser.message
        }

        # 提取车辆名称
        vehicle_name = parser.extract_vehicle_name(model_index)
        if vehicle_name:
            vehicle_info['vehicle_name'] = vehicle_name

        # 提取生产年份
        production_year = parser.extract_production_year(model_index)
        if production_year:
            vehicle_info['production_year'] = production_year

        # 提取多个车型信息
        vehicle_names_with_years = parser.extract_vehicle_names_with_years(max_models=5)
        if vehicle_names_with_years:
            vehicle_info['vehicle_options'] = vehicle_names_with_years

        # 提取车型列表（简化版）
        model_list = []
        for i, model in enumerate(parser.get_model_list()[:3]):  # 只取前3个
            simplified_model = {
                'index': i,
                'model_detail': model.get('Model_detail', ''),
                'brand': model.get('Brand', ''),
                'series': model.get('Series', ''),
                'model_year': model.get('Model_year', ''),
                'engine_no': model.get('Engine_no', ''),
                'cc': model.get('Cc', ''),
                'vehicle_name': parser.extract_vehicle_name(i),
                'production_year': parser.extract_production_year(i)
            }
            model_list.append(simplified_model)

        vehicle_info['model_list'] = model_list

        return vehicle_info

    except Exception as e:
        logger.error(f"查询VIN码失败: {str(e)}")
        return None


def enrich_vehicle_license_with_vin(vehicle_result, model_index: int = 0):
    """
    用VIN查询结果丰富行驶证信息

    Args:
        vehicle_result: VehicleLicenseResult实例
        model_index: 车型列表中的索引，默认取第一个

    Returns:
        bool: 是否成功
    """
    try:
        if not vehicle_result.vin:
            logger.warning("行驶证结果没有VIN码，无法查询")
            return False

        # 查询VIN信息
        vehicle_info = query_vin_for_vehicle_info(vehicle_result.vin, model_index)
        if not vehicle_info:
            logger.warning(f"VIN查询失败，VIN码: {vehicle_result.vin}")
            return False

        # 更新行驶证结果
        if 'vehicle_name' in vehicle_info:
            vehicle_result.vehicle_name = vehicle_info['vehicle_name']

        if 'production_year' in vehicle_info:
            vehicle_result.production_year = vehicle_info['production_year']

        # 保存额外的VIN信息到备注字段（如果需要）
        if vehicle_info.get('vehicle_options'):
            # 将多个车型选项保存为JSON字符串到备注字段
            import json
            options_str = json.dumps(vehicle_info['vehicle_options'], ensure_ascii=False)
            if not vehicle_result.remarks:
                vehicle_result.remarks = f"VIN查询可选车型: {options_str}"
            elif "VIN查询可选车型" not in vehicle_result.remarks:
                vehicle_result.remarks += f"\nVIN查询可选车型: {options_str}"

        vehicle_result.save()
        logger.info(f"成功丰富行驶证信息，VIN: {vehicle_result.vin}, "
                    f"车辆名称: {vehicle_info.get('vehicle_name', 'N/A')}, "
                    f"生产年份: {vehicle_info.get('production_year', 'N/A')}")

        return True

    except Exception as e:
        logger.error(f"丰富行驶证信息失败: {str(e)}")
        return False


def get_user_from_token(token):
    """
    从Token中获取用户对象

    Args:
        token: JWT Token字符串

    Returns:
        User对象或None
    """
    try:
        logger.info(f"尝试从Token获取用户，Token: {token[:20]}...")

        from rest_framework_simplejwt.tokens import AccessToken, TokenError
        from user.models import User

        if not token:
            logger.warning("Token为空")
            return None

        # 移除可能的Token类型前缀
        if token.startswith('Bearer '):
            token = token.replace('Bearer ', '', 1)
        elif token.startswith('Token '):
            token = token.replace('Token ', '', 1)

        try:
            # 验证JWT Token
            access_token = AccessToken(token)
            user_id = access_token.get('user_id')

            if user_id:
                user = User.objects.get(id=user_id, is_active=True)
                logger.info(f"成功从Token获取用户: {user.username} (ID: {user.id})")
                return user
            else:
                logger.warning("Token中没有user_id")
                return None

        except TokenError as e:
            logger.error(f"Token验证失败: {str(e)}")
            return None
        except User.DoesNotExist:
            logger.error(f"用户不存在: {user_id}")
            return None

    except Exception as e:
        logger.error(f"获取用户时发生错误: {str(e)}")
        return None


def get_user_from_token_or_auth_header(request):
    """
    从请求头或请求数据中获取用户

    Args:
        request: Django请求对象

    Returns:
        User对象或None
    """
    try:
        # 1. 从Authorization头获取
        auth_header = request.headers.get('Authorization', '')

        if auth_header:
            logger.info(f"从Authorization头获取认证: {auth_header[:50]}...")
            if auth_header.startswith('Bearer '):
                token = auth_header.replace('Bearer ', '', 1)
                user = get_user_from_token(token)
                if user:
                    return user
            elif auth_header.startswith('Token '):
                token = auth_header.replace('Token ', '', 1)
                user = get_user_from_token(token)
                if user:
                    return user

        # 2. 从POST数据获取
        token_param = request.data.get('token') or request.data.get('access_token')
        if token_param:
            logger.info(f"从POST数据获取Token: {token_param[:20]}...")
            user = get_user_from_token(token_param)
            if user:
                return user

        # 3. 从GET参数获取
        token_param = request.GET.get('token') or request.GET.get('access_token')
        if token_param:
            logger.info(f"从GET参数获取Token: {token_param[:20]}...")
            user = get_user_from_token(token_param)
            if user:
                return user

        logger.warning("未找到有效的Token")
        return None

    except Exception as e:
        logger.error(f"从请求获取用户失败: {str(e)}")
        return None


def extract_phone_number_from_text(all_text):
    """
    从OCR识别的文本中提取手机号

    Args:
        all_text: 从OCR结果中提取的所有文本列表

    Returns:
        str: 提取到的手机号，如果未找到返回None
    """

    if not all_text:
        return None

    # 将文本列表合并为一个字符串
    full_text = " ".join(all_text)

    logger.info(f"开始从文本中提取手机号，文本长度: {len(full_text)}")

    # 先排除身份证号（18位数字）
    id_card_pattern = r'\b[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b'

    # 查找身份证号
    id_card_matches = re.findall(id_card_pattern, full_text)
    if id_card_matches:
        logger.info(f"找到身份证号: {id_card_matches[0]}，将在文本中排除")
        # 移除身份证号，避免误识别
        full_text = re.sub(id_card_pattern, '', full_text)

    # 手机号正则表达式（精确11位手机号，排除身份证号的可能性）
    phone_patterns = [
        r'1[3-9]\d{9}',  # 标准11位手机号
    ]

    # 查找手机号（排除身份证号）
    for pattern in phone_patterns:
        matches = re.findall(pattern, full_text)
        if matches:
            # 验证是否为有效的手机号（排除身份证号的中间部分）
            for match in matches:
                # 确保不是身份证号的一部分（身份证号18位，手机号11位）
                # 身份证号通常不会以1开头，但为了安全，我们进行额外检查
                if len(match) == 11 and match.isdigit():
                    # 进一步验证：手机号第二位通常在3-9之间
                    if match[0] == '1' and match[1] in '3456789':
                        logger.info(f"从文本中提取到手机号: {match}")
                        return match

    # 如果没有找到标准格式，尝试查找"手机"、"电话"等关键词后面的数字
    phone_keywords = ['手机', '电话', '联系电话', '手机号', '手机号码', '移动电话']

    for keyword in phone_keywords:
        pattern = rf'{keyword}[:：]?\s*(\d{{11}})'
        matches = re.findall(pattern, full_text)
        if matches:
            phone_number = matches[0]
            logger.info(f"从关键词'{keyword}'后面提取到手机号: {phone_number}")
            return phone_number

    logger.info("未从文本中找到手机号")
    return None


def enhanced_classify_document_with_phone(all_text):
    """
    文档分类 - 基于文本内容识别证件类型，并提取手机号

    Args:
        all_text: 从OCR结果中提取的所有文本列表

    Returns:
        tuple: (证件类型, 手机号)
    """
    doc_type = enhanced_classify_document(all_text)
    phone_number = None

    # 只有在身份证类型时才提取手机号，并且确保不是从身份证号中提取的
    if doc_type == "id_card":
        phone_number = extract_phone_number_from_text(all_text)
        if phone_number:
            # 额外验证：确保提取的不是身份证号的一部分
            if len(phone_number) == 11:
                # 检查是否是有效的手机号格式（第一位1，第二位3-9）
                if phone_number[0] == '1' and phone_number[1] in '3456789':
                    logger.info(f"提取到有效的手机号: {phone_number}")
                else:
                    logger.warning(f"提取的号码格式不符合手机号规范: {phone_number}")
                    phone_number = None
            else:
                logger.warning(f"提取的号码长度不是11位: {phone_number}")
                phone_number = None

    return doc_type, phone_number
