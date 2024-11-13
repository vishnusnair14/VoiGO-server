"""
URL configuration for VoiGO project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views. Home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, register_converter, include

from server import views
from server.converters import FloatConverter

register_converter(FloatConverter, 'float')

# URLPatterns
urlpatterns = [
    path('', views.index),

    path('ws1/', views.wsIndex1, name="ws"),

    path('ws2/', views.wsIndex2, name="ws"),

    path('admin/', admin.site.urls),

    path('mailto/<str:_to>', views.sendEMail),

    path('send_ws_message/', views.sendOrderUpdatesWS, name='sent_ws_message'),

    path('send_chat_messages/', views.sendChatMessageWS, name='send_chat_messages'),

    path('route-api/<str:lat1>/<str:lon1>/<str:lat2>/<str:lon2>',
         views.computeRouteMatrix, name='send_chat_messages'),

    path('delete-user-account/',
         views.deleteAccount1, name='deleteAccount1'),

    path('', include('server.urls.order')),
    path('', include('server.urls.delivery')),
    path('', include('server.urls.vendor')),
]
