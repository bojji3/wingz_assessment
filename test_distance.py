import django
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'wingz_backend.settings'
django.setup()

from django.db.models import F, Value
from django.db.models.functions import Radians
from rides.views import Cos, Sin, ACos
from rides.models import Ride

lat_ref = Value(37.8000)
lon_ref = Value(-122.4500)
distance_expr = 3959 * ACos(
    Cos(Radians(lat_ref)) * Cos(Radians(F('pickup_latitude'))) *
    Cos(Radians(F('pickup_longitude')) - Radians(lon_ref)) +
    Sin(Radians(lat_ref)) * Sin(Radians(F('pickup_latitude')))
)
qs = Ride.objects.annotate(distance=distance_expr).values('id_ride', 'distance')
result = list(qs)
dist = result[0]['distance']
print(f'Distance: {dist:.2f} miles')
assert dist > 0, 'Distance should be > 0'
print('Distance calculation works correctly!')
