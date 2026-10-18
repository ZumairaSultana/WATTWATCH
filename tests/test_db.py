from datetime import date

import pytest

from wattwatch import db
from wattwatch.sample_data import SAMPLE_PERIOD_END, SAMPLE_PERIOD_START
from wattwatch.tariff import Tariff, calculate_bill

TARIFF = Tariff.from_rows([(100, 0), (400, 5), (500, 10), (None, 20)])

# Units Consumed column from the PDF, H001 to H010.
PDF_UNITS = [150, 180, 120, 250, 120, 220, 300, 150, 150, 180]


@pytest.fixture
def conn():
    connection = db.connect(":memory:")
    db.init_db(connection)
    yield connection
    connection.close()


def test_sample_data_matches_pdf(conn):
    overview = db.households_overview(conn)
    assert [r["House_ID"] for r in overview] == [f"H{i:03d}" for i in range(1, 11)]
    assert [r["Units_Consumed"] for r in overview] == PDF_UNITS
    arun = overview[0]
    assert (arun["Consumer_Number"], arun["Meter_Number"], arun["Household_Name"]) == \
        ("EB10001", "MTR1001", "Arun")
    assert (arun["Previous_Reading"], arun["Current_Reading"]) == (1250, 1400)
    assert overview[3]["Connection_Type"] == "Three phase"


def test_init_does_not_seed_twice(conn):
    db.init_db(conn)
    assert len(db.list_households(conn)) == 10


def test_add_household_and_duplicates(conn):
    assert db.next_house_id(conn) == "H011"
    db.add_household(conn, "H011", "EB10011", "Anitha", "Single phase", "12 Main St")
    assert db.next_house_id(conn) == "H012"
    with pytest.raises(ValueError):
        db.add_household(conn, "H011", "EB99999", "Someone", "Single phase")
    with pytest.raises(ValueError):
        db.add_household(conn, "H012", "EB10011", "Someone", "Single phase")  # consumer no. taken
    with pytest.raises(ValueError):
        db.add_household(conn, "H012", "EB10012", "Someone", "Four phase")


def test_add_reading_uses_previous_row(conn):
    db.add_reading(conn, "H001", date(2026, 10, 10), 1430)
    last = db.last_reading(conn, "H001")
    assert last["Previous_Reading"] == 1400
    assert last["Units_Consumed"] == 30
    assert last["Previous_Reading_Date"] == SAMPLE_PERIOD_END.isoformat()
    assert last["Meter_Number"] == "MTR1001"


def test_add_reading_validation(conn):
    with pytest.raises(ValueError):
        db.add_reading(conn, "H001", date(2026, 10, 10), 1399)  # lower than previous
    with pytest.raises(ValueError):
        db.add_reading(conn, "H001", SAMPLE_PERIOD_END, 1450)  # not after previous date


def test_start_tracking_new_household(conn):
    db.add_household(conn, "H011", "EB10011", "Anitha", "Single phase")
    assert db.current_cycle(conn, "H011", 60) is None
    with pytest.raises(ValueError):
        db.add_reading(conn, "H011", date(2026, 10, 10), 500)
    db.start_tracking(conn, "H011", "MTR1011", date(2026, 10, 1), 400, date(2026, 10, 11), 480)
    cycle = db.current_cycle(conn, "H011", 60)
    assert (cycle.start_date, cycle.start_reading, cycle.units_used()) == (date(2026, 10, 1), 400, 80)
    with pytest.raises(ValueError):
        db.start_tracking(conn, "H011", "MTR1011", date(2026, 10, 1), 400, date(2026, 10, 11), 480)


def test_current_cycle_and_bill(conn):
    cycle = db.current_cycle(conn, "H004", 60)
    assert (cycle.start_date, cycle.start_reading) == (SAMPLE_PERIOD_START, 4500)
    assert cycle.units_used() == 250

    bill_id = db.generate_bill(conn, "H004", TARIFF)
    bill = db.bills(conn, "H004")[0]
    assert bill["Bill_ID"] == bill_id
    assert bill["Units_Consumed"] == 250
    assert bill["Bill_Amount"] == calculate_bill(250, TARIFF)
    assert bill["Payment_Status"] == "Unpaid"
    assert bill["Billing_Period"] == "Aug 2026-Sep 2026"

    # After billing, a new empty cycle starts from the last reading.
    cycle = db.current_cycle(conn, "H004", 60)
    assert (cycle.start_date, cycle.start_reading, cycle.readings) == (SAMPLE_PERIOD_END, 4750, [])
    with pytest.raises(ValueError):
        db.generate_bill(conn, "H004", TARIFF)  # nothing new to bill
    with pytest.raises(ValueError):
        db.delete_last_reading(conn, "H004")  # billed readings are kept

    db.add_reading(conn, "H004", date(2026, 10, 10), 4800)
    db.add_reading(conn, "H004", date(2026, 10, 20), 4870)
    cycle = db.current_cycle(conn, "H004", 60)
    assert cycle.units_used() == 120
    db.generate_bill(conn, "H004", TARIFF)
    assert [b["Units_Consumed"] for b in db.bills(conn, "H004")] == [250, 120]


def test_delete_last_reading(conn):
    db.add_reading(conn, "H002", date(2026, 10, 10), 2500)
    db.delete_last_reading(conn, "H002")
    assert db.last_reading(conn, "H002")["Current_Reading"] == 2480


def test_payment_status(conn):
    bill_id = db.generate_bill(conn, "H001", TARIFF)
    db.set_payment_status(conn, bill_id, "Paid")
    assert db.bills(conn)[0]["Payment_Status"] == "Paid"
    with pytest.raises(ValueError):
        db.set_payment_status(conn, bill_id, "Maybe")


def test_reset_to_sample_data(conn):
    db.add_household(conn, "H011", "EB10011", "Anitha", "Single phase")
    db.generate_bill(conn, "H001", TARIFF)
    db.reset_to_sample_data(conn)
    assert len(db.list_households(conn)) == 10
    assert db.bills(conn) == []
