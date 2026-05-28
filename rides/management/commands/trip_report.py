from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Report: count of trips > 1hr grouped by month and driver'

    def handle(self, *args, **options):
        sql = """
            SELECT
                strftime('%%Y-%%m', re_pickup.created_at) AS month,
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
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

        if not rows:
            self.stdout.write(self.style.WARNING('No trips over 1 hour found.'))
            return

        self.stdout.write(f"{'Month':<12} {'Driver':<12} {'Count':<6}")
        self.stdout.write('-' * 30)
        for row in rows:
            self.stdout.write(f"{row[0]:<12} {row[1]:<12} {row[2]:<6}")
