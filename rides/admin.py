from django.contrib import admin

from .models import Ride, RideEvent, User


class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'phone_number')
    search_fields = ('email', 'first_name', 'last_name')


class RideAdmin(admin.ModelAdmin):
    list_display = ('id_ride', 'status', 'id_rider', 'id_driver', 'pickup_time')
    list_filter = ('status',)
    search_fields = ('id_rider__email', 'id_driver__email')


class RideEventAdmin(admin.ModelAdmin):
    list_display = ('id_ride_event', 'id_ride', 'description', 'created_at')
    list_filter = ('description', 'created_at')


admin.site.register(User, UserAdmin)
admin.site.register(Ride, RideAdmin)
admin.site.register(RideEvent, RideEventAdmin)
