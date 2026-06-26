import csv
import os
import re
import logging

from django.contrib import admin
from django.http import HttpResponse
from django.utils.encoding import smart_str
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin import helpers
from rest_framework.response import Response
from rest_framework import status

from .models import (
    HuaweiCloudConfig, OcrInterface, CertificateType,
    RecognitionRecord, VehicleLicenseResult, IdCardResult, BusinessLicenseResult, ScrapCarInfo
)
from .utils import HuaweiOcrClient
from .image_utils import ImageProcessor
from datetime import datetime
from django.utils import timezone
from user.models import User

logger = logging.getLogger(__name__)


class SecureAdminMixin:
    """安全管理混入类"""

    SENSITIVE_FIELDS = ['ak', 'sk', 'password', 'secret', 'token', 'key']

    def get_fieldsets(self, request, obj=None):
        """获取字段集 - 隐藏敏感信息"""
        fieldsets = super().get_fieldsets(request, obj)

        # 如果不是超级用户，隐藏敏感字段
        if not request.user.is_superuser:
            for name, field_options in fieldsets:
                fields = field_options.get('fields', [])
                # 过滤掉敏感字段
                filtered_fields = [
                    field for field in fields
                    if not any(sensitive in field.lower() for sensitive in self.SENSITIVE_FIELDS)
                ]
                field_options['fields'] = filtered_fields

        return fieldsets

    def get_list_display(self, request):
        """获取列表显示字段 - 隐藏敏感信息"""
        list_display = super().get_list_display(request)

        if not request.user.is_superuser:
            list_display = [
                field for field in list_display
                if not any(sensitive in field.lower() for sensitive in self.SENSITIVE_FIELDS)
            ]

        return list_display


@admin.register(HuaweiCloudConfig)
class HuaweiCloudConfigAdmin(admin.ModelAdmin):
    """华为云配置管理界面 """
    list_display = ('id', 'name', 'ak_preview', 'region', 'is_active', 'created_at')

    list_filter = ('is_active', 'region', 'created_at')
    search_fields = ('name', 'ak', 'region')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20
    actions = ['activate_configs', 'deactivate_configs']
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'ak', 'sk', 'region', 'is_active')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        # 把 list_display 中的所有字段赋值给 list_display_links
        self.list_display_links = self.list_display

    def get_readonly_fields(self, request, obj=None):
        """设置只读字段"""
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly_fields.extend(['ak', 'sk'])
        return readonly_fields

    def ak_preview(self, obj):
        """AK预览 """
        if obj.ak and len(obj.ak) > 8:
            return f"{obj.ak[:2]}••••{obj.ak[-2:]}"
        return "••••"

    ak_preview.short_description = "Access Key"

    def save_model(self, request, obj, form, change):
        """保存模型时记录审计日志"""
        action = "修改" if change else "创建"
        logger.info(f"管理员 {request.user} {action}了华为云配置: {obj.name}")
        super().save_model(request, obj, form, change)

    def activate_configs(self, request, queryset):
        """激活选中的配置"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'成功激活 {updated} 个配置')

    activate_configs.short_description = "激活选中的配置"

    def deactivate_configs(self, request, queryset):
        """禁用选中的配置"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'成功禁用 {updated} 个配置')

    deactivate_configs.short_description = "禁用选中的配置"


@admin.register(OcrInterface)
class OcrInterfaceAdmin(admin.ModelAdmin):
    """OCR接口管理界面"""

    def get_list_display(self, request):
        """动态获取列表显示字段"""
        base_fields = ['id', 'name', 'interface_type', 'huawei_config', 'is_active', 'test_interface_link',
                       'created_at']

        # 检查vin_config字段是否存在
        try:
            # 尝试访问vin_config字段
            OcrInterface.objects.first().vin_config
            return base_fields + ['vin_config']
        except:
            # 如果字段不存在，返回基础字段
            return base_fields

    def get_fieldsets(self, request, obj=None):
        """动态获取字段集"""
        base_fieldsets = (
            ('基本信息', {
                'fields': ('name', 'interface_type', 'description', 'is_active')
            }),
            ('时间信息', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            }),
        )

        # 检查vin_config字段是否存在
        try:
            # 尝试访问vin_config字段
            OcrInterface.objects.first().vin_config
            # 如果字段存在，返回包含VIN配置的字段集
            return (
                ('基本信息', {
                    'fields': ('name', 'interface_type', 'description', 'is_active')
                }),
                ('华为云配置', {
                    'fields': ('huawei_config',),
                    'classes': ('collapse',)
                }),
                ('VIN查询配置', {
                    'fields': ('vin_config',),
                    'classes': ('collapse',)
                }),
                ('时间信息', {
                    'fields': ('created_at', 'updated_at'),
                    'classes': ('collapse',)
                }),
            )
        except:
            # 如果字段不存在，返回基础字段集
            return base_fieldsets

    list_filter = ('interface_type', 'is_active', 'huawei_config', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20
    actions = ['activate_interfaces', 'deactivate_interfaces']
    list_display_links = ('id', 'name', 'interface_type', 'huawei_config')

    def test_interface_link(self, obj):
        """测试接口链接"""
        if obj.is_active:
            if obj.interface_type == 'vin':
                # 检查vin_config字段是否存在
                try:
                    if hasattr(obj, 'vin_config') and obj.vin_config and obj.vin_config.is_active:
                        return format_html(
                            '<a class="button" href="{}">测试接口</a>',
                            reverse('admin:ocr_ocrinterface_test', args=[obj.id])
                        )
                except:
                    pass
            else:
                if obj.huawei_config and obj.huawei_config.is_active:
                    return format_html(
                        '<a class="button" href="{}">测试接口</a>',
                        reverse('admin:ocr_ocrinterface_test', args=[obj.id])
                    )
        return "不可用"

    test_interface_link.short_description = "接口测试"

    def activate_interfaces(self, request, queryset):
        """激活选中的接口"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'成功激活 {updated} 个接口')

    activate_interfaces.short_description = "激活选中的接口"

    def deactivate_interfaces(self, request, queryset):
        """禁用选中的接口"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'成功禁用 {updated} 个接口')

    deactivate_interfaces.short_description = "禁用选中的接口"

    def get_urls(self):
        """添加自定义URL"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/test/',
                self.admin_site.admin_view(self.test_interface_view),
                name='ocr_ocrinterface_test',
            ),
        ]
        return custom_urls + urls

    @staticmethod
    def test_interface_view(request, object_id):
        """接口测试视图 """
        from django.conf import settings
        import tempfile
        import json
        import hashlib

        try:
            interface = OcrInterface.objects.get(id=object_id)

            if request.method == 'POST':
                if interface.interface_type == 'vin':
                    # VIN接口测试逻辑
                    vin_code = request.POST.get('vin_code', '').strip()
                    if not vin_code:
                        messages.error(request, "请输入VIN码")
                        return render(request, 'admin/ocr/interface_test.html', {
                            'interface': interface,
                            'title': f'测试接口 - {interface.name}'
                        })

                    # 检查VIN配置是否存在
                    try:
                        if not hasattr(interface,
                                       'vin_config') or not interface.vin_config or not interface.vin_config.is_active:
                            messages.error(request, "接口关联的VIN配置不可用")
                            return render(request, 'admin/ocr/interface_test.html', {
                                'interface': interface,
                                'title': f'测试接口 - {interface.name}'
                            })
                    except:
                        messages.error(request, "接口关联的VIN配置不可用")
                        return render(request, 'admin/ocr/interface_test.html', {
                            'interface': interface,
                            'title': f'测试接口 - {interface.name}'
                        })

                    try:
                        # 使用vin.py中的VinAPIWithParser类
                        from .vin import VinAPIWithParser

                        vin_config = interface.vin_config
                        api_client = VinAPIWithParser(vin_config.username, vin_config.password)
                        parser = api_client.query_vin(vin_code)

                        if parser.is_success:
                            # 构建响应数据
                            result_data = {
                                'basic_info': {
                                    'brand': parser.brand,
                                    'model_year': parser.model_year_from_vin,
                                    'build_date': parser.build_date,
                                    'epc_cn': parser.epc_cn,
                                },
                                'model_list': [],
                                'original_attributes': parser.get_original_attributes('zh'),
                                'gonggao_list': parser.get_gonggao_list(),
                            }

                            # 处理车型列表
                            for model in parser.get_model_list():
                                model_info = {
                                    'model_detail': model.get('Model_detail', ''),
                                    'factory': model.get('Factory', ''),
                                    'series': model.get('Series', ''),
                                    'sales_version': model.get('Sales_version', ''),
                                    'cc': model.get('Cc', ''),
                                    'engine_no': model.get('Engine_no', ''),
                                    'price': model.get('Price', ''),
                                }
                                result_data['model_list'].append(model_info)

                            return render(request, 'admin/ocr/interface_test_result.html', {
                                'interface': interface,
                                'result': {
                                    'success': True,
                                    'interface_name': interface.name,
                                    'result': result_data
                                },
                                'title': f'测试结果 - {interface.name}'
                            })
                        else:
                            return render(request, 'admin/ocr/interface_test_result.html', {
                                'interface': interface,
                                'result': {
                                    'success': False,
                                    'error': f'VIN查询失败: {parser.message}'
                                },
                                'title': f'测试结果 - {interface.name}'
                            })

                    except Exception as e:
                        logger.error(f"VIN接口测试失败: {str(e)}")
                        return render(request, 'admin/ocr/interface_test_result.html', {
                            'interface': interface,
                            'result': {
                                'success': False,
                                'error': f'VIN查询失败: {str(e)}'
                            },
                            'title': f'测试结果 - {interface.name}'
                        })

                else:
                    # OCR接口测试逻辑
                    # 检查图片上传
                    if 'test_image' not in request.FILES:
                        messages.error(request, "请上传测试图片")
                        return render(request, 'admin/ocr/interface_test.html', {
                            'interface': interface,
                            'title': f'测试接口 - {interface.name}'
                        })

                    image_file = request.FILES['test_image']

                    # 验证图片
                    from .image_utils import ImageProcessor
                    if not ImageProcessor.validate_image_format(image_file):
                        messages.error(request, "不支持的图片格式，请上传JPEG或PNG格式的图片")
                        return render(request, 'admin/ocr/interface_test.html', {
                            'interface': interface,
                            'title': f'测试接口 - {interface.name}'
                        })

                    # 验证图片大小
                    if not ImageProcessor.validate_image_size(image_file):
                        messages.error(request, "图片文件过大，请上传小于5MB的图片")
                        return render(request, 'admin/ocr/interface_test.html', {
                            'interface': interface,
                            'title': f'测试接口 - {interface.name}'
                        })

                    # 检查华为云配置
                    if not interface.huawei_config or not interface.huawei_config.is_active:
                        messages.error(request, "接口关联的华为云配置不可用")
                        return render(request, 'admin/ocr/interface_test.html', {
                            'interface': interface,
                            'title': f'测试接口 - {interface.name}'
                        })

                    # 创建临时文件
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                        # 压缩图片
                        compressed_image = ImageProcessor.compress_image(image_file)

                        # 保存压缩后的图片到临时文件
                        for chunk in compressed_image.chunks():
                            temp_file.write(chunk)
                        temp_path = temp_file.name

                    try:
                        # 创建OCR客户端
                        from .utils import HuaweiOcrClient
                        ocr_client = HuaweiOcrClient(
                            interface.huawei_config.ak,
                            interface.huawei_config.sk,
                            interface.huawei_config.region
                        )

                        # 根据接口类型调用不同的识别方法
                        recognition_result = None
                        if interface.interface_type == 'general_text':
                            recognition_result = ocr_client.recognize_general_text(temp_path)
                        elif interface.interface_type == 'id_card':
                            recognition_result = ocr_client.recognize_id_card(temp_path)
                        elif interface.interface_type == 'vehicle_license':
                            recognition_result = ocr_client.recognize_vehicle_license(temp_path)
                        elif interface.interface_type == 'business_license':
                            recognition_result = ocr_client.recognize_business_license(temp_path)
                        elif interface.interface_type == 'auto_classification':
                            recognition_result = ocr_client.recognize_auto_classification(temp_path)

                        # 处理识别结果
                        if recognition_result:
                            # 将结果转换为可序列化的格式
                            if hasattr(recognition_result, 'to_dict'):
                                result_data = recognition_result.to_dict()
                            else:
                                result_data = str(recognition_result)

                            # 尝试转换为JSON可序列化的格式
                            try:
                                # 如果结果是对象，尝试提取主要数据
                                if hasattr(recognition_result, 'result'):
                                    result_data = recognition_result.result
                                # 进一步处理，确保可以JSON序列化
                                json.dumps(result_data)
                            except:
                                # 如果无法序列化，转换为字符串
                                result_data = str(recognition_result)

                            return render(request, 'admin/ocr/interface_test_result.html', {
                                'interface': interface,
                                'result': {
                                    'success': True,
                                    'interface_name': interface.name,
                                    'result': result_data
                                },
                                'title': f'测试结果 - {interface.name}'
                            })
                        else:
                            return render(request, 'admin/ocr/interface_test_result.html', {
                                'interface': interface,
                                'result': {
                                    'success': False,
                                    'error': '接口调用失败，未返回有效结果'
                                },
                                'title': f'测试结果 - {interface.name}'
                            })

                    except Exception as e:
                        logger.error(f"测试接口失败: {str(e)}")
                        return render(request, 'admin/ocr/interface_test_result.html', {
                            'interface': interface,
                            'result': {
                                'success': False,
                                'error': f'测试失败: {str(e)}'
                            },
                            'title': f'测试结果 - {interface.name}'
                        })
                    finally:
                        # 清理临时文件
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)

            # GET请求显示测试页面
            context = {
                'interface': interface,
                'title': f'测试接口 - {interface.name}'
            }

            # 如果是VIN接口，传递不同的模板上下文
            if interface.interface_type == 'vin':
                context['is_vin_interface'] = True
            else:
                context['is_vin_interface'] = False

            return render(request, 'admin/ocr/interface_test.html', context)

        except OcrInterface.DoesNotExist:
            messages.error(request, "接口不存在")
            return redirect('admin:ocr_ocrinterface_changelist')
        except Exception as e:
            logger.error(f"测试接口页面加载失败: {str(e)}")
            messages.error(request, f"页面加载失败: {str(e)}")
            return redirect('admin:ocr_ocrinterface_changelist')


@admin.register(CertificateType)
class CertificateTypeAdmin(admin.ModelAdmin):
    """证件类型管理"""
    list_display = ('id', 'name', 'type_code', 'interface', 'is_active', 'created_at')
    list_filter = ('type_code', 'is_active', 'interface')
    search_fields = ('name', 'keywords')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'type_code', 'interface', 'keywords', 'is_active')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        # 把 list_display 中的所有字段赋值给 list_display_links
        self.list_display_links = self.list_display


class VehicleLicenseResultInline(admin.TabularInline):
    """行驶证识别结果内嵌表单"""
    model = VehicleLicenseResult
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    can_delete = False

    fieldsets = (
        ('主页信息', {
            'fields': (
                'number', 'vehicle_type', 'owner_name', 'address',
                'engine_no', 'vin', 'model', 'brand', 'vehicle_model',
                'register_date', 'issue_date', 'use_character'
            )
        }),
        ('副页信息', {
            'fields': (
                'file_no', 'approved_passengers', 'gross_mass',
                'unladen_mass', 'dimension', 'energy_type',
                'remarks', 'inspection_record', 'code_number'
            )
        }),
    )


class IdCardResultInline(admin.TabularInline):
    """身份证识别结果内嵌表单"""
    model = IdCardResult
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    can_delete = False

    fieldsets = (
        ('基本信息', {
            'fields': (
                'name', 'gender', 'ethnicity', 'birth',
                'address', 'number', 'side'
            )
        }),
        ('签发信息', {
            'fields': (
                'issue_authority', 'valid_from', 'valid_to'
            )
        }),
    )


class BusinessLicenseResultInline(admin.TabularInline):
    """营业执照识别结果内嵌表单"""
    model = BusinessLicenseResult
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    can_delete = False

    fieldsets = (
        ('企业信息', {
            'fields': (
                'registration_number', 'name', 'type', 'address',
                'legal_representative', 'registered_capital'
            )
        }),
        ('经营信息', {
            'fields': (
                'found_date', 'business_term', 'business_scope'
            )
        }),
    )


@admin.register(RecognitionRecord)
class RecognitionRecordAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'image_thumbnail', 'certificate_type',
        'get_vehicle_info', 'get_id_card_info', 'get_business_info', 'user',
        'recognition_status', 'recognition_time', 'created_at'
    )
    list_filter = ('certificate_type', 'interface_used', 'recognition_status', 'user', 'created_at')
    search_fields = ('user__username', 'certificate_type__name')
    readonly_fields = ('created_at', 'updated_at', 'image_thumbnail', 'recognition_time', 'image_preview')
    list_per_page = 20
    actions = ['delete_selected_records']

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        # 把 list_display 中的所有字段赋值给 list_display_links
        self.list_display_links = self.list_display

    def get_inlines(self, request, obj=None):
        """根据证件类型动态显示对应的内联表单"""
        if obj and obj.certificate_type:
            if obj.certificate_type.type_code == 'vehicle_license':
                return [VehicleLicenseResultInline]
            elif obj.certificate_type.type_code == 'id_card':
                return [IdCardResultInline]
            elif obj.certificate_type.type_code == 'business_license':
                return [BusinessLicenseResultInline]
        return []

    def get_vehicle_info(self, obj):
        """获取行驶证信息"""
        if hasattr(obj, 'vehicle_result'):
            return f"{obj.vehicle_result.number or '无车牌'} - {obj.vehicle_result.owner_name or '无车主'}"
        return "-"

    get_vehicle_info.short_description = "行驶证信息"

    def get_id_card_info(self, obj):
        """获取身份证信息"""
        if hasattr(obj, 'id_card_result'):
            return f"{obj.id_card_result.name or '无名'} - {obj.id_card_result.number or '无身份证号'}"
        return "-"

    get_id_card_info.short_description = "身份证信息"

    def get_business_info(self, obj):
        """获取营业执照信息"""
        if hasattr(obj, 'business_result'):
            return f"{obj.business_result.name or '无企业名'} - {obj.business_result.legal_representative or '无法人'}"
        return "-"

    get_business_info.short_description = "营业执照信息"

    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'image', 'image_preview', 'certificate_type', 'interface_used')
        }),
        ('识别状态', {
            'fields': ('recognition_status', 'recognition_time')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """控制数据访问权限"""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # 非超级管理员只能看到自己的记录
            qs = qs.filter(user=request.user)
        return qs

    def image_thumbnail(self, obj):
        """显示图片缩略图 - 调整为更小的尺寸"""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="width: 60px; height: 60px; object-fit: contain; border: 1px solid #ddd; border-radius: 4px;" title="点击查看大图" />',
                obj.thumbnail.url
            )
        elif obj.image:
            # 如果没有缩略图但存在原图，显示原图的缩略样式
            return format_html(
                '<img src="{}" style="width: 60px; height: 60px; object-fit: contain; border: 1px solid #ddd; border-radius: 4px;" title="点击查看大图" />',
                obj.image.url
            )
        return "无图片"

    image_thumbnail.short_description = "图片预览"

    @staticmethod
    def image_preview(obj):
        """图片预览 - 添加隐私保护提示"""
        if obj.image:
            return format_html(
                '<div style="text-align: center;">'
                '<img src="{}" style="max-width: 300px; max-height: 300px; object-fit: contain; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 10px;" />'
                '<br><small style="color: #666;">隐私保护图片</small>'
                '<br><a href="{}" target="_blank" class="button">查看原图</a>'
                '</div>',
                obj.image.url, obj.image.url
            )
        return "无图片"

    def delete_queryset(self, request, queryset):
        """重写批量删除方法 - 物理删除图片文件"""
        deleted_count = 0
        for obj in queryset:
            # 删除关联的图片文件和缩略图
            if obj.image and os.path.isfile(obj.image.path):
                try:
                    os.remove(obj.image.path)
                    logger.info(f"删除图片文件: {obj.image.path}")
                except Exception as e:
                    logger.error(f"删除图片文件失败: {str(e)}")

            # 删除缩略图文件
            if obj.thumbnail and os.path.isfile(obj.thumbnail.path):
                try:
                    os.remove(obj.thumbnail.path)
                    logger.info(f"删除缩略图文件: {obj.thumbnail.path}")
                except Exception as e:
                    logger.error(f"删除缩略图文件失败: {str(e)}")

            # 删除数据库记录
            obj.delete()
            deleted_count += 1

        self.message_user(request, f"成功删除 {deleted_count} 条记录及关联文件")

    def delete_model(self, request, obj):
        """重写单个删除方法 - 物理删除"""
        # 删除图片文件
        if obj.image and os.path.isfile(obj.image.path):
            try:
                os.remove(obj.image.path)
                logger.info(f"删除图片文件: {obj.image.path}")
            except Exception as e:
                logger.error(f"删除图片文件失败: {str(e)}")

        # 删除缩略图文件
        if obj.thumbnail and os.path.isfile(obj.thumbnail.path):
            try:
                os.remove(obj.thumbnail.path)
                logger.info(f"删除缩略图文件: {obj.thumbnail.path}")
            except Exception as e:
                logger.error(f"删除缩略图文件失败: {str(e)}")

        # 删除数据库记录
        obj.delete()
        self.message_user(request, "成功删除记录及关联文件")

    def delete_selected_records(self, request, queryset):
        """自定义批量删除action"""
        self.delete_queryset(request, queryset)

    delete_selected_records.short_description = "删除选中的记录及图片文件"

    def has_scrap_car_info(self, obj):
        """显示是否有报废车信息"""
        if obj.certificate_type and obj.certificate_type.type_code == 'vehicle_license':
            return ScrapCarInfo.objects.filter(vehicle_record=obj).exists()
        return False

    has_scrap_car_info.boolean = True
    has_scrap_car_info.short_description = '有报废车信息'

    def trigger_matching_for_selected(self, request, queryset):
        """为选中的记录触发匹配"""
        from .signals import MatchEngine
        success_count = 0

        for record in queryset:
            if record.recognition_status:
                result = MatchEngine.trigger_matching_for_record(record)
                if result:
                    success_count += 1

        self.message_user(request, f"成功为 {success_count} 条记录触发匹配")

    trigger_matching_for_selected.short_description = "为选中记录触发匹配"


@admin.register(VehicleLicenseResult)
class VehicleLicenseResultAdmin(admin.ModelAdmin):
    """行驶证识别结果管理"""
    list_display = ('id', 'number', 'owner_name', 'vehicle_type', 'brand',
                    'vehicle_model', 'vehicle_name', 'production_year', 'vin', 'created_at')
    list_filter = ('vehicle_type', 'brand', 'production_year')
    search_fields = ('number', 'owner_name', 'vin', 'brand', 'vehicle_model', 'vehicle_name')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20

    # 添加自定义动作
    actions = ['query_vin_for_selected', 'batch_query_vin']

    fieldsets = (
        ('主页信息', {
            'fields': (
                'number', 'vehicle_type', 'owner_name', 'address',
                'engine_no', 'vin', 'model', 'brand', 'vehicle_model',
                'vehicle_name', 'production_year', 'register_date', 'issue_date', 'use_character'
            )
        }),
        ('副页信息', {
            'fields': (
                'file_no', 'approved_passengers', 'gross_mass',
                'unladen_mass', 'dimension', 'energy_type',
                'remarks', 'inspection_record', 'code_number'
            )
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        # 把 list_display 中的所有字段赋值给 list_display_links
        self.list_display_links = self.list_display

    def query_vin_for_selected(self, request, queryset):
        """为选中的记录查询VIN信息 """
        from .vin_tasks import query_vin_for_vehicle_result_task

        processed_count = 0
        for vehicle_result in queryset:
            if vehicle_result.vin and vehicle_result.vin.strip():
                try:
                    # 直接调用任务函数，而不是delay()
                    success = query_vin_for_vehicle_result_task.delay(vehicle_result.id)
                    if success:
                        processed_count += 1
                        logger.info(f"已触发VIN查询任务: {vehicle_result.id}")
                    else:
                        logger.warning(f"触发VIN查询任务失败: {vehicle_result.id}")
                except Exception as e:
                    logger.error(f"触发VIN查询任务异常: {str(e)}")
                    self.message_user(
                        request,
                        f"任务触发失败: {str(e)}",
                        level='error'
                    )

        if processed_count > 0:
            self.message_user(
                request,
                f"已触发 {processed_count} 条记录的VIN查询任务",
                level='success'
            )
        else:
            self.message_user(
                request,
                "没有有效的VIN码需要查询",
                level='warning'
            )

    query_vin_for_selected.short_description = "查询选中记录的VIN信息"

    def batch_query_vin(self, request, queryset):
        """批量查询VIN信息 """
        try:
            from .tasks import batch_query_vin_for_vehicle_records_task

            # 直接调用同步版本，避免Celery问题
            result = batch_query_vin_for_vehicle_records_task()

            if result and 'success_count' in result:
                self.message_user(
                    request,
                    f"批量VIN查询完成: 成功查询 {result['success_count']} 条记录",
                    level='success'
                )
            else:
                self.message_user(
                    request,
                    "批量VIN查询任务已执行，请查看日志了解详情",
                    level='info'
                )
        except Exception as e:
            self.message_user(
                request,
                f"批量VIN查询失败: {str(e)}",
                level='error'
            )
            logger.error(f"批量VIN查询失败: {str(e)}")

    batch_query_vin.short_description = "批量查询VIN信息"


@admin.register(IdCardResult)
class IdCardResultAdmin(admin.ModelAdmin):
    """身份证识别结果管理 """
    list_display = ('id', 'get_name', 'phone_number', 'gender', 'ethnicity', 'get_number', 'address', 'issue_authority')
    list_filter = ('side', 'gender', 'created_at')
    search_fields = ('name', 'number', 'issue_authority', 'address')
    readonly_fields = ('created_at', 'updated_at', 'get_record_link')
    list_per_page = 20

    # 自定义显示方法
    def get_record_id(self, obj):
        return obj.record.id

    get_record_id.short_description = '记录ID'

    def get_name(self, obj):
        return obj.name or '未识别'

    get_name.short_description = '姓名'

    def get_number(self, obj):
        return obj.number or '未识别'

    get_number.short_description = '身份证号'

    def get_side(self, obj):
        return obj.get_side_display() if obj.side else '未知'

    get_side.short_description = '面类型'

    def get_record_link(self, obj):
        """显示记录链接"""
        url = reverse('admin:ocr_recognitionrecord_change', args=[obj.record.id])
        return format_html('<a href="{}">查看记录 {}</a>', url, obj.record.id)

    get_record_link.short_description = "关联记录"

    fieldsets = (
        ('基本信息', {
            'fields': (
                'get_record_link', 'side', 'phone_number',
            )
        }),
        ('人像面信息', {
            'fields': (
                'name', 'gender', 'ethnicity', 'birth',
                'address', 'number'
            )
        }),
        ('国徽面信息', {
            'fields': (
                'issue_authority', 'valid_from', 'valid_to'
            )
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        # 把 list_display 中的所有字段赋值给 list_display_links
        self.list_display_links = self.list_display


@admin.register(BusinessLicenseResult)
class BusinessLicenseResultAdmin(admin.ModelAdmin):
    """营业执照识别结果管理"""
    list_display = ('id', 'name', 'registration_number', 'legal_representative', 'address', 'type',
                    'registered_capital', 'found_date')
    list_filter = ('type', 'found_date', 'created_at')
    search_fields = ('name', 'registration_number', 'legal_representative')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        # 把 list_display 中的所有字段赋值给 list_display_links
        self.list_display_links = self.list_display


@admin.register(ScrapCarInfo)
class ScrapCarInfoAdmin(admin.ModelAdmin):
    """报废车信息识别管理"""
    list_display = (
        'id', 'owner_name', 'identification_number', 'id_card_phone_number', 'address', 'vin',
        'vehicle_number', 'vehicle_type', 'use_character', 'brand',
        'vehicle_model', 'engine_no', 'approved_passengers', 'register_date',
        'energy_type', 'unladen_mass', 'remarks', 'match_status', 'match_score'
    )

    # 设置可编辑字段
    list_editable = (
        'owner_name', 'identification_number', 'id_card_phone_number', 'address', 'vin',
        'vehicle_number', 'vehicle_type', 'use_character', 'brand',
        'vehicle_model', 'engine_no', 'approved_passengers', 'register_date',
        'energy_type', 'unladen_mass', 'remarks'
    )

    list_display_links = ('id',)  # 设置点击id进入编辑页面

    list_filter = ('match_status', 'use_character', 'energy_type', 'created_at')
    search_fields = (
        'owner_name', 'identification_number', 'vehicle_number',
        'vin', 'brand', 'vehicle_model', 'engine_no'
    )
    readonly_fields = (
        'created_at', 'updated_at', 'match_score', 'match_rules',
        'matched_at', 'vehicle_record_link', 'id_card_record_link',
        'business_record_link', 'match_type_display'
    )
    list_per_page = 13
    ordering = ['-created_at']
    actions = [
        # 'recalculate_match_score',
        'cleanup_blank_records',
        'find_and_merge_duplicates',
        'export_selected_to_excel',
        'export_current_page_to_excel',
        'export_all_to_excel',
    ]

    # 调整字段集顺序
    fieldsets = (
        ('关联记录（请至少选择一条行驶证记录）', {
            'fields': (
                'vehicle_record', 'id_card_record', 'business_record'
            )
        }),
        ('匹配信息', {
            'fields': (
                'match_status', 'match_score', 'match_rules', 'match_type_display',
                'matched_at'
            )
        }),
        ('报废单位/个人信息', {
            'fields': (
                'owner_name', 'identification_number', 'address', 'id_card_phone_number',
            )
        }),
        ('车辆基本信息', {
            'fields': (
                'vin', 'vehicle_number', 'vehicle_type', 'use_character'
            )
        }),
        ('车辆详细信息', {
            'fields': (
                'brand', 'vehicle_model', 'engine_no', 'approved_passengers',
                'register_date', 'energy_type', 'unladen_mass', 'remarks'
            )
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # 来显示弹出窗口选择
    raw_id_fields = ('vehicle_record', 'id_card_record', 'business_record')

    def vehicle_record_link(self, obj):
        """显示行驶证记录链接"""
        if obj.vehicle_record:
            url = reverse('admin:ocr_recognitionrecord_change', args=[obj.vehicle_record.id])
            return format_html('<a href="{}">查看行驶证记录 {}</a>', url, obj.vehicle_record.id)
        return "-"

    vehicle_record_link.short_description = "行驶证记录"

    def id_card_record_link(self, obj):
        """显示身份证记录链接"""
        if obj.id_card_record:
            url = reverse('admin:ocr_recognitionrecord_change', args=[obj.id_card_record.id])
            return format_html('<a href="{}">查看身份证记录 {}</a>', url, obj.id_card_record.id)
        return "-"

    id_card_record_link.short_description = "身份证记录"

    def business_record_link(self, obj):
        """显示营业执照记录链接"""
        if obj.business_record:
            url = reverse('admin:ocr_recognitionrecord_change', args=[obj.business_record.id])
            return format_html('<a href="{}">查看营业执照记录 {}</a>', url, obj.business_record.id)
        return "-"

    business_record_link.short_description = "营业执照记录"

    def match_type_display(self, obj):
        """显示匹配类型"""
        match_types = {
            'id_card': '身份证匹配',
            'business': '营业执照匹配',
            'both': '身份证和营业执照匹配',
            'none': '无匹配'
        }
        return match_types.get(obj.match_type, '未知')

    match_type_display.short_description = "匹配类型"

    def recalculate_match_score(self, request, queryset):
        """重新计算匹配分数"""
        from .signals import MatchEngine
        updated_count = 0

        for obj in queryset:
            try:
                match_score, match_rules = MatchEngine.calculate_match_score(
                    obj.vehicle_record, obj.id_card_record, obj.business_record
                )

                # 更新匹配状态
                obj.update_match_status()

                obj.match_score = match_score
                obj.match_rules = match_rules
                obj.save()

                updated_count += 1

            except Exception as e:
                self.message_user(request, f"重新计算记录 {obj.id} 失败: {str(e)}", level='error')

        self.message_user(request, f"成功重新计算 {updated_count} 条记录的匹配分数")

    recalculate_match_score.short_description = "重新计算匹配分数"

    def cleanup_blank_records(self, request, queryset):
        """清理空白记录"""
        try:
            # 只有管理员可以执行此操作
            if not request.user.is_staff:
                self.message_user(request, "权限不足，只有管理员可以执行此操作", level='error')
                return

            # 忽略传入的queryset，总是使用所有记录
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

            if deleted_count == 0:
                self.message_user(request, "未找到空白记录", level='info')
                return

            # 删除空白记录
            blank_records.delete()

            logger.info(f"管理员 {request.user.username} 清理了 {deleted_count} 条空白记录")
            self.message_user(request, f'成功清理 {deleted_count} 条空白记录')

        except Exception as e:
            logger.error(f"清理空白记录失败: {str(e)}")
            self.message_user(request, f'清理空白记录失败: {str(e)}', level='error')

    cleanup_blank_records.short_description = "清理空白记录"

    def get_queryset(self, request):
        """优化查询性能"""
        return super().get_queryset(request).select_related(
            'vehicle_record',
            'id_card_record',
            'business_record'
        )

    def find_and_merge_duplicates(self, request, queryset):
        """查找并合并重复记录"""
        from .duplicate_utils import DuplicateManager

        try:
            merged_count = DuplicateManager.auto_merge_duplicates()
            self.message_user(request, f"成功合并 {merged_count} 条重复记录")
        except Exception as e:
            self.message_user(request, f"合并重复记录失败: {str(e)}", level='error')

    find_and_merge_duplicates.short_description = "查找并合并重复记录"

    def export_selected_to_excel(self, request, queryset):
        """导出选中的记录到Excel"""
        try:
            from .excel_utils import ExcelExporter

            logger.info(f"开始导出选中记录，用户: {request.user.username}")

            # 获取所有选中的记录ID（包括跨页）
            selected_ids = request.POST.getlist('_selected_action')

            if not selected_ids:
                self.message_user(request, "未选中任何记录", level='warning')
                return

            logger.info(f"选中的记录ID列表: {selected_ids}")

            # 转换为整数列表
            try:
                selected_ids = [int(id) for id in selected_ids]
            except ValueError as e:
                self.message_user(request, f"记录ID格式错误: {str(e)}", level='error')
                return

            # 获取所有选中的记录（包括跨页）
            all_selected_records = ScrapCarInfo.objects.filter(id__in=selected_ids)

            # 如果查询集为空，尝试从request获取原始查询集
            if not all_selected_records.exists():
                logger.warning("未找到选中记录，尝试从queryset获取")
                all_selected_records = queryset

            count = all_selected_records.count()

            if count == 0:
                self.message_user(request, "未找到可导出的记录", level='warning')
                return

            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"报废车信息_选中记录_{timestamp}.xlsx"

            # 导出记录
            response = ExcelExporter.export_scrap_car_info(all_selected_records, filename, record_count=count)

            # 记录操作日志
            logger.info(f"管理员 {request.user.username} 导出了 {count} 条记录")
            self.message_user(request, f"成功导出 {count} 条记录到Excel")

            return response

        except Exception as e:
            self.message_user(request, f"导出失败: {str(e)}", level='error')
            logger.error(f"导出选中记录失败: {str(e)}", exc_info=True)
            return None

    export_selected_to_excel.short_description = "导出选中记录到Excel"

    def export_all_to_excel(self, request, queryset):
        """导出所有记录到Excel"""
        try:
            from .excel_utils import ExcelExporter

            # 获取所有记录（忽略当前选中的查询集）
            all_records = self.get_queryset(request)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"报废车信息_全部记录_{timestamp}.xlsx"

            response = ExcelExporter.export_scrap_car_info(all_records, filename)

            # 记录操作日志
            self.message_user(request, f"成功导出所有 {all_records.count()} 条记录到Excel")
            logger.info(f"管理员 {request.user.username} 导出了所有 {all_records.count()} 条报废车信息记录")

            return response

        except Exception as e:
            self.message_user(request, f"导出失败: {str(e)}", level='error')
            logger.error(f"导出所有记录失败: {str(e)}")

    export_all_to_excel.short_description = "导出所有记录到Excel"

    def export_current_page_to_excel(self, request, queryset):
        """导出当前页记录到Excel """
        try:
            from .excel_utils import ExcelExporter
            from django.core.paginator import Paginator

            # 获取基础查询集（应用了所有过滤和搜索条件），并确保排序
            base_queryset = self.get_queryset(request).order_by('-created_at')

            # 获取当前页码，默认为第1页
            page_number = request.GET.get('p', 1)
            try:
                page_number = int(page_number)
            except (TypeError, ValueError):
                page_number = 1

            # 使用分页器获取当前页的记录
            paginator = Paginator(base_queryset, self.list_per_page)

            try:
                current_page = paginator.page(page_number)
                current_page_records = list(current_page.object_list)
            except:
                # 如果页码无效，使用第一页
                current_page = paginator.page(1)
                current_page_records = list(current_page.object_list)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"报废车信息_本页记录_{timestamp}.xlsx"

            # 修复：传递记录数量而不是调用count方法
            response = ExcelExporter.export_scrap_car_info(current_page_records, filename, len(current_page_records))

            # 记录操作日志
            self.message_user(request, f"成功导出本页 {len(current_page_records)} 条记录到Excel")
            logger.info(f"管理员 {request.user.username} 导出了本页 {len(current_page_records)} 条报废车信息记录")

            return response

        except Exception as e:
            self.message_user(request, f"导出本页记录失败: {str(e)}", level='error')
            logger.error(f"导出本页记录失败: {str(e)}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    export_current_page_to_excel.short_description = "导出本页记录到Excel"
