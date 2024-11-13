# /urls/delivery.py

"""
delivery.py

Part of VoiGO-Server

This module defines URL patterns for the Django project. It contains
mappings between URL patterns and view functions, allowing the Django
application to handle incoming HTTP requests from delivery application

"""

from django.urls import path, register_converter

from server import views
from server.converters import FloatConverter

register_converter(FloatConverter, 'float')

# URLPatterns for Delivery Application
urlpatterns = [

    # path('update-duty-info/',
    #      views.updateDeliveryPartnerLocation, name='update_dp_loc_data'),

    path('register-delivery-account',
         view=views.registerDeliveryAccount, name='registerDeliveryAccount'),

    path('update-duty-data',
         view=views.updateDutyData, name='updateDutyData'),

    path('start-duty/',
         view=views.startDuty, name='start_duty'),

    path('end-duty/',
         view=views.endDuty, name='end_duty'),

    path('get-duty-status/<str:delivery_partner_id>',
         view=views.getDutyStatus, name='getDutyStatus'),

    path('get-delivery-client-data/<str:client_id>',
         view=views.getDeliveryUserData, name='getUserData'),

    path(
        'get-voice-order-data/<str:user_id>/<str:order_by_voice_type>/<str:order_by_voice_doc_id>/<str:order_by_voice_audio_ref_id>/<str:shop_id>',
        view=views.getVoiceOrderData, name='getVoiceOrderData'),

    path('fetch-order-data/',
         view=views.fetchOrderData, name='fetchOrderData'),

    path('set-current-order/<str:dp_id>/<str:user_id>/<str:order_id>',
         view=views.performOrderAcceptedCriteria, name='performOrderAcceptedCriteria'),

    path('decline-order/<str:dp_id>/<str:user_id>/<str:order_id>',
         view=views.performOrderDeclineCriteria),

    path('keep-it-order/<str:dp_id>/<str:user_id>/<str:order_id>',
         view=views.performOrderDeliverNextCriteria),

    path('reached-shop/<str:dp_id>/<str:user_id>/<str:order_id>',
         view=views.performReachedShopCriteria),

    path('order-pickedup/<str:dp_id>/<str:user_id>/<str:order_id>',
         view=views.performOrderPickedUpCriteria),

    path('order-enroute/<str:dp_id>/<str:user_id>/<str:order_id>',
         view=views.performOrderEnrouteCriteria),

    path(
        'order-delivered/<str:dp_id>/<str:user_id>/<str:order_by_voice_doc_id>'
        '/<str:order_by_voice_audio_ref_id>/<str:order_id>',
        view=views.performOrderDeliveredCriteria),
]
