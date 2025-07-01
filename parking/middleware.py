from django.shortcuts import redirect

class BookingSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if 'temporary_booking' in request.session and request.user.is_authenticated:
            if request.path not in ['/complete-booking/', '/clear-booking/']:
                request.session.pop('temporary_booking', None)
        return self.get_response(request)
