"""Predict the units and bill for the whole billing cycle.

The meter reading grows roughly in a straight line over time, so the slope
of that line (units per day) is the household's usage rate. With 3 or more
recent readings we fit the line with least squares (numpy.polyfit), which
smooths out a single unusual day; with exactly 2 readings the slope is just
(difference in reading) / (difference in days).

    projected units = units so far + usage rate x days left in the cycle
"""

from dataclasses import dataclass

import numpy as np

from .tariff import calculate_bill


@dataclass(frozen=True)
class Prediction:
    units_so_far: float
    days_elapsed: int
    days_left: int
    daily_rate: float
    projected_units: float
    current_bill: float
    projected_bill: float


def daily_usage_rate(points, recent=5):
    """Units per day estimated from the last `recent` readings."""
    points = sorted(points, key=lambda r: r.day)[-recent:]
    if len(points) < 2:
        raise ValueError("Need at least two readings to estimate usage.")
    first_day = points[0].day
    x = np.array([(p.day - first_day).days for p in points], dtype=float)
    y = np.array([p.value for p in points], dtype=float)
    if x[-1] == 0:
        raise ValueError("Readings must be on different days.")
    if len(points) == 2:
        slope = (y[1] - y[0]) / (x[1] - x[0])
    else:
        slope = np.polyfit(x, y, 1)[0]
    return max(float(slope), 0.0)


def predict_cycle(cycle, tariff, recent=5):
    """Project usage and bill to the end of `cycle` from its readings."""
    latest = cycle.latest()
    days_elapsed = (latest.day - cycle.start_date).days
    days_left = max(cycle.length_days - days_elapsed, 0)
    rate = daily_usage_rate(cycle.points(), recent=recent)
    units_so_far = cycle.units_used()
    projected = units_so_far + rate * days_left
    return Prediction(
        units_so_far=units_so_far,
        days_elapsed=days_elapsed,
        days_left=days_left,
        daily_rate=rate,
        projected_units=projected,
        current_bill=calculate_bill(units_so_far, tariff),
        projected_bill=calculate_bill(projected, tariff),
    )
