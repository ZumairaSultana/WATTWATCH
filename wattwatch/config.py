"""Default settings for WATT-WATCH.

Tariff source: TNERC Suo-motu Tariff Order No. 6 of 2025, dated 30-06-2025,
effective 01-07-2025 (FY 2025-26), LT IA Domestic, bi-monthly slabs:
  - Commission-determined rates from 01-07-2025 (page 14, section 3.2.2):
      0-400: 4.95, 401-500: 6.65, 501-600: 8.80, 601-800: 9.95,
      801-1000: 11.05, above 1000: 12.15 Rs/unit; fixed charge: Nil.
  - The Government committed to "No tariff hike to the Domestic consumers
    (LT IA)" for one year and to compensate TNPDCL (page 12), so domestic
    consumers keep paying the previous FY 2024-25 rates, which are the
    rates used below.
  - The order says LT IA is "to be partly subsidised by the Government"
    but does not state the 100 free units; that comes from the Government
    subsidy and should be confirmed against a real bill.
The order says rates are adjusted again from 01-07-2026, so check for a
newer tariff order and update these numbers (or edit them in the app
sidebar) when one is issued.
"""

import math

# Billing cycle length in days. Tamil Nadu bills domestic consumers
# every two months, so the default is 60 days.
DEFAULT_CYCLE_DAYS = 60

# Slab table: (upper limit of the slab in units, rate in Rs/unit).
# Slabs are "telescopic": each unit is charged at the rate of the slab it
# falls in. The first 100 units are free (Government subsidy; see above).
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
