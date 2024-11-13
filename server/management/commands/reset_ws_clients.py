# server/management/commands/reset_ws_clients.py

from django.core.management.base import BaseCommand

from VoiGO.settings import log
from server.models import WSChatRegister1


class Command(BaseCommand):
    help = 'Reset all websocket client connection statuses to disconnected'
    log.info("Resetting all websocket client connections...")

    def handle(self, *args, **kwargs):
        WSChatRegister1.objects.update(
            is_order_client_connected=False,
            is_delivery_client_connected=False,
            order_client_id_for_ws='None',
            delivery_client_id_for_ws='None'
        )
        log.success("Successfully reset all websocket client connections.\n")
        self.stdout.write(self.style.SUCCESS('Successfully reset all websocket client connections.'))
