# constants.py

"""
Common constants

"""

"""
Base constants

"""

DIRECTION_API_KEY = "5b3ce3597851110001cf624822f3c911e8e94c9eb2f2140015e11968"
DIRECTION_URL = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"

# Define the base URL for the BigDataCloud API
BIGDATA_BASE_URL = 'https://api.bigdatacloud.net/data/reverse-geocode-client'

APP_EMAIL_HOST = 'voigo.delivery@gmail.com' #TODO


# DES Key and IV must match the client side code
DES_KEY = b'firebase'
DES_IV = b'esaberif'

SSE_ORDER_UPDATE_STREAM_DELAY: int = 6  # in sec


class KEYWORD:
    production = 'production'
    development = 'development'

    connect = 'connect'
    disconnect = 'disconnect'

    delivery = 'delivery'
    user = 'user'
    order = 'order'
    obs = 'obs'
    obv = 'obv'

    cancel = 'cancel'
    update = 'update'

    order_placed = 1
    delivery_partner_not_assigned = 2
    delivery_partner_assigned = 2
    order_accepted = 3
    order_pickup = 4
    order_enrouted = 5
    order_delivered = 6


# ----------------------------------------------------------------------------------------------------------------


"""
Constants for recommendation.py

"""
KEYWORD
SRE_MAX_RADIUS = 10  # in km

GEOCODE_URL = "https://api.openrouteservice.org/geocode/reverse"

SRE_DIRECTION_AUTH_HEADER = {
    'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
    'Authorization': DIRECTION_API_KEY,
    'Content-Type': 'application/json; charset=utf-8'
}

rev_geocode_header = {
    'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
}

# ----------------------------------------------------------------------------------------------------------------
"""
Constants for obv.py

"""

MIN_ASSIGNABLE_TIME_MILLIS = 60 * 1000  # 60sec in milliseconds

"""
Constants for obs.py

"""

OPE_MIN_RADIUS = 2.5  # in km
OPE_MAX_RADIUS = 5  # in km

# ORDER_PLACED = 1
# DELIVERY_PARTNER_ASSIGNED = 2
# DELIVERY_PARTNER_NOT_ASSIGNED = 2
# ORDER_ACCEPTED = 3
# ORDER_PICKUP = 4
# ORDER_ENROUTED = 5
# ORDER_DELIVERED = 6

ope_direction_auth_header = {
    'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
    'Authorization': DIRECTION_API_KEY,
    'Content-Type': 'application/json; charset=utf-8'
}

# ----------------------------------------------------------------------------------------------------------------

"""
Constants for cloud.py

"""

WR_BATCH_SIZE = 15

HTTP_V1_FCM_TOKEN = ("eitR1JsHRZOQJoEDsypv56:APA91bE_HsyKJ4wLPLEDF2m2BapTwdbPgOijxMcV0XQU5tt96nO4wiRn"
                     "mHn_G1K5XQs3l2pBwbctfqEB01fRlNKDU0mFeCSlbR5wBmGudSiHoZ-pv8WryJsFqg4hvuWZLE9s6vk3qoqz")

HTTP_V1_FCM_URL = "https://fcm.googleapis.com/v1/projects/intelli-cart/messages:send"

FCM_MSG_SCOPE: list[str] = ['https://www.googleapis.com/auth/firebase.messaging']

GOOGLE_API_KEY_RICHI = 'AIzaSyBSoDI5Ac5wDO29OhioxtSVXYsz-v5-tp4'

GOOGLE_MAPS_API_KEY_VOIGO = 'AIzaSyBd39kAqdg2XVFpubSLPA_bWHt0v6wf8b4' 


GEOHASH_PRECISION = 4

# ----------------------------------------------------------------------------------------------------------------

"""
constants for payment.py

"""

RAZOR_KEY_SECRET = "Tao4vHxKLzHdasw21RIn4Uj1"
RAZOR_API_KEY = "rzp_test_NCpSk028UHZ9ug"
