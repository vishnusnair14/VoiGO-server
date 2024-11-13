"""
recommendation.py

Part of VoiGO-Server

Module of the Intellicart-Server project responsible for recommending
shops to users based on their location and city within a specified radius.

"""

from pygeohash import geohash
from pymongo import MongoClient

from VoiGO.settings import log
from server import constants, utils
from server.cloud import cloud as fca


# # Master method [legacy]
# def recommend_shops1(user_la: float, user_lo: float, user_city: str,
#                      _user_pincode: str, max_radius_km: int = constants.SRE_MAX_RADIUS):
#     """
#     Recommends shops based on the user's location and city within a specified radius.
#
#     This function takes the user's latitude, longitude, and city, and returns a
#     list of shops within the specified radius from the user's location. It fetches registered
#     shops in the user's city, calculates the distance of each shop from the user's location,
#     and filters shops within the maximum radius. The filtered shops are then sorted based on
#     distance and returned as recommended shops.
#
#     :param user_la: Latitude of the user's location.
#     :param user_lo: Longitude of the user's location.
#     :param user_city: City of the user.
#     :param _user_pincode:
#     :param max_radius_km: Maximum radius in kilometers within which to recommend shops.
#                           Defaults to constants.MAX_RADIUS.
#
#     :return:  dict: A dictionary containing recommended shop data, sorted by distance from
#               the user's location.
#     """
#
#     filtered_shops = []
#     registered_shops = []
#     shop_pincode = ""
#     shops_found = False
#
#     if user_city == "NONE" or user_city is None:
#         user_city = _reverse_geocode(user_la, user_lo)
#         log.info("DECODED CITY: " + user_city)
#
#     # use when post_office_name used as doc reference
#     # post_off_name = validate_pincode(_user_pincode).get('post_off_name').lower()
#
#     # use when pincode used as doc reference
#     post_off_name = _user_pincode
#
#     registered_shops_db = _fetch_shops_in_city(user_city, post_off_name)
#
#     if registered_shops_db:
#         registered_shops = list(registered_shops_db.values())
#         shops_found = True
#         shop_pincode = _user_pincode
#     else:
#         log.info(f"No registered shops found within pincode {_user_pincode}, finding nearby...")
#         log.info("Calculating nearby pincodes...")
#
#         # fetch all pincodes of user city and remove redundant
#         all_pincode_in_city = _get_all_pincodes_db(city=user_city)
#         if _user_pincode in all_pincode_in_city:
#             all_pincode_in_city.remove(_user_pincode)
#             # log.info("ALL PINCODES: ", all_pincode_in_city)
#
#         _nearest_pincodes = _find_nearest_pincodes(_user_pincode, all_pincode_in_city)  # Nearest pincodes
#         log.info(green("Calculated nearest pincodes: ", ['bold']), red(_nearest_pincodes, ['bold']))
#
#         for nearest_pincode, _ in _nearest_pincodes:
#             nearest_shops_db = _fetch_shops_in_city(user_city, nearest_pincode)
#
#             if nearest_shops_db:
#                 log.info(green(f"Recommending shops within pincode {nearest_pincode}: {user_city}"))
#                 shop_pincode = nearest_pincode
#                 registered_shops = (list(nearest_shops_db.values()))
#                 shops_found = True
#                 break
#             else:
#                 log.info(
#                     magenta(f"No registered shops found within pincode {nearest_pincode}, finding next...",
#                             ['bold', 'underlined']))
#
#     if not shops_found:
#         log.info(magenta("No registered shops found in nearby pincodes too.", ['bold', 'underlined']))
#
#     for shop in registered_shops:
#         distance_km = utils.calc_distance(user_la, user_lo, shop['shop_loc_cords'].latitude,
#                                      shop['shop_loc_cords'].longitude, shop['shop_name'])
#
#         if distance_km <= max_radius_km:
#             shop_info = {
#                 "shop_id": shop["shop_id"],
#                 "shop_name": shop["shop_name"],
#                 "shop_place": shop["shop_place"],
#                 "shop_image_url": shop["shop_image_url"],
#                 "shop_lat": shop['shop_loc_cords'].latitude,
#                 "shop_lon": shop['shop_loc_cords'].longitude,
#                 "shop_city": shop["shop_city"],
#                 "distance_km": distance_km
#             }
#             filtered_shops.append(shop_info)
#
#     sorted_shops = sorted(filtered_shops, key=lambda shop1: shop1['distance_km'])
#     log.info(f"RECOMMENDED SHOP DATA: {sorted_shops}")
#
#     return {'recommended_shop_data': sorted_shops, 'shop_pincode': shop_pincode}


def recommend_shops1(user_latitude: float, user_longitude: float, user_state: str,
                     user_district: str = None, user_pincode: str = None,
                     radius_km: int = constants.SRE_MAX_RADIUS):
    """
    Recommends shops based on the user's location and city within a specified radius.

    This function takes the user's latitude, longitude, and city, and returns a
    list of shops within the specified radius from the user's location. It fetches registered
    shops in the user's city, calculates the distance of each shop from the user's location,
    and filters shops within the maximum radius. The filtered shops are then sorted based on
    distance and returned as recommended shops.

    :param user_state:
    :param user_latitude: Latitude of the user's location.
    :param user_longitude: Longitude of the user's location.
    :param user_district: City of the user.
    :param user_pincode: Pincode of the user.
    :param radius_km: Maximum radius in kilometers within which to recommend shops.
#                     Defaults to constants.MAX_RADIUS.
    :return:
    """

    user_location = (user_latitude, user_longitude)
    user_geohash = geohash.encode(user_location[0], user_location[1],
                                  precision=constants.GEOHASH_PRECISION)
    log.info(f"User Geohash: {user_geohash}")
    nearby_shops = []

    if user_latitude == 0 and user_longitude == 0:
        if user_pincode is not None:
            log.warning("User lat, lon are null, using calculated coordinates from pincode...")
            # Use the pincode to fetch latitude and longitude
            user_latitude, user_longitude = utils.get_coordinates_from_pin(user_pincode)
            user_location = (user_latitude, user_longitude)
            log.info(f"Calculated coordinates from pincode {user_pincode}: "
                     f"Latitude = {user_latitude}, Longitude = {user_longitude}")

    if user_district != "None" or user_pincode != "None":
        # Query Firestore to fetch all shops in the city
        query = (fca.cloudFirestore.collection('ShopData').document('data')
                 .collection(user_state.lower()).document(user_district.lower()).collection("allShopData"))
        results = query.stream()
        log.info("Recommendation based on defined co-ordinates")

    elif user_district == "None" or user_pincode == "None":
        resp = utils.reverse_geocode_bigdatacloud(user_latitude, user_longitude)

        user_state = str(resp.get('state')).lower()
        user_district = utils.district_to_format(resp.get('district'))

        # Query Firestore to fetch all shops in the city
        query = (fca.cloudFirestore.collection('ShopData').document('data')
                 .collection(user_state.lower()).document(user_district.lower()).collection("allShopData"))
        results = query.stream()
        log.info("Recommendation based on real-time co-ordinates")

    else:
        return {'recommended_shop_data': {}, 'shop_pincode': user_pincode}

    for shop in results:
        shop_data = shop.to_dict()
        shop_location = (shop_data['shop_loc_coords'].latitude,
                         shop_data['shop_loc_coords'].longitude)

        # Calculate geohash for the shop location
        shop_geohash = geohash.encode(shop_location[0], shop_location[1],
                                      precision=constants.GEOHASH_PRECISION)

        # Check if the shop's geohash is within the geohash range of the user
        if user_geohash[:-1] <= shop_geohash <= user_geohash + '\uf8ff':
            displacement = utils.haversine(user_location[0], user_location[1],
                                           shop_location[0], shop_location[1])

            log.info(f"Shop {str(shop_data['shop_name']).upper()} "
                     f"{displacement}, {shop_geohash} (radius, geohash)")

            if displacement <= radius_km:
                # distance_km = utils.calc_dist_openroutes(user_location[0], user_location[1], shop_location[0],
                #                                          shop_location[1], f"{shop_data['shop_name']} is")

                shop_info = {
                    "shop_id": shop_data["shop_id"],
                    "shop_name": shop_data["shop_name"],
                    "shop_street": shop_data["shop_street"],
                    "shop_image_url": shop_data["shop_image_url"],
                    "shop_lat": shop_data['shop_loc_coords'].latitude,
                    "shop_lon": shop_data['shop_loc_coords'].longitude,
                    "shop_state": shop_data["shop_state"],
                    "shop_district": shop_data['shop_district'],
                    "distance_km": displacement,
                    "displacement": displacement
                }
                nearby_shops.append(shop_info)

    sorted_shops = sorted(nearby_shops, key=lambda _shop: _shop['distance_km'])
    log.info(f"RECOMMENDED SHOP DATA: {sorted_shops}")

    return {'recommended_shop_data': sorted_shops, 'shop_pincode': user_pincode}


def recommend_shops123(user_latitude: float, user_longitude: float, user_state: str,
                       user_district: str = None, user_pincode: str = None,
                       radius_km: int = constants.SRE_MAX_RADIUS):
    """
    Recommends shops based on the user's location and city within a specified radius.

    :param user_state:
    :param user_latitude: Latitude of the user's location.
    :param user_longitude: Longitude of the user's location.
    :param user_district: City of the user.
    :param user_pincode: Pincode of the user.
    :param radius_km: Maximum radius in kilometers within which to recommend shops.
    :return: A dictionary containing recommended shop data and the shop pincode.
    """

    nearby_shops = []
    calculated_from_pincode = False
    user_location = (user_latitude, user_longitude)
    user_geohash = geohash.encode(user_location[0], user_location[1],
                                  precision=constants.GEOHASH_PRECISION)

    log.info(f"User Geohash: {user_geohash}")

    if user_latitude == 0 and user_longitude == 0:
        if user_pincode is not None:
            log.warning("User lat, lon are null, using calculated coordinates from pincode...")
            # Use the pincode to fetch latitude and longitude
            user_latitude, user_longitude = utils.get_coordinates_from_pin(user_pincode)
            user_location = (user_latitude, user_longitude)
            calculated_from_pincode = True
            log.info(f"Calculated coordinates from pincode {user_pincode}: "
                     f"Latitude = {user_latitude}, Longitude = {user_longitude}")

    if user_district != "None" or user_pincode != "None":
        # Query Firestore to fetch all shops in the city
        query = (fca.cloudFirestore.collection('ShopData').document('data')
                 .collection(user_state.lower()).document(user_district.lower()).collection("allShopData"))
        results = query.stream()
        log.info("Recommendation based on defined coordinates")

    elif user_district == "None" or user_pincode == "None":
        resp = utils.reverse_geocode_bigdatacloud(user_latitude, user_longitude)

        user_state = str(resp.get('state')).lower()
        user_district = utils.district_to_format(resp.get('district'))

        # Query Firestore to fetch all shops in the city
        query = (fca.cloudFirestore.collection('ShopData').document('data')
                 .collection(user_state.lower()).document(user_district.lower()).collection("allShopData"))
        results = query.stream()
        log.info("Recommendation based on real-time coordinates")

    else:
        return {'recommended_shop_data': {}, 'shop_pincode': user_pincode}

    for shop in results:
        shop_data = shop.to_dict()
        shop_location = (shop_data['shop_loc_coords'].latitude,
                         shop_data['shop_loc_coords'].longitude)

        # Calculate displacement only when coordinates are calculated from pincode
        displacement = utils.haversine(user_location[0], user_location[1],
                                       shop_location[0], shop_location[1])

        log.info(f"Shop {str(shop_data['shop_name']).upper()} "
                 f"{displacement} km from user, (Geohash comparison skipped)")

        # If the coordinates were calculated from pincode, filter based on 10km radius
        if calculated_from_pincode:
            if displacement <= 10:  # 10 km radius
                shop_info = {
                    "shop_id": shop_data["shop_id"],
                    "shop_name": shop_data["shop_name"],
                    "shop_street": shop_data["shop_street"],
                    "shop_image_url": shop_data["shop_image_url"],
                    "shop_lat": shop_data['shop_loc_coords'].latitude,
                    "shop_lon": shop_data['shop_loc_coords'].longitude,
                    "shop_state": shop_data["shop_state"],
                    "shop_district": shop_data['shop_district'],
                    "distance_km": displacement,
                    "displacement": displacement
                }
                nearby_shops.append(shop_info)
        else:
            # Normal behavior when not calculated from pincode
            shop_geohash = geohash.encode(shop_location[0], shop_location[1],
                                          precision=constants.GEOHASH_PRECISION)
            if user_geohash[:-1] <= shop_geohash <= user_geohash + '\uf8ff':
                if displacement <= radius_km:
                    shop_info = {
                        "shop_id": shop_data["shop_id"],
                        "shop_name": shop_data["shop_name"],
                        "shop_street": shop_data["shop_street"],
                        "shop_image_url": shop_data["shop_image_url"],
                        "shop_lat": shop_data['shop_loc_coords'].latitude,
                        "shop_lon": shop_data['shop_loc_coords'].longitude,
                        "shop_state": shop_data["shop_state"],
                        "shop_district": shop_data['shop_district'],
                        "distance_km": displacement,
                        "displacement": displacement
                    }
                    nearby_shops.append(shop_info)

    sorted_shops = sorted(nearby_shops, key=lambda _shop: _shop['distance_km'])
    log.info(f"RECOMMENDED SHOP DATA: {sorted_shops}")
    # log.info(utils.get_coordinates_from_address('Elappulli, Kerala'))

    return {'recommended_shop_data': sorted_shops, 'shop_pincode': user_pincode}


client = MongoClient('mongodb://localhost:27017/')
db = client['VoiGO']  # Replace with your MongoDB database name
shop_collection = db['ShopData']  # Replace with the correct collection name


def recommend_shops(user_latitude: float, user_longitude: float, user_state: str,
                    user_district: str = None, user_pincode: str = None,
                    radius_km: int = 10):
    """
    Recommends shops based on the user's location and city within a specified radius.

    :param user_state: State of the user.
    :param user_latitude: Latitude of the user's location.
    :param user_longitude: Longitude of the user's location.
    :param user_district: City of the user.
    :param user_pincode: Pincode of the user.
    :param radius_km: Maximum radius in kilometers within which to recommend shops.
    :return: A dictionary containing recommended shop data and the shop pincode.
    """
    nearby_shops = []
    calculated_from_pincode = False
    user_location = (user_latitude, user_longitude)
    user_geohash = geohash.encode(user_location[0], user_location[1], precision=5)

    log.info(f"User Geohash: {user_geohash}")

    # If latitude and longitude are not provided, use pincode to calculate coordinates
    if user_latitude == 0 and user_longitude == 0:
        if user_pincode is not None:
            log.warning("User lat, lon are null, using calculated coordinates from pincode...")
            # You would need a function to convert pincode to coordinates here
            user_latitude, user_longitude = utils.get_coordinates_from_pin(user_pincode)
            user_location = (user_latitude, user_longitude)
            calculated_from_pincode = True
            log.info(f"Calculated coordinates from pincode {user_pincode}: "
                     f"Latitude = {user_latitude}, Longitude = {user_longitude}")

    # Prepare MongoDB query based on available details (state, district, pincode)
    if user_district and user_district != "None":
        # Query MongoDB for shops in the user's district and state
        query = {
            'shop_state': user_state,
            'shop_district': user_district
        }
        shops_cursor = shop_collection.find(query)

        log.info("Recommendation based on defined coordinates")
    elif user_district == "None" or user_pincode == "None":
        # Reverse geocode the coordinates to find state and district
        resp = utils.reverse_geocode_bigdatacloud(user_latitude, user_longitude)
        user_state = str(resp.get('state')).lower()
        user_district = utils.district_to_format(resp.get('district'))

        # Query MongoDB for shops in the user's state and district
        query = {
            'shop_state': user_state,
            'shop_district': user_district
        }
        shops_cursor = shop_collection.find(query)
        log.info("Recommendation based on real-time coordinates")
    else:
        return {'recommended_shop_data': {}, 'shop_pincode': user_pincode}

    # Process the shop data
    for shop in shops_cursor:
        shop_location = (
            shop['shop_loc_coords']['latitude'],
            shop['shop_loc_coords']['longitude'])  # Assuming MongoDB stores coordinates like this

        # Calculate displacement between user and shop using haversine
        displacement = utils.haversine(user_location[0], user_location[1],
                                       shop_location[0], shop_location[1])

        log.info(f"Shop {shop['shop_name']} {displacement} km from user")

        # Filter shops based on distance (radius)
        if displacement <= radius_km:
            shop_info = {
                "shop_id": shop["shop_id"],
                "shop_name": shop["shop_name"],
                "shop_street": shop["shop_street"],
                "shop_address": shop["shop_address"],
                "shop_image_url": shop["shop_image_url"],
                "shop_lat": shop['shop_loc_coords']['latitude'],
                "shop_lon": shop['shop_loc_coords']['longitude'],
                "shop_state": shop["shop_state"],
                "shop_district": shop["shop_district"],
                "distance_km": displacement,
                "displacement": displacement
            }
            nearby_shops.append(shop_info)

    # Sort the shops by distance
    sorted_shops = sorted(nearby_shops, key=lambda _shop: _shop['distance_km'])
    log.info(f"RECOMMENDED SHOP DATA: {sorted_shops}")

    return {'recommended_shop_data': sorted_shops, 'shop_pincode': user_pincode}
