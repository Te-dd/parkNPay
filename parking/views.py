from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login, logout, authenticate
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.conf import settings
from django_daraja.mpesa.core import MpesaClient
import json
from .forms import SignUpForm, BookingForm, CustomLoginForm, LocationForm, LocationImageForm
from .models import ParkingSpace, Booking, Location, LocationEarning, LocationImage
from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum
from decimal import Decimal
from django.views.decorators.http import require_http_methods
from datetime import timedelta
import math
from django.core.mail import send_mail
from django.conf import settings

from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

import stripe
import qrcode
from io import BytesIO

from .models import (
    UserProfile, Vehicle, Notification, Review, PaymentTransaction
)
from .serializers import (
    UserProfileSerializer, VehicleSerializer, LocationSerializer,
    ParkingSpaceSerializer, BookingSerializer, NotificationSerializer,
    ReviewSerializer, PaymentTransactionSerializer, LocationDetailSerializer,
    DashboardStatsSerializer
)
from geopy.distance import geodesic
from django.urls import reverse
from rest_framework import serializers

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

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
            auth_login(request, user)
            return redirect('dashboard')
    else:
        form = SignUpForm()
    return render(request, 'parking/signup.html', {'form': form})

def dashboard(request):
    current_time = timezone.now()
    
    # Get active bookings for the user
    bookings = []
    if request.user.is_authenticated:
        bookings = Booking.objects.filter(
            user=request.user,
            end_time__gt=current_time,
        ).select_related('parking_space', 'parking_space__location').order_by('start_time')
    
    # Get locations with annotated stats
    locations = Location.objects.all()
    for location in locations:
        total_spaces = ParkingSpace.objects.filter(location=location).count()
        available_count = ParkingSpace.objects.filter(location=location, is_available=True).count()
        location.available_spaces = available_count
        location.total_spaces = total_spaces
        location.occupancy_rate = round(((total_spaces - available_count) / total_spaces * 100) if total_spaces > 0 else 0, 1)
    
    context = {
        'locations': locations,
        'bookings': bookings,
    }
    return render(request, 'parking/dashboard.html', context)

@login_required
def booking_history(request):
    current_time = timezone.now()
    past_bookings = Booking.objects.filter(
        user=request.user,
        end_time__lte=current_time
    ).order_by('-end_time')
    
    context = {
        'past_bookings': past_bookings,
    }
    return render(request, 'parking/booking_history.html', context)

def location_spaces(request, location_id):
    location = get_object_or_404(Location, id=location_id)
    current_time = timezone.now()
    
    # Get all spaces for this location
    spaces = ParkingSpace.objects.filter(location=location).order_by('space_number')
    
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
        if not request.user.is_authenticated:
            # Store the intended location in session
            request.session['intended_location'] = location_id
            return redirect(f"{reverse('login')}?next={reverse('location_spaces', args=[location_id])}")
            
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
                return redirect('location_spaces', location_id=location_id)
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
                
                messages.success(request, 'Booking created successfully! Please complete the payment.')
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

from django_daraja.mpesa.core import MpesaClient
from decouple import config
import json

@login_required
def complete_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if booking.payment_status != 'pending':
        messages.error(request, 'This booking has already been paid for or cancelled.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        if not phone_number:
            messages.error(request, 'Please provide a phone number.')
            return render(request, 'parking/complete_payment.html', {'booking': booking})

        # Clean and validate phone number
        phone_number = phone_number.replace('+', '').replace(' ', '')
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif phone_number.startswith('7'):
            phone_number = '254' + phone_number
            
        if not phone_number.startswith('254') or len(phone_number) != 12:
            messages.error(request, 'Please enter a valid Kenyan phone number.')
            return render(request, 'parking/complete_payment.html', {'booking': booking})

        try:
            # Initialize M-Pesa client
            cl = MpesaClient()
            
            # Calculate amount
            amount = int(booking.amount)
            
            # Set callback URL
            callback_url = 'https://darajambili.herokuapp.com/express-payment'
            
            # Set reference and description
            account_reference = f'ParkNPay-{booking.id}'
            transaction_desc = f'Parking Payment - Space {booking.parking_space.space_number}'
            
            # Make the STK push request
            response = cl.stk_push(phone_number, amount, account_reference, transaction_desc, callback_url)
            
            print(f"M-Pesa Response: {response}")
            
            if response.get('ResponseCode') == '0':
                booking.transaction_id = response.get('CheckoutRequestID')
                booking.payment_method = 'mpesa'
                booking.save()
                messages.success(request, 'Please check your phone to complete the payment.')
                return redirect('dashboard')
            else:
                messages.error(request, f'Payment failed: {response.get("ResponseDescription", "Unknown error")}')
                
        except Exception as e:
            print(f"M-Pesa Error: {str(e)}")
            messages.error(request, 'Payment processing error. Please try again.')
    
    return render(request, 'parking/complete_payment.html', {'booking': booking})

@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('home')

def home(request):
    locations = Location.objects.all()
    
    # Get total available spaces
    total_spaces = ParkingSpace.objects.count()
    available_spaces = ParkingSpace.objects.filter(is_available=True).count()
    
    # Get current time
    current_time = timezone.now()
    
    # Get active bookings (current and future)
    active_bookings = Booking.objects.filter(
        Q(start_time__lte=current_time, end_time__gt=current_time) |  # Current bookings
        Q(start_time__gt=current_time),  # Future bookings
        payment_status='paid'
    ).count()
    
    context = {
        'locations': locations,
        'total_spaces': total_spaces,
        'available_spaces': available_spaces,
        'active_bookings': active_bookings,
    }
    return render(request, 'parking/home.html', context)

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        # Send email
        try:
            send_mail(
                f'Contact Form Message from {name}',
                message,
                email,
                [settings.DEFAULT_FROM_EMAIL],
                fail_silently=False,
            )
            messages.success(request, 'Your message has been sent successfully!')
            return redirect('contact')
        except Exception as e:
            messages.error(request, 'Failed to send message. Please try again later.')
            return redirect('contact')
    
    return render(request, 'parking/contact.html')

def login_view(request):
    if request.method == 'POST':
        form = CustomLoginForm(data=request.POST)
        if form.is_valid():
            user = authenticate(username=form.cleaned_data['username'],
                             password=form.cleaned_data['password'])
            if user is not None:
                auth_login(request, user)
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
    else:
        form = CustomLoginForm()
    return render(request, 'parking/login.html', {'form': form})

from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    form_class = CustomLoginForm
    success_url = reverse_lazy('dashboard')
    
    def form_valid(self, form):
        user_type = form.cleaned_data.get('user_type')
        response = super().form_valid(form)
        
        if user_type == 'admin' and self.request.user.is_staff:
            return redirect('admin:index')
        elif user_type == 'admin' and not self.request.user.is_staff:
            form.add_error(None, "You don't have administrator privileges")
            return self.form_invalid(form)
        
        next_url = self.request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return response

class UserProfileViewSet(viewsets.ModelViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class VehicleViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Vehicle.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_active', 'city', 'state']
    search_fields = ['name', 'address', 'city']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LocationDetailSerializer
        return LocationSerializer

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """Find parking locations near a specific point."""
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius = float(request.query_params.get('radius', 5))  # Default 5km radius

        if not all([lat, lng]):
            return Response(
                {'error': 'Latitude and longitude are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_location = (float(lat), float(lng))
        locations = Location.objects.filter(is_active=True)
        
        # Calculate distances and filter locations
        nearby_locations = []
        for location in locations:
            location_point = (float(location.latitude), float(location.longitude))
            distance = geodesic(user_location, location_point).km
            
            if distance <= radius:
                location.distance = distance
                nearby_locations.append(location)
        
        # Sort by distance
        nearby_locations.sort(key=lambda x: x.distance)
        
        # Annotate with available spaces and ratings
        for location in nearby_locations:
            location.available_spaces = ParkingSpace.objects.filter(
                location=location,
                is_available=True
            ).count()
            
            avg_rating = Review.objects.filter(
                booking__parking_space__location=location
            ).aggregate(Avg('rating'))['rating__avg']
            location.rating = avg_rating or 0

        serializer = self.get_serializer(nearby_locations, many=True)
        return Response(serializer.data)

class ParkingSpaceViewSet(viewsets.ModelViewSet):
    queryset = ParkingSpace.objects.all()
    serializer_class = ParkingSpaceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['location', 'space_type', 'is_available']

    def get_queryset(self):
        queryset = ParkingSpace.objects.all()
        location_id = self.request.query_params.get('location', None)
        if location_id:
            queryset = queryset.filter(location_id=location_id)
        return queryset

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update space status from IoT sensor."""
        space = self.get_object()
        is_occupied = request.data.get('is_occupied', None)
        
        if is_occupied is not None:
            space.is_available = not is_occupied
            space.last_status_update = timezone.now()
            space.save()

            # Notify clients about space status change
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"location_{space.location.id}",
                {
                    "type": "space.update",
                    "space_id": space.id,
                    "is_available": space.is_available
                }
            )

            return Response({'status': 'updated'})
        return Response(
            {'error': 'is_occupied parameter is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Get parking space and check availability
        space = get_object_or_404(
            ParkingSpace,
            id=self.request.data.get('parking_space_id')
        )
        
        # Check for conflicting bookings
        start_time = serializer.validated_data['start_time']
        end_time = serializer.validated_data['end_time']
        conflicting_bookings = Booking.objects.filter(
            parking_space=space,
            start_time__lt=end_time,
            end_time__gt=start_time,
            payment_status__in=['pending', 'paid']
        )

        if conflicting_bookings.exists():
            raise serializers.ValidationError(
                'This space is already booked for the selected time period.'
            )

        # Calculate booking amount
        duration = end_time - start_time
        amount = calculate_booking_amount(start_time, end_time)

        # Create Stripe payment intent
        payment_intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Convert to cents
            currency='usd',
            metadata={'booking_id': 'pending'}
        )

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(f"booking_verification_{payment_intent.id}")
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Save QR code
        buffer = BytesIO()
        qr_image.save(buffer, format="PNG")
        
        # Save booking
        booking = serializer.save(
            user=self.request.user,
            amount=amount,
            payment_status='pending',
            qr_code=buffer.getvalue()
        )

        # Update payment intent with actual booking ID
        stripe.PaymentIntent.modify(
            payment_intent.id,
            metadata={'booking_id': str(booking.id)}
        )

        # Create notification
        Notification.objects.create(
            user=self.request.user,
            booking=booking,
            type='booking_confirmation',
            title='Booking Confirmation',
            message=f'Your booking for {space.location.name} has been confirmed.'
        )

        return booking

    @action(detail=True, methods=['post'])
    def extend(self, request, pk=None):
        """Extend an existing booking."""
        booking = self.get_object()
        hours = int(request.data.get('hours', 1))
        
        if not booking.can_extend():
            return Response(
                {'error': 'Booking cannot be extended'},
                status=status.HTTP_400_BAD_REQUEST
            )

        new_end_time = booking.end_time + timedelta(hours=hours)
        additional_amount = calculate_booking_amount(
            booking.end_time,
            new_end_time
        )

        # Create Stripe payment intent for extension
        payment_intent = stripe.PaymentIntent.create(
            amount=int(additional_amount * 100),
            currency='usd',
            metadata={'booking_id': str(booking.id), 'is_extension': 'true'}
        )

        booking.end_time = new_end_time
        booking.amount += additional_amount
        booking.extension_count += 1
        booking.save()

        return Response({
            'booking': BookingSerializer(booking).data,
            'client_secret': payment_intent.client_secret
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking."""
        booking = self.get_object()
        
        if booking.start_time <= timezone.now():
            return Response(
                {'error': 'Cannot cancel an active or completed booking'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if booking.payment_status == 'paid':
            # Process refund through Stripe
            refund = stripe.Refund.create(
                payment_intent=booking.transaction_id
            )
            
            if refund.status == 'succeeded':
                booking.payment_status = 'refunded'
                booking.booking_status = 'cancelled'
                booking.save()

                # Create notification
                Notification.objects.create(
                    user=booking.user,
                    booking=booking,
                    type='booking_cancelled',
                    title='Booking Cancelled',
                    message=f'Your booking for {booking.parking_space.location.name} has been cancelled and refunded.'
                )

                return Response({'status': 'cancelled and refunded'})
            else:
                return Response(
                    {'error': 'Refund failed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            booking.booking_status = 'cancelled'
            booking.save()
            return Response({'status': 'cancel'})

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a notification as read."""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})

class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Review.objects.filter(
            Q(user=self.request.user) |
            Q(booking__parking_space__location__parkingspace__booking__user=self.request.user)
        ).distinct()

    def perform_create(self, serializer):
        booking = get_object_or_404(
            Booking,
            id=self.request.data.get('booking_id'),
            user=self.request.user
        )
        serializer.save(user=self.request.user, booking=booking)

class PaymentWebhook(APIView):
    permission_classes = []

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META['HTTP_STRIPE_SIGNATURE']

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if event.type == 'payment_intent.succeeded':
            payment_intent = event.data.object
            booking_id = payment_intent.metadata.get('booking_id')
            
            if booking_id:
                booking = get_object_or_404(Booking, id=booking_id)
                booking.payment_status = 'paid'
                booking.transaction_id = payment_intent.id
                booking.save()

                # Create payment transaction record
                PaymentTransaction.objects.create(
                    booking=booking,
                    amount=booking.amount,
                    payment_method='stripe',
                    transaction_id=payment_intent.id,
                    status='completed',
                    payment_gateway_response=payment_intent
                )

                # Create notification
                Notification.objects.create(
                    user=booking.user,
                    booking=booking,
                    type='payment_confirmation',
                    title='Payment Confirmation',
                    message=f'Payment for your booking at {booking.parking_space.location.name} has been confirmed.'
                )

        return Response(status=status.HTTP_200_OK)

class DashboardStats(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get dashboard statistics for facility owners."""
        user = request.user
        locations = Location.objects.filter(parkingspace__booking__user=user)

        # Calculate statistics
        total_bookings = Booking.objects.filter(
            parking_space__location__in=locations
        ).count()

        active_bookings = Booking.objects.filter(
            parking_space__location__in=locations,
            booking_status='active'
        ).count()

        total_revenue = PaymentTransaction.objects.filter(
            booking__parking_space__location__in=locations,
            status='completed'
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        available_spaces = ParkingSpace.objects.filter(
            location__in=locations,
            is_available=True
        ).count()

        total_spaces = ParkingSpace.objects.filter(
            location__in=locations
        ).count()

        occupancy_rate = (
            (total_spaces - available_spaces) / total_spaces * 100
            if total_spaces > 0 else 0
        )

        popular_locations = Location.objects.filter(
            id__in=locations
        ).annotate(
            booking_count=Count('parkingspace__booking')
        ).order_by('-booking_count')[:5]

        recent_transactions = PaymentTransaction.objects.filter(
            booking__parking_space__location__in=locations
        ).order_by('-created_at')[:10]

        upcoming_bookings = Booking.objects.filter(
            parking_space__location__in=locations,
            start_time__gt=timezone.now()
        ).order_by('start_time')[:10]

        data = {
            'total_bookings': total_bookings,
            'active_bookings': active_bookings,
            'total_revenue': total_revenue,
            'available_spaces': available_spaces,
            'occupancy_rate': occupancy_rate,
            'popular_locations': LocationSerializer(popular_locations, many=True).data,
            'recent_transactions': PaymentTransactionSerializer(recent_transactions, many=True).data,
            'upcoming_bookings': BookingSerializer(upcoming_bookings, many=True).data
        }

        serializer = DashboardStatsSerializer(data)
        return Response(serializer.data)

def initiate_booking(request):
    if request.method == 'POST':
        # Store booking details in session
        request.session['temporary_booking'] = {
            'parking_space_id': request.POST.get('parking_space_id'),
            'start_time': request.POST.get('start_time'),
            'end_time': request.POST.get('end_time'),
        }
        
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={reverse('complete_booking')}")
        return redirect('complete_booking')

@login_required
def complete_booking(request):
    booking_data = request.session.get('temporary_booking')
    if not booking_data:
        return redirect('parking_search')
        
    # Create the actual booking
    booking = Booking.objects.create(
        user=request.user,
        parking_space_id=booking_data['parking_space_id'],
        start_time=booking_data['start_time'],
        end_time=booking_data['end_time']
    )
    
    request.session.pop('temporary_booking', None)
    return redirect('booking_confirmation', booking_id=booking.id)

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class LocationDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'parking/location_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_profile = UserProfile.objects.get(user=self.request.user)
        
        if not user_profile.is_location_manager:
            return redirect('dashboard')

        location = user_profile.managed_location
        current_time = timezone.now()

        context.update({
            'location': location,
            'total_spaces': ParkingSpace.objects.filter(location=location).count(),
            'available_spaces': ParkingSpace.objects.filter(location=location, is_available=True).count(),
            'active_bookings': Booking.objects.filter(
                parking_space__location=location,
                start_time__lte=current_time,
                end_time__gte=current_time
            ).count(),
            'today_revenue': PaymentTransaction.objects.filter(
                booking__parking_space__location=location,
                created_at__date=current_time.date(),
                status='completed'
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
        })
        return context

@csrf_exempt
def mpesa_callback(request):
    if request.method == 'POST':
        try:
            data = request.body
            print(f"M-Pesa Callback Data: {data}")
            return HttpResponse("STK Push in Django👋")
        except Exception as e:
            print(f"Callback Error: {str(e)}")
            return HttpResponse("Error", status=500)
    return HttpResponse("Invalid request", status=400)

class LocationBookingsView(LoginRequiredMixin, TemplateView):
    template_name = 'parking/location_bookings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_profile = UserProfile.objects.get(user=self.request.user)
        
        if not user_profile.is_location_manager:
            return redirect('dashboard')

        location = user_profile.managed_location
        current_time = timezone.now()

        context.update({
            'location': location,
            'active_bookings': Booking.objects.filter(
                parking_space__location=location,
                start_time__lte=current_time,
                end_time__gte=current_time
            ).order_by('start_time'),
            'upcoming_bookings': Booking.objects.filter(
                parking_space__location=location,
                start_time__gt=current_time
            ).order_by('start_time'),
        })
        return context

def payment_auth(request):
    """Handle authentication before payment."""
    booking_id = request.session.get('pending_booking_id')
    
    if not booking_id:
        messages.error(request, 'No pending booking found.')
        return redirect('home')
    
    if request.user.is_authenticated:
        return redirect('complete_payment', booking_id=booking_id)
    
    if request.method == 'POST':
        if 'login' in request.POST:
            form = CustomLoginForm(data=request.POST)
            if form.is_valid():
                user = authenticate(username=form.cleaned_data['username'],
                                 password=form.cleaned_data['password'])
                if user is not None:
                    auth_login(request, user)
                    booking = get_object_or_404(Booking, id=booking_id)
                    booking.user = user
                    booking.save()
                    return redirect('complete_payment', booking_id=booking_id)
        else:
            form = SignUpForm(request.POST)
            if form.is_valid():
                user = form.save()
                auth_login(request, user)
                booking = get_object_or_404(Booking, id=booking_id)
                booking.user = user
                booking.save()
                return redirect('complete_payment', booking_id=booking_id)
    else:
        login_form = CustomLoginForm()
        signup_form = SignUpForm()
    
    return render(request, 'parking/payment_auth.html', {
        'login_form': login_form,
        'signup_form': signup_form,
        'booking_id': booking_id
    })

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json

@csrf_exempt
def payment_callback(request):
    """Handle M-Pesa payment callback"""
    if request.method == 'POST':
        try:
            # Parse the response from M-Pesa
            stk_response = json.loads(request.body)
            result = stk_response.get('Body', {}).get('stkCallback', {})
            
            # Get the merchant request ID which we stored as transaction_id
            merchant_request_id = result.get('MerchantRequestID')
            
            # Find the booking by transaction ID
            try:
                booking = Booking.objects.get(transaction_id=merchant_request_id)
                
                # Check if payment was successful
                result_code = result.get('ResultCode')
                if result_code == 0:  # Successful payment
                    booking.payment_status = 'paid'
                    booking.save()
                    
                    # Create notification
                    Notification.objects.create(
                        user=booking.user,
                        booking=booking,
                        type='payment_success',
                        title='Payment Successful',
                        message=f'Your payment of KES {booking.amount} for booking #{booking.id} was successful.'
                    )
                else:
                    # Payment failed
                    booking.payment_status = 'failed'
                    booking.save()
                    
                    # Create notification
                    Notification.objects.create(
                        user=booking.user,
                        booking=booking,
                        type='payment_failed',
                        title='Payment Failed',
                        message=f'Your payment for booking #{booking.id} failed. Please try again.'
                    )
            
            except Booking.DoesNotExist:
                # Log error if booking not found
                print(f"Booking not found for merchant request ID: {merchant_request_id}")
                
            return HttpResponse(status=200)
            
        except json.JSONDecodeError:
            return HttpResponse(status=400)
            
    return HttpResponse(status=405)  # Method not allowed

@csrf_exempt
def mpesa_stk_push_callback(request):
    """Handle M-Pesa STK push callback"""
    data = request.body
    return HttpResponse("STK Push in Django👋")

@login_required
def booking_qr(request, booking_id):
    """Display booking QR code"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Generate QR code if it doesn't exist
    if not booking.qr_code:
        booking.generate_qr_code()
    
    return render(request, 'parking/booking_qr.html', {'booking': booking})

# Owner Dashboard Views
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

@login_required
def list_parking_spaces(request):
    """View for users to list and manage their own parking spaces."""
    user = request.user
    # Use the related_name 'owned_locations' if set, else fallback to filter
    my_locations = getattr(user, 'owned_locations', Location.objects.filter(owner=user))
    if hasattr(my_locations, 'all'):
        my_locations = my_locations.all()
    return render(request, 'parking/list.html', {'my_locations': my_locations})