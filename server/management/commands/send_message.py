# myapp/management/commands/send_message.py

from django.core.management.base import BaseCommand
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class Command(BaseCommand):
    help = 'Send a message to WebSocket clients'

    def handle(self, *args, **kwargs):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'chat_group',
            {
                'type': 'chat_message',
                'message': 'Hello from server!'
            }
        )
        self.stdout.write(self.style.SUCCESS('Message sent'))
