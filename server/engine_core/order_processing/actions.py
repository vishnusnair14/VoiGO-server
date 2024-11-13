from simple_colors import *

import server.cloud.cloud as fca
from VoiGO.settings import log
from server import utils, models
from server.constants import KEYWORD

osp_order_placed: dict = {
    # ORDER PLACED
    'order_status_no': 1,
    'order_status_data': {
        '1': {
            'key': 1,
            'title': 'Order placed',
            'sub_title': 'You have successfully placed your order.'},
    },
    'order_status_label': 'Order Placed',
    'order_status_label_bg_color': '#1d4176',
    'order_status_label_fg_color': '#ffffff'
}

osp_order_accepted: dict = {
    # ORDER ACCEPTED
    'order_status_no': 3,
    'order_status_data': {
        '1': {
            'key': 1,
            'title': 'Order placed',
            'sub_title': 'You have successfully placed your order.'},
        '2': {
            'key': 2,
            'title': 'Delivery partner assigned',
            'sub_title': 'Order have been confirmed, partner assigned.'},
        '3': {
            'key': 3,
            'title': 'Order accepted',
            'sub_title': 'Delivery partner had accepted your order.'},
    },
    'order_status_label': 'Order Accepted',
    'order_status_label_bg_color': '#1d4176',
    'order_status_label_fg_color': '#ffffff'
}

osp_order_pickup_success: dict = {
    # ORDER PICKUP SUCCESS
    'order_status_no': 4,
    'order_status_data': {
        '1': {
            'key': 1,
            'title': 'Order placed',
            'sub_title': 'You have successfully placed your order.'},

        '2': {
            'key': 2,
            'title': 'Delivery partner assigned',
            'sub_title': 'Order have been confirmed, partner assigned.'},

        '3': {
            'key': 3,
            'title': 'Order accepted',
            'sub_title': 'Delivery partner had accepted your order.'},

        '4': {'key': 4,
              'title': 'Order picked',
              'sub_title': 'Your order has picked up from shop.'},
    },
    'order_status_label': 'Order Picked',
    'order_status_label_bg_color': '#3d85c6',
    'order_status_label_fg_color': '#ffffff'
}

osp_order_enrouted: dict = {
    # ORDER EN-ROUTED
    'order_status_no': 5,
    'order_status_data': {
        '1': {
            'key': 1,
            'title': 'Order placed',
            'sub_title': 'You have successfully placed your order.'},

        '2': {
            'key': 2,
            'title': 'Delivery partner assigned',
            'sub_title': 'Order have been confirmed, partner assigned.'},

        '3': {
            'key': 3,
            'title': 'Order accepted',
            'sub_title': 'Delivery partner had accepted your order.'},

        '4': {'key': 4,
              'title': 'Order picked',
              'sub_title': 'Your order has picked up from shop.'},

        '5': {'key': 5,
              'title': 'Order en-routed',
              'sub_title': 'Partner is on the way to deliver.'},
    },
    'order_status_label': 'Order enrouted',
    'order_status_label_bg_color': '#8fce00',
    'order_status_label_fg_color': '#16537e'

}

osp_order_delivered: dict = {
    # ORDER DELIVERED
    'order_status_no': 6,
    'order_status_data': {
        '1': {
            'key': 1,
            'title': 'Order placed',
            'sub_title': 'You have successfully placed your order.'},

        '2': {
            'key': 2,
            'title': 'Delivery partner assigned',
            'sub_title': 'Order have been confirmed, partner assigned.'},

        '3': {
            'key': 3,
            'title': 'Order accepted',
            'sub_title': 'Delivery partner had accepted your order.'},

        '4': {'key': 4,
              'title': 'Order picked',
              'sub_title': 'Your order has picked up from shop.'},

        '5': {'key': 5,
              'title': 'Order en-routed',
              'sub_title': 'Partner is on the way to deliver.'},

        '6': {'key': 6,
              'title': 'Order delivered',
              'sub_title': 'Your order has been delivered successfully'}
    },
    'order_status_label': 'Order Delivered',
    'order_status_label_bg_color': '#8fce00',
    'order_status_label_fg_color': '#ffffff'
}

SUCCESS: bool = True
FAILED: bool = False


def update_rtime_order_status(status_pos: int, user_id: str, order_id: str, additional_payload: dict):
    """
    :param status_pos:
    :param user_id:
    :param order_id:
    :param additional_payload:

    """
    order_status_doc_ref = (fca.cloudFirestore.collection("Users").document(user_id)
                            .collection("placedOrderData").document(order_id)
                            .collection("realtimeUpdateData").document("orderStatus"))

    def _update(_payload: dict):
        try:
            doc_snapshot = order_status_doc_ref.get()
            print(doc_snapshot)
            if doc_snapshot.exists:
                order_status_doc_ref.update(_payload)
            else:
                order_status_doc_ref.set(_payload)
        except Exception as re:
            print(f"Exception occurred at file {__file__}._update_or_set_order_data: {str(re)}")

    if status_pos == 1:
        merge_payload = osp_order_placed | additional_payload
        _update(merge_payload)

    elif status_pos == 2:
        merge_payload = additional_payload
        _update(merge_payload)

    elif status_pos == 3:
        merge_payload = osp_order_accepted | additional_payload
        _update(merge_payload)

    elif status_pos == 4:
        merge_payload = osp_order_pickup_success | additional_payload
        _update(merge_payload)

    elif status_pos == 5:
        merge_payload = osp_order_enrouted | additional_payload
        _update(merge_payload)

    elif status_pos == 6:
        merge_payload = osp_order_delivered | additional_payload
        _update(merge_payload)


# Function to handle order accept
def accept_order(dp_id: str, user_id: str, order_id: str):
    """
    Handle the process of accepting an order by a delivery partner.

    This function performs the following steps:
    1. Retrieves the order data from the pending orders collection for the given delivery partner.
    2. Updates the order status to 'Order Accepted'.
    3. Sends a notification to the user about the order acceptance.
    4. Moves the order data to the current orders collection for both the delivery partner and the user.

    :param dp_id: The ID of the delivery partner.
    :param user_id: The ID of the user who placed the order.
    :param order_id: The ID of the order being accepted.

    :return: A dictionary containing the response status and a message or error.
    """

    order_accepted_fcm_payload = {'order_id': order_id,
                                  'title': 'Order accepted',
                                  'user_id': user_id}

    try:
        # Retrieve Firestore document references
        base_dir, source_doc_ref, target_doc_ref1, target_doc_ref2, target_doc_ref3 = (
            fca.get_all_order_data_info_db_refs(dp_id, user_id, order_id))

        # Set ORDER ACCEPTED changes across all the order-data reference.
        for target_doc_ref in [target_doc_ref1, target_doc_ref2, target_doc_ref3, source_doc_ref]:
            fca.update_set_data_in_doc_ref(target_doc_ref, osp_order_accepted)

        fca.set_obs_order_as_current_accepted(user_id, dp_id, order_id)

        # Fetching data for fcm payload
        base_data_snapshot = source_doc_ref.get()
        if base_data_snapshot.exists:
            base_data = base_data_snapshot.to_dict()
            print(base_data)

            if base_data.get('shop_name') == 'STORE PREF ORDER' or base_data.get('shop_name') == 'store pref order':
                order_accepted_fcm_payload['body'] = (f"{base_data.get('dp_name')} is your delivery partner, "
                                                      "and has accepted your store preference order")
            else:
                order_accepted_fcm_payload['body'] = (f"{base_data.get('dp_name')} is your delivery partner, "
                                                      f"has accepted your order from {base_data.get('shop_name')}")

            # Notify user that the order has accepted by the partner
            fca.send_fcm_notification(client_id=user_id,
                                      fcm_data_payload=order_accepted_fcm_payload,
                                      client_type="user")

        try:
            update_rtime_order_status(KEYWORD.order_accepted, user_id, order_id, {'dp_id': dp_id})

            return {'response_status': SUCCESS, 'message': 'Order accepted successfully.'}

        except Exception as ey:
            log.error(f"Exception occurred at:{__file__}.accept_order {str(ey)}")
            return {'response_status': FAILED,
                    'message': f'Unable to update reltime order status: {str(ey)}'}

    except Exception as e:
        log.error(f"Exception occurred at:{__file__}.accept_order {str(e)}")
        return {'response_status': FAILED,
                'message': 'Unable to accept order: ' + str(e)}


def save_order_for_next_or_decline(dp_id: str, user_id: str, order_id: str):
    # TODO: Add order reject logic here

    try:
        base_dir, source_doc_ref, target_doc_ref1, target_doc_ref2, target_doc_ref3 = (
            fca.get_all_order_data_info_db_refs(dp_id, user_id, order_id))

        source_doc = source_doc_ref.get()
        source_data = source_doc.to_dict()
        print(source_data)

        source_data['order_saved_status'] = 'order_saved'

        try:
            # Set ORDER ACCEPTED changes across all the order-data reference.
            for target_doc_ref in [target_doc_ref3, source_doc_ref]:
                fca.update_set_data_in_doc_ref(target_doc_ref, source_data)

            return {'response_status': SUCCESS, 'message': 'Order saved for next delivery.'}
        except Exception as e:
            print(red(f"Exception occurred at:{__file__}.save_order_for_next {e}", ['bold']))
            return {'response_status': FAILED, 'error': 'Unable to save order for next delivery: ' + str(e)}
    except Exception as e:
        print(red(f"Exception occurred at:{__file__}.save_order_for_next {e}", ['bold']))
        return {'response_status': FAILED, 'message': f'Error saving order: {e}'}


def decline_order(dp_id: str, user_id: str, order_id: str):
    # TODO: Add order rejection logic here

    return {'response_status': SUCCESS, 'message': 'Order declined successfully.'}


# Function to handle order pickup
def order_picked_up(dp_id: str, user_id: str, order_id: str):
    """
    Handle the process of marking an order as picked up by a delivery partner.

    This function performs the following steps:
    1. Retrieve the order data from the pending orders collection for the given delivery partner.
    2. Updates the order status to 'Order Pickup Success'.
    3. Sends a notification to the user about the successful pickup.
    4. Move the order data to the current orders collection for both the delivery partner and the user.

    :param dp_id: The ID of the delivery partner.
    :param user_id: The ID of the user who placed the order.
    :param order_id: The ID of the order being picked up.

    :return: A dictionary containing the response status and a message or error.
    """

    order_picked_fcm_payload = {'order_id': order_id,
                                'user_id': user_id,
                                'title': 'Order Pickup'}

    try:
        # Retrieve Firestore document references
        base_dir, source_doc_ref, target_doc_ref1, target_doc_ref2, target_doc_ref3 = (
            fca.get_all_order_data_info_db_refs(dp_id, user_id, order_id))

        # Set ORDER PICKUP changes across all the order-data reference.
        for target_doc_ref in [target_doc_ref1, target_doc_ref2, target_doc_ref3, source_doc_ref]:
            fca.update_set_data_in_doc_ref(target_doc_ref, osp_order_pickup_success)

        # Fetching data for fcm payload
        base_data_snapshot = source_doc_ref.get()
        if base_data_snapshot.exists:
            doc_data = base_data_snapshot.to_dict()

            order_picked_fcm_payload['body'] = (f"{doc_data.get('dp_name')} has picked up your order from "
                                                f"{doc_data.get('shop_name')}")

            # Notify user that the order has been picked up (using FCM)
            fca.send_fcm_notification(client_id=user_id,
                                      fcm_data_payload=order_picked_fcm_payload,
                                      client_type="user")

            try:
                update_rtime_order_status(KEYWORD.order_pickup, user_id, order_id, {})

                return {'response_status': SUCCESS, 'message': 'Order picked up successfully.'}
            except Exception as e:
                print(f"Exception occurred: {e}")
                return {'response_status': FAILED, 'error': f'Error occurred: {e}'}
        else:
            return {'response_status': FAILED, 'message': 'Source document does not exist or order ID not found.'}
    except Exception as e:
        print(f"Exception occurred: {e}")
        return {'response_status': FAILED, 'error': f'Error transferring order: {e}'}


def order_en_route(dp_id: str, user_id: str, order_id: str):
    """
    Handle the process of marking an order as en route.

    This function performs the following steps:
    1. Retrieve the order data from the pending orders collection for the given delivery partner.
    2. Updates the order status to 'Order En route'.
    3. Sends a notification to the user about the order being en route.
    4. Update the order data in the target collections for both the delivery partner and the user.

    :param dp_id: The ID of the delivery partner.
    :param user_id: The ID of the user who placed the order.
    :param order_id: The ID of the order being en route.

    :return: A dictionary containing the response status and a message or error.
    """

    enroute_fcm_data_payload = {'order_id': order_id,
                                'user_id': user_id,
                                'title': 'Order en-routed'}

    try:
        # Retrieve Firestore document references
        base_dir, source_doc_ref, target_doc_ref1, target_doc_ref2, target_doc_ref3 = (
            fca.get_all_order_data_info_db_refs(dp_id, user_id, order_id))

        # Set ORDER PICKUP changes across all the order-data reference.
        for target_doc_ref in [target_doc_ref1, target_doc_ref2, target_doc_ref3, source_doc_ref]:
            fca.update_set_data_in_doc_ref(target_doc_ref, osp_order_enrouted)

        # Fetching data for fcm payload
        base_data_snapshot = source_doc_ref.get()
        if base_data_snapshot.exists:
            doc_data = base_data_snapshot.to_dict()

            enroute_fcm_data_payload['body'] = (f"{doc_data.get('dp_name')} has picked up your order from "
                                                f"{doc_data.get('shop_name')}")

            # Notify user that the order has been picked up (using FCM)
            fca.send_fcm_notification(client_id=user_id,
                                      fcm_data_payload=enroute_fcm_data_payload,
                                      client_type="user")

            try:
                update_rtime_order_status(KEYWORD.order_enrouted, user_id, order_id, {})

                return {'response_status': SUCCESS, 'message': 'Order is on the way'}
            except Exception as e:
                print(f"Exception occurred: {e}")
                return {'response_status': FAILED, 'error': f'Error occurred: {e}'}
        else:
            return {'response_status': FAILED, 'message': 'Source document does not exist or order ID not found.'}
    except Exception as e:
        print(f"Exception occurred: {e}")
        return {'response_status': FAILED, 'error': f'Error transferring order: {e}'}


def order_delivered(dp_id: str, user_id: str, order_by_voice_doc_id: str,
                    order_by_voice_audio_ref_id: str, order_id: str):
    """
    Handle the process of marking an order as delivered by a delivery partner.

    :param order_by_voice_doc_id:
    :param dp_id: The ID of the delivery partner.
    :param user_id: The ID of the user who placed the order.
    :param order_by_voice_audio_ref_id: The ID of the audio reference.
    :param order_id: The ID of the order being delivered.

    :return: A dictionary containing the response status and a message or error.
    """

    def _delete(doc_ref):
        """
        Deletes a Firestore document and its subcollections.

        :param doc_ref: The Firestore document reference.
        """
        try:
            # Get all subcollections of the document
            subcollections = doc_ref.collections()

            for subcollection in subcollections:
                # Get all documents in the subcollection
                for sub_doc in subcollection.stream():
                    # Recursively delete each subcollection document
                    _delete(sub_doc.reference)

            # Delete the main document
            doc_ref.delete()
            log.info(f"Document {doc_ref.id} and its subcollections have been deleted successfully.")
        except Exception as ei:
            log.error(f"Failed to delete document {doc_ref.id} and its subcollections: {str(ei)}")

    update_rtime_order_status(KEYWORD.order_delivered, user_id, order_id, {})

    fcm_data_payload = {'order_id': order_id,
                        'user_id': user_id,
                        'body': f'Order ({order_id[6:]}) successfully delivered',
                        'title': 'Order delivered successfully'}

    # Retrieve Firestore document references for data wipe
    sd_1, td_1, td_2, td_3, td_4, td_5 = fca.get_all_data_delete_doc_refs(dp_id, user_id, order_id,
                                                                          order_by_voice_doc_id,
                                                                          order_by_voice_audio_ref_id)
    del_refs = [td_1, td_2, td_3, td_4, td_5, sd_1]

    update_ref = fca.cloudFirestore.collection('DeliveryPartners').document(dp_id).collection(
        "finishedOrders").document(order_id)

    try:
        # Retrieve the source document data
        source_doc_ref_snapshot = sd_1.get()
        if source_doc_ref_snapshot.exists:
            fca.update_set_data_in_doc_ref(update_ref, source_doc_ref_snapshot.to_dict())

        # preparing to send FCM
        source_data_snapshot = del_refs[len(del_refs) - 1].get()
        if source_data_snapshot.exists:
            source_data = source_data_snapshot.to_dict()
            fcm_data_payload[
                'body'] = f"{source_data.get('shop_name')} | {utils.get_current_date_time()}\nID: {order_id[6:]}"
            fca.send_fcm_notification(client_id=user_id, fcm_data_payload=fcm_data_payload, client_type="user")
        else:
            fca.send_fcm_notification(client_id=user_id, fcm_data_payload=fcm_data_payload, client_type="user")

        # Delete target documents
        for ref in del_refs:
            _delete(ref)

        # Delete related records from db models
        try:
            ws_register = models.WSChatRegister1.objects.get(chat_id=order_id)
            ws_register.delete()

            order_map = models.OrderMap.objects.get(order_id=order_id)
            order_map.delete()
        except models.WSChatRegister1.DoesNotExist:
            log.warning("WSChatRegister instance does not exist.")
            pass
        except models.OrderMap.DoesNotExist:
            log.warning("WSChatRegister instance does not exist.")
            pass
        except Exception as e:
            print(f"Exception occurred during nested delete operations: {str(e)}")
            log.error(f"Exception occurred during nested delete operations: {str(e)}")

        return {'response_status': SUCCESS, 'order_id': order_id, 'message': 'Order delivered successfully.'}

    except Exception as e:
        print(f"Exception occurred: {e}")
        return {'response_status': FAILED, 'message': f'Error: {str(e)}'}
