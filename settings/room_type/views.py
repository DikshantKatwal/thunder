from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from settings.room_type.models import BedType, RoomAmenity, RoomType
from settings.room_type.serializers import (
    BedTypeSerializer,
    RoomAmenitySerializer,
    RoomTypeSerializer,
)


class BedTypeViewSet(viewsets.ModelViewSet):
    """
    CRUD for BedType
    """

    serializer_class = BedTypeSerializer
    permission_classes = [IsAuthenticated]
    queryset = BedType.objects.all()
    search_fields = [
        "name",
    ]


class RoomAmenityViewSet(viewsets.ModelViewSet):
    """
    CRUD for RoomAmenity
    """

    serializer_class = RoomAmenitySerializer
    permission_classes = [IsAuthenticated]
    queryset = RoomAmenity.objects.all()
    search_fields = [
        "name",
    ]


class RoomTypeViewSet(viewsets.ModelViewSet):
    """
    CRUD for RoomType
    """

    serializer_class = RoomTypeSerializer
    permission_classes = [IsAuthenticated]
    queryset = RoomType.objects.all().prefetch_related(
        "amenities", "room_type_beds__bed_type"
    )
    search_fields = [
        "name",
        "code",
    ]
