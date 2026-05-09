import logging

from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from dollshop.metrics import metric_increment

from .captcha_utils import create_captcha, send_email_code as send_email_code_util, verify_captcha, verify_email_code
from .models import Address, User
from .security import (
    check_captcha_rate_limit,
    check_email_send_limits,
    clear_login_failures,
    get_client_ip,
    get_login_lock_status,
    record_email_send_success,
    record_login_failure,
)
from .serializers import AddressSerializer, UserRegisterSerializer, UserSerializer

logger = logging.getLogger(__name__)


def _set_refresh_cookie(response, refresh_token: str) -> None:
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        refresh_token,
        httponly=True,
        secure=settings.JWT_REFRESH_COOKIE_SECURE,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
        path=settings.JWT_REFRESH_COOKIE_PATH,
        max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
    )


def _clear_refresh_cookie(response) -> None:
    response.delete_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        path=settings.JWT_REFRESH_COOKIE_PATH,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
    )


class UserViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """User management viewset - only allow retrieve and update"""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self.request.user, 'role', '') == 'admin':
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

    def get_permissions(self):
        if self.action in [
            'register',
            'login',
            'captcha',
            'send_email_code',
            'forgot_password',
            'refresh_token',
            'logout',
        ]:
            return [AllowAny()]
        return super().get_permissions()

    @action(detail=False, methods=['post'])
    def register(self, request):
        captcha_id = request.data.get('captcha_id')
        captcha_code = request.data.get('captcha_code')
        if not verify_captcha(captcha_id, captcha_code):
            return Response({'error': '图片验证码错误或已过期'}, status=status.HTTP_400_BAD_REQUEST)

        email = request.data.get('email')
        email_code = request.data.get('email_code')
        if not email or not email_code:
            return Response({'error': '邮箱和邮箱验证码必填'}, status=status.HTTP_400_BAD_REQUEST)

        if not verify_email_code(email, email_code, 'register'):
            return Response({'error': '邮箱验证码错误或已过期'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': '注册成功'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def login(self, request):
        ip = get_client_ip(request)
        username_or_email = request.data.get('username')
        password = request.data.get('password')
        if not username_or_email or not password:
            return Response({'error': '用户名和密码必填'}, status=status.HTTP_400_BAD_REQUEST)

        locked, remaining_seconds = get_login_lock_status(username_or_email, ip)
        if locked:
            logger.warning('login_rejected_locked identifier=%s ip=%s remaining_seconds=%s', username_or_email, ip, remaining_seconds)
            return Response({'error': f'登录失败次数过多，请 {remaining_seconds} 秒后再试。'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        captcha_id = request.data.get('captcha_id')
        captcha_code = request.data.get('captcha_code')
        if not verify_captcha(captcha_id, captcha_code):
            return Response({'error': '图片验证码错误或已过期'}, status=status.HTTP_400_BAD_REQUEST)

        username_for_auth = username_or_email
        if '@' in username_or_email:
            user_by_email = User.objects.filter(email__iexact=username_or_email).first()
            if user_by_email:
                username_for_auth = user_by_email.username

        user = authenticate(username=username_for_auth, password=password)
        if not user:
            just_locked, value = record_login_failure(username_or_email, ip)
            if just_locked:
                return Response({'error': f'登录失败次数过多，请 {value} 秒后再试。'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            return Response({'error': '用户名或密码错误'}, status=status.HTTP_401_UNAUTHORIZED)

        clear_login_failures(username_or_email, ip)
        refresh = RefreshToken.for_user(user)
        response = Response(
            {
                'token': str(refresh.access_token),
                'access_token': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                },
            }
        )
        _set_refresh_cookie(response, str(refresh))
        metric_increment('login_success')
        return response

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def captcha(self, request):
        ip = get_client_ip(request)
        allowed, _count = check_captcha_rate_limit(ip)
        if not allowed:
            logger.warning('captcha_rate_limited ip=%s', ip)
            return Response({'error': '验证码请求过于频繁，请稍后再试。'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        metric_increment('captcha_request')
        return Response(create_captcha())

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def send_email_code(self, request):
        email = request.data.get('email')
        code_type = request.data.get('type', 'register')
        ip = get_client_ip(request)

        if not email:
            return Response({'error': '邮箱不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        if code_type == 'register' and User.objects.filter(email=email).exists():
            return Response({'error': '该邮箱已注册'}, status=status.HTTP_400_BAD_REQUEST)

        allowed, reason, value = check_email_send_limits(email, ip)
        if not allowed:
            logger.warning('email_code_rate_limited email=%s ip=%s reason=%s value=%s', email, ip, reason, value)
            if reason == 'cooldown':
                return Response({'error': f'验证码发送过于频繁，请 {value} 秒后再试。'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            return Response({'error': '验证码发送次数已达上限，请稍后再试。'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        result = send_email_code_util(email, code_type)
        ok = result.get('ok', False)
        error = result.get('error') or ''

        if ok:
            record_email_send_success(email)
            metric_increment('email_code_sent', type=code_type)
            return Response({'message': '验证码已发送，请注意查收邮箱'})

        return Response({'error': f'验证码发送失败，请检查邮箱SMTP配置。{error}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def forgot_password(self, request):
        email = request.data.get('email')
        email_code = request.data.get('email_code')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not all([email, email_code, new_password, confirm_password]):
            return Response({'error': '所有字段必填'}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({'error': '两次输入的密码不一致'}, status=status.HTTP_400_BAD_REQUEST)

        if not verify_email_code(email, email_code, 'forgot'):
            return Response({'error': '验证码错误或已过期'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': '该邮箱未注册'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({'message': '密码重置成功'})

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], url_path='refresh-token')
    def refresh_token(self, request):
        raw_refresh_token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME, '')
        if not raw_refresh_token:
            return Response({'error': 'Refresh token missing.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            refresh = RefreshToken(raw_refresh_token)
            user = User.objects.get(id=refresh['user_id'])
            new_refresh = RefreshToken.for_user(user)
        except (TokenError, User.DoesNotExist, KeyError):
            response = Response({'error': 'Refresh token invalid.'}, status=status.HTTP_401_UNAUTHORIZED)
            _clear_refresh_cookie(response)
            return response

        response = Response({'token': str(new_refresh.access_token), 'access_token': str(new_refresh.access_token)})
        _set_refresh_cookie(response, str(new_refresh))
        metric_increment('refresh_token_success')
        return response

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], url_path='logout')
    def logout(self, request):
        response = Response({'message': '已退出登录'})
        _clear_refresh_cookie(response)
        metric_increment('logout_called')
        return response

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
