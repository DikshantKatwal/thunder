# apps/hr/serializers/branches.py
from rest_framework import serializers
from branch.models import Branch


class BranchSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True)
    status = serializers.CharField(required=True)

    class Meta:
        model = Branch
        fields = [
            "id",
            "name",
            "phone",
            "email",
            "status",
            "address",
            "sequence",
            "created_at",
            "updated_at",
        ]
