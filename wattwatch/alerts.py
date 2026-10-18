"""Early warning when usage is heading into a costlier slab.

If the projected units for the cycle go past one or more slab limits that
have not been reached yet, we warn the user and work out:
  - the nearest limit below the projection (the cheapest one to stay under),
  - how many units must be cut to stay under it,
  - roughly how many days until the next limit is crossed at today's pace.
"""

from dataclasses import dataclass

from .tariff import calculate_bill, slab_index

SAFE, WARNING, CRITICAL = "safe", "warning", "critical"


@dataclass(frozen=True)
class SlabAlert:
    level: str
    message: str
    target_units: float | None  # stay at or below this to avoid the jump
    units_to_cut: float
    days_until_cross: float | None
    money_at_stake: float  # projected bill minus bill at target_units


def check_slab_alert(prediction, tariff, critical_days=7):
    p = prediction
    crossing = [b for b in tariff.boundaries if p.units_so_far < b < p.projected_units]

    if not crossing:
        limit = tariff.slabs[slab_index(p.projected_units, tariff)].upto
        limit_text = "the top slab" if limit == float("inf") else f"the slab up to {limit:g} units"
        return SlabAlert(
            level=SAFE,
            message=f"On track: projected {p.projected_units:.0f} units stays within {limit_text}.",
            target_units=None,
            units_to_cut=0.0,
            days_until_cross=None,
            money_at_stake=0.0,
        )

    next_limit = crossing[0]
    target = crossing[-1]
    units_to_cut = p.projected_units - target
    days_until = (next_limit - p.units_so_far) / p.daily_rate if p.daily_rate > 0 else None
    money = calculate_bill(p.projected_units, tariff) - calculate_bill(target, tariff)

    critical = len(crossing) > 1 or (days_until is not None and days_until <= critical_days)
    when = f" in about {days_until:.0f} days" if days_until is not None else ""
    message = (
        f"At your current pace you will cross {next_limit:g} units{when} and finish the cycle "
        f"at about {p.projected_units:.0f} units. Cut about {units_to_cut:.0f} units to stay "
        f"at or below {target:g} units and save about Rs {money:.0f}."
    )
    return SlabAlert(
        level=CRITICAL if critical else WARNING,
        message=message,
        target_units=target,
        units_to_cut=units_to_cut,
        days_until_cross=days_until,
        money_at_stake=money,
    )
