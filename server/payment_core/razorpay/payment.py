# payment.py

# [Part of VoiGO-Server script]

import razorpay
import hmac
import hashlib

from simple_colors import *

from server import constants

client = razorpay.Client(auth=(constants.RAZOR_API_KEY, constants.RAZOR_KEY_SECRET))

last_order_id = ""


def create_order(amount: float):
    """
    Creates a new order with the specified amount using Razorpay API.

    This function takes an amount in float, converts it to an integer string format with "00" appended
    (representing paise for INR), and creates an order using the Razorpay client order creation API.
    The function handles exceptions and prints the response or any errors encountered.

    :param amount: The amount for the order.

    :return: dict: The response from the order creation API, containing details of the created order. If an error
             occurs, an empty dictionary is returned.
    """

    amount = str(int(amount)) + "00"

    try:
        res = client.order.create({
            "amount": amount,
            "currency": "INR",
            "receipt": "receipt#1",
            "partial_payment": False,
            "notes": {
                "key1": "value3",
                "key2": "value2"
            }})
        print(res)
        global last_order_id
        last_order_id = res['id']
        return res
    except Exception as e:
        print(red(f"Exception occurred at:{__file__}.create_order {e}", ['bold']))
        return {}


def verify_signature(order_id: str,  rz_payment_id: str, rz_signature: str):
    """
    Verifies the payment signature  received from the payment gateway.

    This function takes the order ID, Razorpay payment ID, and Razorpay signature, then verifies the signature
    using HMAC-SHA256 hashing with a secret key. If the generated signature matches the provided Razorpay signature,
    the verification is successful. Otherwise, it fails.

    :param order_id: The unique identifier of the order.
    :param rz_payment_id: The payment ID received from Razorpay.
    :param rz_signature: The signature received from Razorpay.

    :return: dict: A dictionary indicating whether the signature verification was successful or not.
              The dictionary contains the order ID and the verification status ('VERIFIED' or 'NOT_VERIFIED').
    """

    # Convert the secret key and message to bytes
    key_secret_byte = bytes(constants.RAZOR_KEY_SECRET, 'utf-8')
    message_bytes = bytes(order_id + "|" + rz_payment_id, 'utf-8')

    # Calculate the HMAC-SHA256 hash
    generated_signature = hmac.new(key_secret_byte, message_bytes, hashlib.sha256).hexdigest()

    if generated_signature == rz_signature:
        print("Signature verified: success")
        return {"order_id": order_id, "is_verified": "VERIFIED"}
    else:
        print("Signature verified: failed")
        return {"order_id": order_id, "is_verified": "NOT_VERIFIED"}
