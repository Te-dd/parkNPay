import qrcode
from io import BytesIO
from django.core.files import File
import json

def generate_booking_qr(booking):
    """
    Generate QR code for a booking containing essential details
    """
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Add booking data to QR code
    qr_data = {
        'booking_id': str(booking.id),
        'space_number': booking.parking_space.space_number,
        'start_time': booking.start_time.isoformat(),
        'end_time': booking.end_time.isoformat(),
        'location': booking.parking_space.location.name,
        'vehicle': booking.vehicle.license_plate if booking.vehicle else None
    }
    
    qr.add_data(json.dumps(qr_data))
    qr.make(fit=True)

    # Create QR code image
    qr_image = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR code
    buffer = BytesIO()
    qr_image.save(buffer, format='PNG')
    buffer.seek(0)
    
    filename = f'booking_qr_{booking.id}.png'
    
    return File(buffer, name=filename)
