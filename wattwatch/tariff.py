"""Slab-based (telescopic) electricity bill calculator.

Example with slabs 0-100 free, 101-400 at Rs 4.80, 401-500 at Rs 6.45:
a 450-unit bill is   100 x 0      (first slab)
                   + 300 x 4.80   (units 101-400)
                   +  50 x 6.45   (units 401-450)
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Slab:
    upto: float  # upper limit of the slab in units (inclusive); math.inf for the last slab
    rate: float  # Rs per unit


@dataclass(frozen=True)
class SlabCharge:
    start: float  # units already billed before this slab
    end: float  # slab upper limit
    units: float  # units of this bill that fall in the slab
    rate: float
    amount: float


@dataclass(frozen=True)
class Tariff:
    slabs: tuple[Slab, ...]
    fixed_charge: float = 0.0

    def __post_init__(self):
        if not self.slabs:
            raise ValueError("Tariff needs at least one slab.")
        previous = 0.0
        for slab in self.slabs:
            if slab.upto <= previous:
                raise ValueError("Slab limits must be positive and strictly increasing.")
            if slab.rate < 0:
                raise ValueError("Slab rates cannot be negative.")
            previous = slab.upto
        if not math.isinf(self.slabs[-1].upto):
            raise ValueError("The last slab must have no upper limit.")

    @classmethod
    def from_rows(cls, rows, fixed_charge=0.0):
        """Build a tariff from (upto, rate) pairs. A missing/NaN limit means 'no limit'."""
        slabs = []
        for upto, rate in rows:
            if upto is None or math.isnan(float(upto)):
                upto = math.inf
            slabs.append(Slab(float(upto), float(rate)))
        return cls(tuple(slabs), float(fixed_charge))

    @property
    def boundaries(self):
        """Finite slab limits, e.g. [100, 400, 500, ...]."""
        return [s.upto for s in self.slabs if not math.isinf(s.upto)]


def slab_breakdown(units, tariff):
    """Split `units` across the slabs and price each part."""
    if units < 0:
        raise ValueError("Units cannot be negative.")
    charges = []
    lower = 0.0
    for slab in tariff.slabs:
        if units <= lower:
            break
        in_slab = min(units, slab.upto) - lower
        charges.append(SlabCharge(lower, slab.upto, in_slab, slab.rate, in_slab * slab.rate))
        lower = slab.upto
    return charges


def calculate_bill(units, tariff):
    """Total bill in Rs for `units` consumed in one billing cycle."""
    energy = sum(c.amount for c in slab_breakdown(units, tariff))
    return round(energy + tariff.fixed_charge, 2)


def slab_index(units, tariff):
    """Index of the slab that the `units`-th unit falls in."""
    for i, slab in enumerate(tariff.slabs):
        if units <= slab.upto:
            return i
    return len(tariff.slabs) - 1  # unreachable: last slab is infinite


def marginal_rate(units, tariff):
    """Price of the next unit at this consumption level."""
    return tariff.slabs[slab_index(units, tariff)].rate
