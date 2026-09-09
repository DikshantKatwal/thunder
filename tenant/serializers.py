from django.db import transaction
from rest_framework import serializers

from tenant.helpers import _is_already_hashed, hash_client_password
from tenant.models import Client, Domain

class ClientSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True)
    class Meta:
        fields=[
            "id",
            "created_on",
            "schema_name",
            "legal_name",
            "given_name",
            "family_name",
            "full_name",
            "email",
            "phone",
            "password",
            "domain_name"
        ]
        model = Client

    @transaction.atomic
    def create(self, validated_data):
        domain_name = str(validated_data.pop("domain_name")).strip().lower()
        password = validated_data.pop("password")
        if not _is_already_hashed(password):
            password = hash_client_password(password)
        client = Client.objects.create(**validated_data,password=password)

        Domain.objects.create(
            tenant=client,
            domain=domain_name,
            is_primary=True,
            is_active=True,
        )

        return client