import json
import re

import firebase_admin
import firebase_admin as fba
import pygeohash as pgh

from django.core.files.storage import default_storage
from django.http import JsonResponse
from firebase_admin import auth
from firebase_admin import storage

from VoiGO.settings import log
from server import utils, constants
from server.cloud import cloud as fca
from server.models import UploadedImage


class BaseRegistration:
    def __init__(self):
        pass

    def update_user_profile(self, user_id, new_display_name, photo_url):
        try:
            user = auth.update_user(
                user_id,
                display_name=new_display_name,
                photo_url=photo_url
            )
            log.info(f'User profile updated successfully: {user.uid}')
            return True
        except firebase_admin.auth.UserNotFoundError as e:
            print('Error updating user profile, user not found', e)
            return False

    def send_verification_email(self, email):
        print("sending verification email...")
        try:
            link = auth.generate_email_verification_link(email)
            utils.send_email(email, "Email verification link", link)
            return True
        except fba.auth.EmailAlreadyExistsError as e:
            log.error(f"Exception occurred at:{__file__}.send_verification_email {e}")
            log.error('Error sending verification email')
            return False

    def register_user(self, email, password):
        try:
            user = auth.create_user(email=email, password=password)
            log.info(f'Successfully created user:{user.uid}')
            return user, str(user.uid)
        except auth.EmailAlreadyExistsError as e:
            log.warning(f'This email already exists{e}')
            return None

    def add_email_to_array(self, item_to_add):
        # Reference to the document
        registered_users_email_ref = (fca.cloudFirestore
                                      .document('AuthenticationData/RegisteredUsersEmail'))

        # Data to update
        update_data = {"email_addresses": fca.gfs.ArrayUnion([item_to_add])}

        # Fetch the document
        doc = registered_users_email_ref.get()

        if doc.exists:
            # Update the array field
            registered_users_email_ref.update(update_data)
            log.info("User email updated to array successfully")
        else:
            # Set the array field
            registered_users_email_ref.set(update_data)
            log.info("User email added to array successfully")

    def add_user_login_creds_to_db(self, email_id, pswd, uid):
        # Reference to the document
        registered_users_credentials_ref = (fca.cloudFirestore
                                            .document('AuthenticationData/RegisteredUsersCredentials'))

        # Prepare the data
        user_data_map = {
            'email_id': email_id,
            'password': pswd,
            'client_type': "vendor",
            'id': uid
        }

        user_data_key_map = {uid: user_data_map}

        # Fetch the document
        doc = registered_users_credentials_ref.get()

        if doc.exists:
            # Update the map-type data
            registered_users_credentials_ref.update(user_data_key_map)
            log.info("User data updated successfully")
        else:
            registered_users_credentials_ref.set(user_data_key_map)
            log.info("User data added successfully")

    def district_to_format(self, input_string):
        # Define the regex pattern to match words containing 'dist'
        pattern = r'\b\w*dist\w*\b'

        # Use re.sub to replace all occurrences of the pattern with an empty string
        rs = re.sub(pattern, '', input_string)

        # Remove any extra whitespace that might have been left behind
        rs = re.sub(r'\s+', ' ', rs).strip()

        return rs.lower()


class ShopRegistration(BaseRegistration):
    def __init__(self):
        super().__init__()

    def register_shop(self, request):
        # Retrieve image file
        image_file = request.FILES.get('image')

        if not image_file:
            return JsonResponse({'status': 'error', 'message': 'No image provided'})

        # Parse the JSON request body
        user_data = json.loads(request.POST.get('account_data'))

        shop_name = user_data.get('shop_name')
        shop_lat = user_data.get('shop_lat')
        shop_lon = user_data.get('shop_lon')
        shop_state = str(user_data.get('shop_state')).lower()
        shop_district = str(user_data.get('shop_district')).lower()
        shop_pincode = user_data.get('shop_pincode')
        shop_reg_email = user_data.get('shop_reg_email', 'None')
        shop_reg_password = user_data.get('shop_reg_password', 'None')
        shop_phone = user_data.get('shop_phone', 'None')

        shop_loc_coords = {'latitude': shop_lat, 'longitude': shop_lon}

        geohash = pgh.encode(shop_loc_coords['latitude'], shop_loc_coords['longitude'],
                             precision=constants.GEOHASH_PRECISION)

        # resp = utils.reverse_geocode_bigdatacloud(shop_loc_coords['latitude'], shop_loc_coords['longitude'])

        # shop_district = self.district_to_format(resp.get('district'))

        shop_loc_coords = fca.gfs.GeoPoint(shop_loc_coords['latitude'], shop_loc_coords['longitude'])

        log.info("Registering user...")
        user, uid = self.register_user(shop_reg_email, shop_reg_password)

        try:
            # Upload image to Firebase Storage
            log.info("Setting profile...")
            bucket = storage.bucket()
            blob = bucket.blob(f'profile_photos/{uid}/{image_file.name}')
            blob.upload_from_filename('images/' + image_file.name)
            blob.make_public()
            image_url = blob.public_url
        except Exception as e:
            log.error(f"Exception occurred at:{__file__}.register_shop {str(e)}")
            return {'status': False, 'message': str(e)}

        if uid is not None:
            shop_info_ref = (fca.cloudFirestore.collection('ShopData')
                             .document("data")
                             .collection(shop_state)
                             .document(shop_district).collection("allShopData").document(uid))

            location_map_ref = (fca.cloudFirestore.collection('ShopData')
                                .document("dataCache")
                                .collection("locationData")
                                .document(uid))

            shop_info_payload = {
                'shop_name': shop_name,
                'shop_email': shop_reg_email,
                'shop_phone': shop_phone,
                'shop_address': user_data.get('shop_address', 'None'),
                'shop_pincode': shop_pincode,
                'shop_image_url': image_url,
                'shop_street': user_data.get('shop_street', 'None'),
                'shop_state': shop_state,
                'shop_district': shop_district,
                'shop_loc_coords': shop_loc_coords,
                'geohash': geohash, 'shop_id': uid
            }

            location_map_info_payload = {
                'shop_id': uid,
                'shop_state': shop_state,
                'shop_district': shop_district,
                'shop_pincode': shop_pincode,
                'shop_loc_coords': shop_loc_coords,
            }

            if self.update_user_profile(user_id=uid, new_display_name=shop_name, photo_url=image_url):
                log.info("Profile updated.")

            # if self.send_verification_email(user.email):
            #     print("Verification email sent success")

            shop_info_ref.set(shop_info_payload, merge=True)
            location_map_ref.set(location_map_info_payload, merge=True)

            inst = UploadedImage.objects.filter(name='images/' + image_file.name)
            log.info('images/' + image_file.name)
            inst.delete()
            # print(f"Deleted {s} image records.")

            try:
                self.add_user_login_creds_to_db(shop_reg_email, shop_reg_password, uid)
                self.add_email_to_array(user.email)

                default_storage.delete(f'images/{image_file.name}')

                return {'status': True, 'message': 'New vendor account registered successfully'}
            except Exception as e:
                log.error(f"Exception occurred at:{__file__}.register_shop {str(e)}")
                return {'status': False, 'message': str(e)}


class UserRegistration(BaseRegistration):
    def __init__(self):
        super().__init__()

    def register_client(self, username, password):
        # Implement user-specific registration logic here
        pass


class DeliveryPartnerRegistration(BaseRegistration):
    def __init__(self):
        super().__init__()

    def register_account(self, request):
        # Retrieve image file
        image_file = request.FILES.get('image')

        if not image_file:
            return JsonResponse({'status': 'error', 'message': 'No image provided'})

        # Parse the JSON request body
        user_data = json.loads(request.POST.get('account_data'))

        username = user_data.get('user_name')
        user_state = str(user_data.get('user_state')).lower()
        user_district = str(user_data.get('user_district')).lower()
        user_pincode = user_data.get('user_pincode')
        user_email = user_data.get('user_email', 'None')
        user_password = user_data.get('user_password', 'None')
        user_phone = user_data.get('user_phone', 'None')

        log.info("Registering user...")
        user, uid = self.register_user(user_email, user_password)

        try:
            # Upload image to Firebase Storage
            log.info("Setting profile...")
            bucket = storage.bucket()
            blob = bucket.blob(f'profile_photos/{uid}/{image_file.name}')
            blob.upload_from_filename('images/' + image_file.name)
            blob.make_public()
            image_url = blob.public_url
        except Exception as e:
            log.error(f"Exception occurred at:{__file__}.DeliveryPartnerRegistration.register_account {str(e)}")
            return {'status': False, 'message': str(e)}

        if uid is not None:
            user_data_ref = (fca.cloudFirestore.
                             document(f"DeliveryPartners/{uid}"))

            # location_map_ref = (fca.cloudFirestore.collection('DeliveryPartnerDutyStatus')
            #                     .document("dataCache")
            #                     .collection("locationData")
            #                     .document(uid))

            shop_info_payload = {
                'user_id': uid,
                'user_name': username,
                'user_email': user_email,
                'user_phone': user_phone,
                'user_pincode': user_pincode,
                'user_profile_image_url': image_url,
                'user_state': user_state,
                'user_district': user_district,
            }

            location_map_info_payload = {
                'user_id': uid,
                'user_state': user_state,
                'user_district': user_district,
                'user_pincode': user_pincode,
            }

            if self.update_user_profile(user_id=uid, new_display_name=username, photo_url=image_url):
                log.info("Profile updated.")

            # if self.send_verification_email(user.email):
            #     print("Verification email sent success")

            user_data_ref.set(shop_info_payload, merge=True)
            # location_map_ref.set(location_map_info_payload, merge=True)

            inst = UploadedImage.objects.filter(name='images/' + image_file.name)
            log.info('images/' + image_file.name)
            inst.delete()
            # print(f"Deleted {s} image records.")

            try:
                self.add_user_login_creds_to_db(user_email, user_password, uid)
                self.add_email_to_array(user.email)

                default_storage.delete(f'images/{image_file.name}')

                return {'status': True, 'message': 'New delivery partner account registered successfully'}
            except Exception as e:
                log.error(f"Exception occurred at:{__file__}.DeliveryPartnerRegistration.register_account {str(e)}")
                return {'status': False, 'message': str(e)}
