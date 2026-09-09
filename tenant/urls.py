from django.urls import path, include
from rest_framework.routers import DefaultRouter
from tenant.views import ClientViewSet




router = DefaultRouter()
router.register("", ClientViewSet, basename="client-viewset")

urlpatterns = [
]+router.urls
