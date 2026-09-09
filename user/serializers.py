
from rest_framework import serializers
from user.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "given_name",
            "family_name",
            "username",
        ]


class CreateUserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    given_name = serializers.CharField()
    family_name = serializers.CharField()
    phone = serializers.CharField(max_length=15, required=False)
    password = serializers.CharField(write_only=True)
    class Meta:
        model= User
        fields=[
            "email",
            "phone",
            "given_name",
            "family_name",
            "password",
        ]  

    def validate(self, attrs):
        email = attrs.get("email")

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({
                "email": "A user with this email has already signed up."
            })

        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


