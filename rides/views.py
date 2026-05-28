from datetime import timedelta

from django.db import connection, models
from django.db.models import F, Func, Value
from django.db.models.functions import Radians
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import Ride, RideEvent, User
from .permissions import IsAdminRole
from .serializers import RideEventSerializer, RideListSerializer, RideSerializer, UserSerializer


class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class Cos(Func):
    function = 'COS'
    arity = 1


class Sin(Func):
    function = 'SIN'
    arity = 1


class ACos(Func):
    function = 'ACOS'
    arity = 1


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination


class RideEventViewSet(viewsets.ModelViewSet):
    queryset = RideEvent.objects.all()
    serializer_class = RideEventSerializer
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination


class RideViewSet(viewsets.ModelViewSet):
    queryset = Ride.objects.all()
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return RideListSerializer
        return RideSerializer

    def get_queryset(self):
        qs = Ride.objects.select_related('id_rider', 'id_driver')
        if self.action in ('list', 'retrieve'):
            cutoff = timezone.now() - timedelta(hours=24)
            qs = qs.prefetch_related(
                models.Prefetch(
                    'ride_events',
                    queryset=RideEvent.objects.filter(created_at__gte=cutoff),
                    to_attr='todays_ride_events'
                )
            )
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        sort_by = request.query_params.get('sort_by')
        if sort_by == 'pickup_time':
            order = request.query_params.get('order', 'asc')
            if order == 'desc':
                queryset = queryset.order_by('-pickup_time')
            else:
                queryset = queryset.order_by('pickup_time')
        elif sort_by == 'distance':
            if 'lat' not in request.query_params or 'lon' not in request.query_params:
                return Response(
                    {'error': 'lat and lon query params required for distance sorting'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                lat = float(request.query_params['lat'])
                lon = float(request.query_params['lon'])
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Invalid lat/lon values'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            lat_ref = Value(lat)
            lon_ref = Value(lon)
            distance_expr = 3959 * ACos(
                Cos(Radians(lat_ref)) * Cos(Radians(F('pickup_latitude'))) *
                Cos(Radians(F('pickup_longitude')) - Radians(lon_ref)) +
                Sin(Radians(lat_ref)) * Sin(Radians(F('pickup_latitude')))
            )
            queryset = queryset.annotate(distance=distance_expr).order_by('distance')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def filter_queryset(self, queryset):
        status_filter = self.request.query_params.get('status')
        rider_email = self.request.query_params.get('rider_email')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if rider_email:
            queryset = queryset.filter(id_rider__email=rider_email)
        return queryset


TRIP_REPORT_SQL = """
    SELECT
        strftime('%Y-%m', re_pickup.created_at) AS month,
        d.first_name || ' ' || substr(d.last_name, 1, 1) AS driver,
        COUNT(*) AS count_of_trips_over_1hr
    FROM rides_ride r
    INNER JOIN rides_ride_event re_pickup
        ON r.id_ride = re_pickup.id_ride
        AND re_pickup.description = 'Status changed to pickup'
    INNER JOIN rides_ride_event re_dropoff
        ON r.id_ride = re_dropoff.id_ride
        AND re_dropoff.description = 'Status changed to dropoff'
    INNER JOIN rides_user d
        ON r.id_driver = d.id_user
    WHERE (julianday(re_dropoff.created_at) - julianday(re_pickup.created_at)) * 24 > 1
    GROUP BY month, d.id_user, d.first_name, d.last_name
    ORDER BY month, driver
"""


@api_view(['GET'])
@permission_classes([IsAdminRole])
def trip_report(request):
    with connection.cursor() as cursor:
        cursor.execute(TRIP_REPORT_SQL)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
    return Response([dict(zip(columns, row)) for row in rows])
