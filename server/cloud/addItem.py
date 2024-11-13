# addItem.py

from server.cloud import cloud as service


# # put items: map @manualCartProductData cloud reference
# def to_manual_cart(client_id, incoming_items):
#     try:
#         service.get_manual_cart_product_data_ref(str(client_id)).update(incoming_items)
#         print(f"update success @{client_id}.manualCartProductData")
#         return True
#     except Exception as e:
#         print(f"Exception occurred {e} !")
#         return False
#
#
# # put items: map @voiceCartProductData cloud reference
# def to_voice_cart(client_id, incoming_items):
#     try:
#         service.get_voice_cart_product_data_ref(str(client_id)).update(incoming_items)
#         print(f"update success @{client_id}.voiceCartProductData")
#         return True
#     except Exception as e:
#         print(f"Exception occurred {e} !")
#         return False
#
#
# # put items: map @orderByVoiceData cloud reference
# def to_order_by_voice(client_id, incoming_items):
#     try:
#         service.get_order_by_voice_data_ref(str(client_id)).update(incoming_items)
#         print(f"update success @{client_id}.orderByVoiceData")
#         return True
#     except Exception as e:
#         print(f"Exception occurred {e} !")
#         return False


# def set_client_as_inactive_partner(ref_date, client_id):
#     try:
#         service.get_inactive_partners_ref(ref_date).update(str(client_id))
#         print(f"update success @{ref_date}.inactivePartners.{client_id}")
#         return True
#     except Exception as e:
#         print(f"Exception occurred {e} !")
#         return False
