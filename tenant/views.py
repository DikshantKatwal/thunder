from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet

from tenant.models import Client
from tenant.serializers import ClientSerializer
# Create your views here.


class ClientViewSet(ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
