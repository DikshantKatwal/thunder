from rest_framework import serializers

from settings.room_type.models import BedType, RoomAmenity, RoomType, RoomTypeBed


class BedTypeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True)

    class Meta:
        model = BedType
        fields = [
            "id",
            "name",
            "status",
            "sequence",
            "created_at",
            "updated_at",
        ]


class RoomTypeBedSerializer(serializers.ModelSerializer):
    bed_type = serializers.PrimaryKeyRelatedField(queryset=BedType.objects.all())
    bed_type_detail = BedTypeSerializer(source="bed_type", read_only=True)

    class Meta:
        model = RoomTypeBed
        fields = [
            "id",
            "bed_type",
            "bed_type_detail",
            "number_of_beds",
        ]


class RoomAmenitySerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True)

    class Meta:
        model = RoomAmenity
        fields = [
            "id",
            "name",
            "icon",
            "description",
            "status",
            "sequence",
            "created_at",
            "updated_at",
        ]


class RoomTypeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True)
    code = serializers.CharField(required=True)

    room_type_beds = RoomTypeBedSerializer(many=True, required=True)

    amenities = serializers.PrimaryKeyRelatedField(
        queryset=RoomAmenity.objects.all(), many=True, required=False
    )
    amenities_detail = RoomAmenitySerializer(
        source="amenities", many=True, read_only=True
    )

    class Meta:
        model = RoomType
        fields = [
            "id",
            "name",
            "code",
            "description",
            "max_adults",
            "max_children",
            "max_occupancy",
            "room_type_beds",
            "room_size",
            "base_price",
            "amenities",
            "amenities_detail",
            "status",
            "sequence",
            "created_at",
            "updated_at",
        ]

    def validate_code(self, value):
        code = value.upper()
        queryset = RoomType.objects.filter(code=code)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Room type with this code already exists.")
        return code

    def validate_room_type_beds(self, value):
        if not value:
            raise serializers.ValidationError("At least one bed type is required.")
        bed_type_ids = [item["bed_type"].id for item in value]
        if len(bed_type_ids) != len(set(bed_type_ids)):
            raise serializers.ValidationError("Duplicate bed types are not allowed.")
        return value

    def _set_room_type_beds(self, room_type, room_type_beds_data):
        room_type.room_type_beds.all().delete()
        RoomTypeBed.objects.bulk_create(
            RoomTypeBed(room_type=room_type, **bed_data)
            for bed_data in room_type_beds_data
        )

    def create(self, validated_data):
        room_type_beds_data = validated_data.pop("room_type_beds")
        print(room_type_beds_data)
        amenities = validated_data.pop("amenities", [])
        room_type = RoomType.objects.create(**validated_data)
        room_type.amenities.set(amenities)
        self._set_room_type_beds(room_type, room_type_beds_data)
        return room_type

    def update(self, instance, validated_data):
        room_type_beds_data = validated_data.pop("room_type_beds", None)
        instance = super().update(instance, validated_data)
        if room_type_beds_data is not None:
            self._set_room_type_beds(instance, room_type_beds_data)
        return instance
