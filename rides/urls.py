from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'rides', views.RideViewSet)
router.register(r'ride-events', views.RideEventViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('reports/trips-over-1hr/', views.trip_report, name='trip-report'),
]
