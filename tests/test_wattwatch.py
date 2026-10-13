import math
from datetime import date, timedelta

import pytest

from wattwatch.alerts import CRITICAL, SAFE, WARNING, check_slab_alert
from wattwatch.appliances import Appliance, estimate_savings, make_saving_plan
from wattwatch.ocr import parse_reading
from wattwatch.predictor import daily_usage_rate, predict_cycle
from wattwatch.tariff import Tariff, calculate_bill, marginal_rate, slab_breakdown
from wattwatch.tracker import Cycle, Reading, load_cycle, save_cycle

# Simple tariff so the expected numbers are easy to check by hand.
TARIFF = Tariff.from_rows([(100, 0), (400, 5), (500, 10), (None, 20)])
START = date(2026, 1, 1)


# ---------- tariff ----------

def test_bill_is_telescopic():
    assert calculate_bill(0, TARIFF) == 0
    assert calculate_bill(100, TARIFF) == 0
    assert calculate_bill(400, TARIFF) == 300 * 5
    assert calculate_bill(450, TARIFF) == 300 * 5 + 50 * 10
    assert calculate_bill(600, TARIFF) == 300 * 5 + 100 * 10 + 100 * 20


def test_breakdown_and_marginal_rate():
    parts = slab_breakdown(450, TARIFF)
    assert [p.units for p in parts] == [100, 300, 50]
    assert marginal_rate(400, TARIFF) == 5  # slab limits are inclusive
    assert marginal_rate(401, TARIFF) == 10


def test_fixed_charge_added():
    t = Tariff.from_rows([(100, 1), (math.nan, 2)], fixed_charge=50)
    assert calculate_bill(150, t) == 100 + 100 + 50


@pytest.mark.parametrize("rows", [[], [(100, 1)], [(100, 1), (50, 2), (None, 3)], [(None, -1)]])
def test_invalid_tariffs_rejected(rows):
    with pytest.raises(ValueError):
        Tariff.from_rows(rows)


# ---------- tracker ----------

def test_cycle_tracks_units():
    cycle = Cycle(START, 1000)
    cycle.add_reading(START + timedelta(days=10), 1050)
    cycle.add_reading(START + timedelta(days=5), 1020)
    assert cycle.units_used() == 50
    rows = cycle.usage_table()
    assert [r["Units since previous"] for r in rows] == [20, 30]


def test_cycle_rejects_impossible_readings():
    cycle = Cycle(START, 1000)
    cycle.add_reading(START + timedelta(days=10), 1050)
    with pytest.raises(ValueError):
        cycle.add_reading(START + timedelta(days=12), 1040)  # meter went backwards
    with pytest.raises(ValueError):
        cycle.add_reading(START + timedelta(days=5), 1060)  # higher than a later reading
    with pytest.raises(ValueError):
        cycle.add_reading(START, 1010)  # not after cycle start


def test_cycle_save_and_load(tmp_path):
    cycle = Cycle(START, 1000, 60, [Reading(START + timedelta(days=3), 1012.5)])
    path = tmp_path / "cycle.json"
    save_cycle(cycle, path)
    assert load_cycle(path) == cycle
    assert load_cycle(tmp_path / "missing.json") is None


# ---------- predictor ----------

def test_rate_from_two_and_many_readings():
    two = [Reading(START, 0), Reading(START + timedelta(days=4), 20)]
    assert daily_usage_rate(two) == pytest.approx(5)
    many = [Reading(START + timedelta(days=d), 5 * d) for d in range(6)]
    assert daily_usage_rate(many) == pytest.approx(5)


def test_prediction_projects_to_cycle_end():
    cycle = Cycle(START, 1000, 60, [Reading(START + timedelta(days=20), 1160)])  # 8 units/day
    p = predict_cycle(cycle, TARIFF)
    assert p.days_left == 40
    assert p.projected_units == pytest.approx(160 + 8 * 40)
    assert p.projected_bill == calculate_bill(480, TARIFF)


# ---------- alerts ----------

def _prediction(units_so_far, rate, days_left):
    cycle = Cycle(START, 0, 60)
    elapsed = 60 - days_left
    cycle.add_reading(START + timedelta(days=elapsed), units_so_far)
    p = predict_cycle(cycle, TARIFF)
    assert p.daily_rate == pytest.approx(rate)
    return p


def test_alert_safe_when_staying_in_slab():
    alert = check_slab_alert(_prediction(150, 5, 30), TARIFF)  # projects 300
    assert alert.level == SAFE
    assert alert.units_to_cut == 0


def test_alert_warns_before_crossing():
    alert = check_slab_alert(_prediction(250, 6.25, 20), TARIFF, critical_days=7)  # projects 375
    assert alert.level == SAFE
    alert = check_slab_alert(_prediction(320, 8, 20), TARIFF, critical_days=7)  # projects 480
    assert alert.level == WARNING
    assert alert.target_units == 400
    assert alert.units_to_cut == pytest.approx(80)
    assert alert.days_until_cross == pytest.approx(10)
    assert alert.money_at_stake == pytest.approx(80 * 10)


def test_alert_critical_when_crossing_two_slabs():
    alert = check_slab_alert(_prediction(300, 10, 30), TARIFF)  # projects 600, crosses 400 and 500
    assert alert.level == CRITICAL
    assert alert.target_units == 500  # nearest limit below the projection


# ---------- appliances / saving plan ----------

APPLIANCES = [
    Appliance("AC", 1500, 6),
    Appliance("TV", 100, 5),
    Appliance("Fridge", 100, 24, essential=True),
]


def test_plan_cuts_biggest_appliance_first():
    plan = make_saving_plan(APPLIANCES, target_daily_kwh=1.5)
    assert [s.name for s in plan.suggestions] == ["AC"]
    assert plan.suggestions[0].hours_cut == 1.0
    assert plan.target_met


def test_plan_respects_cap_and_never_cuts_essentials():
    plan = make_saving_plan(APPLIANCES, target_daily_kwh=100, max_cut_fraction=0.5)
    assert {s.name for s in plan.suggestions} == {"AC", "TV"}
    ac = plan.suggestions[0]
    assert ac.suggested_hours == 3
    assert not plan.target_met


def test_savings_estimate():
    plan = make_saving_plan(APPLIANCES, target_daily_kwh=1.5)
    savings = estimate_savings(plan, days_left=20, projected_units=480, tariff=TARIFF, emission_factor=0.5)
    assert savings.units_saved == pytest.approx(30)
    assert savings.new_projected_units == pytest.approx(450)
    assert savings.money_saved == pytest.approx(30 * 10)
    assert savings.co2_saved_kg == pytest.approx(15)


# ---------- OCR parsing ----------

@pytest.mark.parametrize("text, expected", [
    ("12345", 12345),
    ("kWh 04521.7\n8", 4521.7),
    ("1 2 3 00987", 987),
    ("", None),
    ("no digits", None),
])
def test_parse_reading(text, expected):
    assert parse_reading(text) == expected
