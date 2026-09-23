from decimal import Decimal

from django.db import models, transaction
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone

from common.models import BasicModel
from room.models import Room
from settings.room_type.models import RoomType

ID_CHOICES=[
            ("passport", "Passport"),
            ("national_id", "National ID"),
            ("driving_license", "Driving License"),
            ("other", "Other"),
        ]

class Guest(BasicModel):
    given_name = models.CharField(max_length=50)
    family_name = models.CharField(max_length=50, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(blank=True)

    id_type = models.CharField(
        max_length=20,
        choices=ID_CHOICES,
        null=True,
        blank=True,
    )
    id_number = models.CharField(max_length=50, null=True, blank=True)
    nationality = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = "booking_guest"
        ordering = ["given_name", "family_name"]

    def __str__(self):
        return f"{self.given_name} {self.family_name}".strip()


class Booking(BasicModel):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("checked_in", "Checked In"),
        ("checked_out", "Checked Out"),
        ("cancelled", "Cancelled"),
        ("no_show", "No Show"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("partially_paid", "Partially Paid"),
        ("paid", "Paid"),
        ("refunded", "Refunded"),
    ]

    SOURCE_CHOICES = [
        ("direct", "Direct"),
        ("walk_in", "Walk In"),
        ("phone", "Phone"),
        ("website", "Website"),
        ("ota", "OTA / Third Party"),
        ("agent", "Travel Agent"),
    ]

    reference = models.CharField(max_length=20, unique=True, editable=False)

    guest = models.ForeignKey(
        Guest,
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    check_in = models.DateField()
    check_out = models.DateField()

    adults = models.PositiveIntegerField(default=1)
    children = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="direct")

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="unpaid"
    )

    special_requests = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        "staff.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings_created",
    )

    class Meta:
        db_table = "booking"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(check_out__gt=models.F("check_in")),
                name="booking_check_out_after_check_in",
            )
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_reference()
        super().save(*args, **kwargs)

    def _generate_reference(self):
        with transaction.atomic():
            last = (
                Booking.objects.select_for_update()
                .order_by("-created_at")
                .values_list("reference", flat=True)
                .first()
            )
            next_number = 1
            if last and last.startswith("BK") and last[2:].isdigit():
                next_number = int(last[2:]) + 1
            return f"BK{next_number:06d}"

    def _log_status_change(self, field, from_status, to_status, changed_by=None, note=""):
        if from_status == to_status:
            return
        BookingStatusHistory.objects.create(
            booking=self,
            field=field,
            from_status=from_status,
            to_status=to_status,
            changed_by=changed_by,
            note=note,
        )

    def record_creation(self, changed_by=None):
        """Log the booking's initial status/payment_status. Call once, right after creation."""
        self._log_status_change("status", "", self.status, changed_by, note="Booking created")
        self._log_status_change(
            "payment_status", "", self.payment_status, changed_by, note="Booking created"
        )

    # Which statuses a booking may move to from its current status.
    ALLOWED_TRANSITIONS = {
        "pending": {"confirmed", "cancelled"},
        "confirmed": {"checked_in", "cancelled", "no_show"},
        "checked_in": {"checked_out", "cancelled"},
        "checked_out": set(),
        "cancelled": set(),
        "no_show": set(),
    }

    @property
    def balance_due(self):
        return self.total_amount - self.paid_amount

    def _require_transition(self, new_status):
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValidationError(
                f"Cannot move booking from '{self.status}' to '{new_status}'."
            )

    def recalculate_totals(self, changed_by=None):
        """Recompute subtotal/total/payment_status from active room lines."""
        subtotal = sum(
            (br.amount for br in self.booking_rooms.exclude(status="cancelled")),
            Decimal("0"),
        )
        self.subtotal = subtotal
        self.total_amount = subtotal - self.discount + self.tax
        self.refresh_payment_status(commit=False, changed_by=changed_by)

    def refresh_payment_status(self, commit=True, changed_by=None):
        old_status = self.payment_status
        if self.paid_amount <= 0:
            self.payment_status = "unpaid"
        elif self.paid_amount >= self.total_amount:
            self.payment_status = "paid"
        else:
            self.payment_status = "partially_paid"
        if commit:
            self.save(update_fields=["payment_status"])
        self._log_status_change("payment_status", old_status, self.payment_status, changed_by)

    def sync_status_from_rooms(self, changed_by=None):
        """Derive the booking status from its room lines' individual statuses.
        Used after a single room is checked in/out so multi-room bookings
        progress without needing a whole-booking transition each time."""
        statuses = set(self.booking_rooms.values_list("status", flat=True))
        if not statuses or statuses == {"cancelled"}:
            return
        active_statuses = statuses - {"cancelled"}
        old_status = self.status
        if active_statuses == {"checked_out"}:
            self.status = "checked_out"
        elif "checked_in" in active_statuses:
            self.status = "checked_in"
        if self.status != old_status:
            self.save(update_fields=["status"])
            self._log_status_change("status", old_status, self.status, changed_by)

    @transaction.atomic
    def confirm(self, changed_by=None):
        self._require_transition("confirmed")
        old_status = self.status
        self.status = "confirmed"
        self.save(update_fields=["status"])
        self._log_status_change("status", old_status, self.status, changed_by)

    @transaction.atomic
    def mark_checked_in(self, changed_by=None):
        self._require_transition("checked_in")
        for booking_room in self.booking_rooms.filter(status="reserved"):
            booking_room.mark_checked_in()
        old_status = self.status
        self.status = "checked_in"
        self.save(update_fields=["status"])
        self._log_status_change("status", old_status, self.status, changed_by)

    @transaction.atomic
    def mark_checked_out(self, changed_by=None):
        self._require_transition("checked_out")
        for booking_room in self.booking_rooms.filter(status="checked_in"):
            booking_room.mark_checked_out()
        old_status = self.status
        self.status = "checked_out"
        self.save(update_fields=["status"])
        self._log_status_change("status", old_status, self.status, changed_by)

    @transaction.atomic
    def cancel(self, reason="", changed_by=None):
        self._require_transition("cancelled")
        for booking_room in self.booking_rooms.exclude(
            status__in=["cancelled", "checked_out"]
        ):
            booking_room.cancel()
        old_status = self.status
        self.status = "cancelled"
        self.cancellation_reason = reason
        self.cancelled_at = timezone.now()
        self.save(update_fields=["status", "cancellation_reason", "cancelled_at"])
        self._log_status_change("status", old_status, self.status, changed_by, note=reason)

    @transaction.atomic
    def mark_no_show(self, changed_by=None):
        self._require_transition("no_show")
        for booking_room in self.booking_rooms.exclude(status="cancelled"):
            booking_room.cancel()
        old_status = self.status
        self.status = "no_show"
        self.save(update_fields=["status"])
        self._log_status_change("status", old_status, self.status, changed_by)

    def __str__(self):
        return self.reference


class BookingStatusHistory(BasicModel):
    FIELD_CHOICES = [
        ("status", "Booking Status"),
        ("payment_status", "Payment Status"),
    ]

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    field = models.CharField(max_length=20, choices=FIELD_CHOICES)
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    note = models.TextField(blank=True)

    changed_by = models.ForeignKey(
        "staff.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="booking_status_changes",
    )

    class Meta:
        db_table = "booking_status_history"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.booking.reference}: {self.field} {self.from_status} -> {self.to_status}"


class BookingRoom(BasicModel):
    STATUS_CHOICES = [
        ("reserved", "Reserved"),
        ("checked_in", "Checked In"),
        ("checked_out", "Checked Out"),
        ("cancelled", "Cancelled"),
    ]

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="booking_rooms",
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name="booking_rooms",
    )
    # Snapshot of the room type at time of booking, so pricing/name changes
    # to RoomType later don't rewrite history.
    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.PROTECT,
        related_name="booking_rooms",
    )

    check_in = models.DateField()
    check_out = models.DateField()

    adults = models.PositiveIntegerField(default=1)
    children = models.PositiveIntegerField(default=0)

    rate_per_night = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="reserved")

    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "booking_room"
        ordering = ["check_in"]
        constraints = [
            models.CheckConstraint(
                condition=Q(check_out__gt=models.F("check_in")),
                name="booking_room_check_out_after_check_in",
            )
        ]

    @property
    def nights(self):
        return (self.check_out - self.check_in).days

    def clean(self):
        if self.check_in and self.check_out and self.room_id:
            overlapping = BookingRoom.objects.filter(
                room_id=self.room_id,
                check_in__lt=self.check_out,
                check_out__gt=self.check_in,
            ).exclude(status="cancelled")
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError(
                    "This room is already booked for the selected dates."
                )

    def save(self, *args, **kwargs):
        if self.rate_per_night is not None and self.check_in and self.check_out:
            self.amount = self.rate_per_night * Decimal(self.nights)
        super().save(*args, **kwargs)

    @transaction.atomic
    def mark_checked_in(self):
        if self.status != "reserved":
            raise ValidationError(
                f"Cannot check in room from status '{self.status}'."
            )
        if self.room.status in ("maintenance", "blocked"):
            raise ValidationError(
                f"Room {self.room.room_number} is {self.room.status} and cannot be checked in."
            )
        self.status = "checked_in"
        self.checked_in_at = timezone.now()
        self.save(update_fields=["status", "checked_in_at"])

        self.room.status = "occupied"
        self.room.save(update_fields=["status"])

    @transaction.atomic
    def mark_checked_out(self):
        if self.status != "checked_in":
            raise ValidationError(
                f"Cannot check out room from status '{self.status}'."
            )
        self.status = "checked_out"
        self.checked_out_at = timezone.now()
        self.save(update_fields=["status", "checked_out_at"])

        # Only release the room if it's still marked occupied by this stay -
        # avoids clobbering a status an operator has since set manually.
        if self.room.status == "occupied":
            self.room.status = "available"
            self.room.save(update_fields=["status"])

    @transaction.atomic
    def cancel(self):
        if self.status in ("cancelled", "checked_out"):
            raise ValidationError(f"Cannot cancel room from status '{self.status}'.")
        was_checked_in = self.status == "checked_in"
        self.status = "cancelled"
        self.save(update_fields=["status"])

        if was_checked_in and self.room.status == "occupied":
            self.room.status = "available"
            self.room.save(update_fields=["status"])

    def __str__(self):
        return f"{self.booking.reference} - {self.room.room_number}"
