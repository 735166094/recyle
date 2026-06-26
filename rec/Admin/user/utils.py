# user/utils.py
import requests
import json
from django.conf import settings
import logging
from Crypto.Cipher import AES
import base64
import binascii
import time
from typing import Optional, Dict, Any
from django.utils import timezone
from .models import User, UserAddress, UserCoupon, UserFavorite, SMSVerificationCode
import random
from django.core.cache import cache

logger = logging.getLogger(__name__)


class AccountManager:
    """账号管理工具类"""

    @staticmethod
    def create_employee_account(staff_id, real_name, department, position, phone=None, email=None, password=None):
        """
        创建员工账号
        :return: (用户对象, 是否成功, 错误信息)
        """
        try:
            # 检查员工工号是否已存在
            if User.objects.filter(staff_id=staff_id, user_type='employee').exists():
                return None, False, "员工工号已存在"

            # 如果提供了手机号，检查是否已被其他账号使用
            if phone:
                existing_user = User.objects.filter(phone=phone, is_active=True).first()
                if existing_user:
                    return None, False, "手机号已被其他账号使用"

            # 创建新员工账号
            user = User.objects.create_employee(
                staff_id=staff_id,
                real_name=real_name,
                department=department,
                position=position,
                password=password,
                phone=phone,
                email=email,
                is_active=True
            )

            return user, True, "员工账号创建成功"

        except Exception as e:
            logger.error(f"创建员工账号失败: {str(e)}", exc_info=True)
            return None, False, f"创建员工账号失败: {str(e)}"

    @staticmethod
    def verify_phone_code(phone, code, purpose='bind_phone'):
        """
        验证手机验证码
        :return: (是否有效, 错误信息)
        """
        try:
            # 从缓存获取验证码（如果使用缓存）
            cache_key = f"sms_code_{phone}_{purpose}"
            cached_code = cache.get(cache_key)

            if cached_code and cached_code == code:
                # 验证成功，清除缓存
                cache.delete(cache_key)

                # 记录到数据库
                SMSVerificationCode.objects.create(
                    phone=phone,
                    code=code,
                    purpose=purpose,
                    is_used=True,
                    expires_at=timezone.now(),
                    used_at=timezone.now()
                )
                return True, "验证码正确"

            # 从数据库验证
            recent_codes = SMSVerificationCode.objects.filter(
                phone=phone,
                purpose=purpose,
                is_used=False,
                expires_at__gt=timezone.now()
            ).order_by('-created_at')

            if not recent_codes.exists():
                return False, "验证码已过期或不存在"

            valid_code = recent_codes.first()
            if valid_code.code != code:
                return False, "验证码错误"

            # 验证成功
            valid_code.is_used = True
            valid_code.used_at = timezone.now()
            valid_code.save()

            return True, "验证码正确"

        except Exception as e:
            logger.error(f"验证手机验证码失败: {str(e)}", exc_info=True)
            return False, f"验证失败: {str(e)}"

    @staticmethod
    def generate_phone_code(phone, purpose='bind_phone'):
        """
        生成手机验证码
        :return: (验证码, 是否成功, 错误信息)
        """
        try:
            # 生成6位随机验证码
            code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

            # 设置过期时间（10分钟）
            expires_at = timezone.now() + timezone.timedelta(minutes=10)

            # 保存到数据库
            SMSVerificationCode.objects.create(
                phone=phone,
                code=code,
                purpose=purpose,
                expires_at=expires_at
            )

            # 同时保存到缓存（5分钟）
            cache_key = f"sms_code_{phone}_{purpose}"
            cache.set(cache_key, code, timeout=300)

            logger.info(f"生成验证码: {phone} - {code} - {purpose}")
            return code, True, "验证码生成成功"

        except Exception as e:
            logger.error(f"生成验证码失败: {str(e)}", exc_info=True)
            return None, False, f"生成验证码失败: {str(e)}"


class WeChatLogin:
    @staticmethod
    def get_openid(code: str, retry_count: int = 3) -> Optional[Dict[str, Any]]:
        """通过code获取openid和session_key"""
        appid = getattr(settings, 'WECHAT_APPID', 'your_appid')
        secret = getattr(settings, 'WECHAT_SECRET', 'your_secret')

        if not code:
            logger.error("微信登录失败: code为空")
            return None

        url = f"https://api.weixin.qq.com/sns/jscode2session?appid={appid}&secret={secret}&js_code={code}&grant_type=authorization_code"

        for attempt in range(retry_count):
            try:
                logger.info(f"尝试获取微信openid (第{attempt + 1}次)")
                response = requests.get(url, timeout=10)
                result = response.json()

                logger.info(f"微信API响应: {result}")

                if 'openid' in result:
                    logger.info(f"成功获取openid: {result['openid']}")
                    return {
                        'openid': result['openid'],
                        'session_key': result.get('session_key', ''),
                        'unionid': result.get('unionid', '')
                    }
                else:
                    error_msg = result.get('errmsg', '未知错误')
                    logger.error(f"微信登录错误 (第{attempt + 1}次): {error_msg}")

                    # 如果是系统繁忙错误，重试
                    if result.get('errcode') == -1 and attempt < retry_count - 1:
                        time.sleep(1)  # 等待1秒后重试
                        continue
                    else:
                        return None

            except requests.exceptions.Timeout:
                logger.error(f"微信API请求超时 (第{attempt + 1}次)")
                if attempt < retry_count - 1:
                    time.sleep(1)
                    continue
                else:
                    return None

            except requests.exceptions.ConnectionError:
                logger.error(f"微信API连接错误 (第{attempt + 1}次)")
                if attempt < retry_count - 1:
                    time.sleep(1)
                    continue
                else:
                    return None

            except Exception as e:
                logger.error(f"微信登录异常 (第{attempt + 1}次): {str(e)}")
                if attempt < retry_count - 1:
                    time.sleep(1)
                    continue
                else:
                    return None

        return None

    @staticmethod
    def decrypt_phone_number(session_key: str, encrypted_data: str, iv: str) -> Optional[str]:
        """
        解密手机号
        :param session_key: 微信session_key
        :param encrypted_data: 加密数据
        :param iv: 加密算法的初始向量
        :return: 解密后的手机号或None
        """
        try:
            logger.info("开始解密手机号...")

            # 验证参数
            if not all([session_key, encrypted_data, iv]):
                logger.error("解密手机号失败: 参数不完整")
                return None

            # Base64解码
            try:
                session_key_base64 = base64.b64decode(session_key)
                encrypted_data_base64 = base64.b64decode(encrypted_data)
                iv_base64 = base64.b64decode(iv)
            except (binascii.Error, ValueError) as e:
                logger.error(f"Base64解码失败: {str(e)}")
                return None

            # 验证数据长度
            if len(session_key_base64) != 24:
                logger.error(f"session_key长度不正确: {len(session_key_base64)}")
                return None

            # AES解密
            try:
                cipher = AES.new(session_key_base64, AES.MODE_CBC, iv_base64)
                decrypted = cipher.decrypt(encrypted_data_base64)
            except ValueError as e:
                logger.error(f"AES解密失败: {str(e)}")
                return None

            # PKCS7去除补位
            try:
                pad = decrypted[-1]
                if pad < 1 or pad > 32:
                    pad = 0
                content = decrypted[:-pad]
            except IndexError as e:
                logger.error(f"去除补位失败: {str(e)}")
                return None

            # 解析JSON
            try:
                result = json.loads(content.decode('utf-8'))
                logger.info(f"解密后的手机号数据: {result}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {str(e)}")
                return None

            # 验证watermark
            watermark = result.get('watermark', {})
            appid = watermark.get('appid')
            if appid != settings.WECHAT_APPID:
                logger.error(f"watermark appid 不匹配: {appid} != {settings.WECHAT_APPID}")
                return None

            phone_number = result.get('phoneNumber')
            if phone_number:
                logger.info(f"手机号解密成功: {phone_number}")
                return phone_number
            else:
                logger.error("解密数据中未找到手机号")
                return None

        except Exception as e:
            logger.error(f"手机号解密失败: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def decrypt_user_info(session_key: str, encrypted_data: str, iv: str) -> Optional[Dict[str, Any]]:
        """
        解密用户信息 - 增强版
        :param session_key: 微信session_key
        :param encrypted_data: 加密数据
        :param iv: 加密算法的初始向量
        :return: 解密后的用户信息字典或None
        """
        try:
            logger.info("开始解密用户信息...")

            # 验证参数
            if not all([session_key, encrypted_data, iv]):
                logger.error("解密用户信息失败: 参数不完整")
                return None

            # Base64解码
            try:
                session_key_base64 = base64.b64decode(session_key)
                encrypted_data_base64 = base64.b64decode(encrypted_data)
                iv_base64 = base64.b64decode(iv)
            except (binascii.Error, ValueError) as e:
                logger.error(f"Base64解码失败: {str(e)}")
                return None

            # 验证数据长度
            if len(session_key_base64) != 24:
                logger.error(f"session_key长度不正确: {len(session_key_base64)}")
                return None

            # AES解密
            try:
                cipher = AES.new(session_key_base64, AES.MODE_CBC, iv_base64)
                decrypted = cipher.decrypt(encrypted_data_base64)
            except ValueError as e:
                logger.error(f"AES解密失败: {str(e)}")
                return None

            # PKCS7去除补位
            try:
                pad = decrypted[-1]
                if pad < 1 or pad > 32:
                    pad = 0
                content = decrypted[:-pad]
            except IndexError as e:
                logger.error(f"去除补位失败: {str(e)}")
                return None

            # 解析JSON
            try:
                result = json.loads(content.decode('utf-8'))
                logger.info(f"解密后的用户信息: {result}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {str(e)}")
                return None

            # 验证watermark
            watermark = result.get('watermark', {})
            appid = watermark.get('appid')
            if appid != settings.WECHAT_APPID:
                logger.error(f"watermark appid 不匹配: {appid} != {settings.WECHAT_APPID}")
                return None

            logger.info("用户信息解密成功")
            return result

        except Exception as e:
            logger.error(f"解密用户信息失败: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def validate_session_key(session_key: str) -> bool:
        """
        验证session_key是否有效
        """
        try:
            # 简单的格式验证
            if not session_key or len(session_key) < 8:
                return False

            # 验证是否为有效的base64字符串
            try:
                base64.b64decode(session_key)
                return True
            except (binascii.Error, ValueError):
                return False

        except Exception as e:
            logger.error(f"验证session_key失败: {str(e)}")
            return False

    @staticmethod
    def validate_wechat_params(code: str, encrypted_data: str = None, iv: str = None) -> tuple[bool, str]:
        """
        验证微信登录参数
        :return: (是否有效, 错误信息)
        """
        if not code:
            return False, "微信登录code不能为空"

        if encrypted_data and not iv:
            return False, "提供了加密数据但缺少初始向量"

        if iv and not encrypted_data:
            return False, "提供了初始向量但缺少加密数据"

        return True, "参数有效"


class WeChatAPI:
    """微信API调用工具类"""

    @staticmethod
    def get_access_token() -> Optional[str]:
        """获取微信access_token"""
        appid = getattr(settings, 'WECHAT_APPID', '')
        secret = getattr(settings, 'WECHAT_SECRET', '')

        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={secret}"

        try:
            response = requests.get(url, timeout=10)
            result = response.json()

            if 'access_token' in result:
                logger.info("成功获取微信access_token")
                return result['access_token']
            else:
                logger.error(f"获取access_token失败: {result}")
                return None

        except Exception as e:
            logger.error(f"获取access_token异常: {str(e)}")
            return None

    @staticmethod
    def get_user_phone_number(access_token: str, code: str) -> Optional[Dict[str, Any]]:
        """获取用户手机号（需要用户主动触发）"""
        url = f"https://api.weixin.qq.com/wxa/business/getuserphonenumber?access_token={access_token}"

        data = {
            "code": code
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()

            if result.get('errcode') == 0:
                phone_info = result.get('phone_info', {})
                logger.info(f"成功获取用户手机号: {phone_info}")
                return phone_info
            else:
                logger.error(f"获取用户手机号失败: {result}")
                return None

        except Exception as e:
            logger.error(f"获取用户手机号异常: {str(e)}")
            return None
