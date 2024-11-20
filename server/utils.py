# utils.py


import json
import math
import os
import random
import re
import string
import sqlite3
from datetime import datetime

import requests
from django.core.mail import send_mail
from geopy import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from simple_colors import *

from VoiGO.settings import log
from server import constants
from server.cloud import cloud as fca

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VoiGO.settings')


def _generate_random_str(length: int = 8) -> str:
    """
    Generates a random string of specified length consisting of
    ASCII letters (both uppercase and lowercase) and digits.

    :param length: The length of the random string to generate (default is 8).
    :rtype: str
    :return: A random string of the specified length.
    """

    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def get_coordinates_from_pin(pincode):
    geolocator = Nominatim(user_agent="VoiGO")
    location = geolocator.geocode(pincode)
    if location:
        return location.latitude, location.longitude
    else:
        # raise ValueError(f"Coordinates for pincode {pincode} not found")
        print(magenta(f"Coordinates for pincode {pincode} not found", ['bold', 'underlined']))
        return None


def get_coordinates_from_address(address: str):
    """
    Get the latitude and longitude for a given address.

    :param address: The address as a string.
    :return: Tuple containing (latitude, longitude) or None if not found.
    """
    geolocator = Nominatim(user_agent="shop_recommendation_app")

    try:
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
        else:
            print(f"Address not found: {address}")
            return None
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Geocoding error: {e}")
        return None


def _get_all_pincodes_db(city: str) -> list:
    # Retrieve the document snapshot
    doc_ref = (fca.cloudFirestore.collection("ShopData").document("allShopPincodes")
               .collection("pincodes").document(city))
    doc = doc_ref.get()

    if doc.exists:
        # Access the array field containing all pincodes
        all_pincodes = doc.to_dict().get('all_pincodes', [])
        return list(all_pincodes)
    else:
        print("Document does not exist.")
        return []


def _find_nearest_pincodes(_target_pincode, _pincode_list):
    target_coord = get_coordinates_from_pin(_target_pincode)
    final_pincodes = []

    for pincode in _pincode_list:
        coord = get_coordinates_from_pin(pincode)
        # print(target_coord[0], target_coord[1], coord[0], coord[1])

        distance = calc_dist_openroutes(target_coord[0], target_coord[1],
                                        coord[0], coord[1], pincode)
        final_pincodes.append((pincode, distance))

    # Sort based on distance
    final_pincodes.sort(key=lambda x: x[1])

    # Return the nearest two pincodes
    return final_pincodes[:2]


def get_current_date() -> str:
    """ Returns current date stamp in DDMMMYYYY format

    :rtype: str
    :return str:
    """
    return datetime.now().strftime("%d%b%Y").upper()


def get_current_date_time() -> str:
    """
    Returns the current date-time stamp

    :return: Current timestamp as a string in the format DD-MMM-YYYY HH:MM:SS AM/PM
    :rtype: str
    """

    return datetime.now().strftime("%d-%b-%Y %I:%M:%S %p").upper()


def get_current_millis():
    try:
        # Parse the input string to a datetime object
        current_time = datetime.strptime(datetime.now().strftime("%d-%m-%Y %H:%M:%S").upper(),
                                         "%d-%m-%Y %H:%M:%S")

        current_time_millis = int(current_time.timestamp() * 1000)

        return current_time_millis

    except ValueError:
        # Handle invalid input format
        print("Invalid format. Please enter the date and time in DD-MM-YYYY HH:MM:SS format.")
        return ""


def send_email(_to: str, subject: str = 'Hello from VOIGO Server',
               message: str = 'This is a test email sent from VoiGO server, your account has been hacked'):
    recipient_list = [_to]

    try:
        # Send email using send_mail function
        send_mail(subject, message, constants.APP_EMAIL_HOST, recipient_list)
        return {'success': True}
    except Exception as e:
        print("Error: Exception occurred: " + str(e))
        return {'success': False, 'error': str(e)}


def calc_dist_openroutes(lat1: float, lon1: float, lat2: float, lon2: float,
                         ref_str: str) -> int:
    """
    Calculate the distance (driving-mode) between two co-ordinates,
    This is made possible using openrouteservice.org APIs.

    :param lat1:
    :param lon1:
    :param lat2:
    :param lon2:
    :param ref_str:
    :return: int:Calculated distance (in km)

    """

    distance_km = 0

    body = {"coordinates": [[lon1, lat1], [lon2, lat2]]}

    # Make an API request
    call = requests.post(constants.DIRECTION_URL, json=body, headers=constants.ope_direction_auth_header)

    # Check if the request was successful (status code 200)
    if call.status_code == 200:
        data = call.json()

        # Extract the distance from the response
        distance_meters = data['features'][0]['properties']['segments'][0]['distance']
        distance_km = distance_meters / 1000
        print(blue(f'DISTANCE: {ref_str} {round(distance_km, 4)} km away', ['bold', 'underlined']))
    else:
        print(f"Error calculating distance! {ref_str}")

    return distance_km


def convert_datetime_str(input_str) -> str:
    """
    Convert a datetime string from 'ddmmyyyyHHMMSS' format to 'dd-mm-yyyy hh:mm:ss AM/PM' format.

    Args:
    - input_str (str): The input datetime string in 'ddmmyyyyHHMMSS' format.

    Returns:
    - str: The formatted datetime string in 'dd-mm-yyyy hh:mm:ss AM/PM' format.
    """
    # Parse the input string into a datetime object
    input_str = str(input_str)

    dt = datetime.strptime(input_str, "%d%m%Y%H%M%S")

    # Format the datetime object into the desired string format
    formatted_str = dt.strftime("%d-%m-%Y %I:%M:%S %p")

    return formatted_str


def haversine(lat1_deg, lon1_deg, lat2_deg, lon2_deg):
    """
    Calculate the great-circle distance between two points
    on the Earth specified in decimal degrees of latitude and longitude.
    """
    r = 6371  # Earth radius in kilometers

    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1_deg)
    lon1_rad = math.radians(lon1_deg)
    lat2_rad = math.radians(lat2_deg)
    lon2_rad = math.radians(lon2_deg)

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = r * c
    return round(distance, 4)


def validate_pincode(pincode):
    pincode_val_url = "http://www.postalpincode.in/api/pincode/"
    url = pincode_val_url + pincode.strip()

    try:
        response = requests.get(url)
        response_data = response.json()

        if response_data['Status'] == "Error":
            print("Invalid Pincode")
            return {'is_valid': False, 'post_off_name': 'None', 'message': 'Invalid Pincode!'}
        else:
            post_office_info = response_data.get("PostOffice", [])
            if post_office_info:
                post_office = post_office_info[0]
                state_name = post_office.get("State", "")
                district_name = post_office.get("District", "")
                post_off_name = post_office.get("Name", "")

                print(f"Pincode {pincode} validated: [{post_off_name}-{district_name}-{state_name}]")

                if post_off_name:
                    return {'is_valid': True, 'post_off_name': post_off_name, 'message': 'Pincode validated'}
                else:
                    return {'is_valid': False, 'post_off_name': 'None', 'message': 'Invalid Pincode!'}
            else:
                return {'is_valid': False, 'post_off_name': 'None', 'message': 'Invalid Pincode!'}
    except requests.RequestException as e:
        print(f"Request error: {e}")
        return {'is_valid': False, 'post_off_name': 'None', 'message': 'Request Error!'}
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return {'is_valid': False, 'post_off_name': 'None', 'message': 'Response Error!'}

# Function to get location information based on specific coordinates
def reverse_geocode_bigdatacloud(lat, lon, locality_language='en'):
    """
        Performs reverse geocoding using the BigDataCloud API. It takes latitude and longitude coordinates
        as input and returns a dictionary with geographic information about the specified location, such as
        the country, state, district, and other details.

        :param lat: (float): Latitude of the location to be reverse geocoded.
        :param lon: (float): Longitude of the location to be reverse geocoded.
        :param locality_language: (Optional) The language in which the locality names should be returned.
        Default is 'en' for English.

        :return:
         - dict: A dictionary containing geographic information about the location. The keys are labels
         ("country", "state", "district", "other").
         - None: If the API request fails (i.e., the status code is not 200), the function returns None.
        :rtype: dict

    """

    ret_list = {}
    labels = {
        0: "country",
        1: "state",
        2: "district",
        3: "other"
    }

    params = {
        'latitude': lat,
        'longitude': lon,
        'localityLanguage': locality_language
    }
    response = requests.get(constants.BIGDATA_BASE_URL, params=params)
    if response.status_code == 200:
        res = response.json()

        if res:
            for index, admin in enumerate(res['localityInfo']['administrative']):
                name = str(admin.get('name', 'Name not found'))
                label = labels.get(index, 'Other')
                ret_list[label] = name
                if index == 3:
                    break
        return ret_list
    else:
        return None


def reverse_geocode_openroutes(lat: float, lon: float) -> dict:
    """
    Get the reverse geocode for the specified latitude and longitude.

    This function makes a request to the OpenRouteService API to reverse geocode
    the provided latitude and longitude coordinates and returns the city/place
    from the location coordinates.

    :param lat: Latitude of the location.
    :param lon: Longitude of the location.

    :return: dict: 'city_name': The city/place from the provided location coordinates.
    """

    try:
        call = requests.get(
            f"https://api.openrouteservice.org/geocode/reverse?api_key={constants.DIRECTION_API_KEY}"
            f"&point.lon={lon}&point.lat={lat}")

        data = call.json()
        return {'city_name': str(data['features'][0]['properties']['name']).lower(), 'error': 'NOne'}
    except Exception as e:
        return {'city_name': 'None', 'error': str(e)}


def compute_route_matrix(lat1: str, lon1: str, lat2: str, lon2: str,
                         routing_preference="TRAFFIC_AWARE"):
    """
    Sends a POST request to the Google Distance Matrix API to compute the route matrix.

    :param lon2:
    :param lat2:
    :param lon1:
    :param lat1:
    :param routing_preference: The routing preference (e.g., TRAFFIC_AWARE). Default is "TRAFFIC_AWARE".

    """
    # Define origins and destinations as lists of dictionaries
    origins = [
        {
            "waypoint": {
                "location": {
                    "latLng": {
                        "latitude": lat1,
                        "longitude": lon1
                    }
                }
            },
            "routeModifiers": {"avoid_ferries": True}
        }
    ]

    destinations = [
        {
            "waypoint": {
                "location": {
                    "latLng": {
                        "latitude": lat2,
                        "longitude": lon2
                    }
                }
            }
        }
    ]

    # Set request parameters
    data = {
        "origins": origins,
        "destinations": destinations,
        "routingPreference": routing_preference
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": constants.GOOGLE_API_KEY_RICHI,
        "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,status,condition"
    }

    # Send POST request
    url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
    response = requests.post(url, headers=headers, json=data)

    # Check response status and handle data
    if response.status_code == 200:
        return {'response': response.json()}
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return {'status': 'failed'}


def district_to_format(input_string):
    try:
        # Define the regex pattern to match words containing 'dist'
        pattern = r'\b\w*dist\w*\b'

        # Use re.sub to replace all occurrences of the pattern with an empty string
        rs = re.sub(pattern, '', input_string)

        # Remove any extra whitespace that might have been left behind
        rs = re.sub(r'\s+', ' ', rs).strip()

        return rs.lower()
    except Exception as e:
        print(e)
        return "None"


def intimate_partner(dp_id: str):
    fcm_data_payload = {
        'order_id': "DELIVERY WAITING ALERT",
        'body': "Somebody is waiting for a delivery partner, switch-on DMODE", }

    fca.send_fcm_notification(dp_id, fcm_data_payload, 'delivery')
    pass


def calculate_centroid(coords: list):
    x = 0
    y = 0
    z = 0

    for lat, lon in coords:
        lat = math.radians(lat)
        lon = math.radians(lon)

        x += math.cos(lat) * math.cos(lon)
        y += math.cos(lat) * math.sin(lon)
        z += math.sin(lat)

    x /= len(coords)
    y /= len(coords)
    z /= len(coords)

    lon_centroid = math.atan2(y, x)
    hyp = math.sqrt(x * x + y * y)
    lat_centroid = math.atan2(z, hyp)

    return math.degrees(lat_centroid), math.degrees(lon_centroid)


# ---------------------------------------------------------------------------------------------

def clear_table(table_no: int):
    table_map = {
        1: 'huey_monitor_signalinfomodel',
        2: 'huey_monitor_taskmodel',
        3: 'server_ordermap',
        4: 'server_pendingobvorder',
        5: 'server_pendingobsorder',
        6: 'server_temporaryaddress',
        7: 'server_uploadedimage',
        8: 'server_wschatregister',
        9: 'clear_all_tables'
    }

    if 1 <= table_no <= len(table_map):
        try:
            # Connect to the SQLite3 database
            conn = sqlite3.connect(r"D:\VoiGo-Server\VoiGO\db.sqlite3")
            cursor = conn.cursor()

            if table_no == len(table_map):
                # Delete all the specified tables
                for tbl_no in range(1, len(table_map)):
                    table_name = table_map[tbl_no]
                    cursor.execute(f"DELETE FROM {table_name}")
                    log.info(f"All entries from table '{table_name}' have been deleted.")
            else:
                # Delete entries from the specific table
                table_name = table_map[table_no]
                cursor.execute(f"DELETE FROM {table_name}")
                log.info(f"All entries from table '{table_name}' have been deleted.")

            # Commit the changes
            conn.commit()

            # Close the connection
            conn.close()

        except Exception as eo:
            log.exception(f"Exception occurred at {__file__}.clear_table {str(eo)}")

    else:
        log.warning("Table number should be between 1 to 9")
