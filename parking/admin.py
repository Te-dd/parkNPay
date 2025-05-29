from django.contrib import admin
from .models import Location, ParkingSpace, Booking

class ParkingSpaceInline(admin.TabularInline):
    model = ParkingSpace
    extra = 1  # Number of empty forms to display
    fields = ['side', 'space_number', 'is_available', 'description']
    ordering = ['side', 'space_number']

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'get_total_spaces', 'get_available_spaces']
    search_fields = ['name', 'description']
    inlines = [ParkingSpaceInline]

    def get_total_spaces(self, obj):
        return obj.parkingspace_set.count()
    get_total_spaces.short_description = 'Total Spaces'

    def get_available_spaces(self, obj):
        return obj.parkingspace_set.filter(is_available=True).count()
    get_available_spaces.short_description = 'Available Spaces'

@admin.register(ParkingSpace)
class ParkingSpaceAdmin(admin.ModelAdmin):
    list_display = ['location', 'side', 'space_number', 'is_available', 'description']
    list_filter = ['location', 'side', 'is_available']
    search_fields = ['location__name', 'space_number', 'description']
    list_editable = ['is_available']
    ordering = ['location', 'side', 'space_number']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['user', 'parking_space', 'start_time', 'end_time', 'payment_status', 'payment_method']
    list_filter = ['payment_status', 'payment_method', 'start_time', 'end_time']
    search_fields = ['user__username', 'parking_space__location__name', 'transaction_id']
    readonly_fields = ['created_at']
    ordering = ['-start_time'] 