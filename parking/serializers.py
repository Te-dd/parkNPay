from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    UserProfile, Vehicle, Location, ParkingSpace, 
    Booking, Notification, Review, PaymentTransaction
)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = '__all__'
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'
        read_only_fields = ('id', 'user')

class LocationSerializer(serializers.ModelSerializer):
    available_spaces = serializers.IntegerField(read_only=True)
    rating = serializers.FloatField(read_only=True)
    distance = serializers.FloatField(read_only=True, required=False)

    class Meta:
        model = Location
        fields = (
            'id', 'name', 'description', 'image', 'address', 'city', 'state',
            'country', 'postal_code', 'latitude', 'longitude', 'operating_hours',
            'contact_phone', 'contact_email', 'amenities', 'total_spaces',
            'hourly_rate', 'daily_rate', 'weekly_rate', 'is_active',
            'created_at', 'updated_at', 'available_spaces', 'rating', 'distance'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

class ParkingSpaceSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.name', read_only=True)
    current_booking = serializers.SerializerMethodField()

    class Meta:
        model = ParkingSpace
        fields = '__all__'
        read_only_fields = ('id', 'is_available', 'last_status_update')

    def get_current_booking(self, obj):
        current_booking = obj.booking_set.filter(
            booking_status='active',
            payment_status='paid'
        ).first()
        if current_booking:
            return {
                'id': current_booking.id,
                'start_time': current_booking.start_time,
                'end_time': current_booking.end_time
            }
        return None

class BookingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    parking_space = ParkingSpaceSerializer(read_only=True)
    vehicle = VehicleSerializer(read_only=True)
    parking_space_id = serializers.IntegerField(write_only=True)
    vehicle_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = (
            'id', 'user', 'created_at', 'updated_at', 'payment_status',
            'booking_status', 'amount', 'transaction_id', 'check_in_time',
            'check_out_time', 'extension_count', 'qr_code'
        )

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ('id', 'user', 'created_at', 'sent_at')

class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    booking = BookingSerializer(read_only=True)

    class Meta:
        model = Review
        fields = '__all__'
        read_only_fields = ('id', 'user', 'booking', 'created_at', 'updated_at')

class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

class LocationDetailSerializer(LocationSerializer):
    parking_spaces = ParkingSpaceSerializer(many=True, read_only=True, source='parkingspace_set')
    reviews = ReviewSerializer(many=True, read_only=True, source='parkingspace_set__booking_set__review_set')

    class Meta(LocationSerializer.Meta):
        fields = LocationSerializer.Meta.fields + ('parking_spaces', 'reviews',)

class DashboardStatsSerializer(serializers.Serializer):
    total_bookings = serializers.IntegerField()
    active_bookings = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    available_spaces = serializers.IntegerField()
    occupancy_rate = serializers.FloatField()
    popular_locations = LocationSerializer(many=True)
    recent_transactions = PaymentTransactionSerializer(many=True)
    upcoming_bookings = BookingSerializer(many=True) 