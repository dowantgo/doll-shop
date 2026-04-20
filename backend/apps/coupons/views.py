from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import CouponTemplate, UserCoupon
from .serializers import (
    AdminIssueCouponSerializer,
    ClaimCouponSerializer,
    CouponTemplateSerializer,
    UserCouponSerializer,
)

User = get_user_model()


class IsAdminUser(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'admin'


class CouponTemplateViewSet(viewsets.ModelViewSet):
    queryset = CouponTemplate.objects.all().order_by('-id')
    serializer_class = CouponTemplateSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class MyCouponViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = UserCouponSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = UserCoupon.objects.select_related('template').filter(user=self.request.user).order_by('-id')
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset


class ClaimCouponViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def create(self, request):
        serializer = ClaimCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template_id = serializer.validated_data['template_id']

        try:
            template = CouponTemplate.objects.select_for_update().get(id=template_id)
        except CouponTemplate.DoesNotExist:
            return Response({'error': 'Coupon template not found.'}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        if template.status != CouponTemplate.STATUS_ACTIVE:
            return Response({'error': 'Coupon template is inactive.'}, status=status.HTTP_400_BAD_REQUEST)
        if not (template.valid_from <= now <= template.valid_to):
            return Response({'error': 'Coupon template is not in valid time.'}, status=status.HTTP_400_BAD_REQUEST)
        if template.total_quota and template.claimed_count >= template.total_quota:
            return Response({'error': 'Coupon template is out of stock.'}, status=status.HTTP_400_BAD_REQUEST)

        user_claimed = UserCoupon.objects.filter(user=request.user, template=template).count()
        if user_claimed >= template.per_user_limit:
            return Response({'error': 'You have reached per-user claim limit.'}, status=status.HTTP_400_BAD_REQUEST)

        user_coupon = UserCoupon.objects.create(
            user=request.user,
            template=template,
            status=UserCoupon.STATUS_UNUSED,
        )
        template.claimed_count += 1
        template.save(update_fields=['claimed_count', 'updated_at'])
        return Response(UserCouponSerializer(user_coupon).data, status=status.HTTP_201_CREATED)


class AdminIssueCouponViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def create(self, request):
        serializer = AdminIssueCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template_id = serializer.validated_data['template_id']

        try:
            template = CouponTemplate.objects.select_for_update().get(id=template_id)
        except CouponTemplate.DoesNotExist:
            return Response({'error': 'Coupon template not found.'}, status=status.HTTP_404_NOT_FOUND)

        target_ids = set(serializer.validated_data.get('user_ids') or [])
        if serializer.validated_data.get('user_id'):
            target_ids.add(serializer.validated_data['user_id'])
        users = list(User.objects.filter(id__in=target_ids, role='user', is_active=True))
        if not users:
            return Response({'error': 'No valid target users found.'}, status=status.HTTP_400_BAD_REQUEST)

        if template.total_quota:
            remain = max(template.total_quota - template.claimed_count, 0)
            if remain <= 0:
                return Response({'error': 'Coupon template is out of stock.'}, status=status.HTTP_400_BAD_REQUEST)
            users = users[:remain]

        created = []
        skipped = 0
        now = timezone.now()
        for user in users:
            if UserCoupon.objects.filter(user=user, template=template).count() >= template.per_user_limit:
                skipped += 1
                continue
            created.append(
                UserCoupon(
                    user=user,
                    template=template,
                    status=UserCoupon.STATUS_UNUSED,
                    claimed_at=now,
                )
            )

        if not created:
            return Response({'error': 'All target users reached per-user limit.'}, status=status.HTTP_400_BAD_REQUEST)

        UserCoupon.objects.bulk_create(created)
        template.claimed_count += len(created)
        template.save(update_fields=['claimed_count', 'updated_at'])

        return Response(
            {
                'issued_count': len(created),
                'skipped_count': skipped,
                'template_id': template.id,
            }
        )
