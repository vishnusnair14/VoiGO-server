# order_updates.py

import json
import asyncio

from VoiGO.settings import log
from server import utils, constants
from server.cloud import cloud as fca

client_connections = {}


async def _fetch_data_db(user_id, order_id):
    try:
        doc_ref = (fca.cloudFirestore.collection('Users').document(user_id)
                   .collection('placedOrderData').document(order_id)
                   .collection('realtimeUpdateData').document('orderStatus'))

        order_data_ref = (fca.cloudFirestore.collection('Users').document(user_id)
                          .collection('placedOrderData').document(order_id))

        doc_snapshot = doc_ref.get()
        order_data_snapshot = order_data_ref.get()

        doc_data = doc_snapshot.to_dict()
        order_data = order_data_snapshot.to_dict()

        if order_data:
            doc_data['delivery_lat'] = order_data.get('delivery_loc_coordinates').latitude
            doc_data['delivery_lon'] = order_data.get('delivery_loc_coordinates').longitude
            doc_data['delivery_address'] = order_data.get('delivery_address')

        if 'dp_id' in doc_data:
            dp_id = doc_data['dp_id']
            print(dp_id)

            dp_data_doc_ref = (fca.cloudFirestore.collection('DeliveryPartners').document(dp_id))
            dp_data_doc_data = dp_data_doc_ref.get().to_dict()

            if doc_data:
                doc_data['time'] = utils.get_current_date_time()
                doc_data['dp_lat'] = dp_data_doc_data.get('dp_loc_coordinates').latitude
                doc_data['dp_lon'] = dp_data_doc_data.get('dp_loc_coordinates').longitude
                doc_data['dp_loc_coordinates'] = {'latitude': dp_data_doc_data.get('dp_loc_coordinates').latitude,
                                                  'longitude': dp_data_doc_data.get('dp_loc_coordinates').longitude}
                log.info(doc_data)
                return doc_data
        else:
            return doc_data
    except Exception as e:
        return {'status': 'failed', 'message': f'{e}', 'is_partner_assigned': False, 'dp_name': 'None'}


async def order_updates_stream(client_id, order_id):
    client = client_connections.get(client_id)
    if client:
        try:
            while True:
                if client_id not in client_connections:
                    # Client has disconnected
                    log.error("Client has disconnected!")
                    break

                data = await _fetch_data_db(user_id=client_id, order_id=order_id)
                # print(magenta("Realtime (order-update) data: " + str(data), ['bold']))
                log.info(f"Order update sent for user ({client_id}) at {utils.get_current_date_time()} with data: {data}")
                yield f'data: {json.dumps(data)}\n\n'.encode('utf-8')
                await asyncio.sleep(constants.SSE_ORDER_UPDATE_STREAM_DELAY)
        except Exception as e:
            print(f"Error sending update to client {client_id}: {e}")
        finally:
            if client_id in client_connections:
                del client_connections[client_id]
            print(f"SSE order update broadcasting ended for client ({client_id})")
