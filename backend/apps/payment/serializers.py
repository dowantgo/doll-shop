from rest_framework import serializers


class CreatePaymentSerializer(serializers.Serializer):
    order_id = serializers.CharField(required=True, help_text='订单号')
    payment_method = serializers.ChoiceField(
        choices=['alipay', 'wechat', 'mock'],
        default='alipay',
        help_text='支付方式'
    )


class PaymentQRCodeSerializer(serializers.Serializer):
    out_trade_no = serializers.CharField(read_only=True)
    qr_code = serializers.CharField(read_only=True)
    expire_time = serializers.CharField(read_only=True)


class PaymentNotifySerializer(serializers.Serializer):
    out_trade_no = serializers.CharField(required=True)
    trade_no = serializers.CharField(required=False, allow_blank=True)
    trade_status = serializers.CharField(required=False)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    sign_type = serializers.CharField(required=False)
    sign = serializers.CharField(required=False)


class PaymentQuerySerializer(serializers.Serializer):
    out_trade_no = serializers.CharField(required=True, help_text='商户订单号')
