from rest_framework import serializers
from .models import CartItem
from apps.products.models import Product

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    product_stock = serializers.IntegerField(source='product.stock', read_only=True)
    product_image = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name', 'product_price', 'product_stock', 
                  'product_image', 'quantity', 'subtotal', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_product_image(self, obj):
        if obj.product and obj.product.images.exists():
            main_image = obj.product.images.filter(is_main=True).first()
            if not main_image:
                main_image = obj.product.images.first()
            if main_image:
                request = self.context.get('request')
                return request.build_absolute_uri(main_image.image.url) if request else main_image.image.url
        return None
    
    def get_subtotal(self, obj):
        return obj.product.price * obj.quantity


class AddToCartSerializer(serializers.Serializer):
    """Add product to cart"""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(default=1)
