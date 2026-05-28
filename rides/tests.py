from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from .models import Ride, RideEvent, User


class AdminAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@test.com', password='admin123',
            first_name='Admin', last_name='User', role='admin'
        )
        self.rider = User.objects.create_user(
            email='rider@test.com', password='rider123',
            first_name='Rider', last_name='Test', role='rider'
        )

    def test_admin_can_access(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('ride-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_admin_cannot_access(self):
        self.client.force_authenticate(user=self.rider)
        response = self.client.get(reverse('ride-list'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_access(self):
        response = self.client.get(reverse('ride-list'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RideAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@test.com', password='admin123',
            first_name='Admin', last_name='User', role='admin'
        )
        self.rider1 = User.objects.create_user(
            email='rider1@test.com', password='test123',
            first_name='Rider1', last_name='Test', role='rider'
        )
        self.rider2 = User.objects.create_user(
            email='rider2@test.com', password='test123',
            first_name='Rider2', last_name='Test', role='rider'
        )
        self.client.force_authenticate(user=self.admin)

        self.ride1 = Ride.objects.create(
            status='en-route',
            id_rider=self.rider1,
            id_driver=self.admin,
            pickup_latitude=37.7749,
            pickup_longitude=-122.4194,
            dropoff_latitude=37.7849,
            dropoff_longitude=-122.4094,
            pickup_time='2026-05-28T10:00:00Z'
        )
        self.ride2 = Ride.objects.create(
            status='pickup',
            id_rider=self.rider2,
            id_driver=self.admin,
            pickup_latitude=37.8049,
            pickup_longitude=-122.4094,
            dropoff_latitude=37.8149,
            dropoff_longitude=-122.3994,
            pickup_time='2026-05-28T12:00:00Z'
        )

    def test_list_rides(self):
        response = self.client.get(reverse('ride-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_filter_by_status(self):
        response = self.client.get(reverse('ride-list'), {'status': 'pickup'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['status'], 'pickup')

    def test_filter_by_rider_email(self):
        response = self.client.get(reverse('ride-list'), {'rider_email': 'rider1@test.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(
            response.data['results'][0]['rider']['email'], 'rider1@test.com'
        )

    def test_sort_by_pickup_time_asc(self):
        response = self.client.get(reverse('ride-list'), {'sort_by': 'pickup_time'})
        times = [r['pickup_time'] for r in response.data['results']]
        self.assertEqual(times, sorted(times))

    def test_sort_by_pickup_time_desc(self):
        response = self.client.get(
            reverse('ride-list'), {'sort_by': 'pickup_time', 'order': 'desc'}
        )
        times = [r['pickup_time'] for r in response.data['results']]
        self.assertEqual(times, sorted(times, reverse=True))

    def test_sort_by_distance(self):
        response = self.client.get(
            reverse('ride-list'),
            {'sort_by': 'distance', 'lat': '37.8000', 'lon': '-122.4500'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_sort_by_distance_missing_params(self):
        response = self.client.get(reverse('ride-list'), {'sort_by': 'distance'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pagination(self):
        for _ in range(15):
            Ride.objects.create(
                status='en-route',
                id_rider=self.rider1,
                id_driver=self.admin,
                pickup_latitude=37.7749,
                pickup_longitude=-122.4194,
                dropoff_latitude=37.7849,
                dropoff_longitude=-122.4094,
                pickup_time='2026-05-28T10:00:00Z'
            )
        response = self.client.get(reverse('ride-list'))
        self.assertEqual(len(response.data['results']), 10)
        self.assertIsNotNone(response.data['next'])

    def test_ride_detail_includes_relations(self):
        RideEvent.objects.create(
            id_ride=self.ride1,
            description='Status changed to pickup',
            created_at=timezone.now()
        )
        response = self.client.get(
            reverse('ride-detail', args=[self.ride1.id_ride])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('rider', response.data)
        self.assertIn('driver', response.data)
        self.assertIn('todays_ride_events', response.data)


class RideEventPerformanceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@test.com', password='admin123',
            first_name='Admin', last_name='User', role='admin'
        )
        self.rider = User.objects.create_user(
            email='rider@test.com', password='test123',
            first_name='Rider', last_name='Test', role='rider'
        )
        self.client.force_authenticate(user=self.admin)

        self.ride = Ride.objects.create(
            status='en-route',
            id_rider=self.rider,
            id_driver=self.admin,
            pickup_latitude=37.7749,
            pickup_longitude=-122.4194,
            dropoff_latitude=37.7849,
            dropoff_longitude=-122.4094,
            pickup_time='2026-05-28T10:00:00Z'
        )
        RideEvent.objects.create(
            id_ride=self.ride,
            description='Status changed to pickup',
            created_at=timezone.now() - timedelta(hours=2)
        )
        RideEvent.objects.create(
            id_ride=self.ride,
            description='Status changed to dropoff',
            created_at=timezone.now() - timedelta(hours=48)
        )

    def test_todays_ride_events_only_last_24h(self):
        response = self.client.get(reverse('ride-list'))
        events = response.data['results'][0]['todays_ride_events']
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['description'], 'Status changed to pickup')

    def test_query_count(self):
        from django.db import connection
        with self.assertNumQueries(3):
            response = self.client.get(reverse('ride-list'))
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class UserAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@test.com', password='admin123',
            first_name='Admin', last_name='User', role='admin'
        )
        self.client.force_authenticate(user=self.admin)

    def test_list_users(self):
        response = self.client.get(reverse('user-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_user(self):
        data = {
            'email': 'new@test.com',
            'password': 'test123',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'driver',
            'phone_number': '555-1234'
        }
        response = self.client.post(reverse('user-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 2)


class RideEventAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@test.com', password='admin123',
            first_name='Admin', last_name='User', role='admin'
        )
        self.client.force_authenticate(user=self.admin)

    def test_list_ride_events(self):
        response = self.client.get(reverse('rideevent-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
