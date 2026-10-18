"""SQLite database for households, meter readings and bills.

Tables (see schema.sql): Household, EB_Meter, Electricity_Bill.

How a billing cycle is stored:
  - Each new meter reading adds one EB_Meter row going from the previous
    reading to the new one, so Units_Consumed = Current - Previous.
  - Rows with Bill_ID = NULL are the current, not-yet-billed cycle.
  - "Generate bill" adds up those rows' units into one Electricity_Bill row
    and stamps its Bill_ID on them. The next cycle starts from the last
    reading.
"""

import sqlite3
from datetime import date
from pathlib import Path

from .sample_data import SAMPLE_HOUSEHOLDS, SAMPLE_PERIOD_END, SAMPLE_PERIOD_START
from .tariff import calculate_bill
from .tracker import Cycle, Reading

SCHEMA_FILE = Path(__file__).with_name("schema.sql")
CONNECTION_TYPES = ("Single phase", "Three phase")
PAYMENT_STATUSES = ("Unpaid", "Pending", "Paid")


def connect(path):
    """Open the database (creating the folder if needed). Use ':memory:' for tests."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row  # rows behave like dicts: row["House_ID"]
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn, seed=True):
    """Create the tables if missing, and load the sample households into an empty database."""
    conn.executescript(SCHEMA_FILE.read_text())
    empty = conn.execute("SELECT COUNT(*) FROM Household").fetchone()[0] == 0
    if seed and empty:
        load_sample_data(conn)


def load_sample_data(conn):
    with conn:
        for house_id, consumer, meter, name, connection, previous, current in SAMPLE_HOUSEHOLDS:
            conn.execute(
                "INSERT INTO Household (House_ID, Consumer_Number, Household_Name, Connection_Type) "
                "VALUES (?, ?, ?, ?)",
                (house_id, consumer, name, connection),
            )
            _insert_reading(conn, house_id, meter, SAMPLE_PERIOD_START, previous,
                            SAMPLE_PERIOD_END, current)


def reset_to_sample_data(conn):
    """Delete everything and reload the sample households."""
    with conn:
        conn.execute("DELETE FROM EB_Meter")
        conn.execute("DELETE FROM Electricity_Bill")
        conn.execute("DELETE FROM Household")
    load_sample_data(conn)


# ---------- Households ----------

def add_household(conn, house_id, consumer_number, name, connection_type, address=None):
    if connection_type not in CONNECTION_TYPES:
        raise ValueError(f"Connection type must be one of {CONNECTION_TYPES}.")
    if not house_id.strip() or not consumer_number.strip() or not name.strip():
        raise ValueError("House ID, consumer number and name are required.")
    try:
        with conn:
            conn.execute(
                "INSERT INTO Household (House_ID, Consumer_Number, Household_Name, Address, Connection_Type) "
                "VALUES (?, ?, ?, ?, ?)",
                (house_id.strip(), consumer_number.strip(), name.strip(), address or None, connection_type),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError("A household with this House ID or consumer number already exists.") from exc


def list_households(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM Household ORDER BY House_ID")]


def next_house_id(conn):
    """Suggest the next ID in the H001, H002, ... pattern."""
    numbers = [int(r[0][1:]) for r in conn.execute("SELECT House_ID FROM Household")
               if r[0][:1] == "H" and r[0][1:].isdigit()]
    return f"H{max(numbers, default=0) + 1:03d}"


def households_overview(conn):
    """One row per household with its latest meter reading (like table 1 in the PDF)."""
    query = """
        SELECT h.House_ID, h.Consumer_Number, m.Meter_Number, h.Household_Name,
               h.Connection_Type, m.Previous_Reading, m.Current_Reading,
               m.Units_Consumed, m.Reading_Date
        FROM Household h
        LEFT JOIN EB_Meter m ON m.Meter_ID = (
            SELECT Meter_ID FROM EB_Meter
            WHERE House_ID = h.House_ID
            ORDER BY Reading_Date DESC, Meter_ID DESC LIMIT 1)
        ORDER BY h.House_ID
    """
    return [dict(r) for r in conn.execute(query)]


# ---------- Meter readings ----------

def _insert_reading(conn, house_id, meter_number, previous_date, previous, reading_date, current):
    conn.execute(
        "INSERT INTO EB_Meter (House_ID, Meter_Number, Previous_Reading, Current_Reading, "
        "Units_Consumed, Reading_Date, Previous_Reading_Date) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (house_id, meter_number, previous, current, current - previous,
         reading_date.isoformat(), previous_date.isoformat()),
    )


def readings(conn, house_id):
    """All EB_Meter rows of a household, oldest first."""
    rows = conn.execute(
        "SELECT * FROM EB_Meter WHERE House_ID = ? ORDER BY Reading_Date, Meter_ID", (house_id,)
    )
    return [dict(r) for r in rows]


def last_reading(conn, house_id):
    rows = readings(conn, house_id)
    return rows[-1] if rows else None


def start_tracking(conn, house_id, meter_number, start_date, start_reading, reading_date, reading):
    """First reading for a household that has none: needs the starting reading too."""
    if last_reading(conn, house_id) is not None:
        raise ValueError("This household already has readings. Use add_reading instead.")
    _check_reading(start_date, start_reading, reading_date, reading)
    if not meter_number.strip():
        raise ValueError("Meter number is required.")
    with conn:
        _insert_reading(conn, house_id, meter_number.strip(), start_date, start_reading,
                        reading_date, reading)


def add_reading(conn, house_id, reading_date, reading):
    """Add a new reading; the previous reading and meter number come from the last row."""
    last = last_reading(conn, house_id)
    if last is None:
        raise ValueError("No earlier reading for this household. Use start_tracking first.")
    previous_date = date.fromisoformat(last["Reading_Date"])
    _check_reading(previous_date, last["Current_Reading"], reading_date, reading)
    with conn:
        _insert_reading(conn, house_id, last["Meter_Number"], previous_date,
                        last["Current_Reading"], reading_date, reading)


def _check_reading(previous_date, previous, reading_date, reading):
    if reading_date <= previous_date:
        raise ValueError(f"Reading date must be after the previous reading date ({previous_date}).")
    if reading < previous:
        raise ValueError(f"Reading {reading:g} is lower than the previous reading {previous:g}. "
                         "A meter only counts up.")


def delete_last_reading(conn, house_id):
    """Undo the most recent reading, if it has not been billed yet."""
    last = last_reading(conn, house_id)
    if last is None:
        raise ValueError("There is no reading to delete.")
    if last["Bill_ID"] is not None:
        raise ValueError("The last reading is already part of a bill and can't be deleted.")
    with conn:
        conn.execute("DELETE FROM EB_Meter WHERE Meter_ID = ?", (last["Meter_ID"],))


# ---------- Current cycle ----------

def unbilled_readings(conn, house_id):
    return [r for r in readings(conn, house_id) if r["Bill_ID"] is None]


def current_cycle(conn, house_id, length_days):
    """Build the tracker's Cycle for the not-yet-billed readings (None if no readings at all)."""
    rows = readings(conn, house_id)
    if not rows:
        return None
    unbilled = [r for r in rows if r["Bill_ID"] is None]
    if not unbilled:
        # Everything is billed: a new cycle starts at the last reading.
        last = rows[-1]
        return Cycle(date.fromisoformat(last["Reading_Date"]), last["Current_Reading"], length_days)
    first = unbilled[0]
    return Cycle(
        start_date=date.fromisoformat(first["Previous_Reading_Date"]),
        start_reading=first["Previous_Reading"],
        length_days=length_days,
        readings=[Reading(date.fromisoformat(r["Reading_Date"]), r["Current_Reading"]) for r in unbilled],
    )


# ---------- Bills ----------

def generate_bill(conn, house_id, tariff):
    """Bill all unbilled readings of a household. Returns the new Bill_ID."""
    unbilled = unbilled_readings(conn, house_id)
    if not unbilled:
        raise ValueError("There are no new readings to bill.")
    units = sum(r["Units_Consumed"] for r in unbilled)
    start = date.fromisoformat(unbilled[0]["Previous_Reading_Date"])
    end = date.fromisoformat(unbilled[-1]["Reading_Date"])
    period = f"{start:%b %Y}-{end:%b %Y}" if (start.year, start.month) != (end.year, end.month) \
        else f"{end:%b %Y}"
    with conn:
        cursor = conn.execute(
            "INSERT INTO Electricity_Bill (House_ID, Billing_Period, Units_Consumed, Bill_Amount, "
            "Payment_Status) VALUES (?, ?, ?, ?, 'Unpaid')",
            (house_id, period, units, calculate_bill(units, tariff)),
        )
        bill_id = cursor.lastrowid
        conn.execute("UPDATE EB_Meter SET Bill_ID = ? WHERE House_ID = ? AND Bill_ID IS NULL",
                     (bill_id, house_id))
    return bill_id


def bills(conn, house_id=None):
    query = ("SELECT b.*, h.Household_Name FROM Electricity_Bill b "
             "JOIN Household h ON h.House_ID = b.House_ID")
    params = ()
    if house_id is not None:
        query += " WHERE b.House_ID = ?"
        params = (house_id,)
    return [dict(r) for r in conn.execute(query + " ORDER BY b.Bill_ID", params)]


def set_payment_status(conn, bill_id, status):
    if status not in PAYMENT_STATUSES:
        raise ValueError(f"Payment status must be one of {PAYMENT_STATUSES}.")
    with conn:
        conn.execute("UPDATE Electricity_Bill SET Payment_Status = ? WHERE Bill_ID = ?", (status, bill_id))
