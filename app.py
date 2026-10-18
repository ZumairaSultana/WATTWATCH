"""WATT-WATCH Streamlit app.

Run with:  streamlit run app.py
Flow:      Scan -> Track -> Predict -> Warn -> Reduce -> Save
"""

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from wattwatch import config, db
from wattwatch.alerts import CRITICAL, SAFE, check_slab_alert
from wattwatch.appliances import APPLIANCE_CATALOG, Appliance, estimate_savings, make_saving_plan
from wattwatch.ocr import read_meter
from wattwatch.predictor import predict_cycle
from wattwatch.tariff import Tariff, calculate_bill, slab_breakdown
from wattwatch.sample_data import SAMPLE_PERIOD_END, SAMPLE_PERIOD_START

DB_FILE = Path(__file__).parent / "data" / "wattwatch.db"

st.set_page_config(page_title="WATT-WATCH", page_icon="⚡", layout="wide")


# ---------- Sidebar: billing cycle, tariff, settings ----------

def household_settings(conn):
    st.sidebar.header("1. Household")
    households = db.list_households(conn)
    labels = {h["House_ID"]: f'{h["House_ID"]} - {h["Household_Name"]}' for h in households}
    house_id = st.sidebar.selectbox("Select household", list(labels), format_func=labels.get,
                                    key="house_id") if labels else None

    with st.sidebar.expander("➕ Add a household"):
        with st.form("household_form", clear_on_submit=True):
            new_id = st.text_input("House ID", value=db.next_house_id(conn))
            consumer = st.text_input("Consumer number")
            name = st.text_input("Household name")
            address = st.text_input("Address (optional)")
            connection = st.selectbox("Connection type", db.CONNECTION_TYPES)
            if st.form_submit_button("Add household"):
                try:
                    db.add_household(conn, new_id, consumer, name, connection, address)
                    st.session_state.house_id = new_id.strip()
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    length = st.sidebar.number_input("Billing cycle length (days)", min_value=1, max_value=120,
                                     step=1, value=config.DEFAULT_CYCLE_DAYS)
    return house_id, int(length)


def tariff_settings():
    st.sidebar.header("2. Tariff")
    with st.sidebar.expander("Slab rates (edit to match your current tariff)"):
        st.caption("Example Tamil Nadu domestic slabs. Verify against the current tariff order. "
                   "Leave 'Up to units' empty for the last slab.")
        default = pd.DataFrame(
            [(None if u == float("inf") else u, r) for u, r in config.DEFAULT_SLABS],
            columns=["Up to units", "Rate (Rs/unit)"],
        )
        edited = st.data_editor(default, num_rows="dynamic", key="tariff_editor", hide_index=True)
        fixed = st.number_input("Fixed charge (Rs)", min_value=0.0, value=config.DEFAULT_FIXED_CHARGE)
    try:
        rows = edited.dropna(subset=["Rate (Rs/unit)"]).itertuples(index=False)
        return Tariff.from_rows(rows, fixed)
    except (ValueError, TypeError) as exc:
        st.sidebar.error(f"Invalid tariff ({exc}). Using the default tariff.")
        return Tariff.from_rows(config.DEFAULT_SLABS, config.DEFAULT_FIXED_CHARGE)


def other_settings(conn):
    st.sidebar.header("3. Other settings")
    factor = st.sidebar.number_input(
        "Grid emission factor (kg CO2 per kWh)", min_value=0.0, step=0.01,
        value=config.DEFAULT_EMISSION_FACTOR,
        help="Approximate value for India. Check the latest CEA CO2 Baseline Database.",
    )
    with st.sidebar.expander("Database"):
        st.caption("Deletes all households, readings and bills, and reloads the 10 sample households.")
        if st.checkbox("I understand") and st.button("Reset to sample data"):
            db.reset_to_sample_data(conn)
            st.rerun()
    return factor


# ---------- Tab: Households ----------

def households_tab(conn, length_days, tariff):
    st.subheader("🏠 Household and EB meter records")
    st.caption("Latest meter reading of every household. The 10 sample households are fictional "
               f"data; their reading dates ({SAMPLE_PERIOD_START} to {SAMPLE_PERIOD_END}) are assumed.")
    rows = []
    for r in db.households_overview(conn):
        cycle = db.current_cycle(conn, r["House_ID"], length_days)
        units = cycle.units_used() if cycle else 0
        rows.append({
            "House ID": r["House_ID"], "Consumer No.": r["Consumer_Number"],
            "Meter No.": r["Meter_Number"], "Household Name": r["Household_Name"],
            "Connection": r["Connection_Type"], "Previous Reading (kWh)": r["Previous_Reading"],
            "Current Reading (kWh)": r["Current_Reading"], "Units Consumed": r["Units_Consumed"],
            "Reading Date": r["Reading_Date"], "Unbilled units": units,
            "Bill if billed now (Rs)": calculate_bill(units, tariff),
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.caption("Units Consumed = Current Reading − Previous Reading.")


# ---------- Tab 1: Scan & Track ----------

def scan_and_track(conn, house_id, cycle):
    st.subheader("📷 Scan the meter or type the reading")
    input_key = f"reading_input_{house_id}"
    if input_key not in st.session_state:
        st.session_state[input_key] = float(cycle.latest().value) if cycle else 0.0

    photo = st.file_uploader("Meter photo (optional)", type=["png", "jpg", "jpeg"])
    if photo is not None:
        image = Image.open(photo)
        st.image(image, width=350)
        if st.button("Read number from photo"):
            result = read_meter(image)
            if result.value is not None:
                st.session_state[input_key] = result.value
                st.success(f"Detected {result.value:g}. Please check it below before saving.")
            else:
                st.warning(result.error)
            if result.raw_text:
                st.caption(f"Raw OCR text: {result.raw_text!r}")

    with st.form("reading_form"):
        if cycle is None:
            st.write("No readings yet for this household. Enter the meter number and the reading "
                     "printed on the last electricity bill, then today's reading.")
            col1, col2, col3 = st.columns(3)
            meter = col1.text_input("Meter number")
            start_day = col2.date_input("Last bill reading date", value=date.today() - timedelta(days=15))
            start_value = col3.number_input("Last bill reading (kWh)", min_value=0.0, step=1.0)
        col1, col2 = st.columns(2)
        day = col1.date_input("Reading date", value=date.today())
        value = col2.number_input("Meter reading (kWh)", min_value=0.0, step=1.0, key=input_key)
        if st.form_submit_button("Add reading"):
            try:
                if cycle is None:
                    db.start_tracking(conn, house_id, meter, start_day, start_value, day, value)
                else:
                    db.add_reading(conn, house_id, day, value)
                st.success(f"Saved reading {value:g} for {day}.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    st.subheader("⚡ All readings (EB_Meter table)")
    rows = db.readings(conn, house_id)
    if not rows:
        return
    table = pd.DataFrame(rows).drop(columns=["House_ID"])
    table["Bill_ID"] = table["Bill_ID"].map(lambda b: "not billed yet" if pd.isna(b) else int(b))
    st.dataframe(table, hide_index=True)
    if cycle is not None:
        st.metric("Units used in the current cycle", f"{cycle.units_used():.0f}")

    with st.expander("Delete the last reading"):
        st.caption("Only readings that are not billed yet can be deleted.")
        if st.button("Delete last reading"):
            try:
                db.delete_last_reading(conn, house_id)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


# ---------- Tab 2: Predict & Warn ----------

def predict_and_warn(cycle, tariff):
    prediction = predict_cycle(cycle, tariff)
    alert = check_slab_alert(prediction, tariff, config.CRITICAL_DAYS)

    st.subheader("📈 Bill prediction")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Units so far (day {prediction.days_elapsed})", f"{prediction.units_so_far:.0f}")
    c2.metric("Average per day", f"{prediction.daily_rate:.1f} units")
    c3.metric(f"Projected units ({prediction.days_left} days left)", f"{prediction.projected_units:.0f}")
    c4.metric("Projected bill", f"Rs {prediction.projected_bill:,.0f}")
    st.caption(f"Bill for the units used so far: Rs {prediction.current_bill:,.0f}")

    st.subheader("⚠️ Early warning")
    if alert.level == SAFE:
        st.success(alert.message)
    elif alert.level == CRITICAL:
        st.error(alert.message)
    else:
        st.warning(alert.message)

    # Chart: actual cumulative units, projection line, and the slab limit to watch.
    points = cycle.points()
    actual = pd.Series({p.day: p.value - cycle.start_reading for p in points}, name="Actual units")
    end_day = cycle.start_date + timedelta(days=cycle.length_days)
    projection = pd.Series(
        {points[-1].day: prediction.units_so_far, end_day: prediction.projected_units},
        name="Projected units",
    )
    chart = pd.concat([actual, projection], axis=1)
    if alert.target_units is not None:
        chart[f"Slab limit {alert.target_units:g}"] = alert.target_units
    chart.index = pd.to_datetime(chart.index)
    st.line_chart(chart.sort_index())

    with st.expander("Projected bill breakdown by slab"):
        breakdown = pd.DataFrame([
            {"Slab": f"{c.start:g} - {'above' if c.end == float('inf') else f'{c.end:g}'}",
             "Units": round(c.units, 1), "Rate (Rs/unit)": c.rate, "Amount (Rs)": round(c.amount, 2)}
            for c in slab_breakdown(prediction.projected_units, tariff)
        ])
        st.dataframe(breakdown, hide_index=True)
        if tariff.fixed_charge:
            st.caption(f"Plus fixed charge Rs {tariff.fixed_charge:g}.")

    return prediction, alert


# ---------- Tab 3: Reduce & Save ----------

def _checked(value):
    """True for a ticked checkbox cell; False for unticked or empty (new row) cells."""
    return bool(pd.notna(value) and value)


def appliance_table():
    st.subheader("🔌 Your appliances")
    st.caption("Tick the appliances you use and set roughly how many hours each runs per day. "
               "Wattages are typical values; check your appliance label for the real figure. "
               "You can add rows for other appliances.")
    default = pd.DataFrame(
        [{"Use": False, "Appliance": name, "Watts": w, "Quantity": 1, "Hours/day": h, "Essential": e}
         for name, (w, h, e) in APPLIANCE_CATALOG.items()]
    )
    edited = st.data_editor(
        default, num_rows="dynamic", hide_index=True, key="appliance_editor",
        column_config={
            "Hours/day": st.column_config.NumberColumn(min_value=0.0, max_value=24.0, step=0.5),
            "Watts": st.column_config.NumberColumn(min_value=0.0),
            "Quantity": st.column_config.NumberColumn(min_value=1, step=1),
            "Essential": st.column_config.CheckboxColumn(help="Essential appliances are never cut."),
        },
    )
    appliances = []
    for row in edited.to_dict("records"):
        if _checked(row["Use"]) and isinstance(row["Appliance"], str) \
                and pd.notna(row["Watts"]) and pd.notna(row["Hours/day"]):
            quantity = int(row["Quantity"]) if pd.notna(row["Quantity"]) else 1
            appliances.append(Appliance(row["Appliance"], float(row["Watts"]), float(row["Hours/day"]),
                                        quantity, _checked(row["Essential"])))
    return appliances


def reduce_and_save(prediction, alert, tariff, emission_factor):
    appliances = appliance_table()
    if not appliances:
        st.info("Tick at least one appliance to get a saving plan.")
        return

    total = sum(a.daily_kwh for a in appliances)
    st.caption(f"Your selected appliances use about {total:.1f} units/day; "
               f"your meter shows {prediction.daily_rate:.1f} units/day.")

    st.subheader("💡 Saving plan")
    if prediction.days_left == 0:
        st.info("This billing cycle has ended, so there is nothing left to save in it.")
        return
    if alert.units_to_cut > 0:
        default_goal = alert.units_to_cut / prediction.days_left
        st.write(f"To stay within {alert.target_units:g} units you need to save about "
                 f"**{alert.units_to_cut:.0f} units** over the next {prediction.days_left} days "
                 f"(**{default_goal:.1f} units/day**).")
    else:
        default_goal = round(prediction.daily_rate * 0.10, 1)
        st.write("No slab jump expected. Here is a plan to save about 10% anyway.")

    col1, col2 = st.columns(2)
    goal = col1.number_input("Daily saving goal (units/day)", min_value=0.0, step=0.1,
                             value=round(float(default_goal), 2))
    max_cut = col2.slider("Cut each appliance by at most (%)", 10, 100, 50, step=10) / 100

    plan = make_saving_plan(appliances, goal, max_cut_fraction=max_cut)
    if not plan.suggestions:
        st.info("No reductions possible with the current appliances and limits.")
        return

    st.dataframe(pd.DataFrame([
        {"Appliance": s.name, "Now (h/day)": s.current_hours, "Suggested (h/day)": s.suggested_hours,
         "Cut (h/day)": s.hours_cut, "Units saved/day": round(s.daily_kwh_saved, 2)}
        for s in plan.suggestions
    ]), hide_index=True)
    if not plan.target_met:
        st.warning(f"This plan saves {plan.daily_kwh_saved:.1f} of the {goal:.1f} units/day needed. "
                   "Allow bigger cuts or add more appliances to close the gap.")

    savings = estimate_savings(plan, prediction.days_left, prediction.projected_units,
                               tariff, emission_factor)
    st.subheader("💰 Estimated savings this cycle")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Units saved", f"{savings.units_saved:.0f}")
    c2.metric("Money saved", f"Rs {savings.money_saved:,.0f}")
    c3.metric("CO2 avoided", f"{savings.co2_saved_kg:.0f} kg")
    c4.metric(f"New projected bill ({savings.new_projected_units:.0f} units)",
              f"Rs {savings.new_projected_bill:,.0f}")


# ---------- Tab: Bills ----------

def bills_tab(conn, house_id, cycle, tariff):
    st.subheader("🧾 Bills (Electricity_Bill table)")
    st.caption("Bill amounts use the tariff in the sidebar, which is an example. "
               "They are illustrative, not official bills.")
    unbilled = db.unbilled_readings(conn, house_id)
    if unbilled:
        units = cycle.units_used()
        st.write(f"Current cycle: **{units:.0f} units** not billed yet "
                 f"(bill would be **Rs {calculate_bill(units, tariff):,.2f}**).")
        if st.button("Generate bill for this cycle"):
            db.generate_bill(conn, house_id, tariff)
            st.rerun()
    else:
        st.info("No unbilled readings. Add readings in the Scan & Track tab.")

    rows = db.bills(conn, house_id)
    if not rows:
        return
    st.dataframe(pd.DataFrame(rows).drop(columns=["House_ID", "Household_Name"]), hide_index=True)
    with st.form("payment_form"):
        col1, col2 = st.columns(2)
        bill_id = col1.selectbox("Bill ID", [r["Bill_ID"] for r in rows])
        status = col2.selectbox("Payment status", db.PAYMENT_STATUSES)
        if st.form_submit_button("Update payment status"):
            db.set_payment_status(conn, bill_id, status)
            st.rerun()


# ---------- Main ----------

def main():
    st.title("⚡ WATT-WATCH")
    st.caption("See your electricity bill coming before it arrives. "
               "Scan → Track → Predict → Warn → Reduce → Save 🌱")

    conn = db.connect(DB_FILE)
    try:
        db.init_db(conn)
        run_app(conn)
    finally:
        conn.close()


def run_app(conn):
    house_id, length_days = household_settings(conn)
    tariff = tariff_settings()
    emission_factor = other_settings(conn)

    tabs = st.tabs(["🏠 Households", "📷 Scan & Track", "📈 Predict & Warn", "💡 Reduce & Save", "🧾 Bills"])
    tab_households, tab_track, tab_predict, tab_save, tab_bills = tabs
    with tab_households:
        households_tab(conn, length_days, tariff)
    if house_id is None:
        st.info("👈 Add a household in the sidebar to get started.")
        return

    cycle = db.current_cycle(conn, house_id, length_days)
    with tab_track:
        scan_and_track(conn, house_id, cycle)
    with tab_bills:
        bills_tab(conn, house_id, cycle, tariff)
    if cycle is None or not cycle.readings:
        with tab_predict:
            st.info("Add a reading in the Scan & Track tab to see predictions.")
        with tab_save:
            st.info("Add a reading in the Scan & Track tab to get a saving plan.")
        return
    with tab_predict:
        prediction, alert = predict_and_warn(cycle, tariff)
    with tab_save:
        reduce_and_save(prediction, alert, tariff, emission_factor)


main()
