"""Default settings for WATT-WATCH.

IMPORTANT: the tariff below is an EXAMPLE of the Tamil Nadu domestic
bi-monthly slab structure. Tariffs are revised from time to time, so check
the current tariff order from the Tamil Nadu Electricity Regulatory
Commission (TNERC) / your distribution company and update these numbers
(or edit them in the app sidebar) before trusting the bill estimates.
"""

import math

# Billing cycle length in days. Tamil Nadu bills domestic consumers
# every two months, so the default is 60 days.
DEFAULT_CYCLE_DAYS = 60

# Example slab table: (upper limit of the slab in units, rate in Rs/unit).
# Slabs are "telescopic": each unit is charged at the rate of the slab it
# falls in. The first 100 units are free for domestic consumers.
# math.inf marks the last, open-ended slab.
DEFAULT_SLABS = [
    (100, 0.00),
    (400, 4.80),
    (500, 6.45),
    (600, 8.55),
    (800, 9.65),
    (1000, 10.70),
    (math.inf, 11.80),
]

# Fixed charge added to every bill (Rs). Set to 0 by default.
DEFAULT_FIXED_CHARGE = 0.0

# kg of CO2 emitted per kWh from the Indian grid. Approximate value;
# check the latest CEA "CO2 Baseline Database" for the current figure.
DEFAULT_EMISSION_FACTOR = 0.71

# Warn as "critical" when the next slab will be crossed within this many days.
CRITICAL_DAYS = 7
