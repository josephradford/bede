from datetime import date

import pytest

from bede_core.time_tools import build_time_tools
from bede_core.vault_tools import Vault, build_vault_tools

TODAY = date(2026, 11, 23)  # a Monday


@pytest.fixture
def tools():
    built = build_time_tools(today=lambda: TODAY)
    return {fn.__name__: fn for fn in built}


def test_exposes_three_named_tools(tools):
    assert set(tools) == {"calculate_date", "days_between", "find_weekday"}


def test_add_days(tools):
    assert (
        tools["calculate_date"](3, "days", "2026-11-23")
        == "Thursday, 26 November 2026 (2026-11-26)"
    )


def test_defaults_to_today(tools):
    assert tools["calculate_date"](0) == "Monday, 23 November 2026 (2026-11-23)"


def test_weeks_and_negative_offsets(tools):
    assert (
        tools["calculate_date"](-2, "weeks") == "Monday, 9 November 2026 (2026-11-09)"
    )


def test_rolls_over_the_year(tools):
    assert (
        tools["calculate_date"](5, "days", "2026-12-30")
        == "Monday, 4 January 2027 (2027-01-04)"
    )


def test_month_end_clamps_to_last_day(tools):
    assert (
        tools["calculate_date"](1, "months", "2026-01-31")
        == "Saturday, 28 February 2026 (2026-02-28)"
    )


def test_leap_year_month_end(tools):
    assert (
        tools["calculate_date"](1, "months", "2028-01-31")
        == "Tuesday, 29 February 2028 (2028-02-29)"
    )


def test_years_from_a_leap_day_clamps(tools):
    assert (
        tools["calculate_date"](1, "years", "2028-02-29")
        == "Wednesday, 28 February 2029 (2029-02-28)"
    )


def test_bad_unit_and_bad_date_return_errors_not_exceptions(tools):
    assert tools["calculate_date"](1, "fortnights").startswith("Error:")
    assert tools["calculate_date"](1, "days", "next tuesday").startswith("Error:")
    assert tools["days_between"]("2026-13-45").startswith("Error:")
    assert tools["find_weekday"]("blursday").startswith("Error:")


def test_days_between_counts_forward_and_back(tools):
    assert tools["days_between"]("2026-11-23", "2026-12-25") == "32 days"
    assert tools["days_between"]("2026-12-25", "2026-11-23") == "-32 days"
    assert tools["days_between"]("2026-11-24") == "-1 day"


def test_find_weekday_next_and_last(tools):
    assert (
        tools["find_weekday"]("tuesday", "last")
        == "Tuesday, 17 November 2026 (2026-11-17)"
    )
    assert (
        tools["find_weekday"]("tuesday", "next")
        == "Tuesday, 24 November 2026 (2026-11-24)"
    )


def test_find_weekday_on_that_weekday_skips_to_the_following_one(tools):
    # Today is Monday: "next Monday" is a week away, "last Monday" a week back.
    assert (
        tools["find_weekday"]("monday", "next")
        == "Monday, 30 November 2026 (2026-11-30)"
    )
    assert (
        tools["find_weekday"]("monday", "last")
        == "Monday, 16 November 2026 (2026-11-16)"
    )


def test_find_weekday_accepts_a_start_date_and_abbreviations(tools):
    assert (
        tools["find_weekday"]("fri", "next", "2026-11-27")
        == "Friday, 4 December 2026 (2026-12-04)"
    )


def test_tool_names_do_not_collide_with_vault_tools(tmp_path):
    vault_names = [f.__name__ for f in build_vault_tools(Vault(str(tmp_path)))]
    time_names = [f.__name__ for f in build_time_tools()]
    assert not set(vault_names) & set(time_names)
