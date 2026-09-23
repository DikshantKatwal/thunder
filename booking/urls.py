from django.urls import path
from rest_framework.routers import DefaultRouter

from booking import views

router = DefaultRouter()
router.register("guests", views.GuestViewSet, basename="guest")
router.register("rooms", views.BookingRoomViewSet, basename="booking-room")
router.register("", views.BookingViewSet, basename="booking")

urlpatterns = [
    path("available-rooms/", views.AvailableRoomsView.as_view(), name="available-rooms"),
] + router.urls
