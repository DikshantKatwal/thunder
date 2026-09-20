from rest_framework.routers import DefaultRouter

from settings.room_type import views

router = DefaultRouter()
router.register("bed-type", views.BedTypeViewSet, basename="bed-type")
router.register("amenity", views.RoomAmenityViewSet, basename="room-amenity")
router.register("room-type", views.RoomTypeViewSet, basename="room-type")

urlpatterns = router.urls
