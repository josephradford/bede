from bede_data.tz import utc_to_local


class TestUtcToLocal:
    def test_converts_z_suffix(self):
        result = utc_to_local("2026-04-29T08:00:00Z", "Australia/Sydney")
        assert result == "2026-04-29T18:00:00"

    def test_converts_no_tz_suffix_assumes_utc(self):
        result = utc_to_local("2026-04-29 08:00:00", "Australia/Sydney")
        assert result == "2026-04-29T18:00:00"

    def test_converts_utc_offset_suffix(self):
        result = utc_to_local("2026-04-29T08:00:00+00:00", "Australia/Sydney")
        assert result == "2026-04-29T18:00:00"

    def test_crosses_day_boundary(self):
        result = utc_to_local("2026-04-29T20:00:00Z", "Australia/Sydney")
        assert result == "2026-04-30T06:00:00"

    def test_different_timezone(self):
        result = utc_to_local("2026-04-29T08:00:00Z", "US/Eastern")
        assert result == "2026-04-29T04:00:00"

    def test_returns_none_for_none(self):
        assert utc_to_local(None, "Australia/Sydney") is None

    def test_returns_empty_for_empty(self):
        assert utc_to_local("", "Australia/Sydney") == ""

    def test_passes_through_invalid_string(self):
        assert utc_to_local("not-a-date", "Australia/Sydney") == "not-a-date"

    def test_non_utc_input_still_converts(self):
        result = utc_to_local("2026-04-29T18:00:00+10:00", "Australia/Sydney")
        assert result == "2026-04-29T18:00:00"
