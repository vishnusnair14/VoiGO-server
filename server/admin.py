from django.contrib import admin

from .models import (TemporaryAddress, PendingOBSOrder,
                     WSChatRegister1, UploadedImage,
                     OrderMap, PendingOBVOrder, PartnerOrder)

# Register your models here.

admin.site.register(TemporaryAddress)
admin.site.register(PendingOBVOrder)
admin.site.register(PendingOBSOrder)
admin.site.register(WSChatRegister1)
admin.site.register(UploadedImage)
admin.site.register(OrderMap)
admin.site.register(PartnerOrder)
