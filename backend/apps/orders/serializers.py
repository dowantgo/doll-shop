from rest_framework import serializers
from .models import Order, OrderItem
from apps.products.serializers import ProductSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.SerializerMethodField()
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_image', 'quantity', 'price', 'subtotal']
    
    def get_product_image(self, obj):
        if obj.product and obj.product.images.exists():
            main_image = obj.product.images.filter(is_main=True).first()
            if main_image:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(main_image.image.url)
                return main_image.image.url
        return None


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    address_detail = serializers.SerializerMethodField()
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    shipping_company_display = serializers.CharField(read_only=True)
    shipping_status_display = serializers.CharField(read_only=True)
    discount_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'user', 'user_name', 'total_price',
            'status', 'payment_status', 'payment_status_display',
            'payment_method', 'payment_method_display',
            'shipping_company', 'shipping_company_display',
            'shipping_status', 'shipping_status_display',
            'tracking_no', 'trade_no',
            'discount_detail',
            'address', 'address_detail', 'remark',
            'items', 'created_at', 'paid_at', 'shipped_at', 'delivered_at', 'expires_at'
        ]
        read_only_fields = ['id', 'order_id', 'user', 'created_at', 'paid_at', 'shipped_at', 'delivered_at']
    
    def get_address_detail(self, obj):
        if obj.address:
            return {
                'id': obj.address.id,
                'name': obj.address.name,
                'phone': obj.address.phone,
                'province': obj.address.province,
                'city': obj.address.city,
                'district': obj.address.district,
                'address': obj.address.address,
            }
        return None
    
    def get_shipping_company_display(self, obj):
        return obj.shipping_company_display
    
    def get_shipping_status_display(self, obj):
        return obj.shipping_status_display

    def get_discount_detail(self, obj):
        snapshot = getattr(obj, 'discount_snapshot', None)
        if not snapshot:
            return None
        coupon = snapshot.user_coupon
        return {
            'subtotal_amount': str(snapshot.subtotal_amount),
            'full_reduction_amount': str(snapshot.full_reduction_amount),
            'coupon_discount_amount': str(snapshot.coupon_discount_amount),
            'final_payable_amount': str(snapshot.final_payable_amount),
            'coupon_no': coupon.coupon_no if coupon else '',
            'coupon_template_name': coupon.template.name if coupon and coupon.template else '',
            'pricing_version': snapshot.pricing_version,
        }


class CreateOrderSerializer(serializers.Serializer):
    address_id = serializers.IntegerField()
    remark = serializers.CharField(required=False, allow_blank=True)


class AdminOrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    address_detail = serializers.SerializerMethodField()
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    shipping_company_display = serializers.CharField(read_only=True)
    shipping_status_display = serializers.CharField(read_only=True)
    discount_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'user', 'user_name', 'total_price',
            'status', 'payment_status', 'payment_status_display',
            'payment_method', 'payment_method_display',
            'shipping_company', 'shipping_company_display',
            'shipping_status', 'shipping_status_display',
            'tracking_no', 'trade_no',
            'discount_detail',
            'address', 'address_detail', 'remark',
            'items', 'created_at', 'paid_at', 'shipped_at', 'delivered_at', 'expires_at'
        ]
        read_only_fields = ['id', 'order_id', 'user', 'created_at', 'paid_at', 'shipped_at', 'delivered_at']
    
    def get_address_detail(self, obj):
        if obj.address:
            return {
                'id': obj.address.id,
                'name': obj.address.name,
                'phone': obj.address.phone,
                'province': obj.address.province,
                'city': obj.address.city,
                'district': obj.address.district,
                'address': obj.address.address,
            }
        return None
    
    def get_shipping_company_display(self, obj):
        return obj.shipping_company_display
    
    def get_shipping_status_display(self, obj):
        return obj.shipping_status_display

    def get_discount_detail(self, obj):
        snapshot = getattr(obj, 'discount_snapshot', None)
        if not snapshot:
            return None
        coupon = snapshot.user_coupon
        return {
            'subtotal_amount': str(snapshot.subtotal_amount),
            'full_reduction_amount': str(snapshot.full_reduction_amount),
            'coupon_discount_amount': str(snapshot.coupon_discount_amount),
            'final_payable_amount': str(snapshot.final_payable_amount),
            'coupon_no': coupon.coupon_no if coupon else '',
            'coupon_template_name': coupon.template.name if coupon and coupon.template else '',
            'pricing_version': snapshot.pricing_version,
        }


class UpdateShippingSerializer(serializers.Serializer):
    shipping_company = serializers.CharField(required=False)
    shipping_status = serializers.CharField(required=False)
    tracking_no = serializers.CharField(required=False, allow_blank=True)
