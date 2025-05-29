from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.http import JsonResponse
from .forms import SignUpForm, BookingForm
from .models import ParkingSpace, Booking, Location
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
from django.views.decorators.http import require_http_methods
from datetime import timedelta
import math

def calculate_booking_amount(start_time, end_time):
    """Calculate booking amount based on duration."""
    duration = end_time - start_time
    total_hours = duration.total_seconds() / 3600
    total_days = duration.days
    remaining_hours = (total_hours - (total_days * 24))

    # If duration is less than 24 hours, charge by hour
    if total_days == 0:
        amount = math.ceil(total_hours) * 30  # 30 KES per hour
    else:
        # Charge full days at daily rate
        amount = total_days * 200  # 200 KES per day
        # Add remaining hours at hourly rate
        if remaining_hours > 0:
            amount += math.ceil(remaining_hours) * 30

    return Decimal(str(amount))

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = SignUpForm()
    return render(request, 'parking/signup.html', {'form': form})

@login_required
def dashboard(request):
    user_bookings = Booking.objects.filter(user=request.user)
    locations = Location.objects.all()
    
    context = {
        'bookings': user_bookings,
        'locations': locations,
    }
    return render(request, 'parking/dashboard.html', context)

@login_required
def location_spaces(request, location_id):
    location = get_object_or_404(Location, id=location_id)
    current_time = timezone.now()
    
    # Get all spaces for this location
    spaces = ParkingSpace.objects.filter(location=location).order_by('side', 'space_number')
    
    # Get active bookings (ongoing or future bookings)
    active_bookings = Booking.objects.filter(
        Q(parking_space__location=location),
        Q(start_time__lte=current_time, end_time__gt=current_time) |  # Current bookings
        Q(start_time__gt=current_time),  # Future bookings
        payment_status__in=['pending', 'paid']
    )
    
    # Update space availability based on current bookings
    for space in spaces:
        space_bookings = active_bookings.filter(parking_space=space)
        space.is_available = not space_bookings.exists()
        space.save()
    
    if request.method == 'POST':
        form = BookingForm(request.POST, location=location)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            
            # Check if the space is already booked for the selected time
            conflicting_bookings = Booking.objects.filter(
                parking_space=booking.parking_space,
                start_time__lt=booking.end_time,
                end_time__gt=booking.start_time,
                payment_status__in=['pending', 'paid']
            )
            
            if conflicting_bookings.exists():
                messages.error(request, 'This space is already booked for the selected time period.')
            else:
                # Set payment status as pending
                booking.payment_status = 'pending'
                # Calculate amount based on duration
                booking.amount = calculate_booking_amount(booking.start_time, booking.end_time)
                booking.save()
                
                # Update space availability
                space = booking.parking_space
                space.is_available = False
                space.save()
                
                messages.success(request, 'Booking successful! Please complete the payment.')
                return redirect('dashboard')
    else:
        form = BookingForm(location=location)
    
    context = {
        'location': location,
        'available_spaces': spaces,
        'form': form
    }
    return render(request, 'parking/location_spaces.html', context)

@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if request.method == 'POST':
        # Only allow cancellation if payment status is pending or if it's paid but not yet started
        if booking.payment_status == 'pending' or (booking.payment_status == 'paid' and booking.start_time > timezone.now()):
            # Update space availability
            space = booking.parking_space
            space.is_available = True
            space.save()
            
            booking.delete()
            messages.success(request, 'Booking cancelled successfully.')
        else:
            messages.error(request, 'This booking cannot be cancelled.')
        return redirect('dashboard')
    
    return render(request, 'parking/cancel_booking.html', {'booking': booking})

@login_required
def complete_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if booking.payment_status != 'pending':
        messages.error(request, 'This booking has already been paid for or cancelled.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        if payment_method in ['mpesa', 'card']:
            booking.payment_method = payment_method
            booking.payment_status = 'paid'  # In a real app, this would happen after payment confirmation
            booking.save()
            messages.success(request, f'Payment completed successfully via {payment_method.upper()}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid payment method selected.')
    
    return render(request, 'parking/complete_payment.html', {'booking': booking})

@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login') 