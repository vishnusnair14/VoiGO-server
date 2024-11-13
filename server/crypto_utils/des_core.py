import base64

from Crypto.Cipher import DES
from Crypto.Util.Padding import pad, unpad
from server import constants


def encrypt(plaintext: str):
    """
    Encrypts a given plaintext using DES algorithm and
    returns a URL-safe Base64 encoded string.

    :param plaintext: The plain text to encrypt
    :return: Dictionary containing the URL-safe Base64 encoded cipher text
    """

    try:
        cipher = DES.new(constants.DES_KEY, DES.MODE_CBC, constants.DES_IV)
        padded_plaintext = pad(plaintext.encode('utf-8'), DES.block_size)
        encrypted_data = cipher.encrypt(padded_plaintext)

        cipher_text = base64.b64encode(encrypted_data).decode('utf-8')

        return {'cipher_text': cipher_text}
    except Exception as e:
        print(f'An error occurred during encryption: {e}')
        return {'cipher_text': 'None'}


def decrypt(cipher_text: str):
    """
    Decrypts a given URL-safe Base64 encoded cipher text
    using DES algorithm.

    :param cipher_text: URL-safe Base64 encoded cipher text
    :return: Dictionary containing the plain text
    """

    try:
        # Decode the URL-safe Base64 encoded string
        decoded_data = base64.urlsafe_b64decode(cipher_text)

        cipher = DES.new(constants.DES_KEY, DES.MODE_CBC, constants.DES_IV)
        decrypted_data = cipher.decrypt(decoded_data)
        plaintext = unpad(decrypted_data, DES.block_size).decode('utf-8')

        return {'plain_text': plaintext, 'message': 'Decryption successful'}
    except Exception as e:
        print(f'An error occurred: {e}')
        return {'plain_text': 'None',
                'message': 'Decryption successful',
                'error': str(e)}
