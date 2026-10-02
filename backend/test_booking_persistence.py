import tempfile
import unittest
from pathlib import Path

from app.routers import booking, transport


class BookingPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "travelmate.db"
        booking.DATABASE_PATH = str(self.db_path)
        booking.init_db()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_booking_persists_to_database(self):
        booking_record = booking.create_booking_record("user-123", "bus-1", 2)

        self.assertEqual(booking_record["status"], "pending")
        self.assertEqual(booking_record["seats"], 2)
        self.assertIsNotNone(booking.get_booking(booking_record["booking_id"]))
        self.assertEqual(len(booking.bookings_for_user("user-123")), 1)

    def test_status_updates_are_persisted(self):
        booking_record = booking.create_booking_record("user-456", "train-2", 1)

        booking.update_booking_status(booking_record["booking_id"], "paid")
        saved = booking.get_booking(booking_record["booking_id"])

        self.assertEqual(saved["status"], "paid")

    def test_booking_tracks_trip_details_for_history(self):
        booking_record = booking.create_booking_record(
            "user-789",
            "flight-9",
            2,
            source="Bengaluru",
            destination="Hyderabad",
            date="2026-10-15",
            amount=4200,
            provider="Air India",
            transport_type="flight",
        )

        saved = booking.get_booking(booking_record["booking_id"])
        self.assertEqual(saved["source"], "Bengaluru")
        self.assertEqual(saved["destination"], "Hyderabad")
        self.assertEqual(saved["amount"], 4200)
        self.assertEqual(saved["provider"], "Air India")

    def test_clear_history_removes_all_bookings(self):
        booking.create_booking_record("user-100", "bus-1", 1, source="Delhi", destination="Jaipur", date="2026-10-20", amount=800)
        booking.create_booking_record("user-101", "train-2", 2, source="Mumbai", destination="Pune", date="2026-10-21", amount=1200)

        booking.clear_all_bookings()

        self.assertEqual(len(booking.bookings_for_user()), 0)


class TransportPricingTests(unittest.TestCase):
    def test_search_uses_route_distance_to_adjust_fares(self):
        nearby = transport.search("Bengaluru", "Hyderabad", "2026-10-10", transport="bus")
        far = transport.search("Bengaluru", "Delhi", "2026-10-10", transport="bus")

        nearby_item = next(item for item in nearby if item.id == "bus-1")
        far_item = next(item for item in far if item.id == "bus-1")

        self.assertNotEqual(nearby_item.fare, far_item.fare)
        self.assertGreater(far_item.fare, nearby_item.fare)

    def test_transport_type_and_time_factors_change_fare(self):
        bus_price = transport.calculate_trip_fare(420.0, "bus", "06:45", "2026-10-10", 570)
        flight_price = transport.calculate_trip_fare(420.0, "flight", "06:45", "2026-10-10", 570)
        off_peak_price = transport.calculate_trip_fare(420.0, "bus", "14:00", "2026-10-10", 570)

        self.assertGreater(flight_price, bus_price)
        self.assertGreater(bus_price, off_peak_price)

    def test_early_booking_discount_applies(self):
        regular = transport.calculate_trip_fare(1000.0, "train", "08:00", "2026-10-10", 500)
        early = transport.calculate_trip_fare(1000.0, "train", "08:00", "2026-12-30", 500)

        self.assertLess(early, regular)

    def test_weekend_surcharge_applies(self):
        weekday = transport.calculate_trip_fare(1000.0, "bus", "10:00", "2026-10-05", 500)
        weekend = transport.calculate_trip_fare(1000.0, "bus", "10:00", "2026-10-03", 500)

        self.assertGreater(weekend, weekday)

    def test_seat_class_and_discount_modifiers_apply(self):
        standard = transport.calculate_trip_fare(1000.0, "flight", "10:00", "2026-10-05", 500, seat_class="economy")
        premium = transport.calculate_trip_fare(1000.0, "flight", "10:00", "2026-10-05", 500, seat_class="premium")
        discounted = transport.calculate_trip_fare(1000.0, "train", "10:00", "2026-10-05", 500, discount_code="SAVE10")

        self.assertGreater(premium, standard)
        self.assertLess(discounted, standard)


if __name__ == "__main__":
    unittest.main()
