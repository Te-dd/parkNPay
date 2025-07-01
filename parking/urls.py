from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import CustomLoginView

# Create a router for REST API viewsets
router = DefaultRouter()
router.register(r'users', views.UserProfileViewSet, basename='user')
router.register(r'vehicles', views.VehicleViewSet, basename='vehicle')
router.register(r'locations', views.LocationViewSet, basename='location')
router.register(r'spaces', views.ParkingSpaceViewSet, basename='space')
router.register(r'bookings', views.BookingViewSet, basename='booking')
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'reviews', views.ReviewViewSet, basename='review')

urlpatterns = [
    # Web Views
    path('', views.home, name='home'),
    
    # Owner Dashboard URLs
    path('owner/dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('owner/location/create/', views.location_create, name='location_create'),
    path('owner/location/<int:location_id>/edit/', views.location_edit, name='location_edit'),
    path('owner/location/<int:location_id>/earnings/', views.location_earnings, name='location_earnings'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('signup/', views.signup, name='signup'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('contact/', views.contact, name='contact'),
    path('booking-history/', views.booking_history, name='booking_history'),
    path('location/<int:location_id>/', views.location_spaces, name='location_spaces'),
    path('booking/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('booking/<int:booking_id>/payment/', views.complete_payment, name='complete_payment'),
    path('initiate-booking/', views.initiate_booking, name='initiate_booking'),
    path('complete-booking/', views.complete_booking, name='complete_booking'),

    # Booking QR Code
    path('booking/<int:booking_id>/qr/', views.booking_qr, name='booking_qr'),

    # API Endpoints
    path('api/', include(router.urls)),
    path('api/stats/', views.DashboardStats.as_view(), name='dashboard-stats'),
    path('api/webhook/stripe/', views.PaymentWebhook.as_view(), name='stripe-webhook'),
    path('api/payment/callback/', views.payment_callback, name='payment_callback'),

    # Location Dashboard URLs
    path('location-dashboard/', views.LocationDashboardView.as_view(), name='location_dashboard'),
    path('location-bookings/', views.LocationBookingsView.as_view(), name='location_bookings'),

    # Payment Authentication
    path('payment-auth/', views.payment_auth, name='payment_auth'),

    # M-Pesa Payment URLs
    path('mpesa/stk-push-callback/', views.mpesa_stk_push_callback, name='mpesa_stk_push_callback'),

    # Owner Dashboard URLs
    path('owner/dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('owner/location/create/', views.location_create, name='location_create'),
    path('owner/location/<int:location_id>/edit/', views.location_edit, name='location_edit'),
    path('owner/location/<int:location_id>/earnings/', views.location_earnings, name='location_earnings'),

    # List Your Own Space (Parking List View)
    path('list/', views.list_parking_spaces, name='list'),
]