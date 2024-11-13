# routing.py

from django.urls import path

from server.protocols.tcp.ws import consumers

websocket_urlpatterns = [
    path('ws/chat/<str:chat_id>/<str:client_id>/<str:client_type>/', consumers.ChatConsumer.as_asgi()),
]
