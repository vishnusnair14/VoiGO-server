# Create your views here.

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

import server
from server.cloud import cloud
from server.cloud.cloud import cloudFirestore
from server.constants import KEYWORD
from server.crypto_utils import des_core
from server.engine_core import recommendation as sre
from server.engine_core.order_processing import actions
from server.engine_core.order_processing import obv
from server.engine_core.order_processing.obs import on_new_obs_order_received1
from server.engine_core.order_processing.obv import on_new_obv_order_received_store_pref
from server.models import TemporaryAddress
from server.payment_core.razorpay import payment as rz
from server.protocols.http.sse import order_updates
from server.protocols.http.sse.order_updates import *
from server.registration_core.forms import ProfileImageUpload
from server.registration_core.registration import ShopRegistration, DeliveryPartnerRegistration


def index(request):
    """
    Render the welcome page for localhost

    :param request: HTTP request
    :return: Rendered response
    """

    return render(request=request, template_name='welcome_page.html')


def wsIndex1(request):
    clients = server.models.WSChatRegister1.objects.all()  # Fetch all client IDs from WSClient model
    return render(request, 'ws_order_update.html', {'clients': clients})


def wsIndex2(request):
    clients = server.models.WSChatRegister1.objects.all()  # Fetch all client IDs from WSClient model
    return render(request, 'ws_chat_test.html', {'clients': clients})


def computeRouteMatrix(request, lat1, lon1, lat2, lon2):
    res = utils.compute_route_matrix(lat1, lon1, lat2, lon2)
    return JsonResponse(res)


@csrf_exempt
def deleteAccount1(request):
    client_id = request.GET.get('client_id')
    client_type = request.GET.get('client_type')

    res = cloud.delete_user_account(client_id, client_type)
    return JsonResponse(res)


@csrf_exempt
def sendOrderUpdatesWS(request):
    """
    Handle AJAX request to send WebSocket message.

    :param request: HTTP request
    :return: HTTP response
    """
    data = json.loads(request.body.decode('utf-8'))
    log.info_data(data)

    # Send WebSocket message to specific client
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'order_updates_{data.get("user_id")}',
        {
            'type': 'send_order_update',
            'update_time': utils.get_current_date_time(),
            'location': "Palakkad",
        }
    )
    return HttpResponse(status=200)


def sendChatMessageWS(request):
    """
    Handle AJAX request to send WebSocket message.

    :param request: HTTP request
    :return: HTTP response
    """
    data = json.loads(request.body.decode('utf-8'))

    log.info_data(f"Received: {data}")

    # Send WebSocket message to specific client
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'chat_{data.get("user_id")}',
        {
            'type': 'chat_message',
            'update_time': utils.get_current_date_time(),
            'location': "Palakkad",
            'user_id': data.get('user_id'),
            'message': utils.get_current_date_time()
        }
    )
    return HttpResponse(status=200)


# ---------------------------------------------------------------------------------------------------------------------


async def orderUpdateStream(request, user_id, order_id):
    client_connections[user_id] = True

    response = StreamingHttpResponse(order_updates.order_updates_stream(user_id, order_id),
                                     content_type='text/event-stream')
    return response


# ----------------------------------------------------------------------------------------------------------------


""" 
# Order-App views
-----------------

"""


@csrf_exempt
def saveStorePreference(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))

            # Extract user details
            user_id = data.get('user_id')
            address_phone = data.get('address_phno')
            shop_pref_data = data.get('shop_preferences', [])
            log.info_data("SAVED STORE PREFERENCE DATA:" + str(shop_pref_data))

            shop_ref = (fca.cloudFirestore.collection('Users').document(user_id)
                        .collection('storePreference').document(address_phone))

            log.info(f"Setting shop preference for address with phone:{address_phone}")

            # Process the shop preferences
            for shop in shop_pref_data:
                shop_id = shop.get('shop_id')
                preference = shop.get('shop_preference')
                shop_name = shop.get('shop_name')

                # Fetch the document to check if it exists
                doc = shop_ref.get()
                if doc.exists:
                    shop_ref.update({shop_id: {
                        'shop_preference': preference,
                        'shop_id': shop_id,
                        'shop_name': shop_name
                    }})
                    log.info(f"Preference updated for shop: {shop_name} @{preference}")
                else:
                    shop_ref.set({shop_id: {
                        'shop_preference': preference,
                        'shop_id': shop_id,
                        'shop_name': shop_name
                    }})
                    log.info(f"Preference set for shop: {shop_name} @{preference}")

            return JsonResponse({
                'status': 'success',
                'message': 'Store preferences saved successfully'
            })
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON',
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e),
            }, status=500)
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request method',
        }, status=405)


@require_http_methods(["GET"])
def recommendNearbyShops(request, user_la: float, user_lo: float,
                         user_state: str, user_district: str,
                         user_pincode: str):
    """
    Provide shop recommendations based on user location and city.

    :param user_state:
    :param request: HTTP response
    :param user_la: User latitude
    :param user_lo: User longitude
    :param user_district: User city
    :param user_pincode:
    :return: JSON response containing recommended shops
    """

    recommended_shops = sre.recommend_shops(user_la, user_lo, user_state, user_district, user_pincode)
    log.info_data('RESPONSE:' + str(request))
    return JsonResponse(recommended_shops)


def createPaymentOrderRZ(request, amt: float):
    """
    Create an order using Razorpay payment gateway.

    :param request:
    :param amt: Amount for the order
    :return: JSON response containing order details
    """

    res = rz.create_order(amount=amt)
    return JsonResponse(res)


def verifyPaymentSignature(request, order_id: str, razorpay_payment_id: str, razorpay_signature: str):
    """
    Verify the payment signature for a Razorpay payment.

    :param request:
    :param order_id: Order ID
    :param razorpay_payment_id: Razorpay payment ID
    :param razorpay_signature: Razorpay payment signature
    :return: JSON response indicating signature verification status
    """

    res = rz.verify_signature(order_id, razorpay_payment_id, razorpay_signature)
    return JsonResponse(res)


@csrf_exempt
def addNewDeliveryAddress(request):
    if request.method == 'POST':
        address_data = json.loads(request.POST.get('address_data'))

        phone_number = address_data.get('phone_no')
        full_address = address_data.get('full_address')

        if not phone_number or not full_address:
            return JsonResponse({'error': 'Invalid data'}, status=400)

        existing_address = fca.check_if_address_exists(address_data.get('user_id'), address_data.get('phone_no'))

        if existing_address:
            # Store the new address in temporary storage
            temp_address, created = TemporaryAddress.objects.update_or_create(
                phone_number=phone_number,
                defaults={'address_data': address_data})

            if created:
                log.info("Address stored in temp db successfully")
            else:
                log.info("Address updated in temp db successfully")

            return JsonResponse({'exists': True,
                                 'message': 'Address already exists for this phone number'})
        else:
            # Address.objects.create(phone_number=phone_number, address=address)
            fca.add_new_address(address_data)
            return JsonResponse({'success': True,
                                 'message': 'Address added successfully'})


def deleteAddress(request):
    try:
        # Retrieve the user_id and address_id from the GET request
        user_id = request.GET.get('user_id')
        address_id = request.GET.get('address_id')

        if not user_id or not address_id:
            return JsonResponse({'status': 'error', 'message': 'Missing user_id or address_id'})

        # Assuming you have a function to delete the address from the Firestore database
        deletion_success = fca.delete_address_from_db(user_id, address_id)

        if deletion_success:
            return JsonResponse({'status': 'success', 'message': 'Address deleted successfully'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Failed to delete address'})

    except Exception as e:
        log.error(f"Exception occurred {__file__}.deleteAddress: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'An error occurred', 'exception': str(e)})


def getSavedAddress(request):
    data = fca.get_saved_address(request)
    return JsonResponse(data)


def getItems(request, item_type: str, shop_id: str, shop_state: str, shop_district: str):
    data = fca.get_shop_items(item_type, shop_id, shop_state, shop_district)
    return JsonResponse(data)


@csrf_exempt
def handleAddressDecision(request):
    if request.method == 'POST':
        data = json.loads(request.POST.get('address_decision_data'))

        phone_number = data.get('phone_no')
        decision = data.get('decision')  # "update" or "cancel"

        if not phone_number or not decision:
            return JsonResponse({'success': False,
                                 'error': 'Invalid data',
                                 'message': 'Invalid data'}, status=400)

        temp_address = TemporaryAddress.objects.filter(phone_number=phone_number).first()

        if temp_address:
            if decision == KEYWORD.update:
                log.info_data(temp_address.address_data)
                fca.add_new_address(address_data=temp_address.address_data)
                temp_address.delete()
                return JsonResponse({'success': True,
                                     'message': 'Address updated successfully'})
            elif decision == KEYWORD.cancel:
                temp_address.delete()
                return JsonResponse({'success': True,
                                     'message': 'Ok cancelled'})
        else:
            return JsonResponse(
                {'success': False,
                 'error': 'No temporary address found',
                 'message': 'No temporary address found'},
                status=404)


@csrf_exempt
def placeOrderOBV(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        res = on_new_obv_order_received_store_pref(data)

        log.info_data(res)
        return JsonResponse(res)
    else:
        return JsonResponse({'is_success': False,
                             'message': 'Invalid request method'})


# TODO: migrate to POST method
def placeOrderOBS(request, order_id: str, _user_id: str, _user_email: str,
                  _user_phno: str, order_by_voice_type: str, order_by_voice_doc_id: str,
                  order_by_voice_audio_ref_id: str, shop_id: str, shop_district: str,
                  shop_pincode: str, curr_lat: str, curr_lon: str):
    res = on_new_obs_order_received1(order_id, _user_id, _user_email, _user_phno, order_by_voice_doc_id,
                                     order_by_voice_audio_ref_id, shop_id,
                                     shop_district.lower(), shop_pincode, curr_lat, curr_lon)
    log.info_data(res)
    return JsonResponse(res)


def sendEMail(request, _to: str = 'vishnuskky2001@gmail.com'):
    res = utils.send_email(_to)
    # return render(request=request, template_name='ws_order_update.html')
    return JsonResponse(res)


# -------------------------------------------------------------------------------------------------------------------

""" 
# Delivery-App views
--------------------
"""


# @csrf_exempt
# def updateDeliveryPartnerLocation(request):
#     if request.method == 'POST':
#         # body1 = json.loads(request.body.decode('utf-8'))
#         # dp_id = body1.get('dpID')
#
#         res = fca.update_duty_data(request=request)
#         return JsonResponse(res)


@csrf_exempt
def updateDutyData(request):
    if request.method == 'POST':
        res = fca.update_duty_data(request)
        return JsonResponse(res)


@csrf_exempt
def startDuty(request):
    # TODO

    try:
        body = json.loads(request.body.decode('utf-8'))
        dp_id = body.get('dp_id')
        dp_lat = body.get('dp_lat')
        dp_lon = body.get('dp_lon')

        # resp = utils.reverse_geocode_bigdatacloud(dp_lat, dp_lon)
        # district_name = utils.district_to_format(resp.get('district')).lower()

        partner_data_doc_ref = cloudFirestore.document(f"DeliveryPartners/{dp_id}")

        partner_data_snapshot = partner_data_doc_ref.get()

        if partner_data_snapshot.exists:
            partner_data = partner_data_snapshot.to_dict()

            if partner_data:
                duty_state = partner_data.get('user_state')
                duty_district = partner_data.get('user_district')

                doc_ref = (cloudFirestore.collection('DeliveryPartnerDutyStatus')
                           .document(duty_state).collection(duty_district).document(utils.get_current_date())
                           .collection('dutyStatus')).document(dp_id)

                doc = doc_ref.get()

                body['duty_mode'] = 'on_duty'
                body['dp_loc_coordinates'] = fca.gfs.GeoPoint(dp_lat, dp_lon)
                body['last_duty_status_update_millis'] = utils.get_current_millis()
                body['last_duty_status_update_timestamp'] = fca.gfs.SERVER_TIMESTAMP

                if doc.exists:
                    doc_ref.update(body)
                    log.info(f"Duty mode for {dp_id} set to on duty")
                else:
                    doc_ref.set(body)
                    log.info(f"Duty mode for {dp_id} set to on duty")
                obv.update_partner_order(dp_id=dp_id, is_turning_on=True)
                return JsonResponse({'isDutyStarted': True,
                                     'status': 'success',
                                     'message': 'Duty started.'})
            else:
                return JsonResponse({'isDutyStarted': False,
                                     'status': 'failed',
                                     'message': 'Please initialize GPS'})
    except Exception as e:
        log.error(f"Exception occurred at:{__file__}.start_duty. {str(e)}")
        return JsonResponse({'isDutyStarted': False,
                             'status': 'failed',
                             'message': 'Unable to start duty',
                             'exception': str(e)})


def getDeliveryUserData(request, client_id):
    if request.method == 'GET':

        doc_ref = fca.cloudFirestore.document(f"DeliveryPartners/{client_id}")
        doc_snapshot = doc_ref.get()

        if doc_snapshot.exists:
            data = doc_snapshot.to_dict()
            data['dp_loc_coordinates'] = {
                'latitude': data['dp_loc_coordinates'].latitude,
                'longitude': data['dp_loc_coordinates'].longitude}

            return JsonResponse({'data': data, 'message': 'Data fetched successfully'})


# TODO: dynamic addition of district
@csrf_exempt
def endDuty(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
            dp_id = body.get('dp_id')

            partner_data_doc_ref = cloudFirestore.document(f"DeliveryPartners/{dp_id}")

            partner_data_snapshot = partner_data_doc_ref.get()

            if partner_data_snapshot.exists:
                partner_data = partner_data_snapshot.to_dict()

                if partner_data:
                    duty_state = partner_data.get('user_state')
                    duty_district = partner_data.get('user_district')

                    # Get the delivery partner document from Firestore
                    doc_ref = (cloudFirestore.collection('DeliveryPartnerDutyStatus')
                               .document(duty_state).collection(duty_district).document(utils.get_current_date())
                               .collection('dutyStatus')).document(dp_id)

                    doc_ref.set({
                        'dp_id': dp_id,
                        'duty_mode': 'off_duty',
                        'last_duty_status_update_millis': utils.get_current_millis(),
                        'last_duty_status_update_timestamp': fca.gfs.SERVER_TIMESTAMP,
                    }, merge=True)

                    # obv.update_partner_order(dp_id)
                    log.info(f"Duty mode for {dp_id} set to off duty")
                    obv.update_partner_order(dp_id=dp_id, is_turning_on=False)
                    # PartnerOrder.objects.filter(partner_id=dp_id).delete()
                    return JsonResponse({'isDutyEnded': True,
                                         'status': 'success',
                                         'message': 'Duty ended.'})
        except Exception as e:
            log.error(f"Exception occurred at:{__file__}.end_duty {e}")
            return JsonResponse({'isDutyEnded': False,
                                 'status': 'failed',
                                 'message': 'Unable to end duty',
                                 'exception': str(e)})


def getDutyStatus(request, delivery_partner_id):
    res = fca.get_duty_status(delivery_partner_id)
    return JsonResponse(res)


def getVoiceOrderData(request, user_id: str, order_by_voice_type: str, order_by_voice_doc_id: str,
                      order_by_voice_audio_ref_id: str, shop_id: str):
    res = fca.get_voice_order(user_id, order_by_voice_type, order_by_voice_doc_id, order_by_voice_audio_ref_id, shop_id)
    return JsonResponse(res)


def checkIfStorePrefFound(request, user_id: str, phno_enc: str):
    res = fca.check_if_store_pref_found(user_id, phno_enc)
    return JsonResponse(res)


def deleteStorePrefData(request, user_id: str, phno_enc: str):
    user_phno = des_core.decrypt(phno_enc).get('plain_text')
    if user_phno and len(user_phno) == 10:
        store_pref_doc_ref = fca.cloudFirestore.document(f"Users/{user_id}/"
                                                         f"storePreference/{user_phno}")

        if store_pref_doc_ref.get().exists:
            store_pref_doc_ref.delete()

            return JsonResponse({'is_deleted': True,
                                 'message': f'successfully deleted store preference data for phone'})
        else:
            return JsonResponse({'is_deleted': False,
                                 'message': f'Unable to deleted store preference data for phone,data does not exists'})
    else:
        return JsonResponse({'is_deleted': False,
                             'message': f'Unable to deleted store preference data, decryption failed!'})


@csrf_exempt
def deleteVoiceOrderFromCart(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('UTF-8'))
        res = fca.delete_voice_order_from_cart(data)
        return JsonResponse(res)
    else:
        JsonResponse({'is_success': False,
                      'message': 'Invalid request method'})


@csrf_exempt
def fetchOrderData(request):
    res = fca.fetch_order_data(request)
    return JsonResponse(res)


def performOrderAcceptedCriteria(request, dp_id: str, user_id: str, order_id: str):
    """
    Perform criteria for accepting an order by a delivery partner.

    :param request: HTTP response
    :param dp_id: Delivery partner ID
    :param user_id: User ID
    :param order_id: Order ID
    :return: JSON response indicating order acceptance status
    """

    res = actions.accept_order(dp_id, user_id, order_id)
    log.info_data(res)
    return JsonResponse(res)


def performOrderDeclineCriteria(request, dp_id: str, user_id: str, order_id: str):
    """
    Perform criteria for declining an order by a delivery partner.

    :param request: HTTP response
    :param dp_id: Delivery partner ID
    :param user_id: User ID
    :param order_id: Order ID
    :return: JSON response indicating order decline status
    """

    res = actions.decline_order(dp_id, user_id, order_id)
    log.info_data(res)
    return JsonResponse(res)


def performOrderDeliverNextCriteria(request, dp_id: str, user_id: str, order_id: str):
    """
    Perform criteria for keeping an order for next delivery by a delivery partner.

    :param request: HTTP request
    :param dp_id: Delivery partner ID
    :param user_id: User ID
    :param order_id: Order ID
    :return: JSON response indicating order saving status
    """

    res = actions.save_order_for_next_or_decline(dp_id, user_id, order_id)
    log.info_data(res)
    return JsonResponse(res)


def performReachedShopCriteria(response, dp_id: str,
                               user_id: str, order_id: str):
    """
    Perform criteria for marking an order as picked up by a delivery partner.

    :param response: HTTP response
    :param dp_id: Delivery partner ID
    :param user_id: User ID
    :param order_id: Order ID
    :return: JSON response indicating order pickup status
    """

    res = actions.order_picked_up(dp_id, user_id, order_id)
    log.info_data(res)
    return JsonResponse(res)


def performOrderPickedUpCriteria(response, dp_id: str,
                                 user_id: str, order_id: str):
    """
    Perform criteria for marking an order as picked up by a delivery partner.

    :param response: HTTP response
    :param dp_id: Delivery partner ID
    :param user_id: User ID
    :param order_id: Order ID
    :return: JSON response indicating order pickup status
    """

    res = actions.order_picked_up(dp_id, user_id, order_id)
    log.info_data(res)
    return JsonResponse(res)


def performOrderEnrouteCriteria(response, dp_id: str,
                                user_id: str, order_id: str):
    res = actions.order_en_route(dp_id, user_id, order_id)
    log.info_data(res)
    return JsonResponse(res)


def performOrderDeliveredCriteria(request, dp_id: str, user_id: str,
                                  order_by_voice_doc_id: str,
                                  order_by_voice_audio_ref_id: str, order_id: str):
    """
    Perform criteria for marking an order as delivered by a delivery partner.

    :param order_by_voice_audio_ref_id:
    :param order_by_voice_doc_id:
    :param request: HTTP request
    :param dp_id: Delivery partner ID
    :param user_id: User ID
    :param order_id: Order ID
    :return: JSON response indicating order delivery status
    """

    res = actions.order_delivered(dp_id, user_id, order_by_voice_doc_id, order_by_voice_audio_ref_id, order_id)
    log.info_data(res)
    return JsonResponse(res)


@csrf_exempt
def registerVendorAccount(request):
    if request.method == 'POST':
        shop_registration = ShopRegistration()
        try:
            log.info("Extracting image file...")
            _task = ProfileImageUpload(request.POST, request.FILES)
            if _task.is_valid():
                _task.save()
                log.info("Image extraction success")
                # res = reg_vendor.register_shop(request=request)
                res = shop_registration.register_shop(request)
                return JsonResponse(res, status=200)
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid form'})
        except Exception as e:
            log.error(f"Exception occurred at:{__file__}.registerShop {e}")
            return JsonResponse({'status': False, 'message': str(e)}, status=400)


@csrf_exempt
def registerDeliveryAccount(request):
    if request.method == 'POST':
        delivery_account = DeliveryPartnerRegistration()
        try:
            # log.info("Extracting image file...")
            # _task = ProfileImageUpload(request.POST, request.FILES)
            # if _task.is_valid():
            #     _task.save()
            #     log.info("Image extraction success")
            # res = reg_vendor.register_shop(request=request)
            res = delivery_account.register_account(request)
            return JsonResponse(res, status=200)
            # else:
            #     return JsonResponse({'status': 'error', 'message': 'Invalid form'})
        except Exception as e:
            log.error(f"Exception occurred at:{__file__}.registerShop {e}")
            return JsonResponse({'status': False, 'message': str(e)}, status=400)
