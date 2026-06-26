import os
import json
import logging
from user.models import User

from rest_framework import status
from .tasks import batch_query_vin_for_vehicle_records_task

from . import models
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Avg
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .error_handlers import ErrorHandler
from .excel_utils import ExcelExporter

from .models import (
    HuaweiCloudConfig, OcrInterface, CertificateType,
    RecognitionRecord, VehicleLicenseResult, IdCardResult, BusinessLicenseResult, ScrapCarInfo
)
from .serializers import (
    HuaweiCloudConfigSerializer, OcrInterfaceSerializer,
    CertificateTypeSerializer, RecognitionRecordSerializer,
    ImageUploadSerializer, BatchImageUploadSerializer,
    VehicleLicenseResultSerializer, IdCardResultSerializer, BusinessLicenseResultSerializer,
    StatisticsSerializer, ScrapCarInfoSerializer, ExportFieldSelectionSerializer)
from .input_validators import InputValidator, SQLInjectionValidator
from .permissions import IsOwnerOrAdmin, StrictObjectPermission
from .utils import HuaweiOcrClient, extract_all_text, enhanced_classify_document_with_phone, \
    extract_phone_number_from_text
from .image_utils import ImageProcessor
from .cache_utils import CacheManager
from rest_framework.generics import ListAPIView, RetrieveAPIView

logger = logging.getLogger(__name__)


class BaseAPIView(APIView):
    """基础API视图类  """

    def handle_exception(self, exc):
        """统一异常处理"""
        error_data = ErrorHandler.safe_exception_message(exc)

        if hasattr(exc, 'status_code'):
            status_code = exc.status_code
        elif isinstance(exc, (PermissionDenied, AuthenticationFailed)):
            status_code = status.HTTP_403_FORBIDDEN
        elif isinstance(exc, (ValueError, TypeError)):
            status_code = status.HTTP_400_BAD_REQUEST
        elif isinstance(exc, (RecognitionRecord.DoesNotExist, ScrapCarInfo.DoesNotExist)):
            status_code = status.HTTP_404_NOT_FOUND
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        return Response(error_data, status=status_code)


class BaseViewSet(viewsets.ModelViewSet):
    """基础视图集 - 提供通用功能"""

    def perform_create(self, serializer):
        """创建时清除用户缓存"""
        instance = serializer.save()
        self._clear_user_cache()
        logger.info(f"用户 {self.request.user.username} 创建了 {self._get_model_name()}: {instance.id}")

    def perform_update(self, serializer):
        """更新时清除用户缓存"""
        instance = serializer.save()
        self._clear_user_cache()
        logger.info(f"用户 {self.request.user.username} 更新了 {self._get_model_name()}: {instance.id}")

    def perform_destroy(self, instance):
        """删除时清除用户缓存"""
        self._clear_user_cache()
        instance.delete()
        logger.info(f"用户 {self.request.user.username} 删除了 {self._get_model_name()}: {instance.id}")

    def _clear_user_cache(self):
        """清除用户缓存"""
        user_id = self.request.user.id
        CacheManager.clear_user_records_cache(user_id)

    def _get_model_name(self):
        """获取模型名称"""
        return self.queryset.model.__name__ if self.queryset else '记录'


class SecureViewMixin:
    """安全视图混入类"""

    @staticmethod
    def validate_request_params(request):
        """验证请求参数"""
        # 验证数字参数
        int_params = ['page', 'page_size', 'certificate_type_id', 'record_id']
        for param in int_params:
            value = request.GET.get(param) or request.POST.get(param)
            if value:
                try:
                    InputValidator.validate_integer(value, param)
                except Exception as e:
                    from rest_framework import serializers
                    raise serializers.ValidationError({param: str(e)})

        # 验证字符串参数
        str_params = ['match_status', 'vehicle_number', 'owner_name', 'vin', 'brand']
        for param in str_params:
            value = request.GET.get(param) or request.POST.get(param)
            if value:
                try:
                    cleaned_value = InputValidator.validate_string(value, param, max_length=100)
                    SQLInjectionValidator.validate_sql_safe(cleaned_value)
                except Exception as e:
                    from rest_framework import serializers
                    raise serializers.ValidationError({param: str(e)})


class ImageProcessingMixin:
    """图片处理混入类"""

    @staticmethod
    def _additional_security_checks(image):
        """额外的安全检查"""
        try:
            # 检查文件名安全性
            file_name = image.name
            if not ImageProcessingMixin._is_safe_filename(file_name):
                return False

            # 检查文件内容类型一致性
            if not ImageProcessingMixin._check_content_type_consistency(image):
                return False

            return True
        except Exception as e:
            logger.error(f"安全检查失败: {str(e)}")
            return False

    @staticmethod
    def _is_safe_filename(filename):
        """检查文件名是否安全"""
        # 移除路径遍历字符
        dangerous_patterns = ['..', '/', '\\', ':', ';', '|']
        for pattern in dangerous_patterns:
            if pattern in filename:
                logger.warning(f"检测到危险文件名模式: {pattern} in {filename}")
                return False

        # 限制文件名长度
        if len(filename) > 255:
            logger.warning(f"文件名过长: {len(filename)} characters")
            return False

        return True

    @staticmethod
    def _check_content_type_consistency(file):
        """检查文件内容类型与声明类型是否一致"""
        try:
            file.seek(0)
            header = file.read(100)
            file.seek(0)

            # 简单的文件类型检查
            if file.content_type.startswith('image/jpeg') and not header.startswith(b'\xff\xd8'):
                logger.warning("JPEG文件头与内容类型不匹配")
                return False
            elif file.content_type.startswith('image/png') and not header.startswith(b'\x89PNG'):
                logger.warning("PNG文件头与内容类型不匹配")
                return False

            return True
        except Exception as e:
            logger.error(f"文件类型检查失败: {str(e)}")
            return False


class OCRProcessingMixin:
    """OCR处理混入类"""

    @staticmethod
    def get_huawei_config():
        """获取华为云配置"""
        huawei_config = CacheManager.get_huawei_config()
        if not huawei_config:
            huawei_config = HuaweiCloudConfig.objects.filter(is_active=True).first()
            if huawei_config:
                CacheManager.set_huawei_config(huawei_config)
        return huawei_config

    @staticmethod
    def create_ocr_client(huawei_config):
        """创建OCR客户端"""
        if not huawei_config:
            raise ValueError("未找到有效的华为云配置")

        # 处理从缓存获取的字典配置
        if isinstance(huawei_config, dict):
            ak = huawei_config.get('ak')
            sk = huawei_config.get('sk')
            region = huawei_config.get('region', 'cn-north-4')
        else:
            # 处理模型对象
            ak = huawei_config.ak
            sk = huawei_config.sk
            region = huawei_config.region or 'cn-north-4'

        return HuaweiOcrClient(ak, sk, region)

    @staticmethod
    def recognize_by_certificate_type(ocr_client, image_path, certificate_type, phone_number=None):
        """根据证件类型调用对应的OCR接口 """
        interface_used = certificate_type.interface
        recognition_result = None

        try:
            if certificate_type.type_code == 'vehicle_license':
                recognition_result = ocr_client.recognize_vehicle_license(image_path)
            elif certificate_type.type_code == 'business_license':
                recognition_result = ocr_client.recognize_business_license(image_path)
            elif certificate_type.type_code == 'id_card':
                logger.info("使用智能分类接口进行身份证识别")
                recognition_result = ocr_client.recognize_auto_classification(image_path)
            else:
                recognition_result = ocr_client.recognize_general_text(image_path)

            logger.info(f"证件类型识别完成: {certificate_type.name}")
            # 返回三个值
            return recognition_result, interface_used, phone_number

        except Exception as e:
            logger.error(f"证件类型识别失败: {str(e)}")
            return None, interface_used, phone_number

    @staticmethod
    def auto_classify_document(ocr_client, image_path):
        """自动分类文档类型并识别"""
        # 先调用通用文字识别进行初步分类
        general_result = ocr_client.recognize_general_text(image_path)
        if not general_result:
            logger.error("通用文字识别失败")
            return None, None

        all_text = extract_all_text(general_result)
        doc_type = enhanced_classify_document(all_text)

        # 根据分类结果调用相应的接口
        interface_used = None
        recognition_result = None

        try:
            if doc_type == "vehicle_license":
                interface_used = OcrInterface.objects.filter(
                    interface_type='vehicle_license', is_active=True
                ).first()
                recognition_result = ocr_client.recognize_vehicle_license(image_path)
            elif doc_type == "business_license":
                interface_used = OcrInterface.objects.filter(
                    interface_type='business_license', is_active=True
                ).first()
                recognition_result = ocr_client.recognize_business_license(image_path)
            elif doc_type == "id_card":
                interface_used = OcrInterface.objects.filter(
                    interface_type='auto_classification', is_active=True
                ).first()
                logger.info("自动识别到身份证，使用智能分类接口")
                recognition_result = ocr_client.recognize_auto_classification(image_path)
            else:
                interface_used = OcrInterface.objects.filter(
                    interface_type='auto_classification', is_active=True
                ).first()
                recognition_result = ocr_client.recognize_auto_classification(image_path)

            logger.info(f"自动分类识别完成: {doc_type}")
            return recognition_result, interface_used

        except Exception as e:
            logger.error(f"自动分类识别失败: {str(e)}")
            return None, interface_used

    @staticmethod
    def auto_recognize_document(ocr_client, image_path, record):
        """自动识别文档类型并调用相应接口 """
        try:
            logger.info("开始自动识别流程")

            # 第一步：调用通用文字识别获取文本内容
            general_result = ocr_client.recognize_general_text(image_path)
            if not general_result:
                logger.error("通用文字识别失败")
                return None, None, None

            # 提取所有文本并进行分类
            all_text = extract_all_text(general_result)
            doc_type = enhanced_classify_document(all_text)

            phone_number = None
            # 如果是身份证类型，提取手机号
            if doc_type == "id_card":
                phone_number = extract_phone_number_from_text(all_text)
                if phone_number:
                    logger.info(f"从通用文字识别中提取到手机号: {phone_number}")

            logger.info(f"自动识别结果: {doc_type}")
            if phone_number:
                logger.info(f"提取到的手机号: {phone_number}")
            logger.info(f"识别到的文本: {all_text}")

            # 安全地记录识别的文本
            try:
                safe_text = str(all_text)[:200]  # 只记录前200个字符
                logger.info(f"识别到的文本: {safe_text}")
            except:
                logger.info("识别到文本，但无法安全记录")

            # 根据分类结果调用相应的专用接口
            recognition_result = None
            interface_used = None

            if doc_type == "vehicle_license":
                logger.info("自动识别为行驶证，调用行驶证专用接口")
                interface_used = OcrInterface.objects.filter(
                    interface_type='vehicle_license', is_active=True
                ).first()
                recognition_result = ocr_client.recognize_vehicle_license(image_path)

            elif doc_type == "business_license":
                logger.info("自动识别为营业执照，调用营业执照专用接口")
                interface_used = OcrInterface.objects.filter(
                    interface_type='business_license', is_active=True
                ).first()
                recognition_result = ocr_client.recognize_business_license(image_path)

            elif doc_type == "id_card":
                logger.info("自动识别为身份证，调用智能分类接口")
                interface_used = OcrInterface.objects.filter(
                    interface_type='auto_classification', is_active=True
                ).first()
                recognition_result = ocr_client.recognize_auto_classification(image_path)

            else:
                logger.info("无法识别具体类型，使用智能分类接口")
                interface_used = OcrInterface.objects.filter(
                    interface_type='auto_classification', is_active=True
                ).first()
                recognition_result = ocr_client.recognize_auto_classification(image_path)

            # 更新记录的证件类型为识别出的具体类型
            if doc_type != "unknown" and interface_used:
                # 关键修正：直接查找并更新证件类型
                try:
                    from .models import CertificateType
                    detected_certificate_type = CertificateType.objects.filter(
                        type_code=doc_type, is_active=True
                    ).first()
                    if detected_certificate_type:
                        record.certificate_type = detected_certificate_type
                        record.save()
                        logger.info(f"更新记录证件类型为: {detected_certificate_type.name}")
                except Exception as e:
                    logger.error(f"更新证件类型失败: {str(e)}")

            # 返回三个值
            return recognition_result, interface_used, phone_number

        except Exception as e:
            logger.error(f"自动识别过程失败: {str(e)}")
            return None, None, None

    @staticmethod
    def update_record_certificate_type(record, doc_type):
        """更新记录的证件类型"""
        try:
            # 查找对应的证件类型
            detected_certificate_type = CertificateType.objects.filter(
                type_code=doc_type, is_active=True
            ).first()
            if detected_certificate_type:
                record.certificate_type = detected_certificate_type
                record.save()
                logger.info(f"更新记录证件类型为: {detected_certificate_type.name}")
        except Exception as e:
            logger.error(f"更新证件类型失败: {str(e)}")


class ResultProcessingMixin:
    """结果处理混入类"""

    @staticmethod
    def process_vehicle_license_result(record, ocr_result):
        """处理行驶证识别结果 """
        try:
            result_dict = ocr_result.to_dict()
            result_data = result_dict.get('result', {})

            # 提取主页和副页信息
            front_data = result_data.get('front', {})
            back_data = result_data.get('back', {})

            # 创建或更新行驶证结果记录
            vehicle_result, created = VehicleLicenseResult.objects.get_or_create(record=record)

            # 记录处理前的信息
            logger.info(f"处理行驶证结果 - 记录ID: {record.id}, 创建: {created}")
            logger.info(f"人像面数据: {front_data}")
            logger.info(f"国徽面数据: {back_data}")

            # 提取关键字段
            vehicle_result.number = front_data.get('number')
            vehicle_result.vehicle_type = front_data.get('vehicle_type')
            vehicle_result.owner_name = front_data.get('name')
            vehicle_result.address = front_data.get('address')
            vehicle_result.engine_no = front_data.get('engine_no')
            vehicle_result.vin = front_data.get('vin')
            vehicle_result.model = front_data.get('model')

            # 增强的品牌型号分割逻辑
            model_value = front_data.get('model', '')
            if model_value:
                brand, vehicle_model = ResultProcessingMixin.split_brand_model(model_value)
                vehicle_result.brand = brand
                vehicle_result.vehicle_model = vehicle_model
                logger.info(f"品牌型号分割结果 - 原始: {model_value}, 品牌: {brand}, 型号: {vehicle_model}")

            vehicle_result.register_date = front_data.get('register_date')
            vehicle_result.issue_date = front_data.get('issue_date')
            vehicle_result.use_character = front_data.get('use_character')
            vehicle_result.file_no = back_data.get('file_no')
            vehicle_result.approved_passengers = back_data.get('approved_passengers')
            vehicle_result.gross_mass = back_data.get('gross_mass')
            vehicle_result.unladen_mass = back_data.get('unladen_mass')
            vehicle_result.dimension = back_data.get('dimension')
            vehicle_result.energy_type = back_data.get('energy_type')
            vehicle_result.remarks = back_data.get('remarks')
            vehicle_result.inspection_record = back_data.get('inspection_record')
            vehicle_result.code_number = back_data.get('code_number')

            # 立即保存
            vehicle_result.save()

            # 验证保存结果
            saved_result = VehicleLicenseResult.objects.filter(record=record).first()
            if saved_result:
                logger.info(f"行驶证结果保存成功 - ID: {saved_result.id}, VIN: {saved_result.vin}")
                logger.info(f"关联验证 - 记录ID: {record.id}, 结果记录ID: {saved_result.record.id}")
            else:
                logger.error(f"行驶证结果保存失败 - 记录ID: {record.id}")

            logger.info(f"行驶证结果处理完成: {record.id}")

        except Exception as e:
            logger.error(f"处理行驶证结果失败: {str(e)}", exc_info=True)

    @staticmethod
    def split_brand_model(model_value):
        """智能分割品牌型号"""
        if not model_value:
            return '', ''

        # 去除多余空格
        model_value = model_value.strip()

        # 方法1: 使用"牌"字分割（中文车辆常见格式）
        if '牌' in model_value:
            parts = model_value.split('牌', 1)  # 只分割第一次出现的"牌"
            if len(parts) == 2:
                brand = parts[0] + '牌'  # 把"牌"字加回品牌部分
                vehicle_model = parts[1].strip()
                return brand, vehicle_model

        # 方法2: 使用常见品牌列表匹配
        common_brands = [
            '奔驰', '宝马', '奥迪', '大众', '丰田', '本田', '日产', '现代', '起亚',
            '福特', '雪佛兰', '别克', '雷克萨斯', '沃尔沃', '路虎', '保时捷',
            '法拉利', '兰博基尼', '玛莎拉蒂', '红旗', '比亚迪', '吉利', '长城',
            '长安', '奇瑞', '传祺', '荣威', '名爵', '蔚来', '小鹏', '理想',
            '特斯拉', '威马', '哪吒'
        ]

        for brand in common_brands:
            if model_value.startswith(brand):
                # 检查品牌后面是否跟着"牌"字
                if model_value.startswith(brand + '牌'):
                    vehicle_model = model_value[len(brand + '牌'):].strip()
                    return brand + '牌', vehicle_model
                else:
                    vehicle_model = model_value[len(brand):].strip()
                    return brand, vehicle_model

        # 方法3: 基于字符类型分割（中文+英文/数字）
        # 找到中文和英文/数字的分界点
        import re
        # 匹配中文字符和后续的非中文字符
        match = re.match(r'^([\u4e00-\u9fff]+)(.*)$', model_value)
        if match:
            chinese_part = match.group(1)
            other_part = match.group(2).strip()

            # 如果中文部分在常见品牌列表中或是合理的品牌长度（2-4个汉字）
            if chinese_part in common_brands or (2 <= len(chinese_part) <= 4):
                return chinese_part, other_part

        # 方法4: 简单的空格分割作为最后手段
        parts = model_value.split(' ', 1)
        if len(parts) == 2:
            return parts[0], parts[1]

        # 如果所有方法都失败，将整个值作为品牌
        return model_value, ''

    @staticmethod
    def process_business_license_result(record, ocr_result):
        """处理营业执照识别结果"""
        try:
            result_dict = ocr_result.to_dict()
            result_data = result_dict.get('result', {})

            # 创建或更新营业执照结果记录
            business_result, created = BusinessLicenseResult.objects.get_or_create(record=record)
            business_result.registration_number = result_data.get('registration_number')
            business_result.name = result_data.get('name')
            business_result.type = result_data.get('type')
            business_result.address = result_data.get('address')
            business_result.legal_representative = result_data.get('legal_representative')
            business_result.registered_capital = result_data.get('registered_capital')
            business_result.found_date = result_data.get('found_date')
            business_result.business_term = result_data.get('business_term')
            business_result.business_scope = result_data.get('business_scope')
            business_result.save()

            logger.info(f"营业执照结果处理完成: {record.id}")

        except Exception as e:
            logger.error(f"处理营业执照结果失败: {str(e)}")

    @staticmethod
    def process_id_card_result(record, ocr_result, phone_number=None):
        """处理身份证识别结果 - 修改版，支持手机号"""
        try:
            result_dict = ocr_result.to_dict()
            result_data = result_dict.get('result', [])

            logger.info(f"智能分类识别原始结果类型: {type(result_data)}")
            logger.info(f"智能分类识别原始结果: {result_dict}")

            if phone_number:
                logger.info(f"处理身份证结果，传入的手机号: {phone_number}")

            # 调用调试函数
            from .debug_utils import debug_id_card_auto_classification
            debug_id_card_auto_classification(result_data, record.id)

            # 创建或更新身份证结果记录
            id_card_result, created = IdCardResult.objects.get_or_create(record=record)
            logger.info(f"身份证结果记录: created={created}, id={id_card_result.id}")

            # 检查是否是AutoClassification接口返回的数据结构
            if isinstance(result_data, list):
                # AutoClassification接口返回的是列表格式
                logger.info("开始处理智能分类识别结果列表")
                ResultProcessingMixin.process_auto_classification_id_card(id_card_result, result_data, phone_number)
            else:
                # 标准身份证识别接口数据结构
                logger.info("使用标准身份证识别接口数据结构")
                id_card_result.name = result_data.get('name')
                id_card_result.gender = result_data.get('sex')
                id_card_result.ethnicity = result_data.get('ethnicity')
                id_card_result.birth = result_data.get('birth')
                id_card_result.address = result_data.get('address')
                id_card_result.number = result_data.get('number')
                id_card_result.phone_number = phone_number  # 设置手机号
                id_card_result.issue_authority = result_data.get('issue_authority')
                id_card_result.valid_from = result_data.get('valid_from')
                id_card_result.valid_to = result_data.get('valid_to')
                id_card_result.side = result_data.get('side')
                id_card_result.save()

            logger.info(f"身份证结果处理完成: {record.id}")

        except Exception as e:
            logger.error(f"处理身份证结果失败: {str(e)}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    @staticmethod
    def process_auto_classification_id_card(id_card_result, result_list, phone_number=None):
        """处理智能分类识别的身份证结果 """
        try:
            logger.info(f"开始处理智能分类结果，共 {len(result_list)} 个项目")

            if phone_number:
                # 验证手机号格式
                if len(phone_number) == 11 and phone_number[0] == '1' and phone_number[1] in '3456789':
                    logger.info(f"传入的有效手机号: {phone_number}")
                else:
                    logger.warning(f"传入的手机号格式无效: {phone_number}")
                    phone_number = None

            # 初始化数据存储
            front_data = {}
            back_data = {}

            for item in result_list:
                item_type = item.get('type', '')
                content = item.get('content', {})
                item_status = item.get('status', {})  # 重命名避免与status模块冲突

                logger.info(f"处理项目类型: {item_type}, 内容: {content}")

                # 检查识别状态
                if item_status.get('error_code') != 'AIS.0000':
                    logger.warning(f"身份证识别状态异常: {item_status}")
                    continue

                if item_type == 'id_card_portrait_side':
                    # 人像面信息 - 完整字段映射
                    front_data = {
                        'name': content.get('name'),
                        'gender': content.get('sex'),  # 华为云返回'sex'，映射到'gender'
                        'ethnicity': content.get('ethnicity'),
                        'birth': content.get('birth'),
                        'address': content.get('address'),
                        'number': content.get('number')
                    }
                    logger.info(f"提取人像面信息: 姓名={front_data.get('name')}, 身份证号={front_data.get('number')}")

                elif item_type == 'id_card_emblem_side':
                    # 国徽面信息 - 完整字段映射
                    back_data = {
                        'issue_authority': content.get('issue'),  # 华为云返回'issue'，映射到'issue_authority'
                        'valid_from': content.get('valid_from'),
                        'valid_to': content.get('valid_to')
                    }
                    logger.info(f"提取国徽面信息: 签发机关={back_data.get('issue_authority')}")

            # 检查数据有效性
            has_front_data = bool(front_data and any(front_data.values()))
            has_back_data = bool(back_data and any(back_data.values()))

            logger.info(f"数据有效性检查 - 人像面: {has_front_data}, 国徽面: {has_back_data}")

            # 设置人像面数据
            if has_front_data:
                id_card_result.name = front_data.get('name') or ''
                id_card_result.gender = front_data.get('gender') or ''
                id_card_result.ethnicity = front_data.get('ethnicity') or ''
                id_card_result.birth = front_data.get('birth') or ''
                id_card_result.address = front_data.get('address') or ''
                id_card_result.number = front_data.get('number') or ''
                logger.info(f"已设置人像面数据: 姓名={id_card_result.name}, 身份证号={id_card_result.number}")
            else:
                logger.warning("未找到有效的人像面数据")

            # 设置国徽面数据
            if has_back_data:
                id_card_result.issue_authority = back_data.get('issue_authority') or ''
                id_card_result.valid_from = back_data.get('valid_from') or ''
                id_card_result.valid_to = back_data.get('valid_to') or ''
                logger.info(f"已设置国徽面数据: 签发机关={id_card_result.issue_authority}")
            else:
                logger.warning("未找到有效的国徽面数据")

            # 设置手机号（如果提供了有效的手机号）
            if phone_number:
                id_card_result.phone_number = phone_number
                logger.info(f"已设置手机号: {phone_number}")
            else:
                id_card_result.phone_number = ''  # 清空手机号字段

            # 设置side字段
            if has_front_data and has_back_data:
                id_card_result.side = 'double_side'
                logger.info("身份证双面识别完成")
            elif has_front_data:
                id_card_result.side = 'front'
                logger.info("身份证人像面识别完成")
            elif has_back_data:
                id_card_result.side = 'back'
                logger.info("身份证国徽面识别完成")
            else:
                logger.warning("未识别到有效的身份证信息")
                id_card_result.side = 'unknown'

            # 强制保存对象，确保数据写入数据库
            id_card_result.save(force_update=True)
            logger.info(f"身份证结果保存成功，ID: {id_card_result.id}")

            # 立即从数据库重新加载验证
            try:
                refreshed_result = IdCardResult.objects.get(id=id_card_result.id)
                logger.info(
                    f"数据库验证 - 姓名: {refreshed_result.name}, 身份证号: {refreshed_result.number}, "
                    f"手机号: {refreshed_result.phone_number}, 签发机关: {refreshed_result.issue_authority}"
                )
            except Exception as e:
                logger.error(f"数据库验证失败: {str(e)}")

        except Exception as e:
            logger.error(f"处理智能分类身份证结果失败: {str(e)}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            raise

    @staticmethod
    def handle_recognition_success(record, recognition_result, interface_used, user_id, phone_number=None):
        """
        处理识别成功的逻辑

        Args:
            record: 识别记录对象
            recognition_result: OCR识别结果
            interface_used: 使用的接口
            user_id: 用户ID
            phone_number: 手机号（可选）

        Returns:
            bool: 是否成功
        """
        try:
            record.recognition_status = True
            record.recognition_time = timezone.now()
            record.interface_used = interface_used
            record.save()

            # 根据接口类型处理结果
            if interface_used:
                if interface_used.interface_type == 'vehicle_license':
                    ResultProcessingMixin.process_vehicle_license_result(record, recognition_result)
                elif interface_used.interface_type == 'business_license':
                    ResultProcessingMixin.process_business_license_result(record, recognition_result)
                elif interface_used.interface_type in ['id_card', 'auto_classification']:
                    # 直接调用 process_id_card_result 方法
                    try:
                        # 确保我们有手机号参数
                        ResultProcessingMixin.process_id_card_result(record, recognition_result, phone_number)
                    except Exception as e:
                        logger.error(f"处理身份证结果失败: {str(e)}")
                        # 即使处理失败，也继续执行

            # 立即触发匹配 - 添加延迟确保数据已保存
            import time
            time.sleep(1)

            from .signals import MatchEngine
            match_result = MatchEngine.trigger_matching_for_record(record)

            if match_result:
                if isinstance(match_result, list):
                    logger.info(f"图像识别后触发匹配: 创建了 {len(match_result)} 个报废车信息")
                else:
                    logger.info(f"图像识别后触发匹配: 创建了报废车信息 {match_result.id}")
            else:
                logger.info(f"图像识别后无匹配: 记录 {record.id}")

            # 清除用户记录缓存
            from .cache_utils import CacheManager
            CacheManager.clear_user_records_cache(user_id)
            return True

        except Exception as e:
            logger.error(f"处理识别成功结果失败: {str(e)}")
            return False

    @staticmethod
    def handle_recognition_failure(record):
        """处理识别失败的逻辑"""
        record.recognition_status = False
        record.save()
        from rest_framework.response import Response
        from rest_framework import status
        return Response(
            {"error": "识别失败，请检查图片质量或稍后重试"},
            status=status.HTTP_400_BAD_REQUEST
        )


def enhanced_classify_document(all_text):
    """
    文档分类 - 基于文本内容识别证件类型

    Args:
        all_text: 从OCR结果中提取的所有文本列表

    Returns:
        str: 识别出的证件类型 ('id_card', 'vehicle_license', 'business_license', 'unknown')
    """
    if not all_text:
        return "unknown"

    try:
        # 将文本列表合并为单个字符串并去除空格
        full_text = "".join(all_text).replace(" ", "").lower()

        # 处理可能包含非ASCII字符的情况
        try:
            # 尝试使用UTF-8编码
            full_text = full_text.encode('utf-8', 'ignore').decode('utf-8')
        except:
            # 如果失败，只记录ASCII字符
            full_text = ''.join(c for c in full_text if ord(c) < 128)

        # 只记录前100个字符
        safe_text = full_text[:100] if len(full_text) > 100 else full_text
        logger.info(f"分类文本内容: {safe_text}...")

        # 身份证关键词
        id_card_keywords = [
            "公民身份号码", "居民身份证", "姓名", "性别", "民族",
            "出生", "住址", "签发机关", "有效期限", "身份证"
        ]

        # 行驶证关键词
        vehicle_license_keywords = [
            "中华人民共和国机动车行驶证", "机动车行驶证", "车辆识别代号",
            "发动机号码", "号牌号码", "车辆类型", "所有人", "使用性质",
            "注册日期", "发证日期", "行驶证"
        ]

        # 营业执照关键词
        business_license_keywords = [
            "营业执照", "企业名称", "法定代表人", "注册资本", "成立日期",
            "经营范围", "注册号", "统一社会信用代码", "住所", "营业期限"
        ]

        # 计算关键词匹配分数
        id_card_score = 0
        vehicle_score = 0
        business_score = 0

        # 安全地计算分数，避免编码问题
        for keyword in id_card_keywords:
            clean_keyword = keyword.replace(" ", "")
            if clean_keyword in full_text:
                id_card_score += 3

        for keyword in vehicle_license_keywords:
            clean_keyword = keyword.replace(" ", "")
            if clean_keyword in full_text:
                vehicle_score += 3

        for keyword in business_license_keywords:
            clean_keyword = keyword.replace(" ", "")
            if clean_keyword in full_text:
                business_score += 3

        # 添加简单关键词匹配
        if "身份证" in full_text:
            id_card_score += 2
        if "行驶证" in full_text:
            vehicle_score += 2
        if "营业执照" in full_text:
            business_score += 2

        logger.info(f"分类得分 - 身份证: {id_card_score}, 行驶证: {vehicle_score}, 营业执照: {business_score}")

        # 根据最高分决定类型
        scores = {
            "id_card": id_card_score,
            "vehicle_license": vehicle_score,
            "business_license": business_score
        }

        max_type = max(scores, key=scores.get)
        return max_type if scores[max_type] > 3 else "unknown"

    except Exception as e:
        logger.error(f"文档分类失败: {str(e)}")
        return "unknown"


class CSRFProtectedView(BaseAPIView):
    """提供CSRF令牌的基础视图"""

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        """获取CSRF令牌"""
        return Response({
            'message': 'CSRF token set in cookie',
            'csrf_token': get_token(request)
        })


def csrf_failure(request, reason=""):
    """自定义CSRF失败处理"""
    logger.warning(f"CSRF验证失败: {reason}, 用户: {request.user}, IP: {request.META.get('REMOTE_ADDR')}")

    if request.headers.get('Content-Type') == 'application/json':
        return JsonResponse({
            'error': 'CSRF验证失败',
            'code': 'csrf_failure'
        }, status=403)

    from django.http import HttpResponseForbidden
    return HttpResponseForbidden("""
    <html>
        <head><title>请求被拒绝</title></head>
        <body>
            <h1>请求被拒绝</h1>
            <p>安全验证失败，请刷新页面后重试。</p>
        </body>
    </html>
    """)


class HuaweiCloudConfigViewSet(BaseViewSet):
    """华为云配置视图集"""
    queryset = HuaweiCloudConfig.objects.all()
    serializer_class = HuaweiCloudConfigSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """根据用户权限返回查询集"""
        if self.request.user.is_staff:
            return HuaweiCloudConfig.objects.all()
        else:
            # 普通用户只能查看启用的配置
            return HuaweiCloudConfig.objects.filter(is_active=True)

    def perform_create(self, serializer):
        """创建配置后清除缓存"""
        instance = serializer.save()
        CacheManager.clear_all_cache()
        logger.info(f"华为云配置已创建: {instance.name}")

    def perform_update(self, serializer):
        """更新配置后清除缓存"""
        instance = serializer.save()
        CacheManager.clear_all_cache()
        logger.info(f"华为云配置已更新: {instance.name}")

    def perform_destroy(self, instance):
        """物理删除配置"""
        instance_name = instance.name
        instance.delete()
        CacheManager.clear_all_cache()
        logger.info(f"华为云配置已删除: {instance_name}")


class OcrInterfaceViewSet(BaseViewSet):
    """OCR接口视图集"""
    queryset = OcrInterface.objects.filter(is_active=True)
    serializer_class = OcrInterfaceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """尝试从缓存获取接口列表"""
        cached_interfaces = CacheManager.get_ocr_interfaces()
        if cached_interfaces is not None:
            logger.info("从缓存获取OCR接口列表")
            return cached_interfaces

        interfaces = super().get_queryset()
        CacheManager.set_ocr_interfaces(interfaces)
        return interfaces

    def perform_create(self, serializer):
        """创建接口后清除缓存"""
        instance = serializer.save()
        CacheManager.clear_all_cache()
        logger.info(f"OCR接口已创建: {instance.name}")

    def perform_update(self, serializer):
        """更新接口后清除缓存"""
        instance = serializer.save()
        CacheManager.clear_all_cache()
        logger.info(f"OCR接口已更新: {instance.name}")

    def perform_destroy(self, instance):
        """物理删除接口"""
        instance_name = instance.name
        instance.delete()
        CacheManager.clear_all_cache()
        logger.info(f"OCR接口已删除: {instance_name}")


class ImageUploadView(SecureViewMixin, ImageProcessingMixin, OCRProcessingMixin, ResultProcessingMixin,
                      generics.GenericAPIView):
    """图片上传视图"""
    serializer_class = ImageUploadSerializer
    permission_classes = []  # 移除默认权限检查，改为手动检查

    def post(self, request):
        """上传图片"""
        try:
            # 验证Token
            user = self._authenticate_user(request)
            if not user:
                return Response(
                    {"error": "认证失败，请重新登录"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # 验证请求参数
            self.validate_request_params(request)

            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                logger.warning(f"图片上传验证失败: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            image = serializer.validated_data['image']
            certificate_type_id = serializer.validated_data.get('certificate_type_id')

            # 额外的安全验证
            if not self._additional_security_checks(image):
                logger.warning(f"图片安全性验证失败: {image.name}")
                return Response(
                    {"error": "文件安全性验证失败"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 验证图片格式和大小
            if not ImageProcessor.validate_image_format(image):
                return Response(
                    {"error": "不支持的图片格式，请上传JPEG或PNG格式的图片"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not ImageProcessor.validate_image_size(image):
                return Response(
                    {"error": "图片文件过大，请上传小于5MB的图片"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 压缩图片
            compressed_image = ImageProcessor.compress_image(image)

            # 获取图片信息
            image_info = ImageProcessor.get_image_info(compressed_image)
            logger.info(f"图片信息: {image_info}")

            # 创建识别记录
            certificate_type = None
            if certificate_type_id:
                try:
                    certificate_type = CertificateType.objects.get(id=certificate_type_id, is_active=True)
                    logger.info(f"使用指定证件类型: {certificate_type.name}")
                except CertificateType.DoesNotExist:
                    logger.warning(f"未找到证件类型: {certificate_type_id}")
                    return Response(
                        {"error": "指定的证件类型不存在或已禁用"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # 保存图片并创建记录
            record = RecognitionRecord(
                user=user,  # 使用验证后的用户
                image=compressed_image,
                certificate_type=certificate_type,
                recognition_status=False
            )
            record.save()
            logger.info(f"创建识别记录: {record.id}")

            # 获取华为云配置
            huawei_config = self.get_huawei_config()

            if not huawei_config:
                logger.error("未找到有效的华为云配置")
                return Response(
                    {"error": "未找到有效的华为云配置"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # 创建OCR客户端
            ocr_client = self.create_ocr_client(huawei_config)

            # 根据证件类型选择识别接口
            recognition_result = None
            interface_used = None
            phone_number = None

            if certificate_type and certificate_type.type_code == 'auto':
                logger.info("开始自动识别流程")
                # 直接调用静态方法
                recognition_result, interface_used, phone_number = OCRProcessingMixin.auto_recognize_document(
                    ocr_client, record.image.path, record
                )
            elif certificate_type:
                # 使用指定的证件类型对应的接口
                # 如果是身份证类型，先进行通用文字识别提取手机号
                if certificate_type.type_code == 'id_card':
                    logger.info("开始身份证识别，先进行通用文字识别提取手机号")
                    general_result = ocr_client.recognize_general_text(record.image.path)
                    if general_result:
                        all_text = extract_all_text(general_result)
                        # 使用改进的提取手机号方法
                        phone_number = extract_phone_number_from_text(all_text)
                        if phone_number:
                            # 验证手机号格式
                            if len(phone_number) == 11 and phone_number[0] == '1' and phone_number[1] in '3456789':
                                logger.info(f"从通用文字识别中提取到有效手机号: {phone_number}")
                            else:
                                logger.warning(f"提取的手机号格式无效: {phone_number}")
                                phone_number = None

                # 调用指定证件类型的识别接口
                recognition_result, interface_used, phone_number = self.recognize_by_certificate_type(
                    ocr_client, record.image.path, certificate_type, phone_number
                )
            else:
                # 未指定类型时使用智能分类流程
                logger.info("开始智能分类流程")
                # 先进行通用文字识别提取手机号
                general_result = ocr_client.recognize_general_text(record.image.path)
                if general_result:
                    all_text = extract_all_text(general_result)
                    # 使用改进的提取手机号方法
                    phone_number = extract_phone_number_from_text(all_text)
                    if phone_number:
                        # 验证手机号格式
                        if len(phone_number) == 11 and phone_number[0] == '1' and phone_number[1] in '3456789':
                            logger.info(f"从通用文字识别中提取到有效手机号: {phone_number}")
                        else:
                            logger.warning(f"提取的手机号格式无效: {phone_number}")
                            phone_number = None

                recognition_result, interface_used = self.auto_classify_document(
                    ocr_client, record.image.path
                )

            # 处理识别结果
            if recognition_result:
                success = self.handle_recognition_success(record, recognition_result, interface_used, user.id,
                                                          phone_number)
                if success:
                    try:
                        # 重新从数据库获取记录以确保数据最新
                        record.refresh_from_db()
                        record_serializer = RecognitionRecordSerializer(
                            record, context={'request': request}
                        )
                        serialized_data = record_serializer.data
                        logger.info(f"图片识别成功: {record.id}")
                        return Response(serialized_data, status=status.HTTP_201_CREATED)
                    except Exception as e:
                        logger.error(f"序列化记录失败: {str(e)}")
                        # 即使序列化失败，也返回基本成功信息
                        return Response({
                            'id': record.id,
                            'recognition_status': record.recognition_status,
                            'message': '识别成功但序列化失败',
                            'error': str(e)
                        }, status=status.HTTP_201_CREATED)

            # 识别失败的处理
            return self.handle_recognition_failure(record)

        except Exception as e:
            logger.error(f"处理图片时发生错误: {str(e)}", exc_info=True)
            # 生产环境返回通用错误信息
            error_message = "处理图片时发生错误，请稍后重试"
            if settings.DEBUG:
                error_message = f"处理图片时发生错误: {str(e)}"
            return Response(
                {"error": error_message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @staticmethod
    def _authenticate_user(request):
        """验证用户Token"""
        # 使用新的工具函数
        from .utils import get_user_from_token_or_auth_header
        return get_user_from_token_or_auth_header(request)


class CertificateTypeViewSet(BaseViewSet):
    """证件类型视图集"""
    serializer_class = CertificateTypeSerializer
    permission_classes = []
    pagination_class = None

    def get_queryset(self):
        """获取证件类型，使用缓存，支持多种Token验证"""
        # 尝试从缓存获取
        cached_types = CacheManager.get_certificate_types()
        if cached_types is not None:
            logger.info("从缓存获取证件类型列表")
            # 如果是列表，直接返回；如果是查询集，评估它
            if isinstance(cached_types, list):
                return CertificateType.objects.filter(id__in=[ct['id'] for ct in cached_types if 'id' in ct])
            else:
                return cached_types

        # 缓存未命中，查询数据库
        queryset = CertificateType.objects.filter(is_active=True)

        # 将查询集转换为可序列化的格式进行缓存
        serializable_data = list(queryset.values(
            'id', 'name', 'type_code', 'keywords', 'is_active',
            'created_at', 'updated_at'
        ))

        # 设置缓存
        CacheManager.set_certificate_types(serializable_data)

        logger.info(f"从数据库查询证件类型: {queryset.count()} 个")
        return queryset

    def list(self, request, *args, **kwargs):
        """重写list方法，支持多种Token验证"""
        # 检查员工Token或普通Token
        user = None

        # 首先尝试验证用户
        user = self._authenticate_user(request)

        # 如果用户认证成功，设置request.user
        if user:
            request.user = user
        else:
            # 如果所有认证方式都失败，返回401
            logger.warning(f"证件类型列表访问失败: 所有认证方式都失败")
            return Response(
                {"error": "认证失败，请重新登录"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            # 直接获取序列化的数据，避免查询集问题
            cache_key = CacheManager.CACHE_KEYS['certificate_types']
            cached_data = cache.get(cache_key)

            if cached_data:
                logger.info("从缓存获取证件类型序列化数据")
                return Response(cached_data)

            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

            # 缓存序列化后的数据
            cache.set(cache_key, data, CacheManager.CACHE_TIMEOUTS['certificate_types'])

            logger.info(f"用户 {request.user.username} 获取证件类型成功")
            return Response(data)
        except Exception as e:
            logger.error(f"获取证件类型列表失败: {str(e)}")
            return Response(
                {"error": "获取证件类型失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @staticmethod
    def _authenticate_user(request):
        """统一的用户认证方法 - 与 RecognitionRecordViewSet 保持一致"""
        # 从请求头获取Authorization
        auth_header = request.headers.get('Authorization', '')

        logger.info(f"=== 证件类型认证开始 ===")
        logger.info(f"Authorization头: {auth_header[:50] if auth_header else '空'}")

        # 1. 检查是否为员工Bearer Token
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            logger.info(f"检测到Bearer Token: {token[:20]}...")

            try:
                from rest_framework_simplejwt.tokens import AccessToken
                access_token = AccessToken(token)
                user_id = access_token.get('user_id')

                if user_id:
                    user = User.objects.filter(id=user_id).first()
                    if user:
                        logger.info(f" 证件类型Bearer Token认证成功: {user.username} (ID: {user.id})")

                        # 关键：识别员工用户
                        if hasattr(user, 'employee_id') and user.employee_id:
                            logger.info(f"用户 {user.username} 被识别为员工 (employee_id: {user.employee_id})")
                            # 确保员工用户有正确权限
                            if not user.is_staff:
                                logger.info(f"用户 {user.username} is_staff=False，临时设置为True用于证件类型查询")
                                # 不修改数据库，只在当前请求中临时处理
                                user.is_staff = True

                        return user
                    else:
                        logger.warning(f"用户不存在: {user_id}")
            except Exception as e:
                logger.warning(f"Bearer Token解析失败: {str(e)}")
                import traceback
                logger.error(f"详细错误: {traceback.format_exc()}")

        # 2. 检查普通Token认证
        elif auth_header.startswith('Token '):
            token = auth_header.split(' ')[1]
            logger.info(f"尝试Token认证: {token[:20]}...")

            try:
                from rest_framework.authtoken.models import Token
                token_obj = Token.objects.get(key=token)
                if token_obj.user.is_active:
                    logger.info(f"Token认证成功: {token_obj.user.username}")
                    return token_obj.user
            except Token.DoesNotExist:
                logger.warning("Token认证失败: Token不存在")

        # 3. 检查GET参数中的Token
        token_param = request.GET.get('token') or request.GET.get('access_token')
        if token_param:
            logger.info(f"尝试参数Token认证: {token_param[:20]}...")

            # 先尝试JWT Token
            try:
                from rest_framework_simplejwt.tokens import AccessToken
                access_token = AccessToken(token_param)
                user_id = access_token.get('user_id')
                user = User.objects.filter(id=user_id).first()
                if user:
                    logger.info(f"参数JWT Token认证成功: {user.username}")

                    # 关键：识别员工用户
                    if hasattr(user, 'employee_id') and user.employee_id:
                        logger.info(f"参数认证用户 {user.username} 被识别为员工")
                        if not user.is_staff:
                            user.is_staff = True

                    return user
            except Exception as e:
                logger.warning(f"参数JWT Token解析失败: {str(e)}")

            # 再尝试DRF Token
            try:
                from rest_framework.authtoken.models import Token
                token_obj = Token.objects.get(key=token_param)
                if token_obj.user.is_active:
                    logger.info(f"参数Token认证成功: {token_obj.user.username}")
                    return token_obj.user
            except Token.DoesNotExist:
                logger.warning("参数Token认证失败: Token不存在")

        # 4. 检查POST数据中的Token
        if request.method == 'POST' and request.data:
            token_data = request.data.get('token') or request.data.get('access_token')
            if token_data:
                logger.info(f"尝试POST Token认证: {token_data[:20]}...")

                # 先尝试JWT Token
                try:
                    from rest_framework_simplejwt.tokens import AccessToken
                    access_token = AccessToken(token_data)
                    user_id = access_token.get('user_id')
                    user = User.objects.filter(id=user_id).first()
                    if user:
                        logger.info(f"POST JWT Token认证成功: {user.username}")

                        # 关键：识别员工用户
                        if hasattr(user, 'employee_id') and user.employee_id:
                            logger.info(f"POST认证用户 {user.username} 被识别为员工")
                            if not user.is_staff:
                                user.is_staff = True

                        return user
                except Exception as e:
                    logger.warning(f"POST JWT Token解析失败: {str(e)}")

                # 再尝试DRF Token
                try:
                    from rest_framework.authtoken.models import Token
                    token_obj = Token.objects.get(key=token_data)
                    if token_obj.user.is_active:
                        logger.info(f"POST Token认证成功: {token_obj.user.username}")
                        return token_obj.user
                except Token.DoesNotExist:
                    logger.warning("POST Token认证失败: Token不存在")

        # 5. 检查是否已有认证用户
        if hasattr(request, 'user') and request.user.is_authenticated:
            logger.info(f"使用已认证的用户: {request.user.username}")
            return request.user

        logger.warning("所有认证方式都失败")
        return None

    @staticmethod
    def _check_employee_token(request):
        """检查员工Token"""
        # 从请求头获取Authorization
        auth_header = request.headers.get('Authorization', '')

        # 检查是否包含Bearer token（员工Token格式）
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

            # 验证员工Token
            from rest_framework_simplejwt.tokens import AccessToken
            try:
                # 尝试解析JWT Token
                access_token = AccessToken(token)
                user_id = access_token.get('user_id')

                # 获取用户
                user = User.objects.filter(id=user_id).first()
                if user:
                    request.user = user
                    return True
            except Exception as e:
                logger.warning(f"员工Token验证失败: {str(e)}")

        # 检查Token参数（小程序传递方式）
        token_param = request.GET.get('token') or request.GET.get('access_token')
        if token_param:
            from rest_framework_simplejwt.tokens import AccessToken
            try:
                access_token = AccessToken(token_param)
                user_id = access_token.get('user_id')

                user = User.objects.filter(id=user_id).first()
                if user:
                    request.user = user
                    return True
            except Exception as e:
                logger.warning(f"Token参数验证失败: {str(e)}")

        return False

    def _handle_employee_request(self, request):
        """处理员工请求"""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)

            logger.info(f"员工 {request.user.username} 获取证件类型成功")
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"员工获取证件类型失败: {str(e)}")
            return Response(
                {"error": "获取证件类型失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        """创建证件类型后清除缓存"""
        instance = serializer.save()
        CacheManager.clear_all_cache()
        logger.info(f"证件类型已创建: {instance.name}")

    def perform_update(self, serializer):
        """更新证件类型后清除缓存"""
        instance = serializer.save()
        CacheManager.clear_all_cache()
        logger.info(f"证件类型已更新: {instance.name}")

    def perform_destroy(self, instance):
        """删除证件类型后清除缓存"""
        instance_name = instance.name
        instance.delete()
        CacheManager.clear_all_cache()
        logger.info(f"证件类型已删除: {instance_name}")


class RecognitionRecordViewSet(SecureViewMixin, ResultProcessingMixin, BaseViewSet):
    """识别记录视图集"""
    serializer_class = RecognitionRecordSerializer
    permission_classes = []  # 改为手动权限检查
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['certificate_type', 'recognition_status']
    queryset = RecognitionRecord.objects.all()

    @action(detail=False, methods=['get'])
    def my_records(self, request):
        """
        获取当前用户的记录
        """
        try:
            # 调试日志
            logger.info(f"=== 开始my_records方法 ===")

            # 验证用户 - 使用统一的认证方法
            user = self._authenticate_and_set_user(request)

            if not user or not user.is_authenticated:
                logger.error(f"认证失败: user={user}")
                return Response(
                    {"error": "认证失败，请重新登录"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            logger.info(f"认证成功: 用户={user.username}, ID={user.id}")

            # 设置 request.user 以便后续使用
            request.user = user

            # 所有用户都只能查看自己的记录
            # 不再区分员工和普通用户
            logger.info(f"用户 {user.username} 请求自己的历史记录")
            queryset = RecognitionRecord.objects.filter(user=user)
            logger.info(f"用户 {user.id} 的记录数量: {queryset.count()}")

            # 统计记录数量
            total_count = queryset.count()
            logger.info(f"用户 {user.username} 的总记录数: {total_count}")

            # 应用排序
            queryset = queryset.order_by('-created_at')

            # 获取分页参数
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 20)), 100)

            # 处理日期筛选
            start_date = request.GET.get('start_date', '').strip()
            end_date = request.GET.get('end_date', '').strip()

            if start_date:
                queryset = queryset.filter(created_at__date__gte=start_date)
            if end_date:
                queryset = queryset.filter(created_at__date__lte=end_date)

            # 处理证件类型筛选
            certificate_type = request.GET.get('certificate_type', '').strip()
            if certificate_type and certificate_type != '全部类型':
                queryset = queryset.filter(certificate_type__name__icontains=certificate_type)

            # 手动分页
            total_count = queryset.count()
            offset = (page - 1) * page_size
            records = queryset[offset:offset + page_size]

            # 序列化数据
            serializer = self.get_serializer(records, many=True, context={'request': request})

            # 返回分页响应
            response_data = {
                'results': serializer.data,
                'count': total_count,
                'next': None,
                'previous': None,
                'page': page,
                'page_size': page_size,
                'total_pages': max(1, (total_count + page_size - 1) // page_size)
            }

            # 如果有下一页
            if offset + page_size < total_count:
                next_page = page + 1
                # 构建下一页URL
                next_url = f"?page={next_page}&page_size={page_size}"
                if start_date:
                    next_url += f"&start_date={start_date}"
                if end_date:
                    next_url += f"&end_date={end_date}"
                if certificate_type:
                    next_url += f"&certificate_type={certificate_type}"
                response_data['next'] = next_url

            # 如果有上一页
            if page > 1:
                prev_page = page - 1
                prev_url = f"?page={prev_page}&page_size={page_size}"
                if start_date:
                    prev_url += f"&start_date={start_date}"
                if end_date:
                    prev_url += f"&end_date={end_date}"
                if certificate_type:
                    prev_url += f"&certificate_type={certificate_type}"
                response_data['previous'] = prev_url

            logger.info(f"成功返回 {len(records)} 条记录给用户 {user.username}")
            return Response(response_data)

        except Exception as e:
            logger.error(f"获取我的记录失败: {str(e)}", exc_info=True)
            return Response(
                {"error": "获取记录失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def retry_recognition(self, request, pk=None):
        """
        重新识别记录
        """
        try:
            # 验证用户
            user = self._authenticate_user(request)
            if not user:
                return Response(
                    {"error": "认证失败，请重新登录"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # 获取记录
            if user.is_staff:
                record = RecognitionRecord.objects.get(id=pk)
            else:
                record = RecognitionRecord.objects.get(id=pk, user=user)

            # 检查记录是否已识别
            if record.recognition_status:
                return Response(
                    {"error": "该记录已经识别成功，无需重新识别"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 获取华为云配置
            huawei_config = self.get_huawei_config()
            if not huawei_config:
                return Response(
                    {"error": "未找到有效的华为云配置"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # 创建OCR客户端
            from .utils import HuaweiOcrClient
            ocr_client = HuaweiOcrClient(huawei_config.ak, huawei_config.sk, huawei_config.region)

            # 根据证件类型选择识别接口
            recognition_result = None
            interface_used = None

            if record.certificate_type:
                # 使用指定的证件类型对应的接口
                recognition_result, interface_used = self.recognize_by_certificate_type(
                    ocr_client, record.image.path, record.certificate_type
                )
            else:
                # 未指定类型时使用智能分类流程
                recognition_result, interface_used = self.auto_classify_document(
                    ocr_client, record.image.path
                )

            # 处理识别结果
            if recognition_result:
                success = self.handle_recognition_success(record, recognition_result, interface_used, user.id, None)
                if success:
                    # 重新从数据库获取记录以确保数据最新
                    record.refresh_from_db()
                    record_serializer = RecognitionRecordSerializer(
                        record, context={'request': request}
                    )
                    return Response(record_serializer.data, status=status.HTTP_200_OK)

            # 识别失败的处理
            return Response(
                {"error": "重新识别失败，请稍后重试"},
                status=status.HTTP_400_BAD_REQUEST
            )

        except RecognitionRecord.DoesNotExist:
            return Response(
                {"error": "记录不存在"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"重新识别失败: {str(e)}")
            return Response(
                {"error": f"重新识别失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @staticmethod
    def get_huawei_config():
        """获取华为云配置"""
        # 尝试从缓存获取
        cached_config = CacheManager.get_huawei_config()
        if cached_config is not None:
            logger.info("从缓存获取华为云配置")
            return cached_config

        # 缓存未命中，从数据库获取
        huawei_config = HuaweiCloudConfig.objects.filter(is_active=True).first()
        if huawei_config:
            # 转换为可缓存的数据结构
            config_data = {
                'id': huawei_config.id,
                'name': huawei_config.name,
                'ak': huawei_config.ak,
                'sk': huawei_config.sk,
                'region': huawei_config.region,
                'is_active': huawei_config.is_active,
                'created_at': huawei_config.created_at.isoformat() if huawei_config.created_at else None,
                'updated_at': huawei_config.updated_at.isoformat() if huawei_config.updated_at else None,
            }
            # 设置缓存
            CacheManager.set_huawei_config(config_data)
            logger.info("从数据库获取华为云配置并缓存")
            return config_data

        logger.warning("未找到有效的华为云配置")
        return None

    @staticmethod
    def recognize_by_certificate_type(ocr_client, image_path, certificate_type):
        """根据证件类型调用对应的OCR接口"""
        from .models import OcrInterface
        interface_used = certificate_type.interface
        recognition_result = None

        try:
            if certificate_type.type_code == 'vehicle_license':
                recognition_result = ocr_client.recognize_vehicle_license(image_path)
            elif certificate_type.type_code == 'business_license':
                recognition_result = ocr_client.recognize_business_license(image_path)
            elif certificate_type.type_code == 'id_card':
                logger.info("使用智能分类接口进行身份证识别")
                recognition_result = ocr_client.recognize_auto_classification(image_path)
            else:
                recognition_result = ocr_client.recognize_general_text(image_path)

            logger.info(f"证件类型识别完成: {certificate_type.name}")
            return recognition_result, interface_used

        except Exception as e:
            logger.error(f"证件类型识别失败: {str(e)}")
            return None, interface_used

    @staticmethod
    def auto_classify_document(ocr_client, image_path):
        """自动分类文档类型并识别 """
        # 先调用通用文字识别进行初步分类
        general_result = ocr_client.recognize_general_text(image_path)
        if not general_result:
            logger.error("通用文字识别失败")
            return None, None, None  # 返回三个值

        all_text = extract_all_text(general_result)
        doc_type = enhanced_classify_document(all_text)

        phone_number = None
        # 如果是身份证类型，提取手机号
        if doc_type == "id_card":
            from .utils import extract_phone_number_from_text
            phone_number = extract_phone_number_from_text(all_text)
            if phone_number:
                logger.info(f"从通用文字识别中提取到手机号: {phone_number}")

        # 根据分类结果调用相应的接口
        interface_used = None
        recognition_result = None

        try:
            if doc_type == "vehicle_license":
                interface_used = OcrInterface.objects.filter(
                    interface_type='vehicle_license', is_active=True
                ).first()
                recognition_result = ocr_client.recognize_vehicle_license(image_path)

            elif doc_type == "business_license":
                interface_used = OcrInterface.objects.filter(
                    interface_type='business_license', is_active=True
                ).first()
                recognition_result = ocr_client.recognize_business_license(image_path)

            elif doc_type == "id_card":
                interface_used = OcrInterface.objects.filter(
                    interface_type='auto_classification', is_active=True
                ).first()
                logger.info("自动识别到身份证，使用智能分类接口")
                recognition_result = ocr_client.recognize_auto_classification(image_path)

            else:
                interface_used = OcrInterface.objects.filter(
                    interface_type='auto_classification', is_active=True
                ).first()
                recognition_result = ocr_client.recognize_auto_classification(image_path)

            logger.info(f"自动分类识别完成: {doc_type}")
            # 返回三个值
            return recognition_result, interface_used, phone_number

        except Exception as e:
            logger.error(f"自动分类识别失败: {str(e)}")
            return None, interface_used, phone_number

    @staticmethod
    def _authenticate_and_set_user(request):
        """统一的用户认证方法 """
        # 从请求头获取Authorization
        auth_header = request.headers.get('Authorization', '')

        logger.info(f"=== 开始认证（历史记录）===")
        logger.info(f"Authorization头: {auth_header[:50]}")

        # 1. 优先检查是否为员工Token
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            logger.info(f"检测到Bearer Token: {token[:20]}...")

            try:
                from rest_framework_simplejwt.tokens import AccessToken
                access_token = AccessToken(token)
                user_id = access_token.get('user_id')

                if user_id:
                    user = User.objects.filter(id=user_id).first()
                    if user:
                        logger.info(
                            f"Bearer Token认证成功: {user.username} (ID: {user.id}, is_staff={user.is_staff})")

                        # 关键修复：如果用户是员工，确保 is_staff 为 True
                        if hasattr(user, 'employee_id') or (hasattr(user, 'is_employee') and user.is_employee):
                            logger.info(f"用户 {user.username} 被识别为员工用户")
                            # 强制设置 is_staff 为 True，确保可以查看所有记录
                            user.is_staff = True

                        return user
            except Exception as e:
                logger.warning(f"Bearer Token解析失败: {str(e)}")

        # 2. 检查Token参数（小程序传递方式）
        token_param = request.GET.get('token') or request.GET.get('access_token')
        if token_param:
            logger.info(f"尝试参数Token认证: {token_param[:20]}...")

            # 先尝试JWT Token
            try:
                from rest_framework_simplejwt.tokens import AccessToken
                access_token = AccessToken(token_param)
                user_id = access_token.get('user_id')
                user = User.objects.filter(id=user_id).first()
                if user:
                    logger.info(f"参数JWT Token认证成功: {user.username}")

                    # 关键修复：如果用户是员工，确保 is_staff 为 True
                    if hasattr(user, 'employee_id') or (hasattr(user, 'is_employee') and user.is_employee):
                        logger.info(f"用户 {user.username} 被识别为员工用户")
                        user.is_staff = True

                    return user
            except Exception as e:
                logger.warning(f"参数JWT Token解析失败: {str(e)}")

        # 3. 尝试DRF Token认证
        try:
            from rest_framework.authtoken.models import Token
            if auth_header.startswith('Token '):
                token = auth_header.split(' ')[1]
                token_obj = Token.objects.get(key=token)
                if token_obj.user.is_active:
                    logger.info(f"Token认证成功: {token_obj.user.username}")
                    return token_obj.user
        except Token.DoesNotExist:
            logger.warning("Token认证失败: Token不存在")
        except Exception as e:
            logger.warning(f"Token认证异常: {str(e)}")

        logger.warning("所有认证方式都失败")
        return None

    @staticmethod
    def _authenticate_user(request):
        """验证用户Token"""
        # 从请求头获取Authorization
        auth_header = request.headers.get('Authorization', '')

        logger.info(f"识别记录访问: Authorization头: {auth_header[:20]}...")

        # 检查是否包含Bearer token（员工Token格式）
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

            from rest_framework_simplejwt.tokens import AccessToken
            try:
                # 尝试解析JWT Token
                access_token = AccessToken(token)
                user_id = access_token.get('user_id')

                # 获取用户
                user = User.objects.filter(id=user_id).first()
                if user:
                    logger.info(f"识别记录: Bearer Token认证成功: 用户 {user.username}")
                    return user
            except Exception as e:
                logger.warning(f"识别记录: Bearer Token解析失败: {str(e)}")

        # 检查是否包含Token（普通OCR Token格式）
        elif auth_header.startswith('Token '):
            token = auth_header.split(' ')[1]

            # 使用DRF的Token认证
            from rest_framework.authtoken.models import Token
            try:
                token_obj = Token.objects.get(key=token)
                if token_obj.user.is_active:
                    logger.info(f"识别记录: Token认证成功: 用户 {token_obj.user.username}")
                    return token_obj.user
            except Token.DoesNotExist:
                logger.warning("识别记录: Token认证失败: Token不存在")

        # 检查GET参数中是否有Token
        token_param = request.GET.get('token') or request.GET.get('access_token')
        if token_param:
            # 先尝试JWT Token
            from rest_framework_simplejwt.tokens import AccessToken
            try:
                access_token = AccessToken(token_param)
                user_id = access_token.get('user_id')
                user = User.objects.filter(id=user_id).first()
                if user:
                    logger.info(f"识别记录: 参数JWT Token认证成功: 用户 {user.username}")
                    return user
            except Exception as e:
                logger.warning(f"识别记录: 参数JWT Token解析失败: {str(e)}")

            # 再尝试DRF Token
            from rest_framework.authtoken.models import Token
            try:
                token_obj = Token.objects.get(key=token_param)
                if token_obj.user.is_active:
                    logger.info(f"识别记录: 参数Token认证成功: 用户 {token_obj.user.username}")
                    return token_obj.user
            except Token.DoesNotExist:
                logger.warning("识别记录: 参数Token认证失败: Token不存在")

        logger.warning("识别记录: 所有认证方式都失败")
        return None

    def get_queryset(self):
        """根据用户权限返回不同的查询集"""
        # 验证用户
        user = self._authenticate_and_set_user(self.request)
        if not user:
            logger.warning("用户认证失败，返回空查询集")
            return RecognitionRecord.objects.none()

        logger.info(
            f"获取查询集: 用户={user.username}, is_authenticated={user.is_authenticated}")

        # 所有用户都只能看到自己的记录
        logger.info(f"用户 {user.username} 只能看到自己的记录")
        queryset = RecognitionRecord.objects.filter(user=user)

        # 添加调试信息
        logger.info(f"查询集数量: {queryset.count()}")
        return queryset

    def list(self, request, *args, **kwargs):
        """列表查询"""
        try:
            # 验证用户
            user = self._authenticate_and_set_user(request)
            if not user:
                return Response(
                    {"error": "认证失败，请重新登录"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            request.user = user
            self.validate_request_params(request)
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"列表查询失败: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class BatchImageUploadView(generics.GenericAPIView):
    """批量图片上传视图"""
    serializer_class = BatchImageUploadSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """批量上传图片并进行识别"""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            images = serializer.validated_data['images']
            certificate_type_id = serializer.validated_data.get('certificate_type_id')

            # 限制批量上传数量
            if len(images) > 50:
                return Response(
                    {"error": "单次最多上传50张图片"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            results = []
            errors = []

            for index, image in enumerate(images):
                try:
                    # 验证图片大小
                    if not ImageProcessor.validate_image_size(image):
                        errors.append(f"第{index + 1}张图片文件过大")
                        continue

                    # 压缩图片
                    compressed_image = ImageProcessor.compress_image(image)

                    # 创建识别记录
                    certificate_type = None
                    if certificate_type_id:
                        try:
                            certificate_type = CertificateType.objects.get(id=certificate_type_id)
                        except CertificateType.DoesNotExist:
                            pass

                    record = RecognitionRecord(
                        user=request.user,
                        image=compressed_image,
                        certificate_type=certificate_type,
                        recognition_status=False
                    )
                    record.save()

                    results.append({
                        'index': index + 1,
                        'record_id': record.id,
                        'filename': image.name,
                        'status': 'uploaded'
                    })

                    logger.info(f"批量上传图片 {index + 1}/{len(images)}: {image.name}")

                except Exception as e:
                    errors.append(f"第{index + 1}张图片处理失败: {str(e)}")
                    logger.error(f"批量上传第{index + 1}张图片失败: {str(e)}")

            # 清除用户记录缓存
            CacheManager.clear_user_records_cache(request.user.id)

            response_data = {
                'success_count': len(results),
                'error_count': len(errors),
                'results': results,
                'errors': errors
            }

            logger.info(f"批量上传完成: 成功 {len(results)} 张, 失败 {len(errors)} 张")

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"批量上传失败: {str(e)}")
            return Response(
                {"error": f"批量上传失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StatisticsView(BaseAPIView):
    """统计信息视图"""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get(request):
        """获取统计信息"""
        user = request.user
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # 基础查询
        if user.is_staff:
            records = RecognitionRecord.objects.all()
        else:
            records = RecognitionRecord.objects.filter(user=user)

        # 统计信息
        total_records = records.count()
        success_records = records.filter(recognition_status=True).count()
        today_records = records.filter(created_at__date=today).count()
        week_records = records.filter(created_at__date__gte=week_ago).count()
        month_records = records.filter(created_at__date__gte=month_ago).count()

        # 按证件类型统计
        certificate_stats = records.values(
            'certificate_type__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')

        # 按日期统计（最近7天）
        date_stats = records.filter(
            created_at__date__gte=week_ago
        ).extra(
            {'date': "DATE(created_at)"}
        ).values('date').annotate(count=Count('id')).order_by('date')

        statistics_data = {
            'total_records': total_records,
            'success_records': success_records,
            'success_rate': round((success_records / total_records * 100) if total_records > 0 else 0, 2),
            'today_records': today_records,
            'week_records': week_records,
            'month_records': month_records,
            'certificate_stats': list(certificate_stats),
            'date_stats': list(date_stats),
        }

        serializer = StatisticsSerializer(statistics_data)
        return Response(serializer.data)


class RecognitionResultView(BaseAPIView):
    """识别结果详情视图"""
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    @staticmethod
    def get(request, record_id):
        """获取识别结果详情"""
        try:
            # 验证record_id
            valid_record_id = InputValidator.validate_integer(record_id, "记录ID")

            # 获取记录
            if request.user.is_staff:
                record = RecognitionRecord.objects.get(id=valid_record_id)
            else:
                record = RecognitionRecord.objects.get(id=valid_record_id, user=request.user)

            result_data = {}

            # 根据证件类型获取相应的结果
            if record.certificate_type:
                if record.certificate_type.type_code == 'vehicle_license' and hasattr(record, 'vehicle_result'):
                    serializer = VehicleLicenseResultSerializer(record.vehicle_result)
                    result_data = serializer.data
                    logger.info(f"获取行驶证结果: 记录ID {record.id}")
                elif record.certificate_type.type_code == 'id_card' and hasattr(record, 'id_card_result'):
                    serializer = IdCardResultSerializer(record.id_card_result)
                    result_data = serializer.data
                    logger.info(f"获取身份证结果: 记录ID {record.id}")
                elif record.certificate_type.type_code == 'business_license' and hasattr(record, 'business_result'):
                    serializer = BusinessLicenseResultSerializer(record.business_result)
                    result_data = serializer.data
                    logger.info(f"获取营业执照结果: 记录ID {record.id}")
                else:
                    logger.warning(f"未知的证件类型: {record.certificate_type.type_code}")

            # 构建响应数据
            response_data = {
                'record_id': record.id,
                'certificate_type': record.certificate_type.name if record.certificate_type else '未知',
                'recognition_status': record.recognition_status,
                'recognition_time': record.recognition_time,
                'image_url': request.build_absolute_uri(record.image.url) if record.image else None,
                'thumbnail_url': request.build_absolute_uri(record.thumbnail.url) if record.thumbnail else None,
                'result_data': result_data
            }

            logger.info(f"成功获取识别结果: 记录ID {record.id}")
            return Response(response_data)

        except Exception as e:
            logger.warning(f"记录ID验证失败: {record_id}, 错误: {str(e)}")
            return Response(
                {"error": "无效的记录ID格式"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except RecognitionRecord.DoesNotExist:
            logger.warning(f"记录不存在: {record_id}, 用户: {request.user.username}")
            return Response(
                {"error": "记录不存在"},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionError:
            logger.warning(f"权限不足: 用户 {request.user.username} 尝试访问记录 {record_id}")
            return Response(
                {"error": "权限不足，无法访问该记录"},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"获取识别结果失败: 记录ID {record_id}, 错误: {str(e)}")
            # 生产环境返回通用错误信息
            error_message = "获取识别结果失败，请稍后重试"
            if settings.DEBUG:
                error_message = f"获取识别结果失败: {str(e)}"
            return Response(
                {"error": error_message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ScrapCarInfoViewSet(BaseViewSet):
    """报废车信息识别视图集"""
    serializer_class = ScrapCarInfoSerializer
    permission_classes = [IsAuthenticated, StrictObjectPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        'match_status', 'vehicle_number', 'owner_name', 'vin',
        'vehicle_type', 'use_character', 'brand', 'energy_type'
    ]

    # 添加搜索字段
    search_fields = [
        'owner_name', 'identification_number', 'vehicle_number',
        'vin', 'brand', 'vehicle_model', 'engine_no'
    ]

    # 排序字段
    ordering_fields = ['created_at', 'updated_at', 'match_score', 'vehicle_number']
    ordering = ['-created_at']  # 默认按创建时间倒序排列

    def get_queryset(self):
        """根据用户权限返回查询集"""
        user = self.request.user

        # 先定义cache_key，确保在所有分支中都有定义
        cache_key = f"scrap_car_info_user_{user.id}"

        # 尝试从缓存获取
        if not user.is_staff:
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                logger.info(f"从缓存获取用户 {user.id} 的报废车信息")
                return cached_data

        if user.is_staff:
            queryset = ScrapCarInfo.objects.all()
        else:
            # 普通用户只能查看自己相关的记录
            queryset = ScrapCarInfo.objects.filter(
                Q(vehicle_record__user=user) |
                Q(id_card_record__user=user) |
                Q(business_record__user=user)
            ).distinct()

        # 优化查询性能
        queryset = queryset.select_related(
            'vehicle_record',
            'id_card_record',
            'business_record',
            'vehicle_record__user',
            'id_card_record__user',
            'business_record__user'
        ).prefetch_related(
            'vehicle_record__vehicle_result',
            'id_card_record__id_card_result',
            'business_record__business_result'
        ).order_by('-created_at')

        # 缓存普通用户的查询结果
        if not user.is_staff:
            cache.set(cache_key, queryset, 300)  # 缓存5分钟

        return queryset

    def perform_create(self, serializer):
        """创建记录时进行验证"""
        instance = serializer.save()

        # 验证数据完整性
        if not any([
            instance.owner_name, instance.identification_number, instance.vehicle_number,
            instance.vin, instance.brand, instance.vehicle_model
        ]):
            logger.warning(f"尝试创建空白报废车信息记录: {instance.id}")
            instance.delete()
            from rest_framework import serializers
            raise serializers.ValidationError("无法创建空白记录，请确保有关键字段数据")

        user_id = self.request.user.id
        CacheManager.clear_user_records_cache(user_id)

        # 清除报废车信息缓存
        cache_key = f"scrap_car_info_user_{user_id}"
        cache.delete(cache_key)

        logger.info(f"用户 {self.request.user.username} 创建了报废车信息: {instance.id}")

    @action(detail=False, methods=['get', 'post'])
    def export_excel(self, request):
        """导出报废车信息到Excel - 支持字段选择"""
        try:
            from .excel_utils import ExcelExporter

            # 获取基础查询集
            base_queryset = self.get_queryset()

            # 如果是POST请求，使用字段选择
            if request.method == 'POST':
                serializer = ExportFieldSelectionSerializer(data=request.data)
                if not serializer.is_valid():
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                fields = serializer.validated_data.get('fields')
                export_all = serializer.validated_data.get('export_all', False)
                filters = {
                    'match_status': serializer.validated_data.get('match_status', ''),
                    'vehicle_number': serializer.validated_data.get('vehicle_number', ''),
                    'owner_name': serializer.validated_data.get('owner_name', ''),
                    'vin': serializer.validated_data.get('vin', ''),
                    'brand': serializer.validated_data.get('brand', ''),
                    'use_character': serializer.validated_data.get('use_character', ''),
                    'energy_type': serializer.validated_data.get('energy_type', ''),
                }

                # 执行导出
                response = ExcelExporter.export_with_filters(
                    base_queryset,
                    filters=filters,
                    export_all=export_all,
                    fields=fields
                )
            else:
                # GET请求，使用默认字段和过滤条件
                filters = {
                    'match_status': request.GET.get('match_status', ''),
                    'vehicle_number': request.GET.get('vehicle_number', ''),
                    'owner_name': request.GET.get('owner_name', ''),
                    'vin': request.GET.get('vin', ''),
                    'brand': request.GET.get('brand', ''),
                    'use_character': request.GET.get('use_character', ''),
                    'energy_type': request.GET.get('energy_type', ''),
                }
                export_all = request.GET.get('export_all', 'false').lower() == 'true'

                # 执行导出
                response = ExcelExporter.export_with_filters(
                    base_queryset,
                    filters=filters,
                    export_all=export_all
                )

            return response

        except Exception as e:
            logger.error(f"导出Excel失败: {str(e)}")
            return Response(
                {"error": f"导出失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def export_all_records(self, request):
        """导出所有报废车信息记录"""
        try:
            from .excel_utils import ExcelExporter

            # 执行导出
            response = ExcelExporter.export_all_scrap_car_info()

            return response

        except Exception as e:
            logger.error(f"导出所有记录失败: {str(e)}")
            return Response(
                {"error": f"导出失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def export_template(self, request):
        """导出Excel模板"""
        try:
            from .excel_utils import ExcelExporter

            # 创建一个空的查询集用于生成模板
            empty_queryset = self.get_queryset().filter(id__isnull=True)  # 确保没有数据

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"报废车信息导入模板_{timestamp}.xlsx"

            response = ExcelExporter.export_scrap_car_info(empty_queryset, filename)

            logger.info("Excel模板导出成功")
            return response

        except Exception as e:
            logger.error(f"导出Excel模板失败: {str(e)}")
            return Response(
                {"error": f"模板导出失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """获取报废车信息统计"""
        user = request.user

        if user.is_staff:
            queryset = ScrapCarInfo.objects.all()
        else:
            queryset = self.get_queryset()

        total_count = queryset.count()
        matched_count = queryset.filter(match_status='matched').count()
        unmatched_count = queryset.filter(match_status='unmatched').count()
        manual_review_count = queryset.filter(match_status='manual_review').count()

        # 最近7天匹配趋势
        date_stats = []
        for i in range(7):
            date = datetime.now().date() - timedelta(days=i)
            count = queryset.filter(
                created_at__date=date,
                match_status='matched'
            ).count()
            date_stats.append({
                'date': date.isoformat(),
                'count': count
            })

        statistics_data = {
            'total_count': total_count,
            'matched_count': matched_count,
            'unmatched_count': unmatched_count,
            'manual_review_count': manual_review_count,
            'match_rate': round((matched_count / total_count * 100) if total_count > 0 else 0, 2),
            'date_stats': list(reversed(date_stats)),
        }

        return Response(statistics_data)

    @action(detail=False, methods=['post'])
    def batch_match(self, request):
        """手动触发批量匹配"""
        try:
            from .tasks import batch_process_unmatched_records
            result = batch_process_unmatched_records.apply()

            return Response({
                'success': True,
                'task_id': result.id,
                'message': '批量匹配任务已启动'
            })

        except Exception as e:
            logger.error(f"手动触发批量匹配失败: {str(e)}")
            return Response(
                {'error': f'批量匹配失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def manual_match(self, request, pk=None):
        """手动匹配记录"""
        try:
            scrap_info = self.get_object()
            from .signals import MatchEngine

            # 重新计算匹配
            updated_info = MatchEngine.create_or_update_scrap_car_info(scrap_info.vehicle_record)

            if updated_info:
                serializer = self.get_serializer(updated_info)
                return Response(serializer.data)
            else:
                return Response(
                    {'error': '手动匹配失败，无有效匹配记录'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            logger.error(f"手动匹配失败: {str(e)}")
            return Response(
                {'error': f'手动匹配失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def cleanup_blank_records(self, request):
        """清理空白记录 - 仅管理员可用"""
        try:
            # 只有管理员可以执行此操作
            if not request.user.is_staff:
                return Response(
                    {'error': '权限不足，只有管理员可以执行此操作'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # 查找空白记录（所有关键字段都为空）
            blank_records = ScrapCarInfo.objects.filter(
                owner_name='',
                identification_number='',
                vehicle_number='',
                vin='',
                brand='',
                vehicle_model=''
            )

            deleted_count = blank_records.count()

            # 删除空白记录
            blank_records.delete()

            logger.info(f"管理员 {request.user.username} 清理了 {deleted_count} 条空白记录")

            return Response({
                'success': True,
                'deleted_count': deleted_count,
                'message': f'成功清理 {deleted_count} 条空白记录'
            })

        except Exception as e:
            logger.error(f"清理空白记录失败: {str(e)}")
            return Response(
                {'error': f'清理空白记录失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def export_with_fields(self, request):
        """根据选择的字段导出报废车信息"""
        try:
            serializer = ExportFieldSelectionSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # 获取基础查询集
            base_queryset = self.get_queryset()

            # 获取参数
            fields = serializer.validated_data.get('fields')
            export_all = serializer.validated_data.get('export_all', False)
            filters = {
                'match_status': serializer.validated_data.get('match_status', ''),
                'vehicle_number': serializer.validated_data.get('vehicle_number', ''),
                'owner_name': serializer.validated_data.get('owner_name', ''),
                'vin': serializer.validated_data.get('vin', ''),
                'brand': serializer.validated_data.get('brand', ''),
                'use_character': serializer.validated_data.get('use_character', ''),
                'energy_type': serializer.validated_data.get('energy_type', ''),
            }

            # 执行导出
            response = ExcelExporter.export_with_filters(
                base_queryset,
                filters=filters,
                export_all=export_all,
                fields=fields
            )

            return response

        except Exception as e:
            logger.error(f"导出Excel失败: {str(e)}")
            return Response(
                {"error": f"导出失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def available_export_fields(self, request):
        """获取可用的导出字段列表"""
        try:
            available_fields = ExcelExporter.get_available_fields()
            default_fields = ExcelExporter.get_default_fields()

            return Response({
                'available_fields': available_fields,
                'default_fields': default_fields
            })
        except Exception as e:
            logger.error(f"获取导出字段失败: {str(e)}")
            return Response(
                {"error": f"获取导出字段失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TriggerMatchingView(BaseAPIView):
    """手动触发匹配视图"""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def post(request, record_id):
        """手动为指定记录触发匹配"""
        try:
            from .signals import MatchEngine

            # 获取记录
            if request.user.is_staff:
                record = RecognitionRecord.objects.get(id=record_id)
            else:
                record = RecognitionRecord.objects.get(id=record_id, user=request.user)

            # 触发匹配
            result = MatchEngine.trigger_matching_for_record(record)

            if result:
                if isinstance(result, list):
                    return Response({
                        'success': True,
                        'message': f'成功触发匹配，创建了 {len(result)} 个报废车信息',
                        'created_count': len(result)
                    })
                else:
                    return Response({
                        'success': True,
                        'message': f'成功触发匹配，创建了报废车信息 ID: {result.id}',
                        'scrap_car_info_id': result.id
                    })
            else:
                return Response({
                    'success': False,
                    'message': '无匹配记录'
                }, status=status.HTTP_400_BAD_REQUEST)

        except RecognitionRecord.DoesNotExist:
            return Response(
                {"error": "记录不存在"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"手动触发匹配失败: {str(e)}")
            return Response(
                {"error": f"触发匹配失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DebugMatchingView(BaseAPIView):
    """调试匹配状态视图"""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get(request, record_id):
        """调试指定记录的匹配状态"""
        try:
            # 获取记录
            if request.user.is_staff:
                record = RecognitionRecord.objects.get(id=record_id)
            else:
                record = RecognitionRecord.objects.get(id=record_id, user=request.user)

            # 调用调试函数
            from .debug_utils import debug_matching_status
            debug_matching_status(record_id)

            return Response({
                'success': True,
                'message': '调试信息已记录到日志'
            })

        except RecognitionRecord.DoesNotExist:
            return Response(
                {"error": "记录不存在"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"调试匹配状态失败: {str(e)}")
            return Response(
                {"error": f"调试失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DebugDuplicateView(BaseAPIView):
    """调试重复检测视图"""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def post(request, record_id):
        """调试指定记录的重复检测"""
        try:
            from .duplicate_utils import DuplicateManager

            # 只有管理员可以执行此操作
            if not request.user.is_staff:
                return Response(
                    {'error': '权限不足，只有管理员可以执行此操作'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # 获取记录
            record = ScrapCarInfo.objects.get(id=record_id)

            # 执行重复检测
            is_duplicate, handled_record, duplicate_action = DuplicateManager.check_and_handle_duplicates(record)

            return Response({
                'success': True,
                'original_record_id': record_id,
                'is_duplicate': is_duplicate,
                'handled_record_id': handled_record.id if handled_record else None,
                'action_taken': duplicate_action,
                'message': f'重复检测完成: 是否重复={is_duplicate}, 操作={duplicate_action}'
            })

        except ScrapCarInfo.DoesNotExist:
            return Response(
                {"error": "记录不存在"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"调试重复检测失败: {str(e)}")
            return Response(
                {"error": f"调试失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @staticmethod
    def get(request, record_id):
        """获取记录的重复检测信息"""
        try:
            from .duplicate_utils import DuplicateManager

            # 只有管理员可以执行此操作
            if not request.user.is_staff:
                return Response(
                    {'error': '权限不足，只有管理员可以执行此操作'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # 获取记录
            record = ScrapCarInfo.objects.get(id=record_id)

            # 查找重复记录但不处理
            duplicate_records = ScrapCarInfo.find_duplicate_records(record)

            # 构建响应数据
            duplicate_info = []
            for dup in duplicate_records:
                duplicate_info.append({
                    'id': dup.id,
                    'owner_name': dup.owner_name,
                    'vehicle_number': dup.vehicle_number,
                    'vin': dup.vin,
                    'brand': dup.brand,
                    'vehicle_model': dup.vehicle_model,
                    'created_at': dup.created_at,
                    'match_status': dup.match_status,
                    'match_score': dup.match_score
                })

            return Response({
                'success': True,
                'record_id': record_id,
                'record_info': {
                    'owner_name': record.owner_name,
                    'vehicle_number': record.vehicle_number,
                    'vin': record.vin,
                    'brand': record.brand,
                    'vehicle_model': record.vehicle_model,
                    'created_at': record.created_at,
                    'match_status': record.match_status,
                    'match_score': record.match_score
                },
                'duplicate_count': duplicate_records.count(),
                'duplicates': duplicate_info,
                'message': f'找到 {duplicate_records.count()} 条重复记录'
            })

        except ScrapCarInfo.DoesNotExist:
            return Response(
                {"error": "记录不存在"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"获取重复检测信息失败: {str(e)}")
            return Response(
                {"error": f"获取信息失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VehicleLicenseResultViewSet(viewsets.ReadOnlyModelViewSet):
    """行驶证结果视图集"""
    queryset = VehicleLicenseResult.objects.all()
    serializer_class = VehicleLicenseResultSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def query_vin(self, request, pk=None):
        """查询VIN信息"""
        try:
            vehicle_result = self.get_object()

            if not vehicle_result.vin:
                return Response(
                    {"error": "该行驶证记录没有VIN码"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            from .vin_tasks import query_vin_for_vehicle_result_task
            task = query_vin_for_vehicle_result_task.delay(vehicle_result.id)

            return Response({
                "message": "VIN查询任务已触发",
                "task_id": task.id,
                "vehicle_result_id": vehicle_result.id,
                "vin": vehicle_result.vin
            })

        except VehicleLicenseResult.DoesNotExist:
            return Response(
                {"error": "行驶证记录不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def batch_query_vin(self, request):
        """批量查询VIN信息"""
        try:
            from .tasks import batch_query_vin_for_vehicle_records_task
            task = batch_query_vin_for_vehicle_records_task.delay()

            return Response({
                "message": "批量VIN查询任务已触发",
                "task_id": task.id
            })

        except Exception as e:
            return Response(
                {"error": f"触发批量VIN查询失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VehicleLicenseResultAPIView(APIView):
    """
    行驶证识别结果API接口 - 供其他系统调用
    需要Token认证，返回简化格式的行驶证识别结果
    支持车牌号和VIN码精确查询，支持时间范围查询
    """
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get(request):
        """
        获取行驶证识别结果列表
        支持车牌号、VIN码查询，支持时间范围查询
        """
        try:
            # 构建查询条件
            queryset = VehicleLicenseResult.objects.all()

            # 1. 处理精确查询参数
            exact_vehicle_number = request.GET.get('exact_vehicle_number', '').strip()
            exact_vin = request.GET.get('exact_vin', '').strip()

            if exact_vehicle_number:
                queryset = queryset.filter(number__iexact=exact_vehicle_number)

            if exact_vin:
                queryset = queryset.filter(vin__iexact=exact_vin)

            # 2. 处理模糊查询参数
            vehicle_number = request.GET.get('vehicle_number', '').strip()
            if vehicle_number:
                queryset = queryset.filter(number__icontains=vehicle_number)

            owner_name = request.GET.get('owner_name', '').strip()
            if owner_name:
                queryset = queryset.filter(owner_name__icontains=owner_name)

            vin = request.GET.get('vin', '').strip()
            if vin:
                queryset = queryset.filter(vin__icontains=vin)

            brand = request.GET.get('brand', '').strip()
            if brand:
                queryset = queryset.filter(brand__icontains=brand)

            # 3. 处理时间范围查询参数
            created_at_start = request.GET.get('created_at_start', '').strip()
            created_at_end = request.GET.get('created_at_end', '').strip()
            updated_at_start = request.GET.get('updated_at_start', '').strip()
            updated_at_end = request.GET.get('updated_at_end', '').strip()
            last_updated_at = request.GET.get('last_updated_at', '').strip()

            # 创建时间范围查询
            if created_at_start:
                try:
                    created_start = datetime.fromisoformat(created_at_start.replace('Z', '+00:00'))
                    queryset = queryset.filter(created_at__gte=created_start)
                except (ValueError, TypeError):
                    # 如果日期格式错误，返回错误信息
                    return Response({
                        'success': False,
                        'message': '创建开始时间格式错误，请使用ISO格式（如：2024-01-01T00:00:00）',
                        'data': None
                    }, status=status.HTTP_400_BAD_REQUEST)

            if created_at_end:
                try:
                    created_end = datetime.fromisoformat(created_at_end.replace('Z', '+00:00'))
                    queryset = queryset.filter(created_at__lte=created_end)
                except (ValueError, TypeError):
                    return Response({
                        'success': False,
                        'message': '创建结束时间格式错误，请使用ISO格式（如：2024-01-01T23:59:59）',
                        'data': None
                    }, status=status.HTTP_400_BAD_REQUEST)

            # 更新时间范围查询
            if updated_at_start:
                try:
                    updated_start = datetime.fromisoformat(updated_at_start.replace('Z', '+00:00'))
                    queryset = queryset.filter(updated_at__gte=updated_start)
                except (ValueError, TypeError):
                    return Response({
                        'success': False,
                        'message': '更新开始时间格式错误，请使用ISO格式',
                        'data': None
                    }, status=status.HTTP_400_BAD_REQUEST)

            if updated_at_end:
                try:
                    updated_end = datetime.fromisoformat(updated_at_end.replace('Z', '+00:00'))
                    queryset = queryset.filter(updated_at__lte=updated_end)
                except (ValueError, TypeError):
                    return Response({
                        'success': False,
                        'message': '更新结束时间格式错误，请使用ISO格式',
                        'data': None
                    }, status=status.HTTP_400_BAD_REQUEST)

            # 增量更新查询（获取上次更新时间之后的数据）
            if last_updated_at:
                try:
                    last_updated = datetime.fromisoformat(last_updated_at.replace('Z', '+00:00'))
                    queryset = queryset.filter(updated_at__gt=last_updated)
                except (ValueError, TypeError):
                    return Response({
                        'success': False,
                        'message': '最后更新时间格式错误，请使用ISO格式',
                        'data': None
                    }, status=status.HTTP_400_BAD_REQUEST)

            # 按更新时间倒序排序，确保最新数据在前
            queryset = queryset.order_by('-updated_at')

            # 4. 分页处理
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 20)), 100)

            # 是否获取全部数据（不分页）
            get_all = request.GET.get('get_all', '').lower() == 'true'

            if get_all:
                # 获取全部数据，不分页
                total_count = queryset.count()
                vehicle_results = queryset
                pagination_info = {
                    'page': 1,
                    'page_size': total_count,
                    'total_count': total_count,
                    'total_pages': 1,
                    'has_next': False,
                    'has_previous': False
                }
            else:
                # 分页查询
                total_count = queryset.count()
                total_pages = max(1, (total_count + page_size - 1) // page_size)

                offset = (page - 1) * page_size
                vehicle_results = queryset[offset:offset + page_size]

                pagination_info = {
                    'page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_previous': page > 1,
                }

            # 5. 构建响应数据
            results = []
            for vehicle_result in vehicle_results:
                record = vehicle_result.record

                result_data = {
                    'id': vehicle_result.id,
                    'record_id': record.id,
                    'vehicle_number': vehicle_result.number or '',
                    'owner_name': vehicle_result.owner_name or '',
                    'address': vehicle_result.address or '',
                    'vin': vehicle_result.vin or '',
                    'engine_no': vehicle_result.engine_no or '',
                    'brand': vehicle_result.brand or '',
                    'vehicle_model': vehicle_result.vehicle_model or '',
                    'vehicle_name': vehicle_result.vehicle_name or '',
                    'production_year': vehicle_result.production_year or '',
                    'vehicle_type': vehicle_result.vehicle_type or '',
                    'use_character': vehicle_result.use_character or '',
                    'register_date': vehicle_result.register_date or '',
                    'issue_date': vehicle_result.issue_date or '',
                    'approved_passengers': vehicle_result.approved_passengers or '',
                    'energy_type': vehicle_result.energy_type or '',
                    'unladen_mass': vehicle_result.unladen_mass or '',
                    'gross_mass': vehicle_result.gross_mass or '',
                    'dimension': vehicle_result.dimension or '',
                    'recognition_time': record.recognition_time.strftime(
                        '%Y-%m-%d %H:%M:%S') if record.recognition_time else None,
                    'created_at': vehicle_result.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_at': vehicle_result.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                }

                results.append(result_data)

            # 6. 构建响应
            response_data = {
                'success': True,
                'message': '获取成功',
                'data': {
                    'results': results,
                    'pagination': pagination_info,
                    'query_params': {
                        'exact_vehicle_number': exact_vehicle_number,
                        'exact_vin': exact_vin,
                        'vehicle_number': vehicle_number,
                        'owner_name': owner_name,
                        'vin': vin,
                        'brand': brand,
                        'created_at_start': created_at_start,
                        'created_at_end': created_at_end,
                        'updated_at_start': updated_at_start,
                        'updated_at_end': updated_at_end,
                        'last_updated_at': last_updated_at,
                        'get_all': get_all
                    }
                }
            }

            return Response(response_data)

        except Exception as e:
            logger.error(f"API调用失败: {str(e)}")
            return Response({
                'success': False,
                'message': f'获取失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VehicleLicenseDetailAPIView(BaseAPIView):
    """
    行驶证识别结果详情API接口
    需要Token认证，返回单个行驶证识别结果的详细信息
    """
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get(request, result_id):
        """
        获取单个行驶证识别结果详情
        """
        try:
            # 验证ID
            valid_result_id = InputValidator.validate_integer(result_id, "结果ID")

            # 获取行驶证结果
            vehicle_result = VehicleLicenseResult.objects.get(id=valid_result_id)
            record = vehicle_result.record

            # 构建响应数据
            result_data = {
                'id': vehicle_result.id,
                'record_id': record.id,
                'vehicle_number': vehicle_result.number or '',
                'owner_name': vehicle_result.owner_name or '',
                'address': vehicle_result.address or '',
                'vin': vehicle_result.vin or '',
                'engine_no': vehicle_result.engine_no or '',
                'brand': vehicle_result.brand or '',
                'vehicle_model': vehicle_result.vehicle_model or '',
                'vehicle_name': vehicle_result.vehicle_name or '',  # 修复这里，改为vehicle_name
                'production_year': vehicle_result.production_year or '',  # 添加生产年份字段
                'vehicle_type': vehicle_result.vehicle_type or '',
                'use_character': vehicle_result.use_character or '',
                'register_date': vehicle_result.register_date or '',
                'issue_date': vehicle_result.issue_date or '',
                'approved_passengers': vehicle_result.approved_passengers or '',
                'gross_mass': vehicle_result.gross_mass or '',
                'unladen_mass': vehicle_result.unladen_mass or '',
                'energy_type': vehicle_result.energy_type or '',
                'file_no': vehicle_result.file_no or '',
                'dimension': vehicle_result.dimension or '',
                'remarks': vehicle_result.remarks or '',
                'inspection_record': vehicle_result.inspection_record or '',
                'code_number': vehicle_result.code_number or '',
                'recognition_time': record.recognition_time.isoformat() if record.recognition_time else None,
                'created_at': vehicle_result.created_at.isoformat(),
                'updated_at': vehicle_result.updated_at.isoformat(),
                'user_info': {
                    'user_id': record.user.id,
                    'username': record.user.username,
                }
            }

            # 如果有图片URL，添加到结果中
            if record.image:
                result_data['image_url'] = request.build_absolute_uri(record.image.url)
                if record.thumbnail:
                    result_data['thumbnail_url'] = request.build_absolute_uri(record.thumbnail.url)

            # 获取VIN查询信息（如果存在）
            from .utils import query_vin_for_vehicle_info
            if vehicle_result.vin:
                vin_info = query_vin_for_vehicle_info(vehicle_result.vin)
                if vin_info:
                    result_data['vin_info'] = {
                        'brand': vin_info.get('brand'),
                        'vehicle_name': vin_info.get('vehicle_name'),  # 修复这里，改为vehicle_name
                        'production_year': vin_info.get('production_year'),
                        'model_year': vin_info.get('model_year'),
                        'build_date': vin_info.get('build_date'),
                        'success': vin_info.get('success', False),
                    }

            response_data = {
                'success': True,
                'message': '获取成功',
                'data': result_data
            }

            logger.info(f"行驶证详情API调用成功，结果ID: {result_id}")
            return Response(response_data)

        except VehicleLicenseResult.DoesNotExist:
            logger.warning(f"行驶证结果不存在: {result_id}")
            return Response({
                'success': False,
                'message': '行驶证结果不存在',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"行驶证详情API调用失败: {str(e)}")
            return Response({
                'success': False,
                'message': f'获取失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VehicleSearchAPIView(APIView):
    """
    车辆搜索API接口 - 支持车牌号和VIN码精确搜索
    需要Token认证，返回车辆的完整信息
    """
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get(request):
        """
        根据车牌号或VIN码搜索车辆信息
        支持多种查询方式
        """
        try:
            # 获取查询参数
            vehicle_number = request.GET.get('vehicle_number', '').strip()
            vin = request.GET.get('vin', '').strip()
            include_vin_info = request.GET.get('include_vin_info', 'true').lower() == 'true'

            # 验证至少有一个查询参数
            if not vehicle_number and not vin:
                return Response({
                    'success': False,
                    'message': '请至少提供一个查询参数（vehicle_number或vin）',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)

            # 构建查询条件
            queryset = VehicleLicenseResult.objects.all()

            if vehicle_number:
                queryset = queryset.filter(number__iexact=vehicle_number)

            if vin:
                queryset = queryset.filter(vin__iexact=vin)

            # 处理时间范围查询参数（与列表接口相同逻辑）
            created_at_start = request.GET.get('created_at_start', '').strip()
            created_at_end = request.GET.get('created_at_end', '').strip()
            updated_at_start = request.GET.get('updated_at_start', '').strip()
            updated_at_end = request.GET.get('updated_at_end', '').strip()
            last_updated_at = request.GET.get('last_updated_at', '').strip()

            # 创建时间范围查询
            if created_at_start:
                try:
                    created_start = datetime.fromisoformat(created_at_start.replace('Z', '+00:00'))
                    queryset = queryset.filter(created_at__gte=created_start)
                except (ValueError, TypeError):
                    return Response({
                        'success': False,
                        'message': '创建开始时间格式错误，请使用ISO格式',
                        'data': None
                    }, status=status.HTTP_400_BAD_REQUEST)

            if created_at_end:
                try:
                    created_end = datetime.fromisoformat(created_at_end.replace('Z', '+00:00'))
                    queryset = queryset.filter(created_at__lte=created_end)
                except (ValueError, TypeError):
                    return Response({
                        'success': False,
                        'message': '创建结束时间格式错误，请使用ISO格式',
                        'data': None
                    }, status=status.HTTP_400_BAD_REQUEST)

            # 更新时间范围查询
            if updated_at_start:
                try:
                    updated_start = datetime.fromisoformat(updated_at_start.replace('Z', '+00:00'))
                    queryset = queryset.filter(updated_at__gte=updated_start)
                except (ValueError, TypeError):
                    return Response({
                        'success': False,
                        'message': '更新开始时间格式错误，请使用ISO格式',
                        'data': None
                    }, status=status.HTTP_400_BAD_REQUEST)

            if updated_at_end:
                try:
                    updated_end = datetime.fromisoformat(updated_at_end.replace('Z', '+00:00'))
                    queryset = queryset.filter(updated_at__lte=updated_end)
                except (ValueError, TypeError):
                    return Response({
                        'success': False,
                        'message': '更新结束时间格式错误，请使用ISO格式',
                        'data': None
                    }, status=status.HTTP_400_BAD_REQUEST)

            # 增量更新查询
            if last_updated_at:
                try:
                    last_updated = datetime.fromisoformat(last_updated_at.replace('Z', '+00:00'))
                    queryset = queryset.filter(updated_at__gt=last_updated)
                except (ValueError, TypeError):
                    return Response({
                        'success': False,
                        'message': '最后更新时间格式错误，请使用ISO格式',
                        'data': None
                    }, status=status.HTTP_400_BAD_REQUEST)

            # 获取查询结果
            vehicle_results = queryset.order_by('-created_at')

            if not vehicle_results.exists():
                return Response({
                    'success': False,
                    'message': '未找到匹配的车辆信息',
                    'data': None
                }, status=status.HTTP_404_NOT_FOUND)

            # 构建响应数据
            results = []
            for vehicle_result in vehicle_results:
                record = vehicle_result.record

                # 构建基本车辆信息
                vehicle_data = {
                    'id': vehicle_result.id,
                    'record_id': record.id,
                    'vehicle_number': vehicle_result.number or '',
                    'owner_name': vehicle_result.owner_name or '',
                    'address': vehicle_result.address or '',
                    'vin': vehicle_result.vin or '',
                    'engine_no': vehicle_result.engine_no or '',
                    'brand': vehicle_result.brand or '',
                    'vehicle_model': vehicle_result.vehicle_model or '',
                    'vehicle_name': vehicle_result.vehicle_name or '',
                    'production_year': vehicle_result.production_year or '',
                    'vehicle_type': vehicle_result.vehicle_type or '',
                    'use_character': vehicle_result.use_character or '',
                    'register_date': vehicle_result.register_date or '',
                    'issue_date': vehicle_result.issue_date or '',
                    'approved_passengers': vehicle_result.approved_passengers or '',
                    'gross_mass': vehicle_result.gross_mass or '',
                    'unladen_mass': vehicle_result.unladen_mass or '',
                    'energy_type': vehicle_result.energy_type or '',
                    'file_no': vehicle_result.file_no or '',
                    'dimension': vehicle_result.dimension or '',
                    'remarks': vehicle_result.remarks or '',
                    'inspection_record': vehicle_result.inspection_record or '',
                    'code_number': vehicle_result.code_number or '',
                    'recognition_time': record.recognition_time.strftime(
                        '%Y-%m-%d %H:%M:%S') if record.recognition_time else None,
                    'created_at': vehicle_result.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_at': vehicle_result.updated_at.strftime(
                        '%Y-%m-%d %H:%M:%S') if vehicle_result.updated_at else None,
                    'user_info': {
                        'user_id': record.user.id,
                        'username': record.user.username,
                    }
                }

                # 添加图片URL
                if record.image:
                    vehicle_data['image_url'] = request.build_absolute_uri(record.image.url)
                    if record.thumbnail:
                        vehicle_data['thumbnail_url'] = request.build_absolute_uri(record.thumbnail.url)

                # 如果需要VIN信息，查询并添加
                if include_vin_info and vehicle_result.vin:
                    from .utils import query_vin_for_vehicle_info
                    vin_info = query_vin_for_vehicle_info(vehicle_result.vin)
                    if vin_info:
                        vehicle_data['vin_info'] = {
                            'brand': vin_info.get('brand'),
                            'vehicle_name': vin_info.get('vehicle_name'),
                            'production_year': vin_info.get('production_year'),
                            'model_year': vin_info.get('model_year'),
                            'build_date': vin_info.get('build_date'),
                            'model_list': vin_info.get('model_list', []),
                            'vehicle_options': vin_info.get('vehicle_options', []),
                            'success': vin_info.get('success', False),
                            'message': vin_info.get('message', ''),
                        }

                results.append(vehicle_data)

            response_data = {
                'success': True,
                'message': f'找到 {len(results)} 条匹配记录',
                'data': {
                    'results': results,
                    'total_count': len(results),
                    'query_params': {
                        'vehicle_number': vehicle_number,
                        'vin': vin,
                        'include_vin_info': include_vin_info
                    }
                }
            }

            return Response(response_data)

        except Exception as e:
            logger.error(f"车辆搜索API调用失败: {str(e)}")
            return Response({
                'success': False,
                'message': f'搜索失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
