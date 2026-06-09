from datetime import date
from unittest import TestCase
from unittest.mock import MagicMock, patch

from modis_aerosol import extract_monthly


class ExtractMonthlyTests(TestCase):
    def test_rejects_invalid_coordinates(self):
        with self.assertRaisesRegex(ValueError, "Latitude"):
            extract_monthly(91, 23, date(2020, 1, 1), date(2020, 2, 1))

        with self.assertRaisesRegex(ValueError, "Longitude"):
            extract_monthly(42, 181, date(2020, 1, 1), date(2020, 2, 1))

    def test_rejects_reversed_dates(self):
        with self.assertRaisesRegex(ValueError, "Start date"):
            extract_monthly(42, 23, date(2020, 2, 1), date(2020, 1, 1))

    @patch.dict("sys.modules", {"ee": MagicMock()})
    def test_rejects_unknown_platform(self):
        with self.assertRaisesRegex(ValueError, "Unknown platform"):
            extract_monthly(
                42,
                23,
                date(2020, 1, 1),
                date(2020, 2, 1),
                platforms=["Unknown"],
            )
