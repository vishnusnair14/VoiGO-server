# server/consumers.py

import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

import server.cloud.cloud
from VoiGO.settings import log
from server.constants import KEYWORD
from server.models import *
from simple_colors import *


class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.chat_id = None
        self.client_id = None
        self.client_type = None
        self.room_group_name = None

    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.client_id = self.scope['url_route']['kwargs']['client_id']
        self.client_type = self.scope['url_route']['kwargs']['client_type']
        self.room_group_name = f'chat_{self.chat_id}'

        log.info(f"Received a connection request:"
                 f"\n   -> chat id: {self.chat_id}"
                 f"\n   -> client id: {self.client_id}"
                 f"\n   -> client type: {self.client_type}")

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Set the client as connected
        await self.set_client_status(self.chat_id, self.client_type, self.client_id, 'connect')

    async def disconnect(self, close_code):
        print(f"ChatConsumer disconnected with close-code: {close_code}")

        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Set the client as disconnected
        await self.set_client_status(self.chat_id, self.client_type, self.client_id, 'disconnect')

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        print(text_data)
        message = data['message']
        user_id = data['user_id']
        user_name = data['user_name']
        client_type = data['client_type']
        message_time = data['message_time']

        if len(str(user_name)) == 0:
            user_name = "Unknown"

        # send via fcm if either clients are not in channel
        ws_register = await self.get_ws_register(self.chat_id)
        if client_type == KEYWORD.delivery:
            is_order_connected = await self.is_client_connected(self.chat_id, 'order',
                                                                ws_register.order_client_id)
            if not is_order_connected:
                server.cloud.cloud.send_fcm_notification(ws_register.order_client_id, {
                    'body': message,
                    'title': f'New message from your order partner ({str(user_name).upper()})',
                }, 'user')
                return
            else:
                print("Sending chat via channel: o-client connected, skipping fcm")
        elif client_type == KEYWORD.order:
            is_delivery_connected = await self.is_client_connected(self.chat_id, 'delivery',
                                                                   ws_register.delivery_client_id)

            if not is_delivery_connected:
                if not ws_register.is_delivery_partner_assigned:
                    # Notify sender that the message could not be delivered
                    await self.send(text_data=json.dumps({
                        'message': 'Unable to send message right now. Delivery partner is not assigned.',
                        'user_id': user_id,
                        'user_name': user_name,
                        'client_type': client_type,
                        'message_time': message_time,
                    }))
                    log.info(f"Received chat from {client_type} client. "
                             "Delivery partner is not assigned. Unable to sent chat right now.")
                else:
                    server.cloud.cloud.send_fcm_notification(ws_register.delivery_client_id, {
                        'body': message,
                        'title': f'New message from your order client ({str(user_name).upper()})',
                    }, 'delivery')
                    return
            else:
                print("Sending chat via channel: d-client connected, skipping fcm")

        print("sending msg to room group")
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'user_id': user_id,
                'user_name': user_name,
                'client_type': client_type,
                'message_time': message_time,
            }
        )

    async def chat_message(self, event):
        message = event['message']
        user_id = event['user_id']
        user_name = event['user_name']
        client_type = event['client_type']
        message_time = event['message_time']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'user_id': user_id,
            'user_name': user_name,
            'client_type': client_type,
            'message_time': message_time,
        }))

    @sync_to_async
    def get_ws_register(self, chat_id):
        return WSChatRegister1.objects.get(chat_id=chat_id)

    @sync_to_async
    def set_client_status(self, chat_id: str, client_type: str, client_id: str, action: str):
        try:
            ws_register = WSChatRegister1.objects.get(chat_id=chat_id)
            if client_type == KEYWORD.order:
                if action == KEYWORD.connect:
                    ws_register.is_order_client_connected = True
                    ws_register.order_client_id_for_ws = client_id
                    print(f"Order client connected to chat room: {chat_id}")
                elif action == KEYWORD.disconnect:
                    ws_register.is_order_client_connected = False
                    ws_register.order_client_id_for_ws = "None"
                    print(f"Order client disconnected from chat room: {chat_id}")
            elif client_type == KEYWORD.delivery:
                if action == KEYWORD.connect:
                    ws_register.is_delivery_client_connected = True
                    ws_register.delivery_client_id_for_ws = client_id
                    print(f"Delivery client connected to chat room: {chat_id}")
                elif action == KEYWORD.disconnect:
                    ws_register.is_delivery_client_connected = False
                    ws_register.delivery_client_id_for_ws = "None"
                    print(f"Delivery client disconnected from chat room: {chat_id}")
            ws_register.save()
        except Exception as e:
            print(red(f"Exception occurred at:{__file__}.set_client_status. {str(e)}", ['bold']))
            pass

    @sync_to_async
    def is_client_connected(self, chat_id: str, client_type: str, client_id: str):
        ws_register = WSChatRegister1.objects.get(chat_id=chat_id)
        if client_type == KEYWORD.order:
            return (ws_register.is_order_client_connected and
                    ws_register.order_client_id_for_ws == client_id)
        if client_type == KEYWORD.delivery:
            return (ws_register.is_delivery_client_connected and
                    ws_register.delivery_client_id_for_ws == client_id)
