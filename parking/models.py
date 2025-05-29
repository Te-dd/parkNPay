from django.db import models
from django.contrib.auth.models import User

class Location(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class ParkingSpace(models.Model):
    SIDE_CHOICES = [
        ('A', 'Side A'),
        ('B', 'Side B'),
        ('C', 'Side C'),
        ('D', 'Side D'),
    ]
    
    location = models.ForeignKey(Location, on_delete=models.CASCADE, null=True)
    space_number = models.CharField(max_length=10)
    side = models.CharField(max_length=1, choices=SIDE_CHOICES, null=True)
    is_available = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ['location', 'side', 'space_number']
        ordering = ['location', 'side', 'space_number']

    def __str__(self):
        if self.location:
            return f"{self.location.name} - Side {self.side} - Space {self.space_number}"
        return f"Space {self.space_number}"

class Booking(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('mpesa', 'M-Pesa'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parking_space = models.ForeignKey(ParkingSpace, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES,
        null=True,
        blank=True
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    transaction_id = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    
    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.user.username} - {self.parking_space} ({self.start_time} to {self.end_time})" 