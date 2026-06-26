import os
import sys
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "spyk6$5jt#t-^&6_s*5kgy+usl(7(fzp)&mcw!&%#xsqyw86-k"

# DEBUG = True
DEBUG = False


SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = False

# ALLOWED_HOSTS = ['*']  # 允许所有主机访问，实际部署时应限制为特定域名或IP

# 只允许你的域名 + 公网/内网IP
ALLOWED_HOSTS = [
    "qiqi.cheryapp.com",
    "127.0.0.1",
    "localhost"
]
# 添加 CSRF 信任域名
CSRF_TRUSTED_ORIGINS = [
    "https://qiqi.cheryapp.com"
]

# simpleUI跳转改成域名
SIMPLEUI_INDEX = 'https://qiqi.cheryapp.com'

INSTALLED_APPS = [
    'simpleui',
    "django.contrib.admin",
   # "multi_captcha_admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'rest_framework',
    'rest_framework.authtoken',
    'django.contrib.humanize',
    'django_filters',
    "sslserver",
    'corsheaders',
    'user.apps.UserConfig',
    'news.apps.NewsConfig',
    'mall.apps.MallConfig',
    'recycle.apps.RecycleConfig',
    'vin.apps.VinConfig',
    'ocr.apps.OcrConfig',
    'points.apps.PointsConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# 验证码配置
MULTI_CAPTCHA_ADMIN = {
    'engine': 'simple-captcha',
}

# 自定义用户模型
AUTH_USER_MODEL = 'user.User'

# simpleUi配置
SIMPLEUI_LOGO = '/media/logo.png'  # 替换logo路径

# 隐藏右侧SimpleUI广告链接和使用分析
SIMPLEUI_HOME_INFO = False
# SIMPLEUI_ANALYSIS = False

# 设置simpleui 点击首页图标跳转的地址
SIMPLEUI_INDEX = 'http://127.0.0.1:8000/admin/'
# BACKEND_URL = 'https://www.cheryapp.com'

# CORS配置（小程序需要）
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

ROOT_URLCONF = "recycle_admin.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
         'DIRS': [
            os.path.join(BASE_DIR, 'templates'),  # 确保这一行存在
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "recycle_admin.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# MySQL配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'recycle_db',  # 数据库名
        'USER': 'root',  # 用户名
        'PASSWORD': '111@Chery',  # 数据库密码
        'HOST': '127.0.0.1',  # 主机地址
        'PORT': '3306',  # 端口
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        'CONN_MAX_AGE': 300,  # 连接池
    }
}

# Redis配置
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,
                'retry_on_timeout': True
            },
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'SOCKET_CONNECT_TIMEOUT': 5,  # 连接超时
            'SOCKET_TIMEOUT': 5,  # 读写超时
        },
        'KEY_PREFIX': ['recycle_admin', 'cherry_points', ],

        'TIMEOUT': 60 * 60 * 24,  # 1天
    }
}

REDIS_LOCK_CONFIG = {
    'LOCK_TIMEOUT': 10,  # 锁超时时间（秒）
    'LOCK_RETRY': 3,  # 重试次数
    'LOCK_RETRY_DELAY': 0.1,  # 重试延迟（秒）
}

# 配置Session使用Redis存储
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Celery配置（用于异步任务）
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# 开启media访问
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')  # 这个是图片上传后，放到 media 文件夹中，必须是 BASE_DIR(根目录) 下的一个文件夹

# 静态文件配置
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# REST Framework配置
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # 根据实际需求调整权限
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # JWT认证，作用是让每个请求都带上用户信息
        "rest_framework.authentication.SessionAuthentication",  # 支持session认证
        "rest_framework.authentication.TokenAuthentication",  # 支持Token认证

    ],

    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',  # 分页类
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ) if not DEBUG else (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '1000/day',
        'anon': '100/day',
        'login': '5/hour',
        'wechat_login': '10/minute'
    },

    # 异常处理
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',

}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',

    'JTI_CLAIM': 'jti',

    # 自定义token响应数据
    'TOKEN_OBTAIN_SERIALIZER': 'user.serializers.UserProfileWithTokenSerializer',
}

# 微信小程序配置
WECHAT_APPID = 'wx4ce25a8caecc6505'  # AppID
WECHAT_SECRET = '5bff3eda26180f2a53f03ff19c93a394'  # AppSecret
# WECHAT_LOGIN_URL = 'https://api.weixin.qq.com/sns/jscode2session'
WECHAT_ACCESS_TOKEN_URL = 'https://api.weixin.qq.com/cgi-bin/token'
WECHAT_PHONE_NUMBER_URL = 'https://api.weixin.qq.com/wxa/business/getuserphonenumber'

# 小程序配置
MINI_PROGRAM = {
    'APP_NAME': '奇奇回收',
    'VERSION': '1.0.0',
    'DESCRIPTION': '环保回收，变废为宝',
}


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',          # 只输出 INFO 及以上级别
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',           # 全局最低级别为 WARNING，过滤大量 DEBUG/INFO
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',       # Django 核心只输出警告和错误
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',       # 请求日志只输出警告（如 4xx/5xx）
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',       # 安全相关只输出警告
        },
        # app 的 INFO 日志，便于调试
        # 'user': {
        #     'handlers': ['console'],
        #     'level': 'INFO',
        #     'propagate': False,
        # },
        # 'ocr': {
        #     'handlers': ['console'],
        #     'level': 'INFO',
        #     'propagate': False,
        # },
    },
}