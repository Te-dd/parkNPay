from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from parking import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard, name='dashboard'),
    path('location/<int:location_id>/', views.location_spaces, name='location_spaces'),
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='parking/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('booking/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('booking/<int:booking_id>/payment/', views.complete_payment, name='complete_payment'),
] 