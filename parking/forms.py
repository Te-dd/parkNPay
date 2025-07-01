from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Booking, ParkingSpace, Location, LocationImage
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
            ).order_by('space_number')

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

class CustomLoginForm(AuthenticationForm):
    USER_TYPES = [
        ('user', 'Regular User'),
        ('admin', 'Administrator')
    ]
    
    user_type = forms.ChoiceField(
        choices=USER_TYPES,
        widget=forms.RadioSelect(attrs={'class': 'form-radio'}),
        initial='user'
    )

class LocationForm(forms.ModelForm):
    available_days = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': '[0, 1, 2, 3, 4, 5, 6] (as JSON list)'}),
        help_text='Enter a JSON list of integers for days (0=Mon, 6=Sun)'
    )

    class Meta:
        model = Location
        fields = [
            'name', 'description', 'address', 'postal_code',
            'latitude', 'longitude', 'hourly_rate', 'daily_rate',
            'monthly_rate', 'availability_type', 'opening_time',
            'closing_time', 'available_days', 'has_security',
            'has_camera', 'has_lighting', 'is_covered',
            'max_height', 'rules', 'restricted_vehicles'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'rules': forms.Textarea(attrs={'rows': 4}),
            'opening_time': forms.TimeInput(attrs={'type': 'time'}),
            'closing_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean_available_days(self):
        import json
        data = self.cleaned_data.get('available_days')
        if not data:
            return []
        try:
            days = json.loads(data)
            if not isinstance(days, list):
                raise forms.ValidationError('Must be a JSON list of integers.')
            return days
        except Exception:
            raise forms.ValidationError('Invalid JSON format for available days.')

class LocationImageForm(forms.ModelForm):
    class Meta:
        model = LocationImage
        fields = ['image', 'is_primary']
