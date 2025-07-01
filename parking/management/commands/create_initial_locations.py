from django.core.management.base import BaseCommand
from parking.models import Location, ParkingSpace

class Command(BaseCommand):
    help = 'Creates initial parking locations'

    def handle(self, *args, **kwargs):
        locations_data = [
            {
                'name': 'Westgate Mall',
                'description': 'Parking at Westgate Mall, Westlands',
                'address': 'Ring Road Westlands, Nairobi',
                'postal_code': '00100',
                'latitude': -1.2571,
                'longitude': 36.8027,
                'contact_number': '+254 700 000001',
                'sides': ['A', 'B', 'C'],
                'spaces_per_side': 10
            },
            {
                'name': 'Garden City Mall',
                'description': 'Parking at Garden City Mall, Thika Road',
                'address': 'Garden City Mall, Thika Road, Nairobi',
                'postal_code': '00200',
                'latitude': -1.2547,
                'longitude': 36.9010,
                'contact_number': '+254 700 000002',
                'sides': ['A', 'B', 'C', 'D'],
                'spaces_per_side': 15
            },
            {
                'name': 'Two Rivers Mall',
                'description': 'Parking at Two Rivers Mall, Limuru Road',
                'address': 'Limuru Road, Nairobi',
                'postal_code': '00300',
                'latitude': -1.2232,
                'longitude': 36.7851,
                'contact_number': '+254 700 000003',
                'sides': ['A', 'B', 'C', 'D', 'E'],
                'spaces_per_side': 20
            },
            {
                'name': 'The Hub Karen',
                'description': 'Parking at The Hub, Karen',
                'address': 'Karen Road, Nairobi',
                'postal_code': '00400',
                'latitude': -1.3623,
                'longitude': 36.6855,
                'contact_number': '+254 700 000004',
                'sides': ['A', 'B'],
                'spaces_per_side': 12
            }
        ]

        for loc_data in locations_data:
            location = Location.objects.create(
                name=loc_data['name'],
                description=loc_data['description'],
                address=loc_data['address'],
                postal_code=loc_data['postal_code'],
                latitude=loc_data['latitude'],
                longitude=loc_data['longitude'],
                contact_number=loc_data['contact_number']
            )

            # Create parking spaces for each side
            for side in loc_data['sides']:
                for number in range(1, loc_data['spaces_per_side'] + 1):
                    ParkingSpace.objects.create(
                        location=location,
                        side=side,
                        space_number=number,
                        is_available=True
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f'Created {location.name} with {location.parkingspace_set.count()} spaces')
            )
