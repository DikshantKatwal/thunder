from rest_framework.routers import DefaultRouter

from room import views

router = DefaultRouter()
router.register("", views.RoomViewSet, basename="room")

urlpatterns = router.urls
