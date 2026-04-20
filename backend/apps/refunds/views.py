from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import RefundAuditLog, RefundRequest
from .serializers import (
    RefundCreateSerializer,
    RefundRequestSerializer,
    RefundReviewSerializer,
    validate_refund_request,
)


class IsAdminUser(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'admin'


def _create_audit_log(refund: RefundRequest, operator, action: str, note: str, before_data: dict, after_data: dict):
    RefundAuditLog.objects.create(
        refund=refund,
        operator=operator,
        action=action,
        note=note or '',
        before_data=before_data or {},
        after_data=after_data or {},
    )


class RefundViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = RefundRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = (
            RefundRequest.objects.select_related('order', 'order_item', 'order_item__product')
            .filter(user=self.request.user)
            .order_by('-id')
        )
        order_id = self.request.query_params.get('order_id')
        if order_id:
            queryset = queryset.filter(order__order_id=order_id)
        return queryset

    def create(self, request):
        serializer = RefundCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data['order_id']
        order_item_id = serializer.validated_data['order_item_id']
        quantity = serializer.validated_data['quantity']
        reason = serializer.validated_data.get('reason', '')
        idempotency_key = serializer.validated_data.get('idempotency_key', '').strip()

        if idempotency_key:
            exists = RefundRequest.objects.filter(user=request.user, idempotency_key=idempotency_key).first()
            if exists:
                return Response(RefundRequestSerializer(exists).data)

        order, order_item, requested_amount = validate_refund_request(
            user=request.user,
            order_id=order_id,
            order_item_id=order_item_id,
            quantity=quantity,
        )

        refund = RefundRequest.objects.create(
            user=request.user,
            order=order,
            order_item=order_item,
            quantity=quantity,
            reason=reason,
            requested_amount=requested_amount,
            approved_amount=requested_amount,
            status=RefundRequest.STATUS_PENDING,
            idempotency_key=idempotency_key,
        )
        _create_audit_log(
            refund=refund,
            operator=request.user,
            action='create',
            note=reason,
            before_data={},
            after_data={
                'status': refund.status,
                'quantity': refund.quantity,
                'requested_amount': str(refund.requested_amount),
            },
        )
        return Response(RefundRequestSerializer(refund).data, status=status.HTTP_201_CREATED)


class AdminRefundViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = RefundRequestSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = RefundRequest.objects.select_related('user', 'order', 'order_item', 'order_item__product').order_by('-id')
        status_param = self.request.query_params.get('status')
        order_id = self.request.query_params.get('order_id')
        refund_no = self.request.query_params.get('refund_no')
        if status_param:
            queryset = queryset.filter(status=status_param)
        if order_id:
            queryset = queryset.filter(order__order_id__icontains=order_id)
        if refund_no:
            queryset = queryset.filter(refund_no__icontains=refund_no)
        return queryset

    @action(detail=True, methods=['patch'])
    def review(self, request, pk=None):
        serializer = RefundReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action_type = serializer.validated_data['action']
        note = serializer.validated_data.get('note', '')

        with transaction.atomic():
            refund = RefundRequest.objects.select_for_update().select_related('order').get(pk=pk)
            if refund.status != RefundRequest.STATUS_PENDING:
                return Response({'error': 'Refund request is not in pending state.'}, status=status.HTTP_400_BAD_REQUEST)

            before_data = {
                'status': refund.status,
                'approved_amount': str(refund.approved_amount),
            }
            refund.reviewed_by = request.user
            refund.reviewed_at = timezone.now()
            refund.review_note = note

            if action_type == 'reject':
                refund.status = RefundRequest.STATUS_REJECTED
                refund.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_note', 'updated_at'])
                _create_audit_log(
                    refund=refund,
                    operator=request.user,
                    action='reject',
                    note=note,
                    before_data=before_data,
                    after_data={'status': refund.status},
                )
                return Response(RefundRequestSerializer(refund).data)

            refund.status = RefundRequest.STATUS_APPROVED
            refund.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_note', 'updated_at'])

            # Current stage: execute refund synchronously with a mock-safe path.
            refund.status = RefundRequest.STATUS_REFUNDING
            refund.save(update_fields=['status', 'updated_at'])

            try:
                refund.status = RefundRequest.STATUS_SUCCESS
                refund.processed_at = timezone.now()
                refund.save(update_fields=['status', 'processed_at', 'updated_at'])
            except Exception as exc:
                refund.status = RefundRequest.STATUS_FAILED
                refund.last_error = str(exc)
                refund.save(update_fields=['status', 'last_error', 'updated_at'])

            _create_audit_log(
                refund=refund,
                operator=request.user,
                action='approve',
                note=note,
                before_data=before_data,
                after_data={
                    'status': refund.status,
                    'processed_at': refund.processed_at.isoformat() if refund.processed_at else '',
                },
            )

        return Response(RefundRequestSerializer(refund).data)
