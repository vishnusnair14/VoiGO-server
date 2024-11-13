# /urls/vendor.py

"""
vendor.py

Part of VoiGO-Server

This module defines URL patterns for the Django project. It contains
mappings between URL patterns and view functions, allowing the Django
application to handle incoming HTTP request from vendor-dashboard application

"""

from django.urls import path

from server import views

# URLPatterns for Vendor-Dashboard Application
urlpatterns = [

    path('register-vendor-account', views.registerVendorAccount, name='upload_image'),
]
