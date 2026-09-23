from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.dateparse import parse_date
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from booking.models import Booking, BookingRoom, Guest
from booking.serializers import (
    BookingCancelSerializer,
    BookingRoomSerializer,
    BookingSerializer,
    BookingStatusHistorySerializer,
    GuestSerializer,
)
from room.models import Room
from room.serializers import RoomSerializer


def run_transition(fn, *args, **kwargs):
    """Run a model transition method, turning its ValidationError into a DRF one."""
    try:
        return fn(*args, **kwargs)
    except DjangoValidationError as exc:
        raise DRFValidationError(exc.messages if hasattr(exc, "messages") else str(exc))


class GuestViewSet(viewsets.ModelViewSet):
    """
    CRUD for Guest
    """

    serializer_class = GuestSerializer
    permission_classes = [IsAuthenticated]
    queryset = Guest.objects.all()
    search_fields = [
        "given_name",
        "family_name",
        "email",
        "phone",
    ]


class BookingViewSet(viewsets.ModelViewSet):
    """
    CRUD for Booking, plus actions to move it through its lifecycle:
    confirm -> check-in -> check-out, or cancel / no-show.
    """

    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    queryset = Booking.objects.all().select_related("guest").prefetch_related(
        "booking_rooms__room", "booking_rooms__room_type"
    )
    filterset_fields = [
        "status",
        "payment_status",
        "source",
        "guest",
    ]
    search_fields = [
        "reference",
        "guest__given_name",
        "guest__family_name",
    ]

    def _current_staff(self):
        return getattr(self.request.user, "staff", None)

    def perform_create(self, serializer):
        serializer.save(created_by=self._current_staff())

    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        booking = self.get_object()
        run_transition(booking.confirm, changed_by=self._current_staff())
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request, pk=None):
        booking = self.get_object()
        run_transition(booking.mark_checked_in, changed_by=self._current_staff())
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=["post"], url_path="check-out")
    def check_out(self, request, pk=None):
        booking = self.get_object()
        run_transition(booking.mark_checked_out, changed_by=self._current_staff())
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        booking = self.get_object()
        serializer = BookingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run_transition(
            booking.cancel,
            reason=serializer.validated_data.get("reason", ""),
            changed_by=self._current_staff(),
        )
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=["post"], url_path="no-show")
    def no_show(self, request, pk=None):
        booking = self.get_object()
        run_transition(booking.mark_no_show, changed_by=self._current_staff())
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=["post"], url_path="record-payment")
    def record_payment(self, request, pk=None):
        booking = self.get_object()
        amount = request.data.get("amount")
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            raise DRFValidationError({"amount": "A numeric amount is required."})
        if amount <= 0:
            raise DRFValidationError({"amount": "amount must be greater than 0."})

        booking.paid_amount = booking.paid_amount + amount
        booking.refresh_payment_status(commit=False, changed_by=self._current_staff())
        booking.save(update_fields=["paid_amount", "payment_status"])
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        booking = self.get_object()
        history = booking.status_history.select_related("changed_by__user")
        serializer = BookingStatusHistorySerializer(history, many=True)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        self.queryset.delete()
        return Response(200)

    
class BookingRoomViewSet(viewsets.ModelViewSet):
    """
    Per-room line items of a booking. Supports adding/removing a room to an
    existing booking, and checking a single room in/out independently -
    useful when a multi-room booking's guests arrive/leave at different times.
    """

    serializer_class = BookingRoomSerializer
    permission_classes = [IsAuthenticated]
    queryset = BookingRoom.objects.all().select_related("booking", "room", "room_type")
    filterset_fields = ["booking", "room", "status"]

    def _current_staff(self):
        return getattr(self.request.user, "staff", None)

    def _resolve_booking(self):
        booking_id = self.request.data.get("booking") or self.request.query_params.get("booking")
        if not booking_id:
            raise DRFValidationError({"booking": "This field is required."})
        try:
            return Booking.objects.get(pk=booking_id)
        except Booking.DoesNotExist:
            raise DRFValidationError({"booking": "Booking not found."})

    def perform_create(self, serializer):
        booking = self._resolve_booking()
        if booking.status not in ("pending", "confirmed"):
            raise DRFValidationError(
                {"booking": f"Rooms can't be added once a booking is '{booking.status}'."}
            )
        room = serializer.validated_data["room"]
        rate_per_night = serializer.validated_data.get("rate_per_night") or room.room_type.base_price
        instance = BookingRoom(
            booking=booking,
            room_type=room.room_type,
            rate_per_night=rate_per_night,
            **{k: v for k, v in serializer.validated_data.items() if k != "rate_per_night"},
        )
        run_transition(instance.clean)
        instance.save()
        booking.recalculate_totals(changed_by=self._current_staff())
        booking.save(update_fields=["subtotal", "total_amount", "payment_status"])
        serializer.instance = instance

    def perform_update(self, serializer):
        instance = serializer.save()
        run_transition(instance.clean)
        booking = instance.booking
        booking.recalculate_totals(changed_by=self._current_staff())
        booking.save(update_fields=["subtotal", "total_amount", "payment_status"])

    def perform_destroy(self, instance):
        booking = instance.booking
        if instance.status not in ("reserved", "cancelled"):
            raise DRFValidationError(
                "Only reserved or already-cancelled rooms can be removed from a booking."
            )
        instance.delete()
        booking.recalculate_totals(changed_by=self._current_staff())
        booking.save(update_fields=["subtotal", "total_amount", "payment_status"])

    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request, pk=None):
        booking_room = self.get_object()
        run_transition(booking_room.mark_checked_in)
        booking_room.booking.sync_status_from_rooms(changed_by=self._current_staff())
        return Response(self.get_serializer(booking_room).data)

    @action(detail=True, methods=["post"], url_path="check-out")
    def check_out(self, request, pk=None):
        booking_room = self.get_object()
        run_transition(booking_room.mark_checked_out)
        booking_room.booking.sync_status_from_rooms(changed_by=self._current_staff())
        return Response(self.get_serializer(booking_room).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        booking_room = self.get_object()
        run_transition(booking_room.cancel)
        booking = booking_room.booking
        booking.recalculate_totals(changed_by=self._current_staff())
        booking.save(update_fields=["subtotal", "total_amount", "payment_status"])
        return Response(self.get_serializer(booking_room).data)


class AvailableRoomsView(APIView):
    """
    List rooms that are free for a given date range (and optionally a room
    type), i.e. not maintenance/blocked and with no overlapping active booking.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        check_in = parse_date(request.query_params.get("check_in", ""))
        check_out = parse_date(request.query_params.get("check_out", ""))
        if not check_in or not check_out:
            raise DRFValidationError(
                "check_in and check_out query params are required (YYYY-MM-DD)."
            )
        if check_out <= check_in:
            raise DRFValidationError("check_out must be after check_in.")

        rooms = Room.objects.exclude(status__in=["maintenance", "blocked"])

        room_type = request.query_params.get("room_type")
        if room_type:
            rooms = rooms.filter(room_type_id=room_type)

        booked_room_ids = BookingRoom.objects.filter(
            check_in__lt=check_out,
            check_out__gt=check_in,
        ).exclude(status="cancelled").values_list("room_id", flat=True)

        rooms = rooms.exclude(id__in=booked_room_ids).select_related("room_type")
        serializer = RoomSerializer(rooms, many=True)
        return Response(serializer.data)
