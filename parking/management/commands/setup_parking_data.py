from django.core.management.base import BaseCommand
from parking.models import Location, ParkingSpace

class Command(BaseCommand):
    help = 'Sets up initial parking locations and spaces'

    def handle(self, *args, **kwargs):
        # Create locations
        locations = [
            {
                'name': 'Mall A - Main Building',
                'description': 'Located at the main entrance of Mall A',
                'spaces': 5
            },
            {
                'name': 'Mall B - West Wing',
                'description': 'Located near the food court entrance',
                'spaces': 5
            },
            {
                'name': 'Mall C - East Plaza',
                'description': 'Near the cinema complex',
                'spaces': 5
            },
            {
                'name': 'Mall D - South Gate',
                'description': 'Next to the department store',
                'spaces': 5
            }
        ]
        
        for loc_data in locations:
            location, created = Location.objects.get_or_create(
                name=loc_data['name'],
                defaults={'description': loc_data['description']}
            )
            
            if created:
                self.stdout.write(f'Created location: {location.name}')
                
                # Create parking spaces for each side (A, B, C, D)
                for side in ['A', 'B', 'C', 'D']:
                    for num in range(1, loc_data['spaces'] + 1):
                        space = ParkingSpace.objects.create(
                            location=location,
                            space_number=str(num),
                            side=side,
                            is_available=True,
                            description=f"Regular parking space {num} on side {side}"
                        )
                        self.stdout.write(f'Created space: {space}') 