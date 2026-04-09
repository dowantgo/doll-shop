import base64
import io
import logging
import secrets
from datetime import timedelta

import qrcode
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.views import View
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order

from .models import PaymentTransaction
from .serializers import CreatePaymentSerializer
from .services.alipay import alipay_service
from .services.errors import (
    PaymentConfigurationError,
    PaymentError,
    PaymentNetworkError,
    PaymentSignatureError,
)

logger = logging.getLogger(__name__)


def _gen_out_trade_no() -> str:
    return f"PAY{timezone.now().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(4).upper()}"


def _generate_qr_code_image(qr_url: str) -> str:
    """生成二维码图片的 Base64 Data URL。"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")

        base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{base64_data}"
    except Exception as exc:
        logger.error("生成二维码图片失败: %s", exc)
        return ""


@transaction.atomic
def _mark_paid(txn: PaymentTransaction, trade_no: str = "") -> None:
    # 在事务内重新加锁读取，避免并发重复更新
    txn = PaymentTransaction.objects.select_for_update().select_related("order").get(pk=txn.pk)

    now = timezone.now()
    txn_changed = False
    if txn.status != "paid":
        txn.status = "paid"
        txn.paid_time = now
        txn_changed = True
    if trade_no and txn.trade_no != trade_no:
        txn.trade_no = trade_no
        txn_changed = True
    if txn_changed:
        txn.save(update_fields=["status", "paid_time", "trade_no", "updated_at"])

    order = txn.order
    order_changed = False
    if order.payment_status != "paid":
        order.payment_status = "paid"
        order_changed = True
    if order.status == "pending":
        order.status = "paid"
        order_changed = True
    if not order.payment_method:
        order.payment_method = txn.payment_method
        order_changed = True
    if not order.paid_at:
        order.paid_at = now
        order_changed = True
    if trade_no and not order.trade_no:
        order.trade_no = trade_no
        order_changed = True
    if order_changed:
        order.save()


class CreatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data["order_id"]
        payment_method = serializer.validated_data["payment_method"]

        with transaction.atomic():
            try:
                order = Order.objects.select_for_update().get(order_id=order_id, user=request.user)
            except Order.DoesNotExist:
                return Response({"error": "订单不存在"}, status=status.HTTP_404_NOT_FOUND)

            if order.payment_status == "paid":
                return Response({"error": "订单已支付"}, status=status.HTTP_400_BAD_REQUEST)

            txn = (
                PaymentTransaction.objects.select_for_update()
                .filter(order=order, status="pending")
                .order_by("-created_at")
                .first()
            )
            if not txn:
                txn = PaymentTransaction.objects.create(
                    order=order,
                    payment_method=payment_method,
                    out_trade_no=_gen_out_trade_no(),
                    amount=order.total_price,
                    status="pending",
                    expire_time=timezone.now() + timedelta(minutes=15),
                )
            else:
                txn.payment_method = payment_method
                txn.amount = order.total_price
                txn.expire_time = timezone.now() + timedelta(minutes=15)
                txn.save(update_fields=["payment_method", "amount", "expire_time", "updated_at"])

        try:
            qr_code = ""
            expire_time = txn.expire_time.isoformat() if txn.expire_time else ""

            if payment_method == "alipay":
                result = alipay_service.create_qr_code(
                    out_trade_no=txn.out_trade_no,
                    total_amount=float(txn.amount),
                    subject=f"玩偶商城-{order.order_id}",
                )
                qr_code = result.get("qr_code", "")
                expire_time = result.get("expire_time", expire_time)
            else:
                qr_code = f"mock://pay/{txn.out_trade_no}"

            txn.qr_code = qr_code
            txn.save(update_fields=["qr_code", "updated_at"])

            qr_code_image = _generate_qr_code_image(qr_code)

            return Response(
                {
                    "payment_id": txn.out_trade_no,
                    "qr_code": qr_code,
                    "qr_code_image": qr_code_image,
                    "expire_time": expire_time,
                    "payment_method": payment_method,
                }
            )
        except (PaymentConfigurationError, PaymentNetworkError, PaymentSignatureError) as exc:
            logger.warning("Create payment failed: %s", exc)
            return Response({"error": f"创建支付失败: {exc}"}, status=status.HTTP_400_BAD_REQUEST)
        except PaymentError as exc:
            logger.exception("Create payment error: %s", exc)
            return Response({"error": f"创建支付失败: {exc}"}, status=status.HTTP_400_BAD_REQUEST)


class PaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, out_trade_no):
        try:
            txn = PaymentTransaction.objects.select_related("order").get(
                out_trade_no=out_trade_no,
                order__user=request.user,
            )
        except PaymentTransaction.DoesNotExist:
            return Response({"error": "支付单不存在"}, status=status.HTTP_404_NOT_FOUND)

        if txn.status == "pending" and txn.expire_time and timezone.now() > txn.expire_time:
            txn.status = "closed"
            txn.save(update_fields=["status", "updated_at"])

        if txn.status == "pending" and txn.payment_method == "alipay":
            try:
                query = alipay_service.query_order(txn.out_trade_no)
                trade_status = query.get("trade_status")
                if trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED"):
                    _mark_paid(txn, query.get("trade_no", ""))
                    txn.refresh_from_db()
                elif trade_status == "TRADE_CLOSED" and txn.status != "paid":
                    txn.status = "closed"
                    txn.save(update_fields=["status", "updated_at"])
            except PaymentError:
                pass

        status_map = {
            "paid": "success",
            "failed": "failed",
            "closed": "closed",
            "expired": "closed",
            "pending": "pending",
        }

        return Response(
            {
                "payment_id": txn.out_trade_no,
                "status": status_map.get(txn.status, "pending"),
                "trade_no": txn.trade_no or "",
            }
        )


class MockPayView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, out_trade_no):
        try:
            txn = PaymentTransaction.objects.select_related("order").get(
                out_trade_no=out_trade_no,
                order__user=request.user,
            )
        except PaymentTransaction.DoesNotExist:
            return Response({"error": "支付单不存在"}, status=status.HTTP_404_NOT_FOUND)

        if txn.status == "paid":
            return Response({"message": "已支付"})
        if txn.status in ("closed", "expired", "failed"):
            return Response({"error": "支付单已关闭或失效"}, status=status.HTTP_400_BAD_REQUEST)

        _mark_paid(txn)
        return Response({"message": "支付成功", "status": "success"})


class ClosePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, out_trade_no):
        try:
            txn = PaymentTransaction.objects.select_related("order").get(
                out_trade_no=out_trade_no,
                order__user=request.user,
            )
        except PaymentTransaction.DoesNotExist:
            return Response({"error": "支付单不存在"}, status=status.HTTP_404_NOT_FOUND)

        if txn.status == "paid":
            return Response({"error": "已支付订单不能关闭"}, status=status.HTTP_400_BAD_REQUEST)

        txn.status = "closed"
        txn.save(update_fields=["status", "updated_at"])
        return Response({"message": "支付单已关闭", "status": "closed"})


class PaymentQueryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        out_trade_no = request.query_params.get("out_trade_no", "").strip()
        if not out_trade_no:
            return Response({"error": "out_trade_no 必填"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            txn = PaymentTransaction.objects.select_related("order").get(
                out_trade_no=out_trade_no,
                order__user=request.user,
            )
        except PaymentTransaction.DoesNotExist:
            return Response({"error": "支付单不存在"}, status=status.HTTP_404_NOT_FOUND)

        alipay_info = {}
        if txn.payment_method == "alipay":
            try:
                alipay_info = alipay_service.query_order(out_trade_no)
                trade_status = alipay_info.get("trade_status")
                if trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED"):
                    _mark_paid(txn, alipay_info.get("trade_no", ""))
                    txn.refresh_from_db()
            except PaymentError as exc:
                alipay_info = {"error": str(exc)}

        return Response(
            {
                "payment_id": txn.out_trade_no,
                "status": txn.status,
                "trade_no": txn.trade_no,
                "amount": str(txn.amount),
                "payment_method": txn.payment_method,
                "alipay": alipay_info,
            }
        )


class AliPayNotifyView(View):
    def post(self, request):
        data = request.POST.dict()
        if not data:
            return HttpResponse("fail")

        if not alipay_service.verify_notification(data):
            logger.warning("Alipay notify verify failed: %s", data)
            return HttpResponse("fail")

        out_trade_no = data.get("out_trade_no", "").strip()
        trade_no = data.get("trade_no", "").strip()
        trade_status = data.get("trade_status", "").strip()

        if not out_trade_no:
            return HttpResponse("fail")

        try:
            txn = PaymentTransaction.objects.select_related("order").get(out_trade_no=out_trade_no)
        except PaymentTransaction.DoesNotExist:
            logger.warning("Alipay notify unknown out_trade_no: %s", out_trade_no)
            return HttpResponse("fail")

        if trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED"):
            _mark_paid(txn, trade_no)
        elif trade_status == "TRADE_CLOSED" and txn.status != "paid":
            txn.status = "closed"
            txn.save(update_fields=["status", "updated_at"])

        return HttpResponse("success")
