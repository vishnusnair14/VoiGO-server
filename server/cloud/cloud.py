"""
cloud.py

Part of VoiGO-Server script

-----------------------------------------
Project name: VoiGO (C) 2024
Created on: 14-07-2024 10:56 AM
Author: vishnu s
-----------------------------------------

This module provides functionalities to interact with Firebase services,
including Firestore and Firebase Cloud Messaging (FCM), for managing various
aspects of VoiGO-Server. It includes functions for handling orders,
sending notifications, managing user data, and more.

Functions:
    The script consists of functions designed to interact with
    Firebase Firestore and Firebase Cloud Messaging (FCM).

    Its primary purpose is to manage order and client data within the context of
    an e-commerce platform.

    Tasks handled by the functions include managing user and delivery partner
    orders, sending notifications, updating order statuses, and retrieving data
    from the Firestore database.

    Key functionalities provided by the functions include enqueueing and dequeue
    order data, accepting, declining, saving, picking up, and delivering orders.

    The script also includes functions for fetching shop data and user addresses
    from the Firestore database.

    Additional features include functions for sending FCM messages using both the
    HTTP v1 API and the legacy API.

    Overall, these functions collectively create a robust backend system for
    managing orders and notifications within an e-commerce application.

"""

import json
import os
import threading
from datetime import datetime
from datetime import timedelta

import firebase_admin
import google.auth
import requests
from decouple import config
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from firebase_admin import credentials, messaging, storage, auth, _auth_utils
from firebase_admin import firestore
from google.auth.transport.requests import Request
from google.cloud import firestore as gfs
from google.oauth2 import service_account
from simple_colors import *

from VoiGO.settings import log
from server import constants, utils
from server.constants import KEYWORD
from server.crypto_utils import des_core

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VoiGO.settings')

_stage: str = config('ENV_MODE', default='development')

# init. Firebase-Admin-SDK with SA-credentials
if _stage == KEYWORD.production:
    # use this in production environment
    cred = credentials.Certificate("/workdir/server/cloud/intelli-cart-firebase-adminsdk-pz474-68d5753572.json")
elif _stage == KEYWORD.development:
    # use this in testing
    cred = credentials.Certificate(
        r"D:\voigo\VoiGO-Server\VoiGO\server\cloud\intelli-cart-firebase-adminsdk-pz474-68d5753572.json")
else:
    log.warning("Unable to retrieve environment mode from .env file, "
                "proceeding development environment settings as default.")
    cred = credentials.Certificate(
        r"D:\voigo\VoiGO-Server\VoiGO\server\cloud\intelli-cart-firebase-adminsdk-pz474-68d5753572.json")

try:
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'intelli-cart.appspot.com'})
except Exception as e:
    log.error(f"Exception occurred at {__file__}.firebase_admin_initialize_app. {str(e)}")

# init. firestore client
cloudFirestore = firestore.client()

SUCCESS: bool = True
FAILED: bool = False

#
# # Firebase cloud collection references
# ClientStatusData = cloudFirestore.collection('ClientStatusData')
# DeliveryPartnersData = cloudFirestore.collection('DeliveryPartnersData')
# IntellicartOrderApp = cloudFirestore.collection('IntellicartOrderApp')
#
# # Firebase cloud document references
# serverData = IntellicartOrderApp.document('serverData')
# userAppData = IntellicartOrderApp.document('userAppData')
# availablePartnersForDelivery = ClientStatusData.document('availablePartnersForDelivery')
#
#
# # -------------------------------------------------------------------------------------------------------------
#
# # Firebase-cloud col./doc references
# def get_manual_cart_product_data_ref(client_id: str):
#     return (userAppData.collection(str.strip(client_id)).document("userCartData")
#             .collection("cartItems")
#             .document("manualCartProductData"))
#
#
# def get_voice_cart_product_data_ref(client_id: str):
#     return (userAppData.collection(str.strip(client_id)).document("userCartData")
#             .collection("cartItems")
#             .document("voiceCartProductData"))
#
#
# def get_order_by_voice_data_ref(client_id: str):
#     return userAppData.collection(str.strip(client_id)).document("orderByVoiceData")

registered_users_credentials_ref = cloudFirestore.collection("AuthenticationData").document(
    "RegisteredUsersCredentials")
registered_users_email_ref = cloudFirestore.collection("AuthenticationData").document("RegisteredUsersEmail")


def _get_current_date():
    return datetime.now().strftime("%d%b%Y").upper()


# -------------------------------------------------------------------------------------------------------------

# Utility methods for cloud-api

def get_all_data_delete_doc_refs(dp_id: str, user_id: str, order_id: str,
                                 order_by_voice_doc_id: str, order_by_voice_audio_ref_id: str):
    """

    :param dp_id:
    :param user_id:
    :param order_id:
    :param order_by_voice_doc_id:
    :param order_by_voice_audio_ref_id:
    :return:
    """
    sdr_1 = (cloudFirestore.collection("DeliveryPartners").document(dp_id)
             .collection("pendingOrders").document(order_id)
             .collection('orderData').document('info'))

    tdr_1 = (cloudFirestore.collection("DeliveryPartners").document(dp_id)
             .collection("pendingOrders").document(order_id))

    tdr_2 = (cloudFirestore.collection("DeliveryPartners")
             .document(dp_id).collection("currentOrder")
             .document(order_id))

    tdr_3 = (cloudFirestore.collection("Users").document(user_id)
             .collection("currentActiveOrders").document(order_id))

    tdr_4 = (cloudFirestore.collection("Users").document(user_id)
             .collection("placedOrderData").document(order_id))

    tdr_5 = (cloudFirestore.collection("Users").document(user_id).collection(
        "userCartData").document(order_by_voice_doc_id).collection("voiceCartProductData")
             .document(order_by_voice_audio_ref_id))

    return sdr_1, tdr_1, tdr_2, tdr_3, tdr_4, tdr_5


def get_all_order_data_info_db_refs(dp_id: str, user_id: str, order_id: str):
    """
    Retrieves Firestore document references related to order status for a delivery partner and user.

    This function generates references to Firestore documents for the given delivery
    partner ID (dp_id) and user ID (user_id). It provides references for the source document
    containing pending orders and target documents for current and active orders.

    :param order_id:
    :param dp_id: The unique identifier for the delivery partner.
    :param user_id: The unique identifier for the user.

    :return: tuple: A tuple containing Firestore document references:
            - sdr_1: Ref to the doc containing pending orders for the delivery partner.
            - tdr_1: Ref to the doc containing the current order for the delivery partner.
            - tdr_2: Ref to the doc containing current active orders for the user.
            - tdr_3: Ref to the doc containing active order data for the user.

    """
    base_dir = (cloudFirestore.collection("DeliveryPartners").document(dp_id)
                .collection("pendingOrders").document(order_id)
                .collection('orderData').document('info'))

    sdr_1 = (cloudFirestore.collection("DeliveryPartners").document(dp_id)
             .collection("pendingOrders").document(order_id)
             .collection('orderData').document('info'))

    tdr_1 = (cloudFirestore.collection("DeliveryPartners")
             .document(dp_id).collection("currentOrder")
             .document(order_id).collection('orderData').document('info'))

    tdr_2 = (cloudFirestore.collection("Users").document(user_id)
             .collection("currentActiveOrders").document(order_id)
             .collection('orderData').document('info'))

    tdr_3 = (cloudFirestore.collection("Users").document(user_id)
             .collection("placedOrderData").document(order_id)
             .collection('orderData').document('info'))

    return base_dir, sdr_1, tdr_1, tdr_2, tdr_3


def _remove_token_from_db(token_type: str, dp_id: str) -> bool:
    """
    Remove unregistered or invalid FCM tokens from the db storage.

    This function removes an FCM token from the Firestore database based on the
    token type and the client ID. It supports removal for 'delivery' and 'user' token types.

    :param token_type:  The type of token, either 'delivery' or 'user'.
    :param dp_id: The unique identifier for the client whose token is to be removed.

    :return: Returns True if the token was successfully removed, False otherwise.

    """

    if token_type == KEYWORD.delivery:
        try:
            doc_ref = cloudFirestore.document('FCMTokenMapping/DeliveryAppClient')
            doc_ref.update({dp_id: gfs.DELETE_FIELD})
            return True
        except Exception as ew:

            log.error(f"Exception occurred:{ew}")
            return False
    elif token_type == KEYWORD.user:
        try:
            doc_ref = cloudFirestore.document('FCMTokenMapping/OrderAppClient')
            doc_ref.update({dp_id: gfs.DELETE_FIELD})
            return True
        except Exception as ez:
            log.error("Exception occurred: ", ez)
            return False
    else:
        return False


def _get_fcm_access_token():
    """ Retrieve a valid access token that can be used to authorize requests.
    Utilized for Http v1 FCM.

    :return: Access token.
    """

    if _stage == KEYWORD.development:
        credentials1 = (service_account.Credentials.from_service_account_file(
            r"D:\voigo\VoiGo-Server\VoiGO\server\cloud\intelli-cart-firebase-adminsdk-pz474-68d5753572.json",
            scopes=constants.FCM_MSG_SCOPE))
    elif _stage == KEYWORD.production:
        credentials1 = (service_account.Credentials.from_service_account_file(
            "/home/ubuntu/VoiGo-server/server/cloud/intelli-cart-firebase-adminsdk-pz474-68d5753572.json",
            scopes=constants.FCM_MSG_SCOPE))
    else:
        credentials1 = (service_account.Credentials.from_service_account_file(
            r"D:\voigo\VoiGo-Server\VoiGO\server\cloud\intelli-cart-firebase-adminsdk-pz474-68d5753572.json",
            scopes=constants.FCM_MSG_SCOPE))

    request = google.auth.transport.requests.Request()
    credentials1.refresh(request)
    return credentials1.token


def _get_fcm_registration_token(client_id: str, client_type: str) -> dict:
    """
    Retrieves the FCM token for a given client based on their ID and type.

    This function fetches the FCM token from a Firestore document. The location
    of the document depends on the client type. If the client type is "delivery",
    it fetches from the "DeliveryAppClient" document; if the client type is "user",
    it fetches from the "OrderAppClient" document.

    :rtype: object
    :param client_id: The unique identifier for the client.:
    :param client_type: The type of client, either "delivery" or "user".

    :return: A dictionary containing the FCM token. If the token or document
            does not exist, an empty dictionary is returned.

    """

    log.info(f"Fetching FCM token for client ({client_id})...")

    if client_type == KEYWORD.delivery:
        doc_ref = cloudFirestore.document("FCMTokenMapping/DeliveryAppClient")
    elif client_type == KEYWORD.user:
        doc_ref = cloudFirestore.document("FCMTokenMapping/OrderAppClient")
    else:
        return {}

    doc_snapshot = doc_ref.get()

    # Check if the document exists
    if doc_snapshot.exists:
        # Get data from the document
        document_data = doc_snapshot.to_dict()

        user_data = document_data.get(client_id, {})

        return {"fcm_token": user_data.get("fcm_token")}

    else:
        return {}


def update_set_data_in_doc_ref(doc_ref, data):
    """
    Helper function to update a Firestore document with the given data.
    If the document does not exist, it creates a new one with the given data.

    :param doc_ref: The Firestore document reference.
    :param data: The data to be added or updated in the document.
    """

    try:
        # Use set with merge to handle both update and create
        doc_ref.set(data, merge=True)
        log.info(f"Document {doc_ref.id} created or updated successfully.")
        return True
    except Exception as er:
        log.error(f"Failed to set/update data in document {doc_ref.id}: {str(er)}")
        return False


# -------------------------------------------------------------------------------------------------------------

# TODO: inline 'title' into fcm_data_payload
def send_fcm_notification(client_id: str, fcm_data_payload: dict, client_type: str,
                          on_success_msg: str = "FCM-V1 sent successfully",
                          icon_str: str = "baseline_message_24", icon_color="#9a0707",
                          image_url=""):
    """
    Sends an FCM message using the HTTP v1 API.

    This function sends a notification via Firebase Cloud Messaging (FCM) using
    the HTTP v1 API. It constructs the payload with a predefined title and body,
    and sends a POST request to the FCM endpoint.

    Note:
        This is a demo code and should be upgraded dynamically as per the actual
        requirements. Ensure that `_get_fcm_access_token()` is implemented to
        retrieve a valid access token.

    Payload Structure:
        The payload includes the FCM token, data, and notification details.

        :param client_id:
        :param fcm_data_payload:
        :param client_type:
        :param on_success_msg:
        :param icon_str:
        :param icon_color:
        :param image_url:

    """
    log.info(f"Preparing to sent FCM message to client ({client_id}) of type {client_type}...")

    # fetch app-registration token for fcm from db
    fcm_token_data = _get_fcm_registration_token(client_id=client_id, client_type=client_type)
    fcm_token = fcm_token_data.get("fcm_token")

    if not fcm_token:
        log.error("Unable to fetch FCM token from db, skipping notification.")
        return
    else:
        log.success("FCM token fetch success.")

    if client_type == "delivery":
        icon_str = "baseline_delivery_dining_24"
        icon_color = "#e69138"
    elif client_type == "user":
        icon_str = "baseline_notifications_24"
        icon_color = "#9a0707"

    try:
        fcm_header = {
            "Authorization": f"Bearer {_get_fcm_access_token()}",
            "Content-Type": "application/json; UTF-8"
        }

        fcm_payload = {
            "message": {
                "token": fcm_token,
                "data": fcm_data_payload,

                "notification": {
                    "title": fcm_data_payload.get('title', '-title-'),
                    "body": fcm_data_payload.get('body'),
                    "image": image_url,
                },

                "android": {
                    "direct_boot_ok": True,
                    "ttl": f"{int(timedelta(seconds=3600).total_seconds())}s",
                    "priority": "high",
                    "notification": {
                        "icon": icon_str,
                        "color": icon_color,
                        "sound": "default"
                    }
                },
            }
        }

        # Send POST request
        response = requests.post(
            constants.HTTP_V1_FCM_URL,
            headers=fcm_header,
            json=fcm_payload
        )

        if response.status_code == 200:
            log.success("FCM message sent success")
            log.info_data(f"FCM Response: {response.json()}")
            log.info(on_success_msg)
        else:
            log.error(f"Error sending FCM message: {response.status_code}, {response.text}")

            if response.status_code == 404 and "UNREGISTERED" in response.text:
                if _remove_token_from_db(token_type=client_type, dp_id=fcm_data_payload.get('dp_id')):
                    log.error(f'Error: Unregistered or invalid FCM token. Auto removed from database.\n{fcm_token}')
                else:
                    log.error('Error: The FCM token is unregistered or invalid. '
                              'Unable to remove it from the database, remove manually!')

    except Exception as ef:
        log.error(f"Error: Invalid request: {ef}")


def push_fcm_msg(fcm_token: str, fcm_payload: dict,
                 token_type: str, title: str,
                 msg: str = "FCM-SENT-SUCCESS") -> bool:
    """
    Sends an FCM message with a given payload to a specific token. (Use legacy API)

    This function sends a notification message via Firebase Cloud Messaging (FCM) using the provided
    token and payload. It runs in a separate thread to handle the FCM message sending independently.
    If the FCM token is unregistered or invalid, it attempts to remove the token from the database.

    :param fcm_token: The FCM token to which the message will be sent.
    :param fcm_payload: The payload data to be included in the message.
    :param token_type: The type of token, either 'delivery' or 'user'.
    :param title: The title of the notification message.
    :param msg:

    :return: bool: True if the message was sent successfully, False otherwise.

    """

    fcm_success_flag = threading.Event()

    def foreground_fcm_worker():
        """ Independent target worker method for FCMS service.

        """

        message = messaging.Message(
            data=fcm_payload,
            token=fcm_token,
            notification=messaging.Notification(
                title=title,
                body=f"{fcm_payload.get('body')}",
            ))

        try:
            response = messaging.send(message)
            log.info(green(f'Message sent successfully: {response} ', ['italic', 'underlined']))
            fcm_success_flag.set()
            log.info(msg)

        except messaging.UnregisteredError:
            # remove token from db
            if _remove_token_from_db(token_type=token_type, dp_id=fcm_payload.get('dp_id')):
                log.error(f'Error: Unregistered or invalid FCM token. Auto removed from database.\n{fcm_token}')
            else:
                log.error('Error: The FCM token is unregistered or invalid. Unable to remove it '
                          'from the database, remove manually!')
        except Exception as eo:
            fcm_success_flag.clear()
            log.error('Error sending FCM message:' + str(eo))
            return False

    fcm_thread = threading.Thread(target=foreground_fcm_worker)
    fcm_thread.start()

    # wait thread to finish
    fcm_thread.join()

    return True


def add_order_to_users_bucket(uid: str, base_payload, order_info_payload) -> bool:
    """
    Adds or updates the order data for a user in Firestore under the "placedOrderData" collection.

    This function manages two levels of data:
    1. The base data for the order, stored at the top level under the order ID.
    2. Additional order data stored under the "orderData" sub-collection with the document ID "info".

    If the data already exists, it will be updated; otherwise, it will be created.

    :param uid: The user ID.
    :param base_payload: The base payload data for the order.
    :param order_info_payload: The additional order data.
    :return: Returns True if document updated/created successfully, False otherwise.
    """

    # Define document references
    base_data_doc_ref = (
        cloudFirestore.collection("Users")
        .document(uid)
        .collection("placedOrderData")
        .document(order_info_payload['order_id'])
    )

    order_info_doc_ref = (
        base_data_doc_ref
        .collection("orderData")
        .document("info")
    )

    # Update base payload to include reference to obs data
    base_payload['order_data_payload_reference'] = order_info_doc_ref

    def update_or_set(doc_ref, data):
        """
        Helper function to update or set document data.
        """
        try:
            if doc_ref.get().exists:
                doc_ref.update(data)
            else:
                doc_ref.set(data)
        except Exception as et:
            log.error(f"Error updating or setting document {doc_ref.id}: {et}")
            return False
        return True

    # Update or set data in Firestore
    try:
        if not update_or_set(order_info_doc_ref, order_info_payload):
            return False

        if not update_or_set(base_data_doc_ref, base_payload):
            return False

        log.info("Order successfully added to user's placed-order-data list.")
        return True

    except Exception as eq:
        log.error(f"Error: Unable to add this order to user's placed-orders-data list: {eq}")
        return False


def add_cart_item_to_dp_bucket(user_id: str, dp_id: str, order_id: str, shop_id: str):
    source_manual_cart_doc_ref = cloudFirestore.collection(
        f"Users/{user_id}/userCartData/{shop_id}/manualCartProductData")

    destination_manual_cart_doc_ref = cloudFirestore.collection(
        f"DeliveryPartners/{dp_id}/pendingOrders/{order_id}/manualCartProductData")

    # Retrieve documents from the source collection
    docs = source_manual_cart_doc_ref.stream()

    # Copy each document to the destination collection
    for doc in docs:
        doc_id = doc.id
        doc_data = doc.to_dict()
        destination_manual_cart_doc_ref.document(doc_id).set(doc_data)

    print("Documents copied successfully!")


def add_order_to_dp_bucket(order_id: str, dp_id: str, base_payload, obs_data_payload) -> bool:
    """
    Adds or updates the order data in the delivery partner's bucket in Firestore.

    This function manages two levels of data:
    1. The base data for the order, stored at the top level under the order ID.
    2. Additional order data stored under the "orderData" sub-collection with the document ID "info".

    :param order_id: The order ID.
    :param dp_id: The delivery partner ID.
    :param base_payload: The base payload data for the order.
    :param obs_data_payload: The additional order data.
    :return: Returns True if document updated/created successfully, False otherwise.
    """

    # Define document references
    base_data_doc_ref = cloudFirestore.document(
        f"DeliveryPartners/{dp_id}/pendingOrders/{order_id}"
    )

    obs_data_doc_ref = cloudFirestore.document(
        f"DeliveryPartners/{dp_id}/pendingOrders/{order_id}/orderData/info"
    )

    # Update base payload to include reference to obs data
    base_payload['order_data_payload_reference'] = obs_data_doc_ref

    def update_or_set(doc_ref, data):
        """
        Helper function to update or set document data.
        """
        try:
            if doc_ref.get().exists:
                doc_ref.update(data)
            else:
                doc_ref.set(data)
        except Exception as ep:
            log.error(f"Error updating or setting document {doc_ref.id}: {ep}")
            return False
        return True

    # Update or set data in Firestore
    try:
        if not update_or_set(obs_data_doc_ref, obs_data_payload):
            return False

        if not update_or_set(base_data_doc_ref, base_payload):
            return False

        log.info("Order successfully added to delivery partner's list.")
        return True

    except Exception as e:
        log.error(f"Error: Unable to add this order to delivery partner's list: {e}")
        return False


def set_obs_order_as_current_accepted(uid: str, dp_id: str, order_id: str, base_payload=None,
                                      obs_data_payload=None) -> bool:
    """
    Adds or updates the order data for a user in Firestore under the "currentActiveOrders" collection
    and also updates the corresponding delivery partner's "currentOrder" collection.
    Additionally, copies data from 'copy_doc_ref' and updates all four document references.

    :param uid: The user ID.
    :param dp_id: The delivery partner ID.
    :param order_id: The order ID.
    :param base_payload: The base payload data for the order.
    :param obs_data_payload: The additional order data.
    :return: Returns True if document updated/created successfully, False otherwise.
    """

    # Define 'copy_doc_ref' for copying data
    if obs_data_payload is None:
        obs_data_payload = {}
    if base_payload is None:
        base_payload = {}
    copy_user_base_doc_ref = (
        cloudFirestore.collection("Users")
        .document(uid).collection("placedOrderData").document(order_id)
    )

    copy_user_obs_doc_ref = (
        copy_user_base_doc_ref.collection("orderData").document("info")
    )

    # Define 'currentActiveOrders' document references for the user
    user_base_doc_ref = (
        cloudFirestore.collection("Users")
        .document(uid)
        .collection("currentActiveOrders")
        .document(order_id)
    )

    user_obs_doc_ref = (
        user_base_doc_ref
        .collection("orderData")
        .document("info")
    )

    # Define 'copy_doc_ref' for copying data for the delivery partner
    copy_delivery_base_doc_ref = (
        cloudFirestore.collection("DeliveryPartners")
        .document(dp_id).collection("pendingOrders").document(order_id)
    )

    copy_delivery_obs_doc_ref = (
        copy_delivery_base_doc_ref.collection("orderData").document("info")
    )

    # Define 'currentOrder' document references for the delivery partner
    delivery_base_doc_ref = (
        cloudFirestore.collection("DeliveryPartners")
        .document(dp_id)
        .collection("currentOrder")
        .document(order_id)
    )

    delivery_obs_doc_ref = (
        delivery_base_doc_ref
        .collection("orderData")
        .document("info")
    )

    def update_or_set_order(doc_ref, data):
        """
        Helper function to update or set document data.
        """
        try:
            log.info(f"Updating or setting data for document {doc_ref.path}")
            doc_ref.set(data, merge=True)
            log.info(f"Successfully updated or set data for document {doc_ref.path}")
        except Exception as et:
            log.error(f"Error updating or setting document {doc_ref.path}: {et}")
            return False
        return True

    try:
        # Copy data from user placed order to currentActiveOrders
        # log.info(f"Retrieving data from {copy_user_base_doc_ref.path}")
        copy_base_doc_snapshot = copy_user_base_doc_ref.get()
        if not copy_base_doc_snapshot.exists:
            log.error(f"Source document {copy_user_base_doc_ref.path} does not exist.")
            return False
        copied_user_base_data = copy_base_doc_snapshot.to_dict()
        base_payload.update(copied_user_base_data)
        log.info(f"Successfully copied base data from {copy_user_base_doc_ref.path}")

        # log.info(f"Retrieving data from {copy_user_obs_doc_ref.path}")
        copy_obs_doc_snapshot = copy_user_obs_doc_ref.get()
        if not copy_obs_doc_snapshot.exists:
            log.error(f"Source document {copy_user_obs_doc_ref.path} does not exist.")
            return False
        copied_user_obs_data = copy_obs_doc_snapshot.to_dict()
        obs_data_payload.update(copied_user_obs_data)
        log.info(f"Successfully copied obs data from {copy_user_obs_doc_ref.path}")

        # Copy data from delivery partner's pendingOrders to currentOrder
        log.info(f"Retrieving data from {copy_delivery_base_doc_ref.path}")
        copy_delivery_base_doc_snapshot = copy_delivery_base_doc_ref.get()
        if not copy_delivery_base_doc_snapshot.exists:
            log.error(f"Source document {copy_delivery_base_doc_ref.path} does not exist.")
            return False
        copied_delivery_base_data = copy_delivery_base_doc_snapshot.to_dict()
        log.info(f"Successfully copied base data from {copy_delivery_base_doc_ref.path}")

        # log.info(f"Retrieving data from {copy_delivery_obs_doc_ref.path}")
        copy_delivery_obs_doc_snapshot = copy_delivery_obs_doc_ref.get()
        if not copy_delivery_obs_doc_snapshot.exists:
            log.error(f"Source document {copy_delivery_obs_doc_ref.path} does not exist.")
            return False
        copied_delivery_obs_data = copy_delivery_obs_doc_snapshot.to_dict()
        log.info(f"Successfully copied obs data from {copy_delivery_obs_doc_ref.path}")

        # Update or set data in Firestore
        # log.info(f"Updating user observation data in {user_obs_doc_ref.path}")
        if not update_or_set_order(user_obs_doc_ref, obs_data_payload):
            log.error(f"Failed to update user observation data in {user_obs_doc_ref.path}")
            return False
        log.info(f"Updated user observation data in {user_obs_doc_ref.path}")

        # log.info(f"Updating user base data in {user_base_doc_ref.path}")
        if not update_or_set_order(user_base_doc_ref, base_payload):
            log.error(f"Failed to update user base data in {user_base_doc_ref.path}")
            return False
        log.info(f"Updated user base data in {user_base_doc_ref.path}")

        # log.info(f"Updating delivery observation data in {delivery_obs_doc_ref.path}")
        if not update_or_set_order(delivery_obs_doc_ref, copied_delivery_obs_data):
            log.error(f"Failed to update delivery observation data in {delivery_obs_doc_ref.path}")
            return False
        log.info(f"Updated delivery observation data in {delivery_obs_doc_ref.path}")

        # log.info(f"Updating delivery base data in {delivery_base_doc_ref.path}")
        if not update_or_set_order(delivery_base_doc_ref, copied_delivery_base_data):
            log.error(f"Failed to update delivery base data in {delivery_base_doc_ref.path}")
            return False
        log.info(f"Updated delivery base data in {delivery_base_doc_ref.path}")

        log.info("Order successfully updated in all relevant collections.")
        return True

    except Exception as eq:
        log.error(
            f"Error: Unable to add this order to user's current-active-orders and "
            f"delivery partner's current orders: {eq}")
        return False


def fetch_store_pref_data(uid: str, phno: str, shop_state: str, shop_district: str):
    # Fetch store preference data
    log.info("Fetching store pref. shop data...")
    doc_ref = cloudFirestore.document(f'Users/{uid}/storePreference/{phno}')
    doc = doc_ref.get()

    # New dictionary to store all shop information
    all_shop_info = {}
    all_shop_coords = []

    if doc.exists:
        data = doc.to_dict()

        if not data:
            # log.warning(f"No data found in store preferences for phone {phno}")
            return all_shop_info, all_shop_coords

        store_pref_data = dict(sorted(data.items(), key=lambda item: item[1].get('shop_preference', float('inf'))))

        log.info_data("Store preference data: " + str(store_pref_data))

        for shop_id, shop_info in store_pref_data.items():
            # Fetch the shop info from db using the shop_id
            shop_info_doc_ref = cloudFirestore.document(
                f'ShopData/data/{shop_state.lower()}/{shop_district.lower()}/allShopData/{shop_id}')
            shop_info_snapshot = shop_info_doc_ref.get()

            if shop_info_snapshot.exists:
                # Fetch the shop data and merge with additional data from store_pref_data
                shop_data = shop_info_snapshot.to_dict()

                if not shop_data:
                    log.warning(f"No shop data found for shopID: {shop_id} in city {shop_district}")
                    continue

                # Convert GeoPoint to a dictionary with latitude and longitude
                if 'shop_loc_coords' in shop_data and isinstance(shop_data['shop_loc_coords'], gfs.GeoPoint):
                    all_shop_coords.append(
                        (shop_data['shop_loc_coords'].latitude, shop_data['shop_loc_coords'].longitude))

                    shop_data['shop_loc_coords'] = {
                        'latitude': shop_data['shop_loc_coords'].latitude,
                        'longitude': shop_data['shop_loc_coords'].longitude
                    }
                    # all_shop_coords.append(
                    #     (shop_data['shop_loc_coords'].latitude, shop_data['shop_loc_coords'].longitude))

                combined_data = {**shop_data, **shop_info}  # Merging dictionaries
                all_shop_info[shop_id] = combined_data
            else:
                log.info(f"No shop info found for shopID: {shop_id}")

        if not all_shop_info:
            log.info(f"No shop information was fetched for user {uid} and phone {phno}")

        # Print the new dictionary with all shop information
        log.info_data(f"Store preference shop data: {str(all_shop_info)}")
        log.info_data("All shop coordinates: " + str(all_shop_coords))
        return all_shop_info, all_shop_coords
    else:
        log.error(f"No store preference data found for phone {phno}")
        return all_shop_info, all_shop_coords


def get_address_data(uid: str, phno: str):
    """

    :param uid:
    :param phno:

    :return:
    """
    try:
        # Get the document reference
        doc_ref = cloudFirestore.document(f"Users/{uid}/userAddress/{phno.strip()}")

        # Get the document data
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            return data
        else:
            log.error(f'Address for {phno} does not exists.')
            return None
    except Exception as ae:
        log.error(f"Exception occurred at {__file__}.get_address_data {ae}")
        return None


def delete_address_from_db(user_id, address_id):
    try:
        collection_ref = (cloudFirestore.collection('Users').document(user_id)
                          .collection('userAddress').document(address_id))
        collection_ref.delete()
        return True
    except Exception as ee:
        log.error(f'Error deleting address: {ee}')
        return False


def add_new_address(address_data):
    try:
        user_id = address_data.get('user_id')
        phone_number = address_data.get('phone_no')

        address_db_ref = cloudFirestore.document(f'Users/{user_id}/userAddress/{phone_number}')

        address_data['address_loc_coordinates'] = gfs.GeoPoint(address_data.get('address_lat'),
                                                               address_data.get('address_lon'))

        # resp = utils.reverse_geocode_bigdatacloud(address_data.get('address_lat'),
        #                                           address_data.get('address_lon'))
        #
        # address_data['district'] = utils.district_to_format(resp.get('district'))

        c = address_db_ref.set(address_data, merge=True)
        log.info_data(c)
        return True
    except Exception as ek:
        log.error(f"Exception at:{__file__}.add_new_address {ek}")
        return False


def check_if_address_exists(uid: str, phno: str):
    # Query Firestore to check if the phone number exists
    address_db_ref = cloudFirestore.document(f'Users/{uid}/userAddress/{phno}')
    doc = address_db_ref.get()
    log.info(doc)
    if doc.exists:
        if doc.to_dict():
            return True
        else:
            return False
    else:
        return False


def get_shop_data1(shop_id: str, state: str, district: str):
    # Get the document reference
    doc_ref = cloudFirestore.document(f"ShopData/data/{state.lower()}/{district.lower()}/allShopData/{shop_id}")
    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        if data:
            # Return the entire shop data
            return data
        else:
            log.error("Shop data is empty.")
            return None
    else:
        log.error("Shop data does not exist.")
        return None


def get_saved_address(request):
    if request.method == 'GET':
        try:
            user_id = request.GET.get('user_id')
            collection_ref = (cloudFirestore.collection('Users')
                              .document(user_id).collection('userAddress'))
            docs = collection_ref.stream()

            address_data = []
            for doc in docs:
                if doc.exists:
                    data = doc.to_dict()
                    # Convert GeoPoint fields to address_lat and address_lon
                    if 'address_loc_coordinates' in data and isinstance(data['address_loc_coordinates'],
                                                                        gfs.GeoPoint):
                        geo_point = data['address_loc_coordinates']
                        data['address_lat'] = geo_point.latitude
                        data['address_lon'] = geo_point.longitude
                        del data['address_loc_coordinates']

                    address_data.append(data)

            if address_data:
                json_data = {
                    'status': 'success',
                    'is_address_found': True,
                    'message': 'Addresses retrieved successfully.',
                    'address_data': address_data
                }
                (log.info_data
                 ("All saved address:", json_data))
                return json_data
            else:
                return {'status': 'error', 'is_address_found': False, 'message': 'No addresses found'}
        except Exception as ey:
            return {'status': 'error', 'is_address_found': False, 'message': 'An error occurred', 'exception': str(ey)}


def get_shop_items(item_type, shop_id, shop_state, shop_district):
    item_data_ref = (cloudFirestore.document(f"ShopData/itemData/{shop_state}/"
                                             f"{shop_district}/{shop_id}/{item_type}"))
    item_data_doc_ref = item_data_ref.get()

    item_data = []
    if item_data_doc_ref.exists:
        # Convert map data to JSON array
        data = item_data_doc_ref.to_dict()
        item_data.append(data)

        if item_data:
            json_data = {
                'status': 'success',
                'message': 'Items retrieved successfully.',
                'item_data': [data]
            }
            (log.info_data
             ("All available items:", json_data))
            return json_data
        else:
            return {'status': 'error', 'message': 'No addresses found'}


def update_place_name(dp_id: str, city_name: str):
    duty_status_ref = (cloudFirestore.collection('DeliveryPartnersData')
                       .document("deliveryPartnerDutyStatus"))
    duty_status_doc_ref = duty_status_ref.get()

    if duty_status_doc_ref.exists:
        duty_status_ref.set({dp_id: {
            'city_name': city_name,
        }}, merge=True)
    else:
        log.error("Document does not exist.")

    return HttpResponse({'status': True})


def get_user_data(client_id: str, client_type: str):
    client_type = client_type.lower()

    if client_type not in ['user', 'delivery', 'vendor']:
        return
    else:
        doc_ref = None
        if client_type == 'user':
            doc_ref = cloudFirestore.document(f"Users/{client_type}")
        elif client_type == 'delivery':
            doc_ref = cloudFirestore.document(f"DeliveryPartners/{client_id}")
        elif client_type == 'vendor':
            doc_ref = cloudFirestore.document(f"ShopData/{client_type}")

        if doc_ref is not None:
            doc_snapshot = doc_ref.get()
            if doc_snapshot.exists:
                data = doc_snapshot.to_dict()
                return data


def update_duty_data(request):
    data = json.loads(request.body.decode('utf-8'))
    dp_id = data.get('user_id')
    log.info(data)
    user_data_doc_ref = cloudFirestore.document(f"DeliveryPartners/{dp_id}")
    prev_data = get_user_data(dp_id, 'delivery')
    prev_state = prev_data.get('user_state')
    prev_district = prev_data.get('user_district')

    def _get_ds_ref(_id: str, _s: str, _d: str):
        delivery_partner_duty_status_doc_ref = cloudFirestore.document(
            f"DeliveryPartnerDutyStatus/{_s}/{_d}/{utils.get_current_date()}/dutyStatus/{_id}")
        return delivery_partner_duty_status_doc_ref

    old_status_delete_ref = _get_ds_ref(dp_id, prev_state, prev_district)
    old_status_doc_ref_data = None
    if old_status_delete_ref.get().exists:
        old_status_doc_ref_data = old_status_delete_ref.get().to_dict()
    old_status_delete_ref.delete()

    user_data_doc_ref.set(data, merge=True)
    new_status_add_ref = _get_ds_ref(dp_id, data.get('user_state'), data.get('user_district'))

    if old_status_doc_ref_data is not None:
        new_status_add_ref.set(old_status_doc_ref_data, merge=True)
    return {'message': 'Data updated successfully'}


def get_duty_status(dp_id):
    partner_base_doc_ref = cloudFirestore.document(f"DeliveryPartners/{dp_id}")
    partner_base_doc_snapshot = partner_base_doc_ref.get()

    if partner_base_doc_snapshot.exists:
        base_data = partner_base_doc_snapshot.to_dict()
        state: str = str(base_data.get('user_state'))
        district: str = str(base_data.get('user_district'))

        duty_status_doc_ref = cloudFirestore.document(f"DeliveryPartnerDutyStatus/{state.lower()}/"
                                                      f"{district.lower()}/{utils.get_current_date()}"
                                                      f"/dutyStatus/{dp_id}")

        duty_status_doc_snapshot = duty_status_doc_ref.get()
        if duty_status_doc_snapshot.exists:
            duty_status_data = duty_status_doc_snapshot.to_dict()

            dp_name = duty_status_data.get('dp_name')
            duty_mode = duty_status_data.get('duty_mode')
            last_duty_status_update_millis = duty_status_data.get('last_duty_status_update_millis')
            last_duty_status_update_timestamp = duty_status_data.get('last_duty_status_update_timestamp')

            return {'has_data': True,
                    'data': {
                        'duty_mode': duty_mode,
                        'last_duty_status_update_millis': last_duty_status_update_millis,
                        'last_duty_status_update_timestamp': last_duty_status_update_timestamp},
                    'message': f'Duty status for {dp_name} fetched successfully.'}
        else:
            return {'has_data': False,
                    'message': 'Unable to fetch current duty status!'}
    else:
        return {'has_data': False,
                'message': 'Unable to fetch current duty status!'}


def get_voice_order(user_id: str, order_by_voice_type: str, doc_id: str, voice_order_ref_id: str, shop_id: str):
    try:
        if order_by_voice_type == KEYWORD.obs:
            collection_ref = (cloudFirestore.collection('Users').document(user_id).collection('voiceOrdersData')
                              .document(KEYWORD.obs).collection(doc_id)
                              .document(voice_order_ref_id).collection(shop_id))
        elif order_by_voice_type == KEYWORD.obv:
            collection_ref = (cloudFirestore.collection('Users').document(user_id).collection('voiceOrdersData')
                              .document(KEYWORD.obv).collection(doc_id)
                              .document(voice_order_ref_id).collection("voiceData"))
        else:
            return
        docs = collection_ref.stream()
        log.info_data(docs)

        voice_order_data = []
        for doc in docs:
            if doc.exists:
                data = doc.to_dict()
                voice_order_data.append(data)

        if voice_order_data:
            json_data = {
                'status': 'success',
                'message': 'Voice orders retrieved successfully.',
                'voice_orders_data': voice_order_data
            }
            log.info_data("All saved address:", json_data)
            return json_data
        else:
            return {'status': 'error', 'voice_orders_data': [], 'message': 'No voice orders found'}
    except Exception as el:
        log.error(f"Exception occurred at:{__file__}.get_voice_order {el}")
        return {'status': 'error', 'message': 'An error occurred', 'exception': str(el)}


def check_if_store_pref_found(user_id: str, phno_enc: str):
    phno = des_core.decrypt(phno_enc).get('plain_text')

    if len(phno) == 10:
        store_pref_doc_ref = cloudFirestore.document(f"Users/{user_id}/storePreference/{phno}")
        store_pref = store_pref_doc_ref.get()

        if store_pref.exists:
            store_pref_data = store_pref.to_dict()
            if store_pref_data:
                log.info(f"Store preference data found for phone no {phno_enc}")

                # Fetch and log.info the document data
                log.info(f"Store preference data for phone {phno_enc}:", store_pref_data)
                return {'is_success': True,
                        'status': 'success',
                        'has_data': True,
                        'data': store_pref_data,
                        'message': f"Store preference data successfully fetched for phone no {phno_enc}."}
            else:
                log.warning(f"Phone no {phno_enc} exists in store preference list, but no data found.")
                return {'is_success': False,
                        'status': 'failed',
                        'has_data': False,
                        'message': f"Phone no {phno_enc} exists in store preference list, but no data found."}
        else:
            log.warning(f"Store preference data for phone no {phno_enc} does not exist.")
            return {'is_success': False,
                    'status': 'failed',
                    'has_data': False,
                    'message': f"Store preference data for phone no {phno_enc} does not exist."}
    else:
        log.warning(f'Unable to fetch store preference data, invalid phone no {phno_enc}')
        return {'is_success': False,
                'status': 'failed',
                'has_data': False,
                'message': f'Unable to fetch store preference data, invalid phone no.{phno_enc} '}


def delete_voice_order_from_cart(data):
    _from = data.get('from')
    delete_all_files = data.get('delete_all_files')
    user_id = data.get('user_id')
    audio_ref_id = data.get('order_by_voice_audio_ref_id')
    audio_doc_id = data.get('order_by_voice_doc_id')
    audio_key = data.get('audio_key')
    shop_id = data.get('shop_id')

    def _delete_collection1(coll_ref, batch_size):
        """
        Deletes documents in a Firestore collection in batches.

        :param coll_ref: Firestore collection reference.
        :param batch_size: Number of documents to delete in each batch.
        """
        while True:
            docs = coll_ref.list_documents(page_size=batch_size)
            deleted = 0

            for doc in docs:
                # Recursively delete subcollections
                _delete_all_subcollections(doc)

                log.info(f"Deleting doc {doc.id}")
                doc.delete()
                deleted += 1

            if deleted < batch_size:
                break

    def _delete_all_subcollections(doc_ref):
        """
        Recursively deletes all subcollections under a document.

        :param doc_ref: Firestore document reference.
        """

        subcollections = list(doc_ref.collections())
        for subcollection in subcollections:
            _delete_collection1(subcollection, batch_size=25)

    def _delete_audio_file_from_storage(file_path):
        try:
            # Reference to the file in Cloud Storage
            bucket = storage.bucket()
            blob = bucket.blob(file_path)

            # Check if the file exists
            if blob.exists():
                # Delete the file
                blob.delete()
                print(f"File '{file_path}' has been deleted successfully from Cloud Storage.")
                return True
            else:
                print(f"File '{file_path}' does not exist in Cloud Storage.")
                return False
        except Exception as eu:
            print(f"An error occurred while deleting the file from Cloud Storage: {eu}")
            return False

    def _delete_all_files_from_storage(folder_path):
        bucket = storage.bucket()
        blobs = bucket.list_blobs(prefix=folder_path)

        is_all_deleted = True

        # Iterate through all files in the folder
        for blob in blobs:
            try:
                blob.delete()
                print(f"Deleted file: {blob.name}")
            except Exception as e:
                is_all_deleted = False
                print(f"Failed to delete file: {blob.name}. Error: {e}")
        return is_all_deleted

    audio_storage_file_path = (f'orderData/{audio_doc_id}'
                               f'/orderByVoiceData/{audio_ref_id}/'
                               f'{audio_key}/audio_file_{audio_key}_voice.mp3')

    if _from == 'obv':
        audio_db_doc_ref = cloudFirestore.document(f"Users/{user_id}/voiceOrdersData/{_from}/"
                                                   f"{audio_doc_id}/{audio_ref_id}/voiceData/{audio_key}")
    else:
        audio_db_doc_ref = cloudFirestore.document(f"Users/{user_id}/voiceOrdersData/{_from}/"
                                                   f"{audio_doc_id}/{audio_ref_id}/{shop_id}/{audio_key}")

    clear_cart_storage_ref = (f'orderData/{audio_doc_id}'
                              f'/orderByVoiceData/{audio_ref_id}')

    clear_cart_audio_doc_ref = cloudFirestore.document(f"Users/{user_id}/voiceOrdersData/{_from}/"
                                                       f"{audio_doc_id}/{audio_ref_id}")

    if delete_all_files:
        if _delete_all_files_from_storage(clear_cart_storage_ref):
            try:
                _delete_all_subcollections(clear_cart_audio_doc_ref)
                log.info("File reference cleared from db")
                return {'is_success': True, 'message': 'All voice order(s) deleted successfully, cart cleared'}
            except Exception as et:
                return {'is_success': True,
                        'message': 'All voice orders file only deleted from storage, '
                                   'unable to delete from db refs.',
                        'error': str(et)}

    if _delete_audio_file_from_storage(audio_storage_file_path):
        try:
            audio_db_doc_ref.delete()
            log.info("File reference cleared from db")
            return {'is_success': True, 'message': 'File deleted successfully'}
        except Exception as et:
            return {'is_success': True, 'message': 'Voice order file only deleted from storage,'
                                                   ' unable to delete from db refs.',
                    'error': str(et)}
    else:
        return {'is_success': False, 'message': 'Unable to delete voice order file.'}


def fetch_shop_loc_data_from_id(shop_id: str):
    loc_data_ref = (cloudFirestore.collection("ShopData")
                    .document("dataCache").collection("locationData").document(shop_id))

    loc_data_snapshot = loc_data_ref.get()

    if loc_data_snapshot.exists:
        loc_map_data = loc_data_snapshot.to_dict()

        return {
            'shop_district': loc_map_data.get('shop_district'),
            'shop_id': loc_map_data.get('shop_id'),
            'shop_loc_coords': {'latitude': loc_map_data.get('shop_loc_coords').latitude,
                                'longitude': loc_map_data.get('shop_loc_coords').longitude},
            'shop_pincode': loc_map_data.get('shop_pincode')
        }
    else:
        return {}


@csrf_exempt
def fetch_order_data(request):
    if request.method == 'POST':
        try:
            user_id = request.POST.get('user_id')
            dp_id = request.POST.get('dp_id')
            user_phno = request.POST.get('user_phno')
            order_key = request.POST.get('order_key')
            order_type = request.POST.get('order_type')
            shop_id = request.POST.get('shop_id')

            order_info_doc_ref = (cloudFirestore.collection("DeliveryPartners").document(dp_id)
                                  .collection("currentOrder")
                                  .document(order_key).collection("orderData").document("info"))
            order_info_snapshot = order_info_doc_ref.get()

            if order_info_snapshot.exists:
                info_data = order_info_snapshot.to_dict()

                # Convert GeoPoint to serializable format
                if 'delivery_address_loc' in info_data and isinstance(info_data['delivery_address_loc'], gfs.GeoPoint):
                    info_data['delivery_address_loc'] = {
                        'latitude': info_data['delivery_address_loc'].latitude,
                        'longitude': info_data['delivery_address_loc'].longitude
                    }

                if 'shop_loc' in info_data and isinstance(info_data['shop_loc'], gfs.GeoPoint):
                    info_data['shop_loc'] = {
                        'latitude': info_data['shop_loc'].latitude,
                        'longitude': info_data['shop_loc'].longitude
                    }

                # prepare manual cart product data
                collection_ref = cloudFirestore.collection(f"DeliveryPartners/{dp_id}/pendingOrders/"
                                                           f"{order_key}/manualCartProductData")
                # Retrieve documents from the collection
                docs = collection_ref.stream()

                # Convert documents to a list of dictionaries
                manual_cart_product_data = []
                for doc in docs:
                    manual_cart_product_data.append(doc.to_dict())

                info_data['manual_cart_product_data'] = manual_cart_product_data

                if order_type == 'obv':
                    if len(user_phno) == 10:
                        addr_data = get_address_data(user_id, user_phno)

                        # store_data, all_shop_coords = (
                        #     fetch_store_pref_data(user_id, info_data['user_phno'],
                        #                           addr_data.get('state'), addr_data.get('district')))

                        shop_data = get_shop_data1(shop_id, addr_data.get('state'), addr_data.get('district'))
                        print(shop_data)

                        # Convert to JSON array
                        store_pref_data_list = [
                            {
                                'shop_district': shop_data['shop_district'],
                                'shop_street': shop_data['shop_street'],
                                'shop_id': shop_id,
                                "shop_email": shop_data['shop_email'],
                                "shop_phone": shop_data['shop_phone'],
                                "shop_image_url": shop_data['shop_image_url'],
                                "shop_pincode": shop_data['shop_pincode'],
                                # "geohash": shop_info['geohash'],
                                "shop_lat": shop_data['shop_loc_coords'].latitude,
                                "shop_lon": shop_data['shop_loc_coords'].longitude,
                                "shop_state": shop_data['shop_state'],
                                "shop_name": shop_data['shop_name'],
                                "shop_address": shop_data['shop_address'],
                                # "shop_preference": shop_data['shop_preference'],
                                "distance_km": utils.haversine(addr_data.get('address_lat'),
                                                               addr_data.get('address_lon'),
                                                               shop_data['shop_loc_coords'].latitude,
                                                               shop_data['shop_loc_coords'].longitude),
                                # You can calculate the distance if needed
                                "displacement": 0  # You can calculate the displacement if needed
                            }
                            # for shop_id, shop_info in store_data.items()
                        ]

                        info_data['store_pref_data'] = store_pref_data_list
                    else:
                        log.warning("Unable to fetch store pref data, invalid phone no")

                response_data = {
                    'is_success': True,
                    'status': 'success',
                    'order_type': order_type,
                    'data': info_data

                }
            else:
                response_data = {
                    'is_success': False,
                    'status': 'error',
                    'message': f'Order data ({order_key}) does not exist'
                }

        except Exception as eq:
            response_data = {
                'is_success': False,
                'status': 'error',
                'message': str(eq)
            }
    else:
        response_data = {
            'is_success': False,
            'status': 'error',
            'message': 'Invalid request method'
        }
    log.info(response_data)
    return response_data


def delete_user_account(client_id: str, client_type: str):
    updates = {}
    client_type = client_type.lower()

    try:
        email_id = auth.get_user(client_id).email
    except Exception as er:
        email_id = ""
        pass

    if client_type.lower() not in ['order', 'delivery', 'vendor']:
        log.error(f"Invalid client type provided: {client_type}")
        return {'is_deleted': False, 'message': 'Invalid client type'}

    def _delete_user_firestore(uid: str):
        try:
            # Delete the user's authentication record
            auth.delete_user(uid)
            log.info(f"Successfully deleted user: {uid}")
            return True, f"Successfully deleted user: {uid}"
        except _auth_utils.UserNotFoundError:
            log.warning(f"User with UID {uid} not found or registered.")
            return False, f"User with UID {uid} not found or registered."
        except Exception as ek:
            log.error(f"Error deleting user: {ek}")
            return False, f"Error deleting user: {ek}"

    def _delete_collection1(coll_ref, batch_size):
        """
        Deletes documents in a Firestore collection in batches.

        :param coll_ref: Firestore collection reference.
        :param batch_size: Number of documents to delete in each batch.
        """
        while True:
            docs = coll_ref.list_documents(page_size=batch_size)
            deleted = 0

            for doc in docs:
                # Recursively delete subcollections
                _delete_all_subcollections(doc)

                log.info(f"Deleting doc {doc.id}")
                doc.delete()
                deleted += 1

            if deleted < batch_size:
                break

    def _delete_all_subcollections(doc_ref):
        """
        Recursively deletes all subcollections under a document.

        :param doc_ref: Firestore document reference.
        """

        subcollections = list(doc_ref.collections())
        for subcollection in subcollections:
            _delete_collection1(subcollection, batch_size=25)

    try:
        _s, _r = _delete_user_firestore(uid=client_id)

        if not _s:
            return {'is_deleted': False, 'message': f"Failed to delete account: {str(_r)}"}

        users_doc_ref = cloudFirestore.document(f"Users/{client_id}")
        fcm_token_map_doc_ref = cloudFirestore.document(f"FCMTokenMapping/{client_type.capitalize()}AppClient")

        _delete_all_subcollections(users_doc_ref)
        log.warning(f"Account data deleted for client_id {client_id}")
        fcm_token_map_doc_ref.update({client_id: gfs.DELETE_FIELD})

        # Delete registered email from "RegisteredUsersEmail" db bucket
        doc = registered_users_email_ref.get()
        if doc.exists:
            email_addresses = doc.to_dict().get("email_addresses", [])
            if email_id in email_addresses:
                email_addresses.remove(email_id)
                updates["email_addresses"] = email_addresses
                registered_users_email_ref.update(updates)
                log.info("Email removed successfully from db refs")
            else:
                log.warning("Email not found in reference register.")
        else:
            log.warning("Document does not exist")

        return {'is_deleted': True, 'message': 'Account deleted successfully'}
    except Exception as et:
        log.error(f"Failed to delete account for client_id {client_id}: {str(et)}")
        return {'is_deleted': False, 'message': f"Failed to delete account: {str(et)}"}
