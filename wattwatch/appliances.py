"""Appliances, saving plan and savings estimate.

Energy used by an appliance per day (kWh = units):
    watts x quantity x hours per day / 1000

Saving plan (greedy): to save a given number of units per day, cut hours
from the most power-hungry non-essential appliances first, because every
hour cut there saves the most units. Each appliance is cut by at most a
fraction of its hours (default 50%) so the plan stays practical.
"""

import math
from dataclasses import dataclass

from .tariff import calculate_bill

# name: (typical watts, typical hours/day, essential?)
# Wattages are rough typical values; the real figure is on the appliance's
# label and can be edited in the app.
APPLIANCE_CATALOG = {
    "Air conditioner (1.5 ton)": (1500, 6, False),
    "Water heater (geyser)": (2000, 1, False),
    "Motor pump (1 HP)": (750, 1, False),
    "Refrigerator": (100, 24, True),
    "Ceiling fan": (75, 10, False),
    "LED bulb": (10, 6, False),
    "Tube light": (40, 6, False),
    "Television": (100, 5, False),
    "Washing machine": (500, 1, False),
    "Iron box": (1000, 0.5, False),
    "Mixer grinder": (500, 0.5, True),
    "Microwave oven": (1200, 0.5, False),
    "Desktop computer": (150, 4, False),
    "Wi-Fi router": (10, 24, True),
}


@dataclass(frozen=True)
class Appliance:
    name: str
    watts: float
    hours_per_day: float
    quantity: int = 1
    essential: bool = False  # essential appliances are never cut

    @property
    def kw(self):
        return self.watts * self.quantity / 1000

    @property
    def daily_kwh(self):
        return self.kw * self.hours_per_day


@dataclass(frozen=True)
class Suggestion:
    name: str
    current_hours: float
    suggested_hours: float
    daily_kwh_saved: float

    @property
    def hours_cut(self):
        return self.current_hours - self.suggested_hours


@dataclass(frozen=True)
class SavingPlan:
    suggestions: list[Suggestion]
    target_daily_kwh: float
    daily_kwh_saved: float

    @property
    def target_met(self):
        return self.daily_kwh_saved >= self.target_daily_kwh - 1e-9


@dataclass(frozen=True)
class Savings:
    units_saved: float
    money_saved: float
    co2_saved_kg: float
    new_projected_units: float
    new_projected_bill: float


def _floor_to(x, step):
    return math.floor(x / step + 1e-9) * step


def _ceil_to(x, step):
    return math.ceil(x / step - 1e-9) * step


def make_saving_plan(appliances, target_daily_kwh, max_cut_fraction=0.5, step_hours=0.5):
    """Suggest hour cuts that save about `target_daily_kwh` units per day."""
    remaining = target_daily_kwh
    suggestions = []
    candidates = [a for a in appliances if not a.essential and a.hours_per_day > 0 and a.kw > 0]
    for app in sorted(candidates, key=lambda a: a.kw, reverse=True):
        if remaining <= 1e-9:
            break
        max_cut = _floor_to(app.hours_per_day * max_cut_fraction, step_hours)
        needed = _ceil_to(remaining / app.kw, step_hours)
        cut = min(max_cut, needed)
        if cut <= 0:
            continue
        saved = cut * app.kw
        remaining -= saved
        suggestions.append(Suggestion(app.name, app.hours_per_day, app.hours_per_day - cut, saved))
    total = sum(s.daily_kwh_saved for s in suggestions)
    return SavingPlan(suggestions, target_daily_kwh, total)


def estimate_savings(plan, days_left, projected_units, tariff, emission_factor):
    """Units, money and CO2 saved if the plan is followed for the rest of the cycle."""
    units_saved = min(plan.daily_kwh_saved * days_left, projected_units)
    new_units = projected_units - units_saved
    new_bill = calculate_bill(new_units, tariff)
    return Savings(
        units_saved=units_saved,
        money_saved=calculate_bill(projected_units, tariff) - new_bill,
        co2_saved_kg=units_saved * emission_factor,
        new_projected_units=new_units,
        new_projected_bill=new_bill,
    )
