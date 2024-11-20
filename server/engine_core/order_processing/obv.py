"""
obv.py

Part of VoiGO-Server

-----------------------------------------
project name: VoiGO (C) 2024
created: 31-07-2024 02:52 AM
author: vishnu s
-----------------------------------------

Module of the VoiGO-Server project responsible for handling
new orders, assigning delivery partners, calculating distances,
and managing order processing workflows.

"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

import requests
from geopy.distance import geodesic
from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter

import server.cloud.cloud as fca
from VoiGO.settings import log
from server import utils, constants
from server.constants import KEYWORD
from server.crypto_utils import des_core
from server.engine_core.order_processing import actions
from server.models import PendingOBVOrder, WSChatRegister1
from haversine import haversine, Unit

# Define a constant for minimum assignable time in milliseconds
MIN_ASSIGNABLE_TIME_MILLIS = 60000

last_assigned_dp_id = None

# Track the last assignment time for each partner
last_assignment_time = {}

# Global variables to track partner order and last assigned partner
partner_order = []  # This will hold the order of partner IDs


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


def update_partner_order(dp_id: str, is_turning_on: bool):
    """
    Update the partner_order list when a partner turns duty on or off.

    Args:
    - dp_id (str): Delivery partner ID.
    - is_turning_on (bool): True if the partner is turning on duty, False if turning off.
    """
    global partner_order

    if is_turning_on:
        if dp_id not in partner_order:
            partner_order.append(dp_id)
            log.info(f"Partner {dp_id} added to the end of the queue.")

            # Find the max order value in the current queue
            # max_order = PartnerOrder.objects.aggregate(Max('order'))['order__max']
            # next_order = (max_order or 0) + 1
            #
            # # Add the partner to the queue with the next order
            # PartnerOrder.objects.create(partner_id=dp_id, order=next_order)
    else:
        if dp_id in partner_order:
            partner_order.remove(dp_id)
            log.info(f"Partner {dp_id} removed from the queue.")


def _get_current_time_millis() -> int:
    # Get the current time in UTC as a timezone-aware datetime object
    now_utc = datetime.now(timezone.utc)
    return int(now_utc.timestamp() * 1000)


# def assign_delivery_partner_obv(order_id: str, shop_data: Dict[str, Any], all_shop_coords: list, addr_state: str,
#                                 addr_district: str) -> Optional[Dict[str, Any]]:
#     # Calculate the total distance for each delivery partner to all shops
#     total_travel_distance = 0.0000
#
#     min_total_distance = float('inf')
#
#     log.info(f"Assigning delivery partner for order ({order_id})....")
#
#     delivery_partners = _get_available_delivery_partners(addr_state, addr_district, all_shop_coords)
#
#     if not delivery_partners:
#         log.warning(f"No available delivery partners for order ({order_id}) in {addr_district}, {addr_state}")
#         return {}
#
#     dp_id, assigned_partner = next(iter(delivery_partners.items()))
#
#     # for dp_id, _ in delivery_partners.items():
#     #     # update_partner_order(_.get('dp_id'))
#
#     log.info("Calculating total travel distance...")
#
#     for shop_id, shop in shop_data.items():
#         shop_coords = shop['shop_loc_coords']
#         shop_lat = shop_coords.get('latitude')
#         shop_lon = shop_coords.get('longitude')
#
#         dp_lat = assigned_partner['dp_lat']
#         dp_lon = assigned_partner['dp_lon']
#
#         distance = utils.haversine(shop_lat, shop_lon, dp_lat, dp_lon)
#         total_travel_distance += round(distance, 4)
#         assigned_partner['shop_to_partner_radius'] = total_travel_distance
#
#     log.info(f"Calculated total travel distance for "
#              f"{assigned_partner['dp_name']} ({dp_id}) is {total_travel_distance}km")
#
#     if assigned_partner:
#         log.info(f"Assigned partner: {assigned_partner['dp_name']} ({assigned_partner['dp_id']})")
#
#         # Reset duty-update-status timestamp
#         _update_partner_last_status_time(addr_state, addr_district, assigned_partner['dp_id'])
#
#         return assigned_partner
#     else:
#         return {}

def get_travel_distance(origin, destination):
    # Placeholder function for using a Distance Matrix API
    # Replace with actual API call to get precise travel distance
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?units=metric"
    params = {
        "origins": f"{origin[0]},{origin[1]}",
        "destinations": f"{destination[0]},{destination[1]}",
        "key": constants.GOOGLE_MAPS_API_KEY_VOIGO
    }
    response = requests.get(url, params=params)
    data = response.json()

    if data['status'] == 'OK':
        travel_distance = data['rows'][0]['elements'][0]['distance']['value'] / 1000  # Convert meters to km
        log.info(f"Travel distance from {origin} to {destination}: {travel_distance} km")
        return travel_distance
    else:
        log.warning("Failed to fetch travel distance from Distance Matrix API")
        return float('inf')  # Return a large number if API fails


def get_nearby_shops(address_coords, addr_state: str, addr_dist: str, radius=2.5):
    log.info(f"Fetching shops in {addr_dist}, {addr_state} within {radius} km radius")

    # Fetch shop data from Firestore
    shops_ref = fca.cloudFirestore.collection(f'ShopData/data/{addr_state}/{addr_dist}/allShopData')
    all_shops = shops_ref.stream()

    nearby_shops = []

    # First, find shops within the specified radius using Haversine
    for shop in all_shops:
        shop_data = shop.to_dict()
        shop_coords = (shop_data['shop_loc_coords'].latitude, shop_data['shop_loc_coords'].longitude)
        log.info(f"Calculating Haversine distance to shop at {shop_coords}")

        # Calculate distance using Haversine formula
        distance_km = haversine(address_coords, shop_coords, unit=Unit.KILOMETERS)
        log.info(f"Distance to shop '{shop_data['shop_name']}': {distance_km} km")

        # Check if within the current radius
        if distance_km <= radius:
            log.info(f"Shop within {radius} km radius found: {shop_data['shop_name']}")
            shop_data['distance'] = distance_km
            nearby_shops.append(shop_data)

    # If shops are found within the radius, sort them by distance
    if nearby_shops:
        # Log all shops found within the radius
        log.info(f"{len(nearby_shops)} shop(s) found within {radius} km radius")
        for shop in nearby_shops:
            log.info(f"Shop: {shop['shop_name']}, Haversine Distance: {shop['distance']} km")

        # Sort shops by Haversine distance
        nearby_shops = sorted(nearby_shops, key=lambda x: x['distance'])

        # Use Distance API to find the closest by actual travel distance
        log.info("Using Distance API to refine closest shop based on travel distance")
        for shop in nearby_shops:
            shop_coords = (shop['shop_loc_coords'].latitude, shop['shop_loc_coords'].longitude)
            travel_distance = get_travel_distance(address_coords, shop_coords)
            shop['travel_distance'] = travel_distance

        # Sort by travel distance
        nearby_shops = sorted(nearby_shops, key=lambda x: x['travel_distance'])
        log.info("Shops sorted by travel distance")

        # Return the closest shop by travel distance
        closest_shop = nearby_shops[0]
        log.info(
            f"Nearest shop by travel distance found: {closest_shop['shop_name']} at "
            f"{closest_shop['travel_distance']} km")
        return closest_shop

    # If no shops within the initial radius, expand to 5 km and repeat
    if not nearby_shops and radius == 2.5:
        log.info("No shops found within 2.5 km radius; expanding to 5 km")
        return get_nearby_shops(address_coords, addr_state, addr_dist, radius=5)

    log.info("No nearby shops found after expanding search radius")
    return None


# Function to query on-duty delivery partners from Firestore within expected radius
def _get_available_delivery_partners(addr_state: str, addr_district: str, nearby_shop_coords):
    def _fetch_partners_within_radius(radius_km: float):
        partners = {}

        docs = partners_ref.stream()
        try:
            for doc in docs:
                data = doc.to_dict()
                location = data.get('dp_loc_coordinates', {})

                # Extract latitude and longitude if location is not empty
                dp_lat = location.latitude if location else 0.0
                dp_lon = location.longitude if location else 0.0

                distance = utils.haversine(nearby_shop_coords[0], nearby_shop_coords[1], dp_lat, dp_lon)
                log.info(f"Radius calculated, partner {data.get('dp_name')}({data.get('dp_id')}) is within "
                         f"{radius_km}km radius from the shop location: {distance}km")

                if distance <= radius_km:
                    _dp_id = data.get('dp_id')

                    partners[_dp_id] = {
                        "dp_id": _dp_id,
                        "dp_name": data.get('dp_name'),
                        "dp_lat": dp_lat,
                        "dp_lon": dp_lon,
                        "last_duty_status_update_millis": data.get('last_duty_status_update_millis'),
                    }

            log.info_data(f"Filtered and sorted partners (within {radius_km}km) data : {str(partners)}")
            return partners
        except Exception as e:
            log.error(f"Exception occurred during partner fetching: {str(e)}")
            return {}

    log.info(f"Fetching all available partners at {addr_district}, {addr_state}")

    # shop_centroid = utils.calculate_centroid(coords=all_shop_coords)
    # log.info("Shop centroid: " + str(shop_centroid))

    earliest_duty_time_millis = float('inf')
    earliest_duty_time_id = None
    earliest_duty_time_name = None

    partners_ref = (fca.cloudFirestore.collection(
        f'DeliveryPartnerDutyStatus/{addr_state}/{addr_district}/{utils.get_current_date()}/dutyStatus').where(
        filter=FieldFilter('duty_mode', '==', 'on_duty'))
                    .order_by('last_duty_status_update_millis', direction=firestore.Query.ASCENDING))

    # First attempt within 2.5 km
    delivery_partners = _fetch_partners_within_radius(constants.OPE_MIN_RADIUS)

    # # Initialize earliest_duty_time on the first iteration
    for dp_id, dp in delivery_partners.items():
        if dp['last_duty_status_update_millis'] < earliest_duty_time_millis:
            earliest_duty_time_millis = dp['last_duty_status_update_millis']
            earliest_duty_time_name = dp['dp_name']
            earliest_duty_time_id = dp['dp_id']

    log.info(f"Duty started first among all is {earliest_duty_time_name} "
             f"({earliest_duty_time_id} @{earliest_duty_time_millis})")

    # If no partners found, attempt with 5 km radius
    if not delivery_partners:
        log.warning(f"No partners found within 2.5km. Extending search radius to 5km.")
        delivery_partners = _fetch_partners_within_radius(constants.OPE_MAX_RADIUS)

    return delivery_partners


def assign_delivery_partner_obv1(order_id: str, addr_state: str,
                                 addr_district: str, nearby_shop_coords) -> Optional[Dict[str, Any]]:
    # Calculate the total distance for each delivery partner to all shops
    total_travel_distance = 0.0000

    min_total_distance = float('inf')

    log.info(f"Assigning delivery partner for order ({order_id})....")

    delivery_partners = _get_available_delivery_partners(addr_state, addr_district, nearby_shop_coords)

    if not delivery_partners:
        log.warning(f"No available delivery partners for order ({order_id}) in {addr_district}, {addr_state}")
        return {}

    dp_id, assigned_partner = next(iter(delivery_partners.items()))

    # for dp_id, _ in delivery_partners.items():
    #     # update_partner_order(_.get('dp_id'))

    dp_lat = assigned_partner['dp_lat']
    dp_lon = assigned_partner['dp_lon']

    distance = utils.haversine(nearby_shop_coords[0], nearby_shop_coords[1], dp_lat, dp_lon)
    assigned_partner['shop_to_partner_radius'] = distance

    log.info(f"Calculated total travel distance for "
             f"{assigned_partner['dp_name']} ({dp_id}) is {total_travel_distance}km")

    if assigned_partner:
        log.info(f"Assigned partner: {assigned_partner['dp_name']} ({assigned_partner['dp_id']})")

        # Reset duty-update-status timestamp
        _update_partner_last_status_time(addr_state, addr_district, assigned_partner['dp_id'])

        return assigned_partner
    else:
        return {}


# def on_new_obv_order_received(data):
#     try:
#         order_time = utils.get_current_date_time()
#         order_time_millis = utils.get_current_millis()
#
#         # Extract and decrypt user information
#         order_id = data.get('order_id')
#         user_id_enc = data.get('user_id')
#         user_email_enc = data.get('user_email')
#         user_phno_enc = data.get('user_phno')
#         order_by_voice_doc_id = data.get('order_by_voice_doc_id')
#         order_by_voice_audio_ref_id = data.get('order_by_voice_audio_ref_id')
#         curr_lat = data.get('curr_lat')
#         curr_lon = data.get('curr_lon')
#
#         user_id = des_core.decrypt(user_id_enc).get('plain_text')
#         user_email = des_core.decrypt(user_email_enc).get('plain_text')
#         user_phno = des_core.decrypt(user_phno_enc).get('plain_text')
#
#         log.info("OBV order received")
#         actions.update_rtime_order_status(1, user_id=user_id, order_id=order_id, additional_payload={})
#
#         if not (user_phno != "0" and len(user_phno) == 10):
#             log.warning("Invalid phone number, unable to fetch user address data.")
#             return _generate_response(user_id, "Unknown", "Unknown", False)
#
#         log.info("Data decryption success, using DES")
#         addr_data = fca.get_address_data(uid=user_id, phno=user_phno)
#         user_name = addr_data.get('name', 'unknown')
#         user_full_address = addr_data.get('full_address', 'unknown')
#         addr_loc = addr_data.get('address_loc_coordinates', firestore.GeoPoint(0.0, 0.0))
#
#         addr_state = addr_data.get('state')
#         addr_district = addr_data.get('district')
#
#     except Exception as e:
#         log.error(f"Exception occurred in on_new_obv_order_received: {e}")
#         return _generate_response(data.get('user_id'), "Error occurred!",
#                                   None, False, str(e))


def on_new_obv_order_received_store_pref(data):
    try:
        order_time = utils.get_current_date_time()
        order_time_millis = utils.get_current_millis()

        # Extract and decrypt user information
        order_id = data.get('order_id')
        user_id_enc = data.get('user_id')
        user_email_enc = data.get('user_email')
        user_phno_enc = data.get('user_phno')
        order_by_voice_doc_id = data.get('order_by_voice_doc_id')
        order_by_voice_audio_ref_id = data.get('order_by_voice_audio_ref_id')
        curr_lat = data.get('curr_lat')
        curr_lon = data.get('curr_lon')

        user_id = des_core.decrypt(user_id_enc).get('plain_text')
        user_email = des_core.decrypt(user_email_enc).get('plain_text')
        user_phno = des_core.decrypt(user_phno_enc).get('plain_text')

        log.info("OBV order received (store-pref)")
        actions.update_rtime_order_status(1, user_id=user_id, order_id=order_id, additional_payload={})

        if not (user_phno != "0" and len(user_phno) == 10):
            log.warning("Invalid phone number, unable to fetch address and shop pref. data.")
            # addr_loc = firestore.GeoPoint(0.0, 0.0)
            return _generate_response(user_id, "Unknown", "Unknown", False)

        log.info("Data decryption success, using DES")
        addr_data = fca.get_address_data(uid=user_id, phno=user_phno)
        user_name = addr_data.get('name', 'unknown')
        user_full_address = addr_data.get('full_address', 'unknown')
        addr_loc = addr_data.get('address_loc_coordinates', firestore.GeoPoint(0.0, 0.0))

        addr_state = addr_data.get('state')
        addr_district = addr_data.get('district')

        del_addr_state_as_shop_state = ""
        del_addr_dist_as_shop_dist = ""

        if addr_district is not None and len(str(addr_district)) != 0:
            del_addr_dist_as_shop_dist = addr_district

        if addr_state is not None and len(str(addr_state)) != 0:
            del_addr_state_as_shop_state = addr_state

        if curr_lat and curr_lon:
            addr_loc = firestore.GeoPoint(round(float(curr_lat), 10), round(float(curr_lon), 10))
            addr_loc_type = "current"
        else:
            addr_loc_type = "actual"

        # # Fetch shop data
        # store_pref_data, all_shop_coords = fca.fetch_store_pref_data(uid=user_id, phno=user_phno,
        #                                                              shop_state=del_addr_state_as_shop_state,
        #                                                              shop_district=del_addr_dist_as_shop_dist)

        nearby_shop_data = get_nearby_shops((addr_loc.latitude, addr_loc.longitude), addr_state, addr_district)

        # if not store_pref_data:
        #     log.warning(f"No store preference data stored in db for phone {user_phno}")
        #     return _generate_response(user_id, None, None, False,
        #                               "No store preference stored in db")

        base_payload = {
            'user_id': user_id,
            'order_id': order_id,
            'order_type': KEYWORD.obv,
            'delivery_address': user_full_address,
            'delivery_loc_coordinates': addr_loc,
            'order_time': order_time,
            'order_time_millis': order_time_millis,
        }

        obv_data_payload = {
            'delivery_address_loc': addr_loc,
            'delivery_address_loc_type': addr_loc_type,
            'delivery_full_address': user_full_address,
            'order_by_voice_audio_ref_id': order_by_voice_audio_ref_id,
            'order_by_voice_doc_id': order_by_voice_doc_id,
            'order_type': KEYWORD.obv,
            'order_delivery_destination_distance': 0,
            'order_id': order_id,
            'shop_name': "VOICE ORDER",
            'order_saved_status': 'None',
            'order_status_bg_color': '#e0af19',
            'order_status_fg_color': '#990000',
            'order_status_label': 'Partner not assigned!',
            'order_status_no': 0,
            'order_time': order_time,
            'order_time_millis': order_time_millis,
            'pickup_destination_distance': 0,
            'user_email': user_email,
            'user_id': user_id,
            'user_name': user_name,
            'user_phno': user_phno
        }

        fcm_data_payload = {
            'order_id': order_id,
            'user_id': user_id,
            'title': 'New order received',
            'body': f"OBV order received from {user_name.upper()}",
        }

        # Assign delivery partner
        try:
            assigned_dp_data = assign_delivery_partner_obv1(order_id,
                                                            del_addr_state_as_shop_state,
                                                            del_addr_dist_as_shop_dist,
                                                            (nearby_shop_data.get('shop_loc_coords').latitude,
                                                             nearby_shop_data.get('shop_loc_coords').longitude))

            update_partner_order(assigned_dp_data.get('dp_id'), True)
            base_payload['dp_name'] = assigned_dp_data.get('dp_name')
            obv_data_payload['dp_name'] = assigned_dp_data.get('dp_name')

            if not assigned_dp_data:
                log.warning('No nearby delivery partner available!')

                osp_delivery_partner_not_assigned_payload = {
                    'user_name': user_name,
                    'shop_name': 'VOICE ORDER',
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
                    'dp_name': 'None',
                    'order_status_label': 'Delivery partner not assigned',
                    'order_status_label_bg_color': '#ab3109',
                    'order_status_label_fg_color': '#ffffff'
                }

                fca.add_order_to_users_bucket(user_id, base_payload, obv_data_payload)
                actions.update_rtime_order_status(2, user_id, order_id, osp_delivery_partner_not_assigned_payload)

                PendingOBVOrder.objects.update_or_create(
                    order_id=order_id,
                    defaults={
                        'user_id_enc': user_id_enc,
                        'request_body': data,
                        'order_type': KEYWORD.obv,
                        'status': 'pending'
                    }
                )

                WSChatRegister1.objects.update_or_create(
                    chat_id=order_id,
                    defaults={
                        'delivery_client_id': "None",
                        'order_client_id': user_id,
                        'is_delivery_partner_assigned': False,
                        'order_type': KEYWORD.obv,
                        'delivery_client_id_for_ws': 'None',
                        'order_client_id_for_ws': 'None'
                    }
                )

                log.info("ChatRegister updated for order ID %s", order_id)

                log.info(f"Order ({order_id}) added to pending list")

                return _generate_response(user_id, None, None,
                                          False,
                                          "No partner available nearby, we will assign a partner soon")

            dp_id = assigned_dp_data.get('dp_id', "None")
            dp_name = assigned_dp_data.get('dp_name', "Unknown")
            dp_lat = assigned_dp_data.get('dp_lat', 0)
            dp_lon = assigned_dp_data.get('dp_lon', 0)

            if dp_id == "None":
                log.error("Unable to determine delivery partner id, we will assign another partner soon...")

                osp_delivery_partner_not_assigned_payload = {
                    'user_name': user_name,
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
                    'dp_name': 'None',
                    'order_status_label': 'Delivery partner not assigned',
                    'order_status_label_bg_color': '#ab3109',
                    'order_status_label_fg_color': '#ffffff'
                }
                actions.update_rtime_order_status(2, user_id, order_id,
                                                  osp_delivery_partner_not_assigned_payload)
                return _generate_response(user_id, dp_id, dp_name, False,
                                          "Invalid delivery partner id returned")

            log.success(f"Delivery partner ({dp_id}) assigned successfully.")
            log.info_data(f"Assigned partner data: {assigned_dp_data}")

            oddd = utils.calc_dist_openroutes(dp_lat, dp_lon,
                                              addr_loc.latitude, addr_loc.longitude, "ODDD Distance")

            obv_data_payload.update({
                'shop_name': nearby_shop_data.get('shop_name'),
                'shop_id': nearby_shop_data.get('shop_id'),
                'order_delivery_destination_distance': oddd,
                'pickup_destination_distance': assigned_dp_data.get('shop_to_partner_radius')
            })

            fca.add_order_to_users_bucket(user_id, base_payload, obv_data_payload)
            fca.add_order_to_dp_bucket(order_id, dp_id, base_payload, obv_data_payload)

            osp_delivery_partner_assigned_payload = {
                'user_name': user_name,
                'dp_name': dp_name,
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

            actions.update_rtime_order_status(KEYWORD.delivery_partner_assigned, user_id, order_id,
                                              osp_delivery_partner_assigned_payload)

            fca.send_fcm_notification(dp_id, fcm_data_payload, 'delivery', f"Delivery partner {dp_name} ({dp_id}), "
                                                                           f"has been notified about the order")

            WSChatRegister1.objects.update_or_create(
                chat_id=order_id,
                defaults={
                    'delivery_client_id': dp_id,
                    'order_client_id': user_id,
                    'order_type': KEYWORD.obv,
                    'is_delivery_partner_assigned': True,
                    'delivery_client_id_for_ws': 'None',
                    'order_client_id_for_ws': 'None'
                }
            )
            log.info("ChatRegister updated for order ID %s", order_id)
            log.info_data(partner_order)
            return _generate_response(user_id, dp_id, dp_name, True)

        except Exception as e:
            log.error(f"Error assigning delivery partner: {e}")
            return _generate_response(user_id, "Error occurred!", None, False, str(e))

    except Exception as e:
        log.error(f"Exception occurred in on_new_obv_order_received (store-pref): {e}")
        return _generate_response(data.get('user_id'), "Error occurred!",
                                  None, False, str(e))


def _generate_response(user_id, dp_id, partner_name, is_assigned, message=None):
    if dp_id is None:
        response = {
            "user_id": user_id,
            "dp_id": "No delivery partner available",
            "is_assigned": is_assigned
        }
    else:
        response = {
            "user_id": user_id,
            "dp_id": dp_id,
            "partner_name": partner_name,
            "is_assigned": is_assigned
        }
    if message:
        response["message"] = message
    return response
