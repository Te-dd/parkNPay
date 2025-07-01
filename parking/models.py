from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    default_payment_method = models.CharField(max_length=50, blank=True)
    notification_preferences = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_location_manager = models.BooleanField(default=False)
    managed_location = models.ForeignKey(
        'Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managers'
    )

    def __str__(self):
        return f"{self.user.username}'s Profile"

class Vehicle(models.Model):
    VEHICLE_TYPES = [
        ('car', 'Car'),
        ('motorcycle', 'Motorcycle'),
        ('van', 'Van'),
        ('truck', 'Truck'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    license_plate = models.CharField(max_length=20)
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.IntegerField(validators=[MinValueValidator(1900), MaxValueValidator(2100)])
    color = models.CharField(max_length=30)
    is_default = models.BooleanField(default=False)

    class Meta:
        unique_together = ['user', 'license_plate']

    def __str__(self):
        return f"{self.license_plate} - {self.make} {self.model}"

class Location(models.Model):
    AVAILABILITY_24_7 = '24/7'
    AVAILABILITY_CUSTOM = 'custom'
    AVAILABILITY_CHOICES = [
        (AVAILABILITY_24_7, '24/7'),
        (AVAILABILITY_CUSTOM, 'Custom Hours'),
    ]

    name = models.CharField(max_length=200)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_locations')
    description = models.TextField()
    address = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=10)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    # Pricing
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2)
    monthly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Availability
    availability_type = models.CharField(max_length=10, choices=AVAILABILITY_CHOICES, default=AVAILABILITY_24_7)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    available_days = models.JSONField(default=list)  # List of days when parking is available
    
    # Features and Rules
    has_security = models.BooleanField(default=False)
    has_camera = models.BooleanField(default=False)
    has_lighting = models.BooleanField(default=False)
    is_covered = models.BooleanField(default=False)
    max_height = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    rules = models.TextField(blank=True)
    restricted_vehicles = models.JSONField(default=list)  # List of vehicle types not allowed
    
    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class ParkingSpace(models.Model):
    SPACE_TYPE_CHOICES = [
        ('standard', 'Standard'),
        ('covered', 'Covered'),
        ('handicap', 'Handicap'),
        ('ev', 'Electric Vehicle'),
        ('vip', 'VIP'),
    ]
    
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    space_number = models.CharField(max_length=10)
    space_type = models.CharField(max_length=20, choices=SPACE_TYPE_CHOICES, default='standard')
    is_available = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    dimensions = models.JSONField(default=dict)  # {"length": "5.5m", "width": "2.5m"}
    features = models.JSONField(default=list)
    last_status_update = models.DateTimeField(auto_now=True)
    sensor_id = models.CharField(max_length=50, blank=True)  # For IoT integration

    class Meta:
        unique_together = ['location', 'space_number']
        ordering = ['location', 'space_number']

    def __str__(self):
        return f"{self.location.name} - Space {self.space_number}"

class Booking(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('mpesa', 'M-Pesa'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
    ]

    BOOKING_STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True)
    parking_space = models.ForeignKey(ParkingSpace, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending')
    booking_status = models.CharField(max_length=10, choices=BOOKING_STATUS_CHOICES, default='active')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    extension_count = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    qr_code = models.ImageField(upload_to='booking_qr_codes/', blank=True, null=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.user.username} - {self.parking_space} ({self.start_time} to {self.end_time})"

    def is_active(self):
        return self.start_time <= timezone.now() <= self.end_time and self.booking_status == 'active'

    def can_extend(self):
        return self.is_active() and self.extension_count < 3

    def generate_qr_code(self):
        """Generate QR code for the booking"""
        from .utils import generate_booking_qr
        self.qr_code = generate_booking_qr(self)
        self.save()

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('booking_confirmation', 'Booking Confirmation'),
        ('payment_confirmation', 'Payment Confirmation'),
        ('booking_reminder', 'Booking Reminder'),
        ('expiry_reminder', 'Expiry Reminder'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('payment_failed', 'Payment Failed'),
        ('booking_modified', 'Booking Modified'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.type} - {self.created_at}"

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.booking.parking_space.location.name} - {self.rating}★"

class PaymentTransaction(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20)
    payment_gateway_response = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.booking.user.username} - {self.amount} {self.currency} - {self.status}"

class LocationImage(models.Model):
    location = models.ForeignKey(Location, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='location_images/')
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', '-created_at']

class LocationEarning(models.Model):
    location = models.ForeignKey(Location, related_name='earnings', on_delete=models.CASCADE)
    booking = models.ForeignKey('Booking', on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ])
    created_at = models.DateTimeField(auto_now_add=True)