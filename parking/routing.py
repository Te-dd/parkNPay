from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/location/(?P<location_id>\w+)/$', consumers.LocationConsumer.as_asgi()),
] 