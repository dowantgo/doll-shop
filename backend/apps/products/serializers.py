from rest_framework import serializers
from .models import Category, Product, ProductImage, InventoryLog

class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'image_url', 'is_main', 'sort_order']
    
    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'icon', 'sort_order', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), allow_null=True, required=False)

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'category', 'category_name', 'price', 'cost',
                  'stock', 'sales', 'is_hot', 'hot_sort_order', 'status', 'images', 'created_at']
        read_only_fields = ['id', 'sales', 'created_at']


class ProductDetailSerializer(ProductSerializer):
    pass


class InventoryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryLog
        fields = ['id', 'product', 'log_type', 'quantity', 'before_stock', 'after_stock', 'remark', 'created_at']
        read_only_fields = ['id', 'created_at']
