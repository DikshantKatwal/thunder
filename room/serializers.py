from rest_framework import serializers

from room.models import Room
from settings.room_type.models import RoomType
from settings.room_type.serializers import RoomTypeSerializer


class RoomSerializer(serializers.ModelSerializer):
    room_number = serializers.CharField(required=True)
    floor = serializers.IntegerField(required=True)

    room_type = serializers.PrimaryKeyRelatedField(queryset=RoomType.objects.all())
    room_type_detail = RoomTypeSerializer(source="room_type", read_only=True)

    class Meta:
        model = Room
        fields = [
            "id",
            "room_type",
            "room_type_detail",
            "room_number",
            "floor",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
