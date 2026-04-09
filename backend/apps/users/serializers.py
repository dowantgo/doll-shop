from rest_framework import serializers
from .models import User, Address, PaymentRecord


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'name', 'phone', 'province', 'city', 'district', 'address', 'is_default', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    addresses = AddressSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'role', 'avatar', 'addresses', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=False)
    password2 = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirm_password', 'password2', 'phone']

    def validate(self, data):
        confirm_password = data.pop('confirm_password', None)
        legacy_password2 = data.pop('password2', None)
        final_confirm_password = confirm_password or legacy_password2

        if not final_confirm_password:
            raise serializers.ValidationError({'confirm_password': '请填写确认密码'})

        if data['password'] != final_confirm_password:
            raise serializers.ValidationError({'confirm_password': '两次密码输入不一致'})

        email = data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email': '该邮箱已注册'})

        return data

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class PaymentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRecord
        fields = ['id', 'order_id', 'payment_method', 'amount', 'status', 'transaction_id', 'created_at']
        read_only_fields = ['id', 'created_at']
