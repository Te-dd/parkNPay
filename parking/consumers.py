import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Location, ParkingSpace, Booking

class LocationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.location_id = self.scope['url_route']['kwargs']['location_id']
        self.room_group_name = f'location_{self.location_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')
        
        if message_type == 'space.update':
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'space_update',
                    'space_id': text_data_json['space_id'],
                    'is_available': text_data_json['is_available']
                }
            )

    # Receive message from room group
    async def space_update(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'space.update',
            'space_id': event['space_id'],
            'is_available': event['is_available']
        }))

class ParkingSpaceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.location_id = self.scope['url_route']['kwargs']['location_id']
        self.location_group_name = f'location_{self.location_id}'

        # Join location group
        await self.channel_layer.group_add(
            self.location_group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial space status
        spaces = await self.get_parking_spaces()
        await self.send(text_data=json.dumps({
            'type': 'initial_status',
            'spaces': spaces
        }))

    async def disconnect(self, close_code):
        # Leave location group
        await self.channel_layer.group_discard(
            self.location_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming messages from clients."""
        pass

    async def space_update(self, event):
        """Handle space status updates."""
        await self.send(text_data=json.dumps({
            'type': 'space_update',
            'space_id': event['space_id'],
            'is_available': event['is_available']
        }))

    @database_sync_to_async
    def get_parking_spaces(self):
        """Get current status of all parking spaces in the location."""
        spaces = ParkingSpace.objects.filter(location_id=self.location_id)
        return [
            {
                'id': space.id,
                'space_number': space.space_number,
                'side': space.side,
                'space_type': space.space_type,
                'is_available': space.is_available,
                'last_update': space.last_status_update.isoformat() if space.last_status_update else None
            }
            for space in spaces
        ]

class BookingNotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
            return

        self.user_id = self.scope["user"].id
        self.notification_group_name = f'user_notifications_{self.user_id}'

        # Join user's notification group
        await self.channel_layer.group_add(
            self.notification_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'notification_group_name'):
            # Leave notification group
            await self.channel_layer.group_discard(
                self.notification_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming messages from clients."""
        pass

    async def notification_message(self, event):
        """Handle new notifications."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))

    async def booking_update(self, event):
        """Handle booking status updates."""
        await self.send(text_data=json.dumps({
            'type': 'booking_update',
            'booking': event['booking']
        })) 