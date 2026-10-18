"""Sample households from "Household EB Meter Database" (fictional data).

The PDF lists one previous and one current reading per household but no
reading dates, so the dates below are ASSUMED for the demo: every sample
reading is treated as covering one 60-day billing period. Change them if
your sample period is different.
"""

from datetime import date

SAMPLE_PERIOD_START = date(2026, 8, 1)  # assumed date of "Previous Reading"
SAMPLE_PERIOD_END = date(2026, 9, 30)  # assumed date of "Current Reading"

# (House ID, Consumer No., Meter No., Household Name, Connection,
#  Previous Reading kWh, Current Reading kWh)
SAMPLE_HOUSEHOLDS = [
    ("H001", "EB10001", "MTR1001", "Arun", "Single phase", 1250, 1400),
    ("H002", "EB10002", "MTR1002", "Kumar", "Single phase", 2300, 2480),
    ("H003", "EB10003", "MTR1003", "Priya", "Single phase", 3400, 3520),
    ("H004", "EB10004", "MTR1004", "Ravi", "Three phase", 4500, 4750),
    ("H005", "EB10005", "MTR1005", "Divya", "Single phase", 1800, 1920),
    ("H006", "EB10006", "MTR1006", "Suresh", "Single phase", 5200, 5420),
    ("H007", "EB10007", "MTR1007", "Lakshmi", "Three phase", 6100, 6400),
    ("H008", "EB10008", "MTR1008", "Karthik", "Single phase", 2800, 2950),
    ("H009", "EB10009", "MTR1009", "Meena", "Single phase", 7200, 7350),
    ("H010", "EB10010", "MTR1010", "Vijay", "Single phase", 1500, 1680),
]
