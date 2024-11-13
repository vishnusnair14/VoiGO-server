

"""
server/models.py

"""

import os

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from decouple import config

# Load the DEBUG_MODE from the .env file
# debug_mode = config('ENV_MODE', default='DEV')
# if debug_mode == 'DEV':
#     os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VoiGO.settings.development')
# elif debug_mode == 'PROD':
#     os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VoiGO.settings.production')
# else:
#     os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VoiGO.settings.development')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VoiGO.settings')


class PartnerOrder(models.Model):
    partner_id = models.CharField(max_length=255, unique=True)
    order = models.IntegerField()

    objects = models.Manager()

    class Meta:
        ordering = ['order']


class UploadedImage(models.Model):
    image = models.ImageField(upload_to='images/')
    name = models.CharField(max_length=256, unique=False, default=str(image.name))
    uploaded_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        verbose_name = "Uploaded Image Bucket"


@receiver(post_save, sender=UploadedImage)
def update_image_name(sender, instance, created, **kwargs):
    if created:
        instance.name = instance.image.name
        instance.save()


class TemporaryAddress(models.Model):
    phone_number = models.CharField(max_length=13, unique=True)
    address_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        verbose_name = "Temporary Address Register"


class PendingOBVOrder(models.Model):
    order_id = models.CharField(max_length=256, unique=True)
    request_body = models.JSONField()
    user_id_enc = models.CharField(max_length=256, default='None')
    status = models.CharField(max_length=50, default='pending')
    order_type = models.CharField(max_length=256, default='unknown')
    received_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = models.Manager()

    class Meta:
        verbose_name = "Pending OBV Order Register"


class PendingOBSOrder(models.Model):
    order_id = models.CharField(max_length=256, unique=True)
    user_id_enc = models.CharField(max_length=256, default='None')
    user_email = models.CharField(max_length=256, default='None')
    user_phno_enc = models.CharField(max_length=256, default='None')
    order_by_voice_doc_id = models.CharField(max_length=256, default='None')
    order_by_voice_audio_ref_id = models.CharField(max_length=256, default='None')
    shop_id = models.CharField(max_length=256, default='None')
    shop_district = models.CharField(max_length=100, default='None')
    shop_pincode = models.CharField(max_length=100, default='None')
    curr_lat = models.CharField(max_length=100, null=True, blank=True)
    curr_lon = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=50, default='pending')
    dp_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order_type = models.CharField(max_length=256, default='unknown')

    objects = models.Manager()

    class Meta:
        verbose_name = "Pending OBS Order Register"


class WSChatRegister1(models.Model):
    chat_id = models.CharField(max_length=256, unique=True)
    order_type = models.CharField(max_length=256, default='None')
    order_client_id = models.CharField(max_length=256, default='None')
    is_delivery_partner_assigned = models.BooleanField(default=False)
    delivery_client_id = models.CharField(max_length=256, default="None")

    is_order_client_connected = models.BooleanField(default=False)
    order_client_id_for_ws = models.CharField(max_length=256, default="None")

    is_delivery_client_connected = models.BooleanField(default=False)
    delivery_client_id_for_ws = models.CharField(max_length=256, default="None")

    objects = models.Manager()

    class Meta:
        verbose_name = "Chat Register"


class OrderMap(models.Model):
    order_id = models.CharField(max_length=256, default="None")
    client_id = models.CharField(max_length=256, default="None")

    objects = models.Manager()

    class Meta:
        verbose_name = "Order Map Register"
