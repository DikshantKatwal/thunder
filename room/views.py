from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from room.models import Room
from room.serializers import RoomSerializer


class RoomViewSet(viewsets.ModelViewSet):
    """
    CRUD for Room
    """

    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated]
    queryset = Room.objects.all().select_related("room_type")
    filterset_fields = [
        "room_type",
        "status",
        "floor",
    ]
    search_fields = [
        "room_number",
    ]
