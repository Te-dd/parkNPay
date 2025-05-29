from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Booking, ParkingSpace
from django.utils import timezone
from datetime import datetime, timedelta

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

class BookingForm(forms.ModelForm):
    start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'min': datetime.now().strftime('%Y-%m-%dT%H:%M'),
        })
    )
    end_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'min': datetime.now().strftime('%Y-%m-%dT%H:%M'),
        })
    )
    
    class Meta:
        model = Booking
        fields = ['parking_space', 'start_time', 'end_time']
    
    def __init__(self, *args, **kwargs):
        location = kwargs.pop('location', None)
        super().__init__(*args, **kwargs)
        
        if location:
            self.fields['parking_space'].queryset = ParkingSpace.objects.filter(
                location=location,
                is_available=True
            ).order_by('side', 'space_number')

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        now = timezone.now()

        if start_time and end_time:
            if start_time < now:
                raise forms.ValidationError("Start time cannot be in the past.")
            
            if end_time <= start_time:
                raise forms.ValidationError("End time must be after start time.")
            
            # Check if the duration is at least 1 hour
            if (end_time - start_time) < timedelta(hours=1):
                raise forms.ValidationError("Minimum booking duration is 1 hour.")

        return cleaned_data 