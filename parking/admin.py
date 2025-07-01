from django.contrib import admin
from .models import (
    UserProfile, Vehicle, Location, ParkingSpace,
    Booking, Notification, Review, PaymentTransaction
)

class ParkingSpaceInline(admin.TabularInline):
    model = ParkingSpace
    extra = 1

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'is_location_manager', 'managed_location', 'created_at')
    list_filter = ('is_location_manager', 'managed_location')
    search_fields = ('user__username', 'phone_number')

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('license_plate', 'user', 'vehicle_type', 'make', 'model', 'year')
    list_filter = ('vehicle_type', 'is_default')
    search_fields = ('license_plate', 'user__username', 'make', 'model')

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Location Details', {
            'fields': ('latitude', 'longitude', 'address')
        }),
        ('Facilities', {
            'fields': ('has_security', 'has_camera', 'has_lighting', 'is_covered', 'max_height', 'rules', 'restricted_vehicles')
        }),
        ('Pricing', {
            'fields': ('hourly_rate', 'daily_rate', 'monthly_rate')
        }),
        ('Availability', {
            'fields': ('availability_type', 'opening_time', 'closing_time', 'available_days')
        }),
        ('Status', {
            'fields': ('is_active', 'is_verified', 'owner')
        }),
    )
    inlines = [ParkingSpaceInline]

    def total_spaces(self, obj):
        return obj.parkingspace_set.count()
    total_spaces.short_description = 'Total Parking Spaces'

@admin.register(ParkingSpace)
class ParkingSpaceAdmin(admin.ModelAdmin):
    list_display = ('location', 'space_number', 'space_type', 'is_available')
    list_filter = ('location', 'space_type', 'is_available')
    search_fields = ('space_number', 'location__name')
    ordering = ('location', 'space_number')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'parking_space', 'start_time', 'end_time', 'payment_status', 'booking_status')
    list_filter = ('payment_status', 'booking_status', 'start_time', 'end_time')
    search_fields = ('user__username', 'parking_space__location__name')
    date_hierarchy = 'start_time'

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'title', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'booking', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'comment')

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('booking', 'amount', 'currency', 'payment_method', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'currency')
    search_fields = ('transaction_id', 'booking__user__username')

    def has_delete_permission(self, request, obj=None):
        return True  # Explicitly allow deletion