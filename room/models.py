from django.db import models

from common.models import BasicModel
from settings.room_type.models import RoomType

class Room(BasicModel):
    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.PROTECT,
        related_name="rooms"
    )

    room_number = models.CharField(max_length=20)
    floor = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=[
            ("available", "Available"),
            ("occupied", "Occupied"),
            ("maintenance", "Maintenance"),
            ("blocked", "Blocked"),
        ],
        default="available"
    )

    notes = models.TextField(blank=True)

    class Meta:
        db_table = "hotel_room"
        ordering = ["floor", "room_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["room_number"],
                name="unique_room_number"
            )
        ]

    def __str__(self):
        return self.room_number