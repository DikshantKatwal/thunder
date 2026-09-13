from rest_framework import serializers
from django.utils import timezone
from branch.models import Branch
from branch.serializers import BranchSerializer
from staff.models import StaffInvitation, Staff
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken


from user.serializers import CreateUserSerializer, UserSerializer


class StaffSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(read_only=True, source="user")
    branch_detail = BranchSerializer(read_only=True, source="branch")
    class Meta:
        model= Staff
        fields="__all__"  


class StaffInvitationSerializer(serializers.ModelSerializer):
    branch_id = serializers.PrimaryKeyRelatedField(source="branch", queryset=Branch.objects.all(), required=True)
    branch = BranchSerializer(read_only=True)
    expires_at = serializers.DateTimeField(required=False)
    email= serializers.EmailField(required=True)

    class Meta:
        model= StaffInvitation
        fields=[
            "branch_id",
            "branch",
            "email",
            "joined_at",
            "expires_at",
            "given_name",
            "family_name",
            "accepted_at",
        ]  


    def validate(self, attrs):
        email = attrs.get("email")
        if StaffInvitation.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email":"user with this email already invited"})

        return super().validate(attrs)

    def create(self, validated_data):
        from datetime import  timedelta
        expires_at = timezone.now() + timedelta(days=2)
        validated_data["expires_at"]=expires_at
        invitation =  super().create(validated_data)
        invite_link = get_invite_link(invitation)
        print(invite_link)
        return invitation


def get_invite_link(obj:StaffInvitation):
    return f"{settings.FRONTEND_URL}/invitations/accept/{obj.token}/"



class UseStaffInvitationSerializer(serializers.ModelSerializer):
    user = CreateUserSerializer(write_only=True)
    token = serializers.UUIDField(write_only=True)
    joined_at = serializers.DateField(required=False)

    class Meta:
        model= StaffInvitation
        fields=[
            "token",
            "user",
            "joined_at",
        ]  


    def update(self, instance:StaffInvitation, validated_data):
        user = validated_data.get("user")
        serializer = CreateUserSerializer(data=user)
        serializer.is_valid(raise_exception=True)
        user=serializer.save()
        instance.accepted_at = timezone.now()
        Staff.objects.create(
            user=user,
            branch=instance.branch,
            joined_at=instance.joined_at
        )
        instance.save(update_fields=["accepted_at"])
        refresh = RefreshToken.for_user(user)
        data =  {
            "user":serializer.data,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
            }
        return data



class CreateStaffSerializer(serializers.ModelSerializer):
    user = CreateUserSerializer(write_only=True)
    branch = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all()
    )
    class Meta:
        model= Staff
        fields=[
            "id",
            "user",
            "branch",
            "is_active",
            "joined_at"
        ]  


    def create(self,  validated_data):
        user = validated_data.get("user")
        serializer = CreateUserSerializer(data=user)
        serializer.is_valid(raise_exception=True)
        user=serializer.save()
        validated_data["user"] = user
        instance = Staff.objects.create(**validated_data)
        return instance