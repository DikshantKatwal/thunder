# apps/hr/views/branches.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from branch.models import Branch
from branch.serializers import BranchSerializer



class BranchViewSet(viewsets.ModelViewSet):
    """
    CRUD for Branch
    """

    serializer_class = BranchSerializer
    permission_classes = [IsAuthenticated]
    queryset = Branch.objects.all()
    search_fields = [
        "name",
        "status",
    ]
