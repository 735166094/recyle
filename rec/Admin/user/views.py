# user/views.py
from rest_framework import status, permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView, DestroyAPIView, CreateAPIView
from django.contrib.auth import login, logout, authenticate
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
import time
from rest_framework_simplejwt.views import TokenRefreshView as SimpleJWTTokenRefreshView

from .models import User, UserAddress, UserCoupon, UserFavorite, EmployeeApp, EmployeeLoginRecord
from .serializers import (
    UserSerializer, UserSimpleSerializer, UserLoginSerializer, CustomerRegisterSerializer,
    UserProfileUpdateSerializer, EmployeeProfileUpdateSerializer, UserAddressSerializer,
    UserCouponSerializer, UserFavoriteSerializer, WeChatLoginSerializer, PhoneBindSerializer,
    UserProfileWithTokenSerializer, EmployeeLoginSerializer, EmployeeProfileWithTokenSerializer,
    EmployeeAppSerializer, EmployeeAppAccessSerializer, EmployeeRegisterSerializer, SMSVerifySerializer,
    UserPasswordChangeSerializer, EmployeePasswordChangeSerializer
)

from .utils import AccountManager, WeChatLogin, WeChatAPI
import logging
import re

logger = logging.getLogger(__name__)


class UserProfileView(APIView):
    """用户个人信息API视图"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        """获取当前用户信息"""
        serializer = UserSerializer(request.user, context={'request': request})
        return Response({
            'code': 200,
            'message': '获取用户信息成功',
            'data': serializer.data
        })

    @staticmethod
    def put(request):
        """更新当前用户信息"""
        # 根据用户类型选择不同的序列化器
        if request.user.user_type in ['employee', 'admin']:
            serializer = EmployeeProfileUpdateSerializer(
                request.user, data=request.data, partial=True
            )
        else:
            serializer = UserProfileUpdateSerializer(
                request.user, data=request.data, partial=True
            )

        if serializer.is_valid():
            serializer.save()
            user_serializer = UserSerializer(request.user, context={'request': request})
            return Response({
                'code': 200,
                'message': '更新用户信息成功',
                'data': user_serializer.data
            })

        return Response({
            'code': 400,
            'message': '更新失败',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class UnifiedLoginView(APIView):
    """统一登录API视图"""
    permission_classes = [permissions.AllowAny]

    @staticmethod
    def post(request):
        """统一登录"""
        serializer = UserLoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({
                'code': 400,
                'message': '参数错误',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = serializer.validated_data['user']

            # 检查账号状态
            if not user.is_active:
                return Response({
                    'code': 400,
                    'message': '账号已被禁用'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 更新登录时间
            user.last_login_time = timezone.now()
            user.save(update_fields=['last_login_time', 'updated_at'])

            # 登录系统
            login(request, user)

            # 根据用户类型返回不同的序列化器
            if user.user_type in ['employee', 'admin']:
                user_serializer = EmployeeProfileWithTokenSerializer(user, context={'request': request})
            else:
                user_serializer = UserProfileWithTokenSerializer(user, context={'request': request})

            # 如果是员工，返回应用列表
            apps_data = None
            if user.user_type in ['employee', 'admin']:
                apps = EmployeeApp.objects.filter(is_active=True).order_by('sort_order')
                app_serializer = EmployeeAppSerializer(apps, many=True)
                apps_data = app_serializer.data

            response_data = {
                'code': 200,
                'message': '登录成功',
                'data': {
                    'user': user_serializer.data,
                    'apps': apps_data
                }
            }

            return Response(response_data)

        except Exception as e:
            logger.error(f"登录异常: {str(e)}", exc_info=True)
            return Response({
                'code': 500,
                'message': '登录异常',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserPasswordChangeView(APIView):
    """用户密码修改API视图"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def post(request):
        """修改密码"""
        # 根据用户类型选择不同的序列化器
        if request.user.user_type in ['employee', 'admin']:
            serializer = EmployeePasswordChangeSerializer(
                data=request.data,
                context={'user': request.user}
            )
        else:
            serializer = UserPasswordChangeSerializer(data=request.data)

            # 普通用户需要验证旧密码
            if serializer.is_valid():
                old_password = serializer.validated_data['old_password']
                if not request.user.check_password(old_password):
                    return Response({
                        'code': 400,
                        'message': '旧密码错误'
                    }, status=status.HTTP_400_BAD_REQUEST)

        if serializer.is_valid():
            new_password = serializer.validated_data['new_password']

            try:
                request.user.set_password(new_password)
                request.user.save(update_fields=['password', 'updated_at'])

                return Response({
                    'code': 200,
                    'message': '密码修改成功'
                })

            except Exception as e:
                logger.error(f"修改密码异常: {str(e)}", exc_info=True)
                return Response({
                    'code': 500,
                    'message': '密码修改失败',
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'code': 400,
            'message': '参数错误',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class EmployeeLoginView(APIView):
    """员工登录API视图（专用于后台）"""
    permission_classes = [permissions.AllowAny]

    @staticmethod
    def get_client_ip(request):
        """获取客户端IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @staticmethod
    def is_ip_blocked(ip):
        """检查IP是否被封禁"""
        block_key = f'employee_login_blocked_{ip}'
        return cache.get(block_key)

    @staticmethod
    def record_failed_attempt(ip):
        """记录失败尝试"""
        attempt_key = f'employee_login_attempts_{ip}'
        attempts = cache.get(attempt_key, 0) + 1
        cache.set(attempt_key, attempts, timeout=3600)

        if attempts >= 5:
            block_key = f'employee_login_blocked_{ip}'
            cache.set(block_key, True, timeout=1800)

    @staticmethod
    def clear_failed_attempts(ip):
        """清除失败记录"""
        attempt_key = f'employee_login_attempts_{ip}'
        cache.delete(attempt_key)

    def post(self, request):
        """员工登录"""
        # 检查IP是否被封禁
        ip_address = self.get_client_ip(request)
        if self.is_ip_blocked(ip_address):
            return Response({
                'code': 429,
                'message': '登录尝试过于频繁，请30分钟后再试'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        serializer = EmployeeLoginSerializer(data=request.data)

        if not serializer.is_valid():
            # 记录失败的登录尝试
            self.record_failed_attempt(ip_address)
            return Response({
                'code': 400,
                'message': '参数错误',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = serializer.validated_data['user']

            # 检查账号状态
            if not user.is_active:
                self.record_failed_attempt(ip_address)
                return Response({
                    'code': 400,
                    'message': '员工账号已被禁用'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 登录成功，清除失败记录
            self.clear_failed_attempts(ip_address)

            # 更新登录时间
            user.last_login_time = timezone.now()
            user.save(update_fields=['last_login_time'])

            # 记录登录日志
            EmployeeLoginRecord.objects.create(
                user=user,
                login_ip=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                login_type='password',
                is_success=True
            )

            # 生成JWT token
            refresh = RefreshToken.for_user(user)

            # 序列化用户信息
            user_serializer = EmployeeProfileWithTokenSerializer(user, context={'request': request})

            # 获取员工可访问的应用
            apps = EmployeeApp.objects.filter(is_active=True).order_by('sort_order')
            app_serializer = EmployeeAppSerializer(apps, many=True)

            # 按照前端期望的格式返回
            response_data = {
                'code': 200,
                'message': '员工登录成功',
                'data': {
                    'user': user_serializer.data,
                    'apps': app_serializer.data,
                    'token': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                }
            }

            return Response(response_data)

        except Exception as e:
            logger.error(f"员工登录异常: {str(e)}", exc_info=True)
            self.record_failed_attempt(ip_address)
            return Response({
                'code': 500,
                'message': '登录异常',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def wechat_login(request):
    """微信登录API"""
    serializer = WeChatLoginSerializer(data=request.data)

    if not serializer.is_valid():
        logger.error(f"微信登录参数验证失败: {serializer.errors}")
        return Response({
            'code': 400,
            'message': '参数错误',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    code = serializer.validated_data.get('code')
    encrypted_data = serializer.validated_data.get('encrypted_data')
    iv = serializer.validated_data.get('iv')

    if not code:
        return Response({
            'code': 400,
            'message': '请提供微信登录code'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # 调用微信登录工具获取openid和session_key
        wechat_result = WeChatLogin.get_openid(code)

        if not wechat_result:
            return Response({
                'code': 400,
                'message': '微信登录失败，无法获取openid'
            }, status=status.HTTP_400_BAD_REQUEST)

        openid = wechat_result['openid']
        session_key = wechat_result['session_key']
        unionid = wechat_result.get('unionid', '').strip()

        if unionid == '':
            unionid = None  # 完全设置为 None

        logger.info(f"微信登录成功: openid={openid}, unionid={unionid if unionid else 'None'}")

        # 查找用户（通过openid）
        user = User.objects.filter(openid=openid, is_active=True).first()

        if user:
            # 用户已存在，更新session_key
            user.session_key = session_key
            user.last_login_time = timezone.now()

            # 如果用户已绑定手机号，更新微信昵称为手机号
            if user.phone and (not user.nickname or user.nickname.startswith('用户')):
                user.nickname = user.phone

            user.save(update_fields=['session_key', 'last_login_time', 'updated_at', 'nickname'])

            logger.info(f"用户已存在: {user.username}")
        else:
            # 创建新用户 使用openid后8位作为用户名
            username = f'wx_{openid[-8:]}'

            # 检查用户名是否已存在
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f'wx_{openid[-8:]}_{counter}'
                counter += 1

            user = User.objects.create_user(
                username=username,
                openid=openid,
                session_key=session_key,
                unionid=unionid,  # 这里可能是None
                user_type='customer',
                is_wechat_bound=True,
                last_login_time=timezone.now(),
                nickname='用户',  # 初始昵称
                avatar_url='/static/img/default_avatar.png'
            )

            logger.info(f"创建新用户: {user.username}")

        # 如果有加密数据，解密用户信息
        if encrypted_data and iv:
            try:
                decrypted_user_info = WeChatLogin.decrypt_user_info(session_key, encrypted_data, iv)
                if decrypted_user_info:
                    # 更新用户基本信息
                    update_fields = ['updated_at']

                    # 如果用户有手机号，优先使用手机号作为昵称
                    if user.phone:
                        user.nickname = user.phone
                    else:
                        user.nickname = decrypted_user_info.get('nickName', user.nickname)
                    update_fields.append('nickname')

                    user.avatar_url = decrypted_user_info.get('avatarUrl', user.avatar_url)
                    update_fields.append('avatar_url')

                    user.gender = decrypted_user_info.get('gender', user.gender)
                    update_fields.append('gender')

                    user.country = decrypted_user_info.get('country', user.country)
                    update_fields.append('country')

                    user.province = decrypted_user_info.get('province', user.province)
                    update_fields.append('province')

                    user.city = decrypted_user_info.get('city', user.city)
                    update_fields.append('city')

                    user.save(update_fields=update_fields)
                    logger.info("通过加密数据更新用户信息成功")

            except Exception as e:
                logger.error(f"解密用户信息失败: {str(e)}")
                # 解密失败不影响后续流程

        # 生成JWT token
        refresh = RefreshToken.for_user(user)

        # 序列化用户信息
        user_serializer = UserProfileWithTokenSerializer(user, context={'request': request})

        response_data = {
            'code': 200,
            'message': '微信登录成功',
            'data': user_serializer.data
        }

        return Response(response_data)

    except Exception as e:
        logger.error(f"微信登录异常: {str(e)}", exc_info=True)
        return Response({
            'code': 500,
            'message': '微信登录异常',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def customer_register(request):
    """普通用户注册API"""
    serializer = CustomerRegisterSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()

        # 自动登录
        login(request, user)
        user_serializer = UserProfileWithTokenSerializer(user, context={'request': request})

        return Response({
            'code': 201,
            'message': '注册成功',
            'data': user_serializer.data
        }, status=status.HTTP_201_CREATED)

    return Response({
        'code': 400,
        'message': '注册失败',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


class UserPointsRedirectView(APIView):
    """用户积分重定向视图（兼容性处理）"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """重定向到points应用的积分汇总"""
        from django.urls import reverse

        return Response({
            'code': 301,
            'message': '积分功能已迁移到points应用',
            'data': {
                'redirect_url': reverse('points_summary'),
                'new_endpoint': '/api/points/summary/'
            }
        })


class BindPhoneView(APIView):
    """绑定手机号API视图"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def post(request):
        """绑定手机号"""
        serializer = PhoneBindSerializer(data=request.data, context={'request': request})

        if not serializer.is_valid():
            return Response({
                'code': 400,
                'message': '参数错误',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            phone = serializer.validated_data['phone']
            user = request.user

            # 检查手机号是否已被其他用户使用
            existing_user = User.objects.filter(
                phone=phone,
                is_active=True
            ).exclude(id=user.id).first()

            if existing_user:
                return Response({
                    'code': 400,
                    'message': '该手机号已被其他账号使用'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 绑定手机号
            user.bind_phone(phone)

            # 绑定手机号后，更新昵称为手机号
            if not user.nickname or user.nickname.startswith('微信用户'):
                user.nickname = phone
                user.save(update_fields=['nickname'])

            return Response({
                'code': 200,
                'message': '手机号绑定成功',
                'data': {
                    'phone': phone
                }
            })

        except ValueError as e:
            logger.error(f"绑定手机号失败: {str(e)}")
            return Response({
                'code': 400,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"绑定手机号异常: {str(e)}", exc_info=True)
            return Response({
                'code': 500,
                'message': '绑定手机号异常',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SendSMSView(APIView):
    """发送短信验证码API视图"""
    permission_classes = [permissions.AllowAny]

    @staticmethod
    def post(request):
        """发送短信验证码"""
        serializer = SMSVerifySerializer(data=request.data)

        if not serializer.is_valid():
            return Response({
                'code': 400,
                'message': '参数错误',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            phone = serializer.validated_data['phone']
            purpose = serializer.validated_data['purpose']

            # 生成验证码
            code, success, message = AccountManager.generate_phone_code(phone, purpose)

            if not success:
                return Response({
                    'code': 500,
                    'message': message
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # TODO: 这里调用实际的短信发送服务
            # 例如: send_sms(phone, f"您的验证码是: {code}，有效期10分钟")

            logger.info(f"发送短信验证码: {phone} - {code} - {purpose}")

            # 开发环境直接返回验证码
            if settings.DEBUG:
                return Response({
                    'code': 200,
                    'message': '验证码发送成功（开发模式）',
                    'data': {
                        'phone': phone,
                        'code': code,  # 开发环境返回验证码，生产环境移除
                        'expires_in': 600  # 10分钟
                    }
                })
            else:
                return Response({
                    'code': 200,
                    'message': '验证码发送成功',
                    'data': {
                        'phone': phone,
                        'expires_in': 600  # 10分钟
                    }
                })

        except Exception as e:
            logger.error(f"发送短信验证码异常: {str(e)}", exc_info=True)
            return Response({
                'code': 500,
                'message': '发送验证码失败',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def user_logout(request):
    """用户退出登录API"""
    logout(request)
    return Response({
        'code': 200,
        'message': '退出登录成功'
    })


class EmployeeLogoutView(APIView):
    """员工退出登录API视图"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def post(request):
        """员工退出登录"""
        logout(request)
        return Response({
            'code': 200,
            'message': '员工退出登录成功'
        })


class UserCouponListView(ListAPIView):
    """用户优惠券列表API"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserCouponSerializer

    def get_queryset(self):
        queryset = UserCoupon.objects.filter(user=self.request.user)
        status_filter = self.request.query_params.get('status')

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-created_at')


class UserCouponDetailView(RetrieveAPIView):
    """用户优惠券详情API"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserCouponSerializer

    def get_queryset(self):
        return UserCoupon.objects.filter(user=self.request.user)


class UserFavoriteListView(ListAPIView):
    """用户收藏列表API"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserFavoriteSerializer

    def get_queryset(self):
        queryset = UserFavorite.objects.filter(user=self.request.user)
        favorite_type = self.request.query_params.get('type')
        item_id = self.request.query_params.get('item_id')

        if favorite_type:
            queryset = queryset.filter(favorite_type=favorite_type)

        if item_id:
            try:
                item_id_int = int(item_id)
                queryset = queryset.filter(item_id=item_id_int)
            except ValueError:
                pass

        return queryset.order_by('-created_at')

    def list(self, request, *args, **kwargs):
        """获取收藏列表"""
        try:
            queryset = self.get_queryset()
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response({
                    'code': 200,
                    'message': '获取收藏列表成功',
                    'data': serializer.data
                })

            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'code': 200,
                'message': '获取收藏列表成功',
                'data': serializer.data
            })

        except Exception as e:
            logger.error(f"获取收藏列表异常: {str(e)}", exc_info=True)
            return Response({
                'code': 500,
                'message': '获取收藏列表失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserFavoriteCreateView(CreateAPIView):
    """用户收藏创建API"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserFavoriteSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        favorite_type = request.data.get('favorite_type')
        item_id = request.data.get('item_id')

        if favorite_type and item_id:
            try:
                existing_favorite = UserFavorite.objects.get(
                    user=request.user,
                    favorite_type=favorite_type,
                    item_id=item_id
                )
                serializer = self.get_serializer(existing_favorite)
                return Response({
                    'code': 200,
                    'message': '已经收藏过该商品',
                    'data': serializer.data
                }, status=status.HTTP_200_OK)
            except UserFavorite.DoesNotExist:
                pass

        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)

            return Response({
                'code': 201,
                'message': '收藏成功',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED, headers=headers)

        except serializers.ValidationError as e:
            logger.error(f"收藏创建验证失败: {str(e)}")
            return Response({
                'code': 400,
                'message': '收藏失败',
                'errors': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"收藏创建异常: {str(e)}", exc_info=True)
            return Response({
                'code': 500,
                'message': '服务器内部错误'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_create(self, serializer):
        serializer.save()


class UserFavoriteDetailView(DestroyAPIView):
    """用户收藏删除API"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserFavoriteSerializer

    def get_queryset(self):
        return UserFavorite.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'code': 200,
            'message': '取消收藏成功'
        })


class UserAddressView(APIView):
    """用户地址管理API视图"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        """获取用户的所有地址"""
        addresses = UserAddress.objects.filter(user=request.user)
        serializer = UserAddressSerializer(addresses, many=True)
        return Response({
            'code': 200,
            'message': '获取地址列表成功',
            'data': serializer.data
        })

    @staticmethod
    def post(request):
        """创建新地址"""
        serializer = UserAddressSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            address = serializer.save()
            return Response({
                'code': 201,
                'message': '地址创建成功',
                'data': UserAddressSerializer(address).data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'code': 400,
            'message': '地址创建失败',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class UserAddressDetailView(APIView):
    """用户地址详情API视图"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get_address(pk, user):
        """获取地址对象"""
        return get_object_or_404(UserAddress, pk=pk, user=user)

    def get(self, request, pk):
        """获取单个地址详情"""
        address = self.get_address(pk, request.user)
        serializer = UserAddressSerializer(address)
        return Response({
            'code': 200,
            'message': '获取地址成功',
            'data': serializer.data
        })

    def put(self, request, pk):
        """更新地址信息"""
        address = self.get_address(pk, request.user)
        serializer = UserAddressSerializer(address, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                'code': 200,
                'message': '地址更新成功',
                'data': serializer.data
            })

        return Response({
            'code': 400,
            'message': '地址更新失败',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """删除地址"""
        address = self.get_address(pk, request.user)
        address.delete()
        return Response({
            'code': 200,
            'message': '地址删除成功'
        })


class SetDefaultAddressView(APIView):
    """设置默认地址API视图"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def post(request, pk):
        """设置默认地址"""
        address = get_object_or_404(UserAddress, pk=pk, user=request.user)
        UserAddress.objects.filter(user=request.user).update(is_default=False)
        address.is_default = True
        address.save()

        return Response({
            'code': 200,
            'message': '设置默认地址成功'
        })


class EmployeeAppsView(APIView):
    """员工应用列表API视图"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        """获取员工可访问的应用列表"""
        # 检查是否是员工
        if not request.user.user_type in ['employee', 'admin']:
            return Response({
                'code': 403,
                'message': '只有员工可以访问此功能'
            }, status=status.HTTP_403_FORBIDDEN)

        apps = EmployeeApp.objects.filter(is_active=True).order_by('sort_order')
        serializer = EmployeeAppSerializer(apps, many=True)

        return Response({
            'code': 200,
            'message': '获取应用列表成功',
            'data': serializer.data
        })


class EmployeeAccessAppView(APIView):
    """员工访问应用API视图"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def post(request):
        """访问指定应用"""
        # 检查是否是员工
        if not request.user.user_type in ['employee', 'admin']:
            return Response({
                'code': 403,
                'message': '只有员工可以访问此功能'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = EmployeeAppAccessSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({
                'code': 400,
                'message': '参数错误',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        app = serializer.validated_data['app']

        # 调试日志：打印用户信息和应用配置
        logger.info(f"用户访问应用检查 - 用户ID: {request.user.id}")
        logger.info(f"员工工号: {request.user.staff_id}")
        logger.info(f"应用ID: {app.app_id}, 应用名称: {app.app_name}")
        logger.info(f"应用权限配置: {app.access_roles}")
        logger.info(f"用户类型: {request.user.user_type}")

        # 检查访问权限
        if app.access_roles and len(app.access_roles) > 0:
            user_role = request.user.user_type

            logger.info(f"检查权限 - 用户角色: {user_role}, 应用允许角色: {app.access_roles}")

            if user_role not in app.access_roles:
                logger.warning(f"权限拒绝 - 用户角色 {user_role} 不在允许的角色列表中")
                return Response({
                    'code': 403,
                    'message': f'您没有权限访问此应用。您的角色: {user_role}，需要的角色: {app.access_roles}'
                }, status=status.HTTP_403_FORBIDDEN)
        else:
            logger.info("应用没有配置访问角色限制，允许所有员工访问")

        # 检查是否需要认证
        if app.require_auth and not request.user.is_authenticated:
            return Response({
                'code': 401,
                'message': '需要认证'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # 获取应用访问信息
        app_access_info = app.get_app_access_url()

        # 生成访问令牌（仅用于需要认证的应用）
        access_token = None
        if app.require_auth:
            refresh = RefreshToken.for_user(request.user)
            access_token = str(refresh.access_token)

        # 构建返回数据
        response_data = {
            'code': 200,
            'message': '应用访问授权成功',
            'data': {
                'app_id': app.app_id,
                'app_name': app.app_name,
                'open_type': app.open_type,
                'access_info': app_access_info,
                'access_token': access_token,
                'user_info': {
                    'staff_id': request.user.staff_id,
                    'real_name': request.user.real_name or request.user.nickname or '员工用户',
                    'department': request.user.department or '未分配部门',
                    'position': request.user.position or '未分配职位',
                },
                'app_config': app.app_config or {}
            }
        }

        logger.info(f"应用访问授权成功 - 应用: {app.app_name}, 用户: {request.user.username}")
        return Response(response_data)


class EmployeeProfileView(APIView):
    """员工个人信息API视图"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        """获取员工信息"""
        # 检查是否是员工
        if not request.user.user_type in ['employee', 'admin']:
            return Response({
                'code': 403,
                'message': '只有员工可以访问此功能'
            }, status=status.HTTP_403_FORBIDDEN)

        user_serializer = EmployeeProfileWithTokenSerializer(request.user, context={'request': request})

        response_data = {
            'code': 200,
            'message': '获取员工信息成功',
            'data': {
                'user': user_serializer.data
            }
        }

        return Response(response_data)


class AdminCreateEmployeeView(APIView):
    """管理员创建员工账号API视图"""
    permission_classes = [permissions.IsAdminUser]

    @staticmethod
    def post(request):
        """创建员工账号"""
        serializer = EmployeeRegisterSerializer(data=request.data)

        if serializer.is_valid():
            try:
                user = serializer.save()
                user_serializer = UserSerializer(user, context={'request': request})

                return Response({
                    'code': 201,
                    'message': '员工账号创建成功',
                    'data': user_serializer.data
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                logger.error(f"创建员工账号异常: {str(e)}", exc_info=True)
                return Response({
                    'code': 500,
                    'message': '创建员工账号失败',
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'code': 400,
            'message': '参数错误',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class TokenRefreshView(SimpleJWTTokenRefreshView):
    """自定义Token刷新视图，返回格式与API一致"""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        # 重新包装响应格式
        if response.status_code == 200:
            return Response({
                'code': 200,
                'message': 'Token刷新成功',
                'data': response.data
            })
        else:
            return Response({
                'code': response.status_code,
                'message': 'Token刷新失败',
                'errors': response.data
            }, status=response.status_code)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def wechat_phone_login(request):
    """微信手机号一键登录"""
    from .utils import WeChatAPI

    code = request.data.get('code')

    if not code:
        return Response({
            'code': 400,
            'message': '请提供微信手机号授权code'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # 1. 获取微信 access_token
        access_token = WeChatAPI.get_access_token()
        if not access_token:
            return Response({
                'code': 500,
                'message': '微信服务异常，请稍后重试'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 2. 通过微信API获取手机号
        phone_info = WeChatAPI.get_user_phone_number(access_token, code)
        if not phone_info or not phone_info.get('phoneNumber'):
            logger.error(f"获取手机号失败: {phone_info}")
            return Response({
                'code': 400,
                'message': '获取手机号失败，请重新授权'
            }, status=status.HTTP_400_BAD_REQUEST)

        phone_number = phone_info.get('phoneNumber')
        pure_phone_number = phone_info.get('purePhoneNumber', phone_number)

        logger.info(f"获取到微信手机号: {phone_number}")

        # 3. 查找或创建用户
        user = User.objects.filter(
            phone=pure_phone_number,
            is_active=True
        ).first()

        if not user:
            # 创建新用户
            username = f'phone_{pure_phone_number}'
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f'phone_{pure_phone_number}_{counter}'
                counter += 1

            user = User.objects.create_user(
                username=username,
                phone=pure_phone_number,
                user_type='customer',
                is_phone_bound=True,
                last_login_time=timezone.now(),
                nickname=pure_phone_number
            )
            user.set_unusable_password()
            user.save()

        # 更新登录时间
        user.last_login_time = timezone.now()
        user.save(update_fields=['last_login_time'])

        # 4. 生成JWT token
        refresh = RefreshToken.for_user(user)
        user_serializer = UserProfileWithTokenSerializer(user)

        return Response({
            'code': 200,
            'message': '手机号登录成功',
            'data': user_serializer.data
        })

    except Exception as e:
        logger.error(f"微信手机号登录异常: {str(e)}", exc_info=True)
        return Response({
            'code': 500,
            'message': '登录异常，请稍后重试',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def phone_login(request):
    """手机号登录"""
    phone = request.data.get('phone')
    code = request.data.get('code')
    wechat_phone_code = request.data.get('wechat_phone_code')  # 新增参数

    # 判断是哪种登录方式
    if wechat_phone_code:
        # 微信手机号授权登录
        from .utils import WeChatAPI

        access_token = WeChatAPI.get_access_token()
        if not access_token:
            return Response({
                'code': 500,
                'message': '微信服务异常'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        phone_info = WeChatAPI.get_user_phone_number(access_token, wechat_phone_code)
        if not phone_info or not phone_info.get('phoneNumber'):
            return Response({
                'code': 400,
                'message': '获取手机号失败'
            }, status=status.HTTP_400_BAD_REQUEST)

        phone = phone_info.get('purePhoneNumber') or phone_info.get('phoneNumber')

    elif not phone or not code:
        return Response({
            'code': 400,
            'message': '请输入手机号和验证码'
        }, status=status.HTTP_400_BAD_REQUEST)

    # 验证短信验证码
    is_valid, error_msg = AccountManager.verify_phone_code(phone, code, 'login')
    if not is_valid:
        return Response({
            'code': 400,
            'message': f'验证码错误: {error_msg}'
        }, status=status.HTTP_400_BAD_REQUEST)

    # 查找或创建用户
    user = User.objects.filter(
        phone=phone,
        is_active=True
    ).first()

    if not user:
        # 创建新用户
        username = f'phone_{phone}'
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f'phone_{phone}_{counter}'
            counter += 1

        user = User.objects.create_user(
            username=username,
            phone=phone,
            user_type='customer',
            is_phone_bound=True,
            last_login_time=timezone.now(),
            nickname=phone
        )
        user.set_unusable_password()
        user.save()

    # 更新登录时间
    user.last_login_time = timezone.now()
    user.save(update_fields=['last_login_time'])

    refresh = RefreshToken.for_user(user)
    user_serializer = UserProfileWithTokenSerializer(user)

    return Response({
        'code': 200,
        'message': '登录成功',
        'data': user_serializer.data
    })


class EmployeeManagementView(APIView):
    """员工管理API视图"""
    permission_classes = [permissions.IsAdminUser]

    @staticmethod
    def get(request):
        """获取所有员工列表"""
        employees = User.objects.filter(
            user_type__in=['employee', 'admin'],
            is_active=True
        ).order_by('staff_id')

        serializer = UserSerializer(employees, many=True, context={'request': request})

        return Response({
            'code': 200,
            'message': '获取员工列表成功',
            'data': serializer.data
        })

    @staticmethod
    def patch(request, pk=None):
        """更新员工信息"""
        if pk:
            try:
                user = User.objects.get(id=pk, user_type__in=['employee', 'admin'])
            except User.DoesNotExist:
                return Response({
                    'code': 404,
                    'message': '员工不存在'
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = UserSerializer(user, data=request.data, partial=True, context={'request': request})

            if serializer.is_valid():
                serializer.save()

                return Response({
                    'code': 200,
                    'message': '更新员工信息成功',
                    'data': serializer.data
                })

            return Response({
                'code': 400,
                'message': '更新失败',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'code': 400,
            'message': '请提供员工ID'
        }, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def delete(request, pk):
        """删除员工账号（软删除）"""
        try:
            user = User.objects.get(id=pk, user_type__in=['employee', 'admin'])
            user.is_active = False
            user.save(update_fields=['is_active', 'updated_at'])

            return Response({
                'code': 200,
                'message': '员工账号已禁用'
            })
        except User.DoesNotExist:
            return Response({
                'code': 404,
                'message': '员工不存在'
            }, status=status.HTTP_404_NOT_FOUND)


class ResetPasswordView(APIView):
    """重置密码API视图"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def post(request):
        """重置密码"""
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not all([old_password, new_password, confirm_password]):
            return Response({
                'code': 400,
                'message': '请填写完整信息'
            }, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({
                'code': 400,
                'message': '两次输入的新密码不一致'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user

        # 验证旧密码
        if user.user_type == 'employee':
            # 员工账号支持默认密码
            if not user.check_employee_password(old_password):
                return Response({
                    'code': 400,
                    'message': '旧密码错误'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            # 普通用户必须验证密码
            if not user.check_password(old_password):
                return Response({
                    'code': 400,
                    'message': '旧密码错误'
                }, status=status.HTTP_400_BAD_REQUEST)

        # 设置新密码
        try:
            user.set_password(new_password)
            user.save(update_fields=['password', 'updated_at'])

            return Response({
                'code': 200,
                'message': '密码修改成功'
            })

        except Exception as e:
            logger.error(f"修改密码异常: {str(e)}", exc_info=True)
            return Response({
                'code': 500,
                'message': '密码修改失败',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ForgotPasswordView(APIView):
    """忘记密码API视图"""
    permission_classes = [permissions.AllowAny]

    @staticmethod
    def post(request):
        """忘记密码"""
        phone = request.data.get('phone')
        code = request.data.get('code')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not all([phone, code, new_password, confirm_password]):
            return Response({
                'code': 400,
                'message': '请填写完整信息'
            }, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({
                'code': 400,
                'message': '两次输入的新密码不一致'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 验证手机号
        phone_pattern = re.compile(r'^1[3-9]\d{9}$')
        if not phone_pattern.match(phone):
            return Response({
                'code': 400,
                'message': '请输入有效的手机号码'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 查找用户
        user = User.objects.filter(phone=phone, is_active=True).first()
        if not user:
            return Response({
                'code': 404,
                'message': '该手机号未注册'
            }, status=status.HTTP_404_NOT_FOUND)

        # 验证短信验证码
        is_valid, error_msg = AccountManager.verify_phone_code(phone, code, 'reset_password')
        if not is_valid:
            return Response({
                'code': 400,
                'message': f'验证码错误: {error_msg}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 重置密码
        try:
            user.set_password(new_password)
            user.save(update_fields=['password', 'updated_at'])

            return Response({
                'code': 200,
                'message': '密码重置成功'
            })

        except Exception as e:
            logger.error(f"重置密码异常: {str(e)}", exc_info=True)
            return Response({
                'code': 500,
                'message': '密码重置失败',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
