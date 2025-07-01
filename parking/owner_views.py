from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime
from .models import Location, LocationEarning, Booking
from .forms import LocationForm, LocationImageForm

@login_required
def owner_dashboard(request):
    locations = Location.objects.filter(owner=request.user)
    total_earnings = LocationEarning.objects.filter(
        location__owner=request.user,
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    recent_bookings = Booking.objects.filter(
        parking_space__location__owner=request.user
    ).order_by('-created_at')[:5]
    
    context = {
        'locations': locations,
        'total_earnings': total_earnings,
        'recent_bookings': recent_bookings,
    }
    return render(request, 'parking/owner_dashboard.html', context)

@login_required
def location_create(request):
    if request.method == 'POST':
        form = LocationForm(request.POST)
        image_form = LocationImageForm(request.POST, request.FILES)
        
        if form.is_valid() and image_form.is_valid():
            location = form.save(commit=False)
            location.owner = request.user
            location.save()
            
            if image_form.cleaned_data.get('image'):
                image = image_form.save(commit=False)
                image.location = location
                image.save()
            
            messages.success(request, 'Location created successfully!')
            return redirect('owner_dashboard')
    else:
        form = LocationForm()
        image_form = LocationImageForm()
    
    return render(request, 'parking/location_form.html', {
        'form': form,
        'image_form': image_form,
        'title': 'Add New Location'
    })
