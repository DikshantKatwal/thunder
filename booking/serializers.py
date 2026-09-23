from rest_framework import serializers

from booking.models import ID_CHOICES, Booking, BookingRoom, BookingStatusHistory, Guest
from room.models import Room
from room.serializers import RoomSerializer
from settings.room_type.serializers import RoomTypeSerializer


class GuestSerializer(serializers.ModelSerializer):
    given_name = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)
    id_type = serializers.CharField(required=True)
    id_number = serializers.CharField(required=True)
    class Meta:
        model = Guest
        fields = [
            "id",
            "given_name",
            "family_name",
            "email",
            "phone",
            "address",
            "id_type",
            "id_number",
            "nationality",
            "created_at",
            "updated_at",
        ]


class BookingRoomSerializer(serializers.ModelSerializer):
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    room_detail = RoomSerializer(source="room", read_only=True)
    room_type_detail = RoomTypeSerializer(source="room_type", read_only=True)
    nights = serializers.ReadOnlyField()

    class Meta:
        model = BookingRoom
        fields = [
            "id",
            "room",
            "room_detail",
            "room_type_detail",
            "check_in",
            "check_out",
            "nights",
            "adults",
            "children",
            "rate_per_night",
            "amount",
            "status",
            "checked_in_at",
            "checked_out_at",
        ]
        read_only_fields = ["amount", "status", "checked_in_at", "checked_out_at"]

    def validate(self, attrs):
        check_in = attrs.get("check_in")
        check_out = attrs.get("check_out")
        if check_in and check_out and check_out <= check_in:
            raise serializers.ValidationError(
                "check_out must be after check_in."
            )
        return attrs


class BookingSerializer(serializers.ModelSerializer):
    guest = serializers.PrimaryKeyRelatedField(queryset=Guest.objects.all())
    guest_detail = GuestSerializer(source="guest", read_only=True)
    booking_rooms = BookingRoomSerializer(many=True)
    balance_due = serializers.ReadOnlyField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "reference",
            "guest",
            "guest_detail",
            "check_in",
            "check_out",
            "adults",
            "children",
            "status",
            "source",
            "booking_rooms",
            "subtotal",
            "discount",
            "tax",
            "total_amount",
            "paid_amount",
            "payment_status",
            "balance_due",
            "special_requests",
            "cancellation_reason",
            "cancelled_at",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "reference",
            "status",
            "subtotal",
            "total_amount",
            "payment_status",
            "cancellation_reason",
            "cancelled_at",
            "created_by",
        ]

    def validate_booking_rooms(self, value):
        if not value:
            raise serializers.ValidationError("At least one room is required.")
        room_ids = [item["room"].id for item in value]
        if len(room_ids) != len(set(room_ids)):
            raise serializers.ValidationError("Duplicate rooms are not allowed in the same booking.")
        return value

    def _build_booking_room(self, booking, room_data):
        room:Room = room_data["room"]
        rate_per_night = room_data.get("rate_per_night") or room.room_type.base_price
        booking_room = BookingRoom(
            booking=booking,
            room=room,
            room_type=room.room_type,
            check_in=room_data.get("check_in", booking.check_in),
            check_out=room_data.get("check_out", booking.check_out),
            adults=room_data.get("adults", 1),
            children=room_data.get("children", 0),
            rate_per_night=rate_per_night,
        )
        booking_room.clean()
        return booking_room

    def _current_staff(self):
        request = self.context.get("request")
        if request is None:
            return None
        return getattr(request.user, "staff", None)

    def create(self, validated_data):
        rooms_data = validated_data.pop("booking_rooms")
        booking = Booking.objects.create(**validated_data)

        for room_data in rooms_data:
            booking_room = self._build_booking_room(booking, room_data)
            booking_room.save()

        staff = self._current_staff()
        booking.recalculate_totals(changed_by=staff)
        booking.save(update_fields=["subtotal", "total_amount", "payment_status"])
        booking.record_creation(changed_by=staff)
        return booking

    def update(self, instance, validated_data):
        rooms_data = validated_data.pop("booking_rooms", None)

        if rooms_data is not None:
            if instance.status not in ("pending", "confirmed"):
                raise serializers.ValidationError(
                    {"booking_rooms": f"Rooms can't be edited once a booking is '{instance.status}'."}
                )
            instance.booking_rooms.all().delete()
            for room_data in rooms_data:
                booking_room = self._build_booking_room(instance, room_data)
                booking_room.save()

        instance = super().update(instance, validated_data)
        instance.recalculate_totals(changed_by=self._current_staff())
        instance.save(update_fields=["subtotal", "total_amount", "payment_status"])
        return instance


class BookingCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class BookingStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = BookingStatusHistory
        fields = [
            "id",
            "field",
            "from_status",
            "to_status",
            "note",
            "changed_by",
            "changed_by_name",
            "created_at",
        ]

    def get_changed_by_name(self, obj):
        if not obj.changed_by:
            return None
        user = obj.changed_by.user
        name = f"{user.given_name or ''} {user.family_name or ''}".strip()
        return name or user.email
