# tasks.py

from django.utils import timezone
from huey import crontab
from huey.contrib.djhuey import periodic_task

from VoiGO.settings import log
from server.cloud import cloud as fca
from .crypto_utils import des_core
from .engine_core.order_processing import obs
from .engine_core.order_processing import obv
from .models import PendingOBSOrder
from .models import PendingOBVOrder


@periodic_task(crontab(minute="*/1"))
def check_and_assign_orders(*args, **kwargs):
    try:
        log.info("Running periodic task to check and assign orders.")

        # Process PendingOBSOrder
        process_pending_orders(PendingOBSOrder, 'obs')

        # Process PendingOBVOrder
        process_pending_orders(PendingOBVOrder, 'obv')

        log.info("Periodic task completed successfully.")
    except Exception as e:
        log.exception(f"Exception occurred in check_and_assign_orders task. {str(e)}")


def process_pending_orders(model, order_type):
    pending_orders = model.objects.filter(status='pending')

    if not pending_orders:
        log.info(f"NO PENDING ORDER(S) FOUND FOR {order_type.upper()}.")
        return

    orders_to_update = []
    orders_to_delete = []
    notifications = []

    for order in pending_orders:
        assigned_dp = None

        if order_type == 'obs':
            assigned_dp = obs.on_new_obs_order_received1(
                order.order_id, order.user_id_enc, order.user_email,
                order.user_phno_enc, order.order_by_voice_doc_id,
                order.order_by_voice_audio_ref_id, order.shop_id,
                order.shop_district, order.shop_pincode, order.curr_lat, order.curr_lon
            )
        elif order_type == 'obv':
            assigned_dp = obv.on_new_obv_order_received_store_pref(order.request_body)

        user_id = des_core.decrypt(order.user_id_enc).get('plain_text')
        log.info(f"TASK USER_ID: {user_id}")

        if assigned_dp and assigned_dp.get('is_assigned'):
            fcm_data_payload = {
                'title': 'Pending order assigned',
                'body': f"Order {order.order_id[6:23]} has been assigned."
                        f" {assigned_dp['partner_name']} is your delivery partner."
            }

            order.status = 'assigned'
            order.updated_at = timezone.now()
            orders_to_update.append(order)
            notifications.append((user_id, fcm_data_payload, 'Order assigned'))

            # Notify the delivery partner and the user
            # notify_partner(assigned_dp['dp_id'], order.order_id)
            # notify_user(order.user_id, order.order_id)
            orders_to_delete.append(order)
        else:
            fcm_data_payload = {
                'title': 'Order not assigned',
                'body': f"Order {order.order_id[6:23]} has not been assigned. We'll assign a partner soon..."
            }
            notifications.append((user_id, fcm_data_payload, "Order not assigned"))
            log.warning(f"Order {order.order_id[6:23]} has not been assigned. We'll assign a partner soon...")

    # Bulk update and delete orders
    model.objects.bulk_update(orders_to_update, ['status', 'updated_at'])
    log.info(f'Successfully updated {len(orders_to_update)} orders.')

    deleted_count, _ = model.objects.filter(pk__in=[order.pk for order in orders_to_delete]).delete()
    log.info(f'Successfully deleted {deleted_count} orders.')

    # Send notifications
    for user_id, fcm_data_payload, title in notifications:
        fca.send_fcm_notification(user_id, fcm_data_payload, 'user')
