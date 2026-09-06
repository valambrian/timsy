from datetime import date, datetime, timezone as dt_timezone
from unittest.mock import patch

from django.test import SimpleTestCase

from timsy.reports.utils import local_today


class LocalTodayTests(SimpleTestCase):
    """Calendar today follows Eastern, not Django TIME_ZONE (UTC)."""

    def test_late_evening_eastern_is_still_that_calendar_date(self):
        # 10 PM EDT on 2026-09-05 is 02:00 UTC on 2026-09-06.
        frozen = datetime(2026, 9, 6, 2, 0, tzinfo=dt_timezone.utc)
        with patch('django.utils.timezone.now', return_value=frozen):
            self.assertEqual(local_today(), date(2026, 9, 5))

    def test_after_eastern_midnight_is_the_next_calendar_date(self):
        # 12:30 AM EDT on 2026-09-06 is 04:30 UTC on 2026-09-06.
        frozen = datetime(2026, 9, 6, 4, 30, tzinfo=dt_timezone.utc)
        with patch('django.utils.timezone.now', return_value=frozen):
            self.assertEqual(local_today(), date(2026, 9, 6))
