from django.db import models, transaction
from django.db.models import Max
from common.models import BasicModel


class BedType(BasicModel):
    name = models.CharField(max_length=50)
    status = models.BooleanField(default=True)
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "settings_bed_type"
        ordering = ["sequence"]

    def save(self, *args, **kwargs):
        if not self.sequence or self.sequence == 0:
            with transaction.atomic():
                max_sequence = (
                    BedType.objects.all().aggregate(max_seq=Max("sequence"))
                    .get("max_seq")
                )
                self.sequence = (max_sequence or 0) + 1

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class RoomTypeBed(BasicModel):
    room_type = models.ForeignKey(
        "RoomType",
        on_delete=models.CASCADE,
        related_name="room_type_beds"
    )
    bed_type = models.ForeignKey(
        BedType,
        on_delete=models.PROTECT,
        related_name="room_type_beds"
    )
    number_of_beds = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "settings_room_type_bed"
        unique_together = ("room_type", "bed_type")

    def __str__(self):
        return f"{self.room_type.name} - {self.bed_type.name} x{self.number_of_beds}"


class RoomAmenity(BasicModel):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=255, blank=True)
    status = models.BooleanField(default=True)
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "settings_room_amenity"
        ordering = ["sequence"]

    def save(self, *args, **kwargs):
        if not self.sequence or self.sequence == 0:
            with transaction.atomic():
                max_sequence = (
                    RoomAmenity.objects.all().aggregate(max_seq=Max("sequence"))
                    .get("max_seq")
                )
                self.sequence = (max_sequence or 0) + 1

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class RoomType(BasicModel):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)

    max_adults = models.PositiveIntegerField(default=2)
    max_children = models.PositiveIntegerField(default=0)
    max_occupancy = models.PositiveIntegerField(default=2)

    bed_types = models.ManyToManyField(
        BedType,
        through="RoomTypeBed",
        related_name="room_types"
    )

    # Room characteristics
    room_size = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )

    base_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    amenities = models.ManyToManyField(
        RoomAmenity,
        blank=True,
        related_name="room_types"
    )

    status = models.BooleanField(default=True)
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "settings_room_type"
        ordering = ["sequence"]

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.upper()

        if not self.sequence or self.sequence == 0:
            with transaction.atomic():
                max_sequence = (
                    RoomType.objects.all().aggregate(max_seq=Max("sequence"))
                    .get("max_seq")
                )
                self.sequence = (max_sequence or 0) + 1

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


