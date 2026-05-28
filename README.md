# Wingz Ride Management API

A Django REST Framework API for managing ride information, built as part of the Wingz Software Engineer assessment.

## Setup

```bash
# Clone the repository
git clone <repo-url>
cd wingz_assessment

# Create and activate a virtual environment (optional but recommended)
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create an admin user
python manage.py shell -c "from rides.models import User; User.objects.create_superuser(email='admin@wingz.com', password='changeme', first_name='Admin', last_name='User', role='admin')"

# Start the development server
python manage.py runserver
```

## API Endpoints

All endpoints require authentication with a user that has `role='admin'`.

### Users
- `GET /api/users/` — List users
- `POST /api/users/` — Create user
- `GET /api/users/{id}/` — Retrieve user
- `PUT /api/users/{id}/` — Update user
- `DELETE /api/users/{id}/` — Delete user

### Rides
- `GET /api/rides/` — List rides (paginated, filterable, sortable)
- `POST /api/rides/` — Create ride
- `GET /api/rides/{id}/` — Retrieve ride (includes rider, driver, and today's ride events)
- `PUT /api/rides/{id}/` — Update ride
- `DELETE /api/rides/{id}/` — Delete ride

#### Ride List Query Parameters

| Parameter     | Type   | Description                                   |
|---------------|--------|-----------------------------------------------|
| `status`      | str    | Filter by ride status (e.g., `en-route`, `pickup`, `dropoff`) |
| `rider_email` | str    | Filter by rider email                         |
| `sort_by`     | str    | Sort field: `pickup_time` or `distance`       |
| `order`       | str    | Sort order: `asc` (default) or `desc` (for `pickup_time` only) |
| `lat`         | float  | Reference latitude (required when `sort_by=distance`) |
| `lon`         | float  | Reference longitude (required when `sort_by=distance`) |
| `page`        | int    | Page number                                   |
| `page_size`   | int    | Items per page (default: 10, max: 100)        |

### Ride Events
- `GET /api/ride-events/` — List ride events
- `POST /api/ride-events/` — Create ride event
- `GET /api/ride-events/{id}/` — Retrieve ride event
- `PUT /api/ride-events/{id}/` — Update ride event
- `DELETE /api/ride-events/{id}/` — Delete ride event

### Authentication
Login via the browsable API: `GET /api-auth/login/` or use HTTP Basic Auth.

## Performance Design

The Ride List API is optimized for large tables:

- **`select_related('id_rider', 'id_driver')`** — Fetches rider and driver in a single JOIN, avoiding N+1 queries.
- **`Prefetch` with filtered queryset** — Only loads RideEvents from the last 24 hours into `todays_ride_events`, instead of loading all events and filtering in Python.
- **Total queries: 3** — 1 for the ride list (with JOINs), 1 for the prefetched RideEvents, 1 for the pagination COUNT.

## SQL Bonus: Trips Longer Than 1 Hour

```sql
SELECT
    strftime('%Y-%m', re_pickup.created_at) AS month,
    d.first_name || ' ' || substr(d.last_name, 1, 1) || '.' AS driver,
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
ORDER BY month, driver;
```

## Design Decisions

- **Custom User model**: Implemented as `AbstractBaseUser` subclass to match the specified schema exactly (`id_user` PK, `role`, `email`, etc.) while integrating with Django's auth system.
- **SQLite for development**: Uses SQLite for simplicity. In production, PostgreSQL would be recommended.
- **Distance sorting**: Uses the Haversine formula via Django ORM database functions, which are supported in SQLite through Django's registered math functions. This keeps sorting at the database level, avoiding loading all rows into Python.
- **`todays_ride_events` as a non-model attribute**: Prefetched into a `to_attr` list rather than stored in the database. The serializer reads this attribute directly.
