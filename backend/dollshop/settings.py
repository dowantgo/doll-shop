"""
Django settings for dollshop project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent
# Always prefer project-local .env over inherited process env values.
# This avoids stale/empty system env values shadowing valid local config.
load_dotenv(BASE_DIR / '.env', override=True)


def env_first(*keys, default=''):
    """Return the first non-empty env value from candidate keys."""
    for key in keys:
        val = os.getenv(key)
        if val is not None and str(val).strip() != '':
            return val
    return default

# Build paths inside the project like this: BASE_DIR / 'subdir'.

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'corsheaders',
    
    # Local apps
    'apps.users.apps.UsersConfig',
    'apps.products.apps.ProductsConfig',
    'apps.orders.apps.OrdersConfig',
    'apps.cart.apps.CartConfig',
    'apps.payment.apps.PaymentConfig',
    'apps.coupons.apps.CouponsConfig',
    'apps.refunds.apps.RefundsConfig',
    'apps.reviews.apps.ReviewsConfig',
    'apps.seckill.apps.SeckillConfig',
]

# Use custom user model
AUTH_USER_MODEL = 'users.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'dollshop.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'dollshop.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'shop'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'zw14785336002'),
        'HOST': os.getenv('DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE', '120')),
        'CONN_HEALTH_CHECKS': os.getenv('DB_CONN_HEALTH_CHECKS', 'True') == 'True',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'connect_timeout': int(os.getenv('DB_CONNECT_TIMEOUT', '5')),
        },
    }
}

# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Product feed cache settings (seconds)
PRODUCT_FEED_CACHE_NAMESPACE = os.getenv('PRODUCT_FEED_CACHE_NAMESPACE', 'products:feed')
PRODUCT_FEED_CACHE_TTL = int(os.getenv('PRODUCT_FEED_CACHE_TTL', '300'))
PRODUCT_TOP_SALES_CACHE_TTL = int(os.getenv('PRODUCT_TOP_SALES_CACHE_TTL', str(PRODUCT_FEED_CACHE_TTL)))
PRODUCT_HOT_FEED_CACHE_TTL = int(os.getenv('PRODUCT_HOT_FEED_CACHE_TTL', str(PRODUCT_FEED_CACHE_TTL)))
SECKILL_RESERVATION_EXPIRE_MINUTES = int(os.getenv('SECKILL_RESERVATION_EXPIRE_MINUTES', '10'))

# Order pricing rules
def parse_full_reduction_rules(raw: str):
    rules = []
    for token in (raw or '').split(','):
        pair = token.strip()
        if not pair:
            continue
        if ':' not in pair:
            continue
        threshold, reduction = pair.split(':', 1)
        try:
            rules.append((float(threshold), float(reduction)))
        except ValueError:
            continue
    if not rules:
        return [(200, 20), (500, 60)]
    return rules


ORDER_FULL_REDUCTION_RULES = parse_full_reduction_rules(
    os.getenv('ORDER_FULL_REDUCTION_RULES', '200:20,500:60')
)

# Review sensitive words configuration
REVIEW_SENSITIVE_WORDS = [
    word.strip()
    for word in os.getenv('REVIEW_SENSITIVE_WORDS', '傻逼,垃圾,妈的').split(',')
    if word.strip()
]

# Email configuration
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.qq.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '25'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'False') == 'True'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False') == 'True'
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'noreply@localhost')

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

# Simple JWT configuration
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

JWT_REFRESH_COOKIE_NAME = os.getenv('JWT_REFRESH_COOKIE_NAME', 'refresh_token')
JWT_REFRESH_COOKIE_SECURE = os.getenv('JWT_REFRESH_COOKIE_SECURE', 'False') == 'True'
JWT_REFRESH_COOKIE_SAMESITE = os.getenv('JWT_REFRESH_COOKIE_SAMESITE', 'Lax')
JWT_REFRESH_COOKIE_PATH = os.getenv('JWT_REFRESH_COOKIE_PATH', '/api/users/users/')

# CORS configuration
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:5174',
    'http://127.0.0.1:5174',
    'http://localhost:5175',
    'http://127.0.0.1:5175',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
CORS_ALLOW_CREDENTIALS = True

# drf-spectacular configuration
SPECTACULAR_SETTINGS = {
    'TITLE': '玩偶商城 API',
    'DESCRIPTION': '玩偶商城 RESTful API 文档',
    'VERSION': '1.0.0',
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorizationData': True,
        'displayOperationId': True,
    },
}

# Payment configuration
PAYMENT_CONFIG = {
    'ALIPAY': {
        # Compatible keys: ALIPAY_APP_ID (preferred), ALIPAY_APPID (legacy)
        'APPID': env_first('ALIPAY_APP_ID', 'ALIPAY_APPID', default=''),
        'PRIVATE_KEY': env_first('ALIPAY_PRIVATE_KEY', default=''),
        'PUBLIC_KEY': env_first('ALIPAY_PUBLIC_KEY', default=''),
        'NOTIFY_URL': os.getenv('ALIPAY_NOTIFY_URL', 'http://localhost:8000/api/pay/notify/alipay/'),
        'RETURN_URL': os.getenv('ALIPAY_RETURN_URL', 'http://localhost:5173/orders'),
        'DEBUG': os.getenv('ALIPAY_DEBUG', 'True') == 'True',
    },
    'WECHAT': {
        'APPID': env_first('WECHAT_APP_ID', 'WECHAT_APPID', default=''),
        'MCH_ID': os.getenv('WECHAT_MCH_ID', ''),
        'API_KEY': os.getenv('WECHAT_API_KEY', ''),
        'NOTIFY_URL': os.getenv('WECHAT_NOTIFY_URL', 'http://localhost:8000/api/pay/notify/wechat/'),
        'DEBUG': os.getenv('WECHAT_DEBUG', 'True') == 'True',
    },
    'MOCK': {
        'ENABLED': os.getenv('MOCK_PAYMENT_ENABLED', 'True') == 'True',
    },
    'EXPIRE_MINUTES': int(os.getenv('PAYMENT_EXPIRE_MINUTES', '30')),
}

# Logistics provider configuration
LOGISTICS_PROVIDER = os.getenv('LOGISTICS_PROVIDER', 'mock')
KUAIDI100_API_KEY = os.getenv('KUAIDI100_API_KEY', '')
KUAIDI100_CUSTOMER = os.getenv('KUAIDI100_CUSTOMER', '')

# Celery configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0'))
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', CELERY_BROKER_URL)
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    'payment-reconcile-pending-every-15-min': {
        'task': 'payment.reconcile_pending',
        'schedule': crontab(minute='*/15'),
    },
    'order-cleanup-expired-every-minute': {
        'task': 'orders.cleanup_expired_orders',
        'schedule': crontab(minute='*/1'),
    },
    'seckill-cleanup-expired-every-minute': {
        'task': 'seckill.cleanup_expired_reservations',
        'schedule': crontab(minute='*/1'),
    },
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'debug.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'DEBUG',
    },
}
