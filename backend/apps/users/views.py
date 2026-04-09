from django.contrib.auth import authenticate
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .captcha_utils import create_captcha, send_email_code as send_email_code_util, verify_captcha, verify_email_code
from .models import Address, User
from .serializers import AddressSerializer, UserRegisterSerializer, UserSerializer


class UserViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """User management viewset - only allow retrieve and update"""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['register', 'login', 'captcha', 'send_email_code', 'forgot_password']:
            return [AllowAny()]
        return super().get_permissions()

    @action(detail=False, methods=['post'])
    def register(self, request):
        """User registration with captcha and email verification"""
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
        """User login with captcha"""
        captcha_id = request.data.get('captcha_id')
        captcha_code = request.data.get('captcha_code')
        if not verify_captcha(captcha_id, captcha_code):
            return Response({'error': '图片验证码错误或已过期'}, status=status.HTTP_400_BAD_REQUEST)

        username_or_email = request.data.get('username')
        password = request.data.get('password')
        if not username_or_email or not password:
            return Response({'error': '用户名和密码必填'}, status=status.HTTP_400_BAD_REQUEST)

        username_for_auth = username_or_email
        if '@' in username_or_email:
            user_by_email = User.objects.filter(email__iexact=username_or_email).first()
            if user_by_email:
                username_for_auth = user_by_email.username

        user = authenticate(username=username_for_auth, password=password)
        if not user:
            return Response({'error': '用户名或密码错误'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'token': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                },
            }
        )

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def captcha(self, request):
        """Get captcha image"""
        return Response(create_captcha())

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def send_email_code(self, request):
        """Send email verification code"""
        email = request.data.get('email')
        code_type = request.data.get('type', 'register')

        if not email:
            return Response({'error': '邮箱不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        if code_type == 'register' and User.objects.filter(email=email).exists():
            return Response({'error': '该邮箱已注册'}, status=status.HTTP_400_BAD_REQUEST)

        result = send_email_code_util(email, code_type)
        ok = result.get('ok', False)
        error = result.get('error') or ''

        if ok:
            return Response({'message': '验证码已发送，请注意查收邮箱'})

        return Response(
            {'error': f'验证码发送失败，请检查邮箱SMTP配置。{error}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def forgot_password(self, request):
        """Forgot password - reset with email verification"""
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

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Get current authenticated user info."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class AddressViewSet(viewsets.ModelViewSet):
    """Address management viewset"""

    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

