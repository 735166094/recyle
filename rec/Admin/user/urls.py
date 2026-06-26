# user/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # 用户个人信息
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),

    # 统一登录
    path('login/', views.UnifiedLoginView.as_view(), name='user_login'),

    # 微信登录
    path('wechat_login/', views.wechat_login, name='wechat_login'),
    path('wechat_phone_login/', views.wechat_phone_login, name='wechat_phone_login'),

    # 员工登录
    path('employee/login/', views.EmployeeLoginView.as_view(), name='employee_login'),
    path('employee/logout/', views.EmployeeLogoutView.as_view(), name='employee_logout'),

    # 用户注册和退出
    path('register/', views.customer_register, name='customer_register'),
    path('logout/', views.user_logout, name='user_logout'),

    # 手机号绑定
    path('bind_phone/', views.BindPhoneView.as_view(), name='bind_phone'),

    # 短信验证码
    path('send_sms/', views.SendSMSView.as_view(), name='send_sms'),

    # 密码管理
    path('change_password/', views.UserPasswordChangeView.as_view(), name='change_password'),
    path('forgot_password/', views.ForgotPasswordView.as_view(), name='forgot_password'),

    # JWT Token刷新
    path('token/refresh/', views.TokenRefreshView.as_view(), name='token_refresh'),

    # 员工相关
    path('employee/profile/', views.EmployeeProfileView.as_view(), name='employee_profile'),
    path('employee/apps/', views.EmployeeAppsView.as_view(), name='employee_apps'),
    path('employee/access_app/', views.EmployeeAccessAppView.as_view(), name='employee_access_app'),
    path('employee/manage/', views.EmployeeManagementView.as_view(), name='employee_manage'),
    path('employee/manage/<int:pk>/', views.EmployeeManagementView.as_view(), name='employee_manage_detail'),

    # 管理员创建员工账号
    path('admin/create_employee/', views.AdminCreateEmployeeView.as_view(), name='admin_create_employee'),

    # 用户积分
    path('points/', views.UserPointsRedirectView.as_view(), name='user_points_redirect'),

    # 用户地址管理
    path('addresses/', views.UserAddressView.as_view(), name='user_addresses'),
    path('addresses/<int:pk>/', views.UserAddressDetailView.as_view(), name='user_address_detail'),
    path('addresses/<int:pk>/set_default/', views.SetDefaultAddressView.as_view(), name='set_default_address'),

    # 用户收藏
    path('favorites/', views.UserFavoriteListView.as_view(), name='user_favorites'),
    path('favorites/create/', views.UserFavoriteCreateView.as_view(), name='user_favorite_create'),
    path('favorites/<int:pk>/', views.UserFavoriteDetailView.as_view(), name='user_favorite_detail'),

    # 用户优惠券管理
    path('coupons/', views.UserCouponListView.as_view(), name='user_coupons'),
    path('coupons/<int:pk>/', views.UserCouponDetailView.as_view(), name='user_coupon_detail'),
]
