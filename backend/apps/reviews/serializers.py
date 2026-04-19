from rest_framework import serializers

from .models import Review, ReviewReply


class ReviewReplySerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ReviewReply
        fields = [
            'id',
            'review',
            'user_id',
            'user_name',
            'content',
            'created_at',
        ]
        read_only_fields = fields


class ReviewSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    replies = ReviewReplySerializer(many=True, read_only=True)

    class Meta:
        model = Review
        fields = [
            'id',
            'product_id',
            'user_id',
            'rating',
            'content',
            'status',
            'created_at',
            'user_name',
            'product_name',
            'audit_remark',
            'replies',
        ]
        read_only_fields = [
            'id',
            'product_id',
            'user_id',
            'status',
            'created_at',
            'user_name',
            'product_name',
            'audit_remark',
            'replies',
        ]


class CreateReviewSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    content = serializers.CharField(min_length=1, max_length=2000)


class CreateReviewReplySerializer(serializers.Serializer):
    content = serializers.CharField(min_length=1, max_length=2000)
