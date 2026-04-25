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

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError('价格不能为负数')
        return value

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError('库存不能为负数')
        return value

    def validate_cost(self, value):
        if value < 0:
            raise serializers.ValidationError('成本不能为负数')
        return value


class ProductDetailSerializer(ProductSerializer):
    pass


class ProductFeedSerializer(serializers.ModelSerializer):
    main_image = serializers.SerializerMethodField()
    hot_score = serializers.FloatField(read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'main_image', 'sales', 'hot_score']

    def get_main_image(self, obj):
        images = list(obj.images.all())
        main = next((image for image in images if image.is_main), None)
        if not main and images:
            main = images[0]
        if not main:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(main.image.url) if request else main.image.url


class InventoryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryLog
        fields = ['id', 'product', 'log_type', 'quantity', 'before_stock', 'after_stock', 'remark', 'created_at']
        read_only_fields = ['id', 'created_at']
