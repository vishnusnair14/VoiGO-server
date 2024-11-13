# /urls/order.py

"""
order.py

Part of VoiGO-Server

This module defines URL patterns for the Django project. It contains
mappings between URL patterns and view functions, allowing the Django
application to handle incoming HTTP requests from order application

"""

from django.urls import path, register_converter

from server import views
from server.converters import FloatConverter

register_converter(FloatConverter, 'float')

# URLPatterns for Order Application
urlpatterns = [

    # SSE-PATTERN
    path('stream/<str:user_id>/<str:order_id>',
         view=views.orderUpdateStream, name='orderUpdateStream'),

    path('add-new-address',
         view=views.addNewDeliveryAddress, name='addNewDeliveryAddress'),

    path('delete-address/',
         view=views.deleteAddress, name='deleteAddress'),

    path('get-saved-address/',
         view=views.getSavedAddress, name='getSavedAddress'),

    path('get-items/<str:item_type>/<str:shop_id>/<str:shop_state>/<str:shop_district>',
         view=views.getItems, name='getItems'),
    path(
        'get-voice-order-data/<str:user_id>/<str:order_by_voice_type>/<str:order_by_voice_doc_id>/<str:order_by_voice_audio_ref_id>/<str:shop_id>',
        view=views.getVoiceOrderData, name='getVoiceOrderData'),

    path('handle-address-decision',
         view=views.handleAddressDecision, name='handleAddressDecision'),

    path('recommend-shop/<float:user_la>/<float:user_lo>/<str:user_state>/<str:user_district>/<str:user_pincode>',
         view=views.recommendNearbyShops, name='recommendNearbyShops'),

    path('save_preferences/',
         view=views.saveStorePreference, name='saveStorePreference'),

    path('fetch-store-pref-data/<str:user_id>/<str:phno_enc>',
         view=views.checkIfStorePrefFound, name='checkIfStorePrefFound'),

    path('delete-store-pref-data/<str:user_id>/<str:phno_enc>',
         view=views.deleteStorePrefData, name='deleteStorePrefData'),

    path('delete-voice-order-cart',
         view=views.deleteVoiceOrderFromCart, name='deleteVoiceOrderFromCart'),

    path('create-order-rz/<float:amt>',
         view=views.createPaymentOrderRZ, name='createPaymentOrderRZ'),

    path('verify-payment-sign/<str:order_id>/<str:razorpay_payment_id>/<str:razorpay_signature>',
         view=views.verifyPaymentSignature, name='verifyPaymentSignature'),

    path('place-order-obv',
         view=views.placeOrderOBV, name='placeOrderOBV'),

    path('place-order-obs/<str:order_id>/<str:_user_id>/<str:_user_email>'
         '/<str:_user_phno>/<str:order_by_voice_type>/<str:order_by_voice_doc_id>'
         '/<str:order_by_voice_audio_ref_id>/<str:shop_id>/<str:shop_district>'
         '/<str:shop_pincode>/<str:curr_lat>/<str:curr_lon>',
         view=views.placeOrderOBS, name='placeOrderOBS'),
]
