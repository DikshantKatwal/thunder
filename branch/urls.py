# apps/hr/urls.py
from rest_framework.routers import DefaultRouter
from branch.views import BranchViewSet

router = DefaultRouter()
router.register("", BranchViewSet, basename="branch")

urlpatterns = router.urls
