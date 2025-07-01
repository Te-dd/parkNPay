@login_required
def location_edit(request, location_id):
    location = get_object_or_404(Location, id=location_id, owner=request.user)
    
    if request.method == 'POST':
        form = LocationForm(request.POST, instance=location)
        image_form = LocationImageForm(request.POST, request.FILES)
        
        if form.is_valid():
            form.save()
            if image_form.is_valid() and image_form.cleaned_data.get('image'):
                image = image_form.save(commit=False)
                image.location = location
                image.save()
            
            messages.success(request, 'Location updated successfully!')
            return redirect('owner_dashboard')
    else:
        form = LocationForm(instance=location)
        image_form = LocationImageForm()
    
    return render(request, 'parking/location_form.html', {
        'form': form,
        'image_form': image_form,
        'location': location,
        'title': 'Edit Location'
    })

@login_required
def location_earnings(request, location_id):
    location = get_object_or_404(Location, id=location_id, owner=request.user)
    
    # Get date range from request or default to current month
    start_date = request.GET.get('start_date', timezone.now().replace(day=1).date())
    end_date = request.GET.get('end_date', timezone.now().date())
    
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    earnings = LocationEarning.objects.filter(
        location=location,
        date__range=[start_date, end_date]
    ).order_by('-date')
    
    total = earnings.aggregate(total=Sum('amount'))['total'] or 0
    
    return render(request, 'parking/location_earnings.html', {
        'location': location,
        'earnings': earnings,
        'total': total,
        'start_date': start_date,
        'end_date': end_date
    })
