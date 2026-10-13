"""Meter readings and units used in the current billing cycle.

A cycle starts at the reading printed on the last bill. Every new reading
the user adds (typed or scanned) is stored with its date, and the units
used so far is simply   latest reading - starting reading.
"""

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class Reading:
    day: date
    value: float  # meter reading in kWh (units)


@dataclass
class Cycle:
    start_date: date
    start_reading: float
    length_days: int = 60
    readings: list[Reading] = field(default_factory=list)

    def points(self):
        """All readings in date order, starting with the cycle-start reading."""
        start = Reading(self.start_date, self.start_reading)
        return [start] + sorted(self.readings, key=lambda r: r.day)

    def latest(self):
        return self.points()[-1]

    def units_used(self):
        return self.latest().value - self.start_reading

    def add_reading(self, day, value):
        """Add (or replace) the reading for `day`, checking it makes sense."""
        if day <= self.start_date:
            raise ValueError("Reading date must be after the cycle start date.")
        others = [p for p in self.points() if p.day != day]
        before = [p for p in others if p.day < day]
        after = [p for p in others if p.day > day]
        # A meter only counts up, so readings must never go down over time.
        if before and value < before[-1].value:
            raise ValueError(
                f"Reading {value:g} is lower than the earlier reading "
                f"{before[-1].value:g} on {before[-1].day}."
            )
        if after and value > after[0].value:
            raise ValueError(
                f"Reading {value:g} is higher than the later reading "
                f"{after[0].value:g} on {after[0].day}."
            )
        self.readings = [r for r in self.readings if r.day != day] + [Reading(day, value)]

    def remove_reading(self, day):
        self.readings = [r for r in self.readings if r.day != day]

    def usage_table(self):
        """Rows describing usage between consecutive readings."""
        rows = []
        points = self.points()
        for prev, curr in zip(points, points[1:]):
            days = (curr.day - prev.day).days
            units = curr.value - prev.value
            rows.append({
                "Date": curr.day,
                "Reading": curr.value,
                "Units since previous": units,
                "Days": days,
                "Units per day": round(units / days, 2),
                "Units since cycle start": curr.value - self.start_reading,
            })
        return rows


def save_cycle(cycle, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "start_date": cycle.start_date.isoformat(),
        "start_reading": cycle.start_reading,
        "length_days": cycle.length_days,
        "readings": [{"day": r.day.isoformat(), "value": r.value} for r in cycle.readings],
    }
    path.write_text(json.dumps(data, indent=2))


def load_cycle(path):
    """Load the saved cycle, or return None if nothing has been saved yet."""
    path = Path(path)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return Cycle(
        start_date=date.fromisoformat(data["start_date"]),
        start_reading=float(data["start_reading"]),
        length_days=int(data["length_days"]),
        readings=[Reading(date.fromisoformat(r["day"]), float(r["value"])) for r in data["readings"]],
    )
