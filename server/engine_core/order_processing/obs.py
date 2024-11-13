"""
obs.py

Part of VoiGO-Server

-----------------------------------------
project name: VoiGO (C) 2024
created: 14-05-2024 10:56 AM
author: vishnu s
-----------------------------------------

Module of the Intellicart-Server project responsible for handling
new orders, assigning delivery partners, calculating distances,
and managing order processing workflows.

"""
from typing import Dict, Any, Optional

from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter

from simple_colors import *
import server.cloud.cloud as fca
from VoiGO.settings import log
from server import constants, utils, models
from server.constants import KEYWORD
from server.crypto_utils import des_core
from server.engine_core.order_processing import actions
from server.models import PendingOBSOrder, WSChatRegister1, OrderMap

SUCCESS: bool = True
FAILED: bool = False

# Define a constant for minimum assignable time in milliseconds
MIN_ASSIGNABLE_TIME_MILLIS = 60000

last_assigned_dp_id = None

# Track the last assignment time for each partner
last_assignment_time = {}

# Global variables to track partner order and last assigned partner
partner_order = []  # This will hold the order of partner IDs


# osp_order_placed: dict = {
#     # ORDER PLACED
#     'order_status_no': 1,
#     'order_status_label': 'Order Accepted',
#     'order_status_label_bg_color': '#1d4176',
#     'order_status_label_fg_color': '#ffffff'
# }
#
# osp_delivery_partner_not_assigned: dict = {
#     # DELIVERY PARTNER NOT ASSIGNED
#     'order_status_no': 2,
#     'is_partner_assigned': False,
#     'order_status_label': 'Delivery partner not assigned',
#     'order_status_label_bg_color': '#ab3109',
#     'order_status_label_fg_color': '#ffffff'
# }
#
# osp_delivery_partner_assigned: dict = {
#     # DELIVERY PARTNER ASSIGNED
#     'order_status_no': 2,
#     'is_partner_assigned': True,
#     'order_status_label': 'Delivery partner assigned',
#     'order_status_label_bg_color': '#1d4176',
#     'order_status_label_fg_color': '#ffffff'
# }
#
# osp_order_accepted: dict = {
#     # ORDER ACCEPTED
#     'order_status_no': 3,
#     'order_status_label': 'Order Accepted',
#     'order_status_label_bg_color': '#1d4176',
#     'order_status_label_fg_color': '#ffffff'
# }
#
# osp_order_pickup_success: dict = {
#     # ORDER PICKUP SUCCESS
#     'order_status_no': 4,
#     'order_status_label': 'Order Picked',
#     'order_status_label_bg_color': '#3d85c6',
#     'order_status_label_fg_color': '#ffffff'
# }
#
# osp_order_enrouted: dict = {
#     # ORDER EN-ROUTED
#     'order_status_no': 5,
#     'order_status_label': 'Order enrouted',
#     'order_status_label_bg_color': '#8fce00',
#     'order_status_label_fg_color': '#16537e'
#
# }
#
# osp_order_delivered: dict = {
#     # ORDER DELIVERED
#     'order_status_no': 6,
#     'order_status_label': 'Order Delivered',
#     'order_status_label_bg_color': '#8fce00',
#     'order_status_label_fg_color': '#ffffff'
# }


# Function to query on-duty delivery partners from Firestore
# def _get_available_delivery_partners(addr_state: str, addr_district: str):
#     delivery_partners = []
#     partners_ref = fca.cloudFirestore.collection(
#         f'DeliveryPartnerDutyStatus/{addr_state}/{addr_district}/{utils.get_current_date()}/dutyStatus').where(
#         filter=FieldFilter('duty_mode', '==', 'on_duty'))
#     docs = partners_ref.stream()
#
#     try:
#         for doc in docs:
#             data = doc.to_dict()
#             location = data.get('dp_loc_coordinates', {})
#
#             delivery_partners.append({
#                 "dp_id": data.get('dp_id'),
#                 "dp_name": data.get('dp_name'),
#                 "dp_lat": location.latitude,
#                 "dp_lon": location.longitude,
#             })
#     except Exception as e:
#         print(f"Exception occurred at {__file__}.get_delivery_partners. {str(e)}")
#
#     return delivery_partners

def _update_partner_last_status_time(addr_state: str, addr_district: str, dp_id: str):
    try:
        partner_ref = fca.cloudFirestore.collection(
            f'DeliveryPartnerDutyStatus/{addr_state}/{addr_district}/'
            f'{utils.get_current_date()}/dutyStatus').document(dp_id)

        new_status_time = utils.get_current_millis()
        partner_ref.update({
            'last_duty_status_update_millis': new_status_time
        })
        log.info(f"Updated last_duty_status_update_millis for partner {dp_id} to {new_status_time}")
    except Exception as e:
        log.error(f"Exception occurred while updating last_duty_status_update_millis for partner {dp_id}. {str(e)}")


def round_robin_assign(delivery_partners: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Round-robin assignment of delivery partners.

    Args:
    - delivery_partners (dict): Dictionary of delivery partners.

    Returns:
    - dict: The next delivery partner to be assigned.
    """
    global last_assigned_dp_id
    global partner_order

    if not delivery_partners:
        return {}

    # If no partners are in the order list, initialize it with current partners
    if not partner_order:
        partner_order = list(delivery_partners.keys())

    # If the last assigned partner is not set or is not in the current list, start from the first
    if last_assigned_dp_id is None or last_assigned_dp_id not in partner_order:
        next_dp_id = partner_order[0]
    else:
        # Move to the next partner in the queue
        try:
            last_index = partner_order.index(last_assigned_dp_id)
            next_dp_index = (last_index + 1) % len(partner_order)
            next_dp_id = partner_order[next_dp_index]
        except ValueError:
            # If somehow the last assigned ID isn't found, just start from the first
            next_dp_id = partner_order[0]

    last_assigned_dp_id = next_dp_id
    return delivery_partners.get(next_dp_id)


def _get_available_delivery_partners(addr_state: str, addr_district: str, shop_lat: float, shop_lon: float):
    log.info(f"Fetching all available partners at {addr_district}, {addr_state}")

    delivery_partners = []
    partners_ref = (fca.cloudFirestore.collection(
        f'DeliveryPartnerDutyStatus/{addr_state}/{addr_district}/{utils.get_current_date()}/dutyStatus')
                    .where(filter=FieldFilter('duty_mode', '==', 'on_duty'))
                    .order_by('last_duty_status_update_millis', direction=firestore.Query.ASCENDING))

    docs = partners_ref.stream()

    try:
        for doc in docs:
            data = doc.to_dict()
            location = data.get('dp_loc_coordinates', {})

            dp_lat = location.latitude if location else None
            dp_lon = location.longitude if location else None

            if dp_lat is not None and dp_lon is not None:
                distance = utils.haversine(shop_lat, shop_lon, dp_lat, dp_lon)
                log.info(f"Partner {data.get('dp_name')}({data.get('dp_id')}) "
                         f"radius from shop centroid: {distance}km")

                # Include only partners within the initial 5km radius
                if distance <= 5.0:
                    delivery_partners.append({
                        "dp_id": data.get('dp_id'),
                        "dp_name": data.get('dp_name'),
                        "dp_lat": dp_lat,
                        "dp_lon": dp_lon,
                        "distance": distance,
                        "last_duty_status_update_millis": data.get('last_duty_status_update_millis'),
                    })

        # If no partners found within 5km, extend the search to 10km
        if not delivery_partners:
            print("No delivery partners found within 5km, extending search radius to 10km...")
            for doc in docs:
                data = doc.to_dict()
                location = data.get('dp_loc_coordinates', {})

                dp_lat = location.latitude if location else None
                dp_lon = location.longitude if location else None

                if dp_lat is not None and dp_lon is not None:
                    distance = utils.haversine(shop_lat, shop_lon, dp_lat, dp_lon)
                    log.info(f"Partner {data.get('dp_name')}({data.get('dp_id')}) "
                             f"radius from shop centroid: {distance}km")

                    if 5.0 < distance <= 10.0:
                        delivery_partners.append({
                            "dp_id": data.get('dp_id'),
                            "dp_name": data.get('dp_name'),
                            "dp_lat": dp_lat,
                            "dp_lon": dp_lon,
                            "distance": distance,
                            "last_duty_status_update_millis": data.get('last_duty_status_update_millis'),
                        })

            log.info_data(f"Filtered and sorted partners (within 10km) data : {str(delivery_partners)}")
        else:
            log.info_data(f"Filtered and sorted partners (within 5km) data : {str(delivery_partners)}")

    except Exception as e:
        print(f"Exception occurred at {__file__}.get_delivery_partners. {str(e)}")

    return delivery_partners


# Function to find delivery partners within radius
def assign_delivery_partner_obs(order_id: str, shop_lat: float, shop_lon: float, addr_state: str, addr_district: str):
    log.info(f"Assigning delivery partner for order ({order_id})....")
    delivery_partners = _get_available_delivery_partners(addr_state, addr_district, shop_lat, shop_lon)

    if not delivery_partners:
        print("No delivery partners found.")
        return {}

    log.info("Finding optimal delivery partner....")

    # Sort delivery partners by last duty status update time (optional)
    delivery_partners = sorted(delivery_partners, key=lambda x: x['last_duty_status_update_millis'])
    assigned_partner = delivery_partners[0]

    # # Convert list to dictionary with dp_id as the key for round-robin assignment
    # delivery_partners_dict = {partner['dp_id']: partner for partner in delivery_partners}
    #
    # # Use round-robin to assign the next delivery partner
    # assigned_partner = round_robin_assign(delivery_partners_dict)

    if not assigned_partner:
        print("No delivery partners available for assignment.")
        return {}

    log.info(f"Round-robin assigned partner: {assigned_partner['dp_name']} ({assigned_partner['dp_id']})")
    # Reset duty-update-status timestamp
    _update_partner_last_status_time(addr_state, addr_district, assigned_partner['dp_id'])

    print(f"Assigned delivery partner: {assigned_partner['dp_name']} with ID: {assigned_partner['dp_id']}")
    return assigned_partner


def add_orders_to_pending(order_id: str = None):
    """
    TODO:   Logic to be added for appending incoming orders to pending list,
            when there is no delivery partner available nearby respective
            shop location. Hence need to be create a separate watchdog for
            mapping pending orders occasionally.
            ( ~ perform 'round-robin-model' approach here )

    :param order_id:
    :return:

    """

    log.info(f'ORDER WITH ID: {order_id} ADDED TO PENDING')
    pass


def on_new_obs_order_received1(order_id: str, user_id_enc: str, user_email_enc: str,
                               user_phno_enc: str, order_by_voice_doc_id: str,
                               order_by_voice_audio_ref_id: str, shop_id: str,
                               shop_district: str,
                               shop_pincode: str, curr_lat: str, curr_lon: str):
    """
    Handles a new OBS order by decrypting user information, fetching shop data,
    and assigning a delivery partner.

    :param order_id: The unique identifier of the order.
    :param user_id_enc: The encrypted user ID.
    :param user_email_enc: The encrypted user email.
    :param user_phno_enc: The encrypted user phone number.
    :param order_by_voice_doc_id: The document ID associated with the order by voice.
    :param order_by_voice_audio_ref_id: The audio reference ID associated with the order.
    :param shop_id: The unique identifier of the shop.
    :param shop_district: The district where the shop is located.
    :param shop_pincode: The pincode of the shop.
    :param curr_lat: The current latitude of the delivery location (if available).
    :param curr_lon: The current longitude of the delivery location (if available).

    :return: dict: A dictionary containing the user ID, shop ID, assigned delivery partner ID,
                   partner name, and assignment status.
    """
    try:
        log.info("OBS order received. Order ID: %s", order_id)

        order_time = utils.get_current_date_time()
        order_time_millis = utils.get_current_millis()
        log.info("Order time: %s, Order time millis: %d", order_time, order_time_millis)

        # Decrypt user information
        user_info = {
            'user_id': des_core.decrypt(user_id_enc).get('plain_text'),
            'user_email': des_core.decrypt(user_email_enc).get('plain_text'),
            'user_phno': des_core.decrypt(user_phno_enc).get('plain_text')
        }
        log.info("Decrypted user info: %s", user_info)

        # Validate phone number
        if not (user_info['user_phno'] and len(user_info['user_phno']) == 10):
            log.warning("Invalid phone number: %s. Skipping address and shop data fetching.", user_info['user_phno'])
            addr_loc = firestore.GeoPoint(0.0, 0.0)
            return {"user_id": user_info['user_id'], "shop_id": shop_id,
                    "dp_id": None,
                    "dp_name": None,
                    "is_assigned": False}

        # Fetch user address data
        addr_data = fca.get_address_data(uid=user_info['user_id'], phno=user_info['user_phno'])
        user_name = addr_data.get('name', 'unknown')
        user_full_address = addr_data.get('full_address', 'unknown')
        addr_state = addr_data.get('state')
        addr_district = addr_data.get('district')
        addr_loc = addr_data.get('address_loc_coordinates', firestore.GeoPoint(0.0, 0.0))
        log.info("Fetched address data: Name: %s, Full address: %s, Location: %s°N, %s°E", user_name, user_full_address,
                 addr_loc.latitude, addr_loc.longitude)

        # Update address location if current location provided
        if curr_lat != 'None' and curr_lon != 'None':
            addr_loc = firestore.GeoPoint(float(curr_lat), float(curr_lon))
            addr_loc_type = "current"
            log.info("Updated address location to current location: Latitude: %s, Longitude: %s", curr_lat, curr_lon)
        else:
            addr_loc_type = "actual"
            log.info("Using actual address location: %s°N, %s°E", addr_loc.latitude, addr_loc.longitude)

        # Fetch shop data
        shop_data = fca.get_shop_data1(shop_id=shop_id, state=addr_state,
                                       district=addr_district)

        if shop_data is None:
            return {"user_id": user_info['user_id'], "shop_id": shop_id,
                    "message": f"No shop data found for id {shop_id} ",
                    "is_assigned": False}

        shop_loc = firestore.GeoPoint(shop_data['shop_loc_coords'].latitude,
                                      shop_data['shop_loc_coords'].longitude)
        log.info_data("Fetched shop data: %s", shop_data)

        # Prepare payloads
        new_order_received_fcm_payload = {
            'order_id': order_id,
            'user_id': user_info['user_id'],
            'shop_id': shop_id,
            'title': 'New order received',
            'body': f"Order received from {user_name.upper()}.\n{shop_data.get('shop_name')} | "
                    f"{shop_data.get('shop_street')}",
            'shop_name': shop_data.get('shop_name')
        }
        log.info("FCM data payload prepared")

        base_payload = {
            'order_type': KEYWORD.obs,
            'order_time': order_time,
            'shop_id': shop_id,
            'delivery_loc_coordinates': addr_loc,
            'shop_name': shop_data.get('shop_name'),
            'user_id': user_info['user_id'],
            'dp_name': 'unknown'
        }

        obs_data_payload = {
            'body': shop_data.get('shop_name'),
            'delivery_address_loc': addr_loc,
            'delivery_address_loc_type': addr_loc_type,
            'delivery_full_address': user_full_address,
            'order_by_voice_audio_ref_id': order_by_voice_audio_ref_id,
            'order_by_voice_doc_id': order_by_voice_doc_id,
            'order_type': KEYWORD.obs,
            'order_delivery_destination_distance': 0,
            'order_id': order_id,
            'order_saved_status': 'None',
            'order_status_bg_color': '#e0af19',
            'order_status_fg_color': '#990000',
            'order_status_label': 'Partner not assigned!',
            'order_status_no': 0,
            'order_time': order_time,
            'order_time_millis': order_time_millis,
            'pickup_destination_distance': 0,
            'shop_state': shop_data.get('shop_state'),
            'shop_district': shop_data.get('shop_district'),
            'shop_id': shop_id,
            'shop_loc': shop_loc,
            'shop_name': shop_data.get('shop_name'),
            'shop_phno': shop_data.get('shop_phone'),
            'shop_pincode': shop_data.get('shop_pincode'),
            'shop_street': shop_data.get('shop_street'),
            'user_email': user_info['user_email'],
            'user_id': user_info['user_id'],
            'user_name': user_name,
            'user_phno': user_info['user_phno']
        }
        log.info("OBS data payload prepared")

        # Assign delivery partner
        try:
            assigned_dp_data = assign_delivery_partner_obs(order_id, shop_data['shop_loc_coords'].latitude,
                                                           shop_data['shop_loc_coords'].longitude,
                                                           addr_state.lower(), addr_district.lower())
            log.info("Assigned delivery partner data received")

            dp_id = assigned_dp_data.get('dp_id', 'None')
            dp_name = assigned_dp_data.get('dp_name', 'unknown')

            if dp_id != 'None':
                pickup_dist_km = assigned_dp_data.get('shop_to_partner_radius', 0.00)
                dp_lat = assigned_dp_data.get('dp_lat', 0.00)
                dp_lon = assigned_dp_data.get('dp_lon', 0.00)

                oddd = utils.calc_dist_openroutes(shop_loc.latitude, shop_loc.longitude,
                                                  addr_loc.latitude, addr_loc.longitude, "ODDD Distance")

                log.info("Distance calculations: Pickup to destination (km): %f, ODDD Distance: %f",
                         pickup_dist_km, oddd)

                obs_data_payload.update({
                    'pickup_destination_distance': pickup_dist_km,
                    'order_delivery_destination_distance': oddd,
                    'dp_id': dp_id,
                    'dp_name': dp_name,
                    'order_status_label': 'Delivery partner assigned',
                    'order_status_no': 2,
                    'order_status_fg_color': '#ffffff',
                    'order_status_bg_color': '#1d4176'
                })

                base_payload.update({
                    'dp_id': dp_id,
                    'dp_name': dp_name
                })

                osp_delivery_partner_assigned_payload = {
                    'user_name': user_name,
                    'dp_name': dp_name,
                    'shop_name': shop_data.get('shop_name'),
                    'order_id': order_id,
                    'order_time': order_time,
                    'order_status_no': 2,
                    'order_status_data': {
                        '1': {
                            'key': 1,
                            'title': 'Order placed',
                            'sub_title': 'You have successfully placed your order.'},
                        '2': {
                            'key': 2,
                            'title': 'Delivery partner assigned',
                            'sub_title': 'Order have been confirmed, partner assigned.'},
                    },
                    'is_partner_assigned': True,
                    'order_status_label': 'Delivery partner assigned',
                    'order_status_label_bg_color': '#1d4176',
                    'order_status_label_fg_color': '#ffffff'
                }

                log.info("Realtime order payload prepared: DELIVERY_PARTNER_ASSIGNED")

                fca.send_fcm_notification(client_id=dp_id, fcm_data_payload=new_order_received_fcm_payload,
                                          client_type="delivery",
                                          on_success_msg=f"Order assigned to {dp_name},"
                                                         " order notification has been sent.")

                fca.add_order_to_users_bucket(uid=user_info['user_id'], base_payload=base_payload,
                                              order_info_payload=obs_data_payload)
                log.info("Order added to user's bucket")

                fca.add_order_to_dp_bucket(order_id=order_id, dp_id=dp_id,
                                           base_payload=base_payload, obs_data_payload=obs_data_payload)
                log.info("Order added to delivery partner's bucket")

                fca.add_cart_item_to_dp_bucket(user_id=user_info['user_id'], dp_id=dp_id, order_id=order_id,
                                               shop_id=shop_data.get('shop_id'))
                log.info("Manual cart data added to delivery partner's bucket")

                actions.update_rtime_order_status(KEYWORD.delivery_partner_not_assigned, user_info['user_id'], order_id,
                                                  osp_delivery_partner_assigned_payload)
                log.info("Realtime order status updated to DELIVERY_PARTNER_ASSIGNED")

                WSChatRegister1.objects.update_or_create(
                    chat_id=order_id,
                    defaults={
                        'delivery_client_id': dp_id,
                        'order_client_id': user_info['user_id'],
                        'is_delivery_partner_assigned': True,
                        'order_type': KEYWORD.obs,
                        'delivery_client_id_for_ws': 'None',
                        'order_client_id_for_ws': 'None'
                    }
                )
                log.info("ChatRegister updated for order ID %s", order_id)

                OrderMap.objects.update_or_create(
                    order_id=order_id,
                    defaults={'client_id': user_info['user_id']}
                )
                log.info("OrderMap updated for order ID %s", order_id)

                return {"user_id": user_info['user_id'], "dp_id": dp_id,
                        "shop_id": shop_id, "partner_name": dp_name,
                        "is_assigned": True}

            else:
                # Delivery partner not found/available
                osp_delivery_partner_not_assigned_payload = {
                    'user_name': user_name,
                    'shop_name': shop_data.get('shop_name'),
                    'order_id': order_id,
                    'order_time': order_time,
                    'order_status_no': 2,
                    'order_status_data': {
                        '1': {
                            'key': 1,
                            'title': 'Order placed',
                            'sub_title': 'You have successfully placed your order.'},
                        '2': {
                            'key': 2,
                            'title': 'Delivery not partner assigned',
                            'sub_title': "We'll assign a delivery partner soon."},
                    },
                    'is_partner_assigned': False,
                    'order_status_label': 'Delivery partner not assigned',
                    'order_status_label_bg_color': '#ab3109',
                    'order_status_label_fg_color': '#ffffff'
                }

                log.info("Realtime order payload prepared: DELIVERY_PARTNER_NOT_ASSIGNED")

                fca.add_order_to_users_bucket(uid=user_info['user_id'], base_payload=base_payload,
                                              order_info_payload=obs_data_payload)
                log.info("Order added to user's bucket")
                add_orders_to_pending(order_id)
                log.info("Order added to pending")

                actions.update_rtime_order_status(KEYWORD.delivery_partner_assigned, user_info['user_id'],
                                                  order_id, osp_delivery_partner_not_assigned_payload)
                log.info("Realtime order status updated to DELIVERY_PARTNER_NOT_ASSIGNED")

                # Add to pending order list
                PendingOBSOrder.objects.update_or_create(
                    order_id=order_id,
                    defaults={
                        'user_id_enc': user_id_enc,
                        'user_email': user_email_enc,
                        'user_phno_enc': user_phno_enc,
                        'order_by_voice_doc_id': order_by_voice_doc_id,
                        'order_by_voice_audio_ref_id': order_by_voice_audio_ref_id,
                        'shop_id': shop_id,
                        'shop_district': shop_district,
                        'shop_pincode': shop_pincode,
                        'curr_lat': curr_lat or "0.0",
                        'curr_lon': curr_lon or "0.0",
                        'status': 'pending',
                        'order_type': KEYWORD.obs
                    }
                )

                WSChatRegister1.objects.update_or_create(
                    chat_id=order_id,
                    defaults={
                        'delivery_client_id': dp_id,
                        'order_client_id': user_info['user_id'],
                        'is_delivery_partner_assigned': False,
                        'order_type': KEYWORD.obs,
                        'delivery_client_id_for_ws': 'None',
                        'order_client_id_for_ws': 'None'
                    }
                )
                log.info("ChatRegister updated for order ID %s", order_id)

                log.info(f"Order ({order_id}) added to pending list")
                log.warning(f"Order ({order_id}) has not assigned to a partners, scheduled for auto assignation.")

                return {"user_id": user_info['user_id'], "shop_id": shop_id,
                        "dp_id": "No partner available nearby, we will assign a partner soon",
                        "is_assigned": False}

        except Exception as e:
            log.error(f"Error during delivery partner assignment: {e}")
            return {"user_id": user_info['user_id'], "shop_id": shop_id,
                    "dp_id": "Error occurred!",
                    "is_assigned": False}

    except Exception as e:
        log.error(f"Exception in on_new_obs_order_received: {e}")
        return {"user_id": des_core.decrypt(user_id_enc).get('plain_text'), "shop_id": shop_id,
                "dp_id": "Error occurred!",
                "is_assigned": False}

# ------------------------------------------------------------------------------------------------------------
