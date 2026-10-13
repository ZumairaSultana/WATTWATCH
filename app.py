"""WATT-WATCH Streamlit app.

Run with:  streamlit run app.py
Flow:      Scan -> Track -> Predict -> Warn -> Reduce -> Save
"""

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from wattwatch import config
from wattwatch.alerts import CRITICAL, SAFE, check_slab_alert
from wattwatch.appliances import APPLIANCE_CATALOG, Appliance, estimate_savings, make_saving_plan
from wattwatch.ocr import read_meter
from wattwatch.predictor import predict_cycle
from wattwatch.tariff import Tariff, slab_breakdown
from wattwatch.tracker import Cycle, load_cycle, save_cycle

DATA_FILE = Path(__file__).parent / "data" / "cycle.json"

st.set_page_config(page_title="WATT-WATCH", page_icon="⚡", layout="wide")


# ---------- Sidebar: billing cycle, tariff, settings ----------

def cycle_settings():
    if "cycle" not in st.session_state:
        st.session_state.cycle = load_cycle(DATA_FILE)
    cycle = st.session_state.cycle

    st.sidebar.header("1. Billing cycle")
    st.sidebar.caption("Use the reading and date printed on your last electricity bill.")
    with st.sidebar.form("cycle_form"):
        start_date = st.date_input(
            "Cycle start date", value=cycle.start_date if cycle else date.today() - timedelta(days=15)
        )
        start_reading = st.number_input(
            "Meter reading at cycle start (kWh)",
            min_value=0.0, step=1.0, value=float(cycle.start_reading) if cycle else 0.0,
        )
        length = st.number_input(
            "Cycle length (days)", min_value=1, max_value=120, step=1,
            value=cycle.length_days if cycle else config.DEFAULT_CYCLE_DAYS,
        )
        if st.form_submit_button("Save cycle"):
            # Keep only readings that still fit the (possibly changed) cycle.
            old = cycle.readings if cycle else []
            kept = [r for r in old if r.day > start_date and r.value >= start_reading]
            cycle = Cycle(start_date, start_reading, int(length), kept)
            st.session_state.cycle = cycle
            save_cycle(cycle, DATA_FILE)
            st.sidebar.success("Cycle saved.")
    return cycle


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


def other_settings():
    st.sidebar.header("3. Other settings")
    return st.sidebar.number_input(
        "Grid emission factor (kg CO2 per kWh)", min_value=0.0, step=0.01,
        value=config.DEFAULT_EMISSION_FACTOR,
        help="Approximate value for India. Check the latest CEA CO2 Baseline Database.",
    )


# ---------- Tab 1: Scan & Track ----------

def scan_and_track(cycle):
    st.subheader("📷 Scan the meter or type the reading")
    if "reading_input" not in st.session_state:
        st.session_state.reading_input = float(cycle.latest().value)

    photo = st.file_uploader("Meter photo (optional)", type=["png", "jpg", "jpeg"])
    if photo is not None:
        image = Image.open(photo)
        st.image(image, width=350)
        if st.button("Read number from photo"):
            result = read_meter(image)
            if result.value is not None:
                st.session_state.reading_input = result.value
                st.success(f"Detected {result.value:g}. Please check it below before saving.")
            else:
                st.warning(result.error)
            if result.raw_text:
                st.caption(f"Raw OCR text: {result.raw_text!r}")

    with st.form("reading_form"):
        col1, col2 = st.columns(2)
        day = col1.date_input("Reading date", value=date.today())
        value = col2.number_input("Meter reading (kWh)", min_value=0.0, step=1.0, key="reading_input")
        if st.form_submit_button("Add reading"):
            try:
                cycle.add_reading(day, value)
                save_cycle(cycle, DATA_FILE)
                st.success(f"Saved reading {value:g} for {day}.")
            except ValueError as exc:
                st.error(str(exc))

    st.subheader("⚡ Usage so far")
    rows = cycle.usage_table()
    if not rows:
        st.info("Add at least one reading after the cycle start to see your usage.")
        return
    st.metric("Units used since cycle start", f"{cycle.units_used():.0f}")
    st.dataframe(pd.DataFrame(rows), hide_index=True)

    with st.expander("Delete a reading"):
        day = st.selectbox("Reading to delete", [r.day for r in cycle.readings])
        if st.button("Delete"):
            cycle.remove_reading(day)
            save_cycle(cycle, DATA_FILE)
            st.rerun()


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


# ---------- Main ----------

def main():
    st.title("⚡ WATT-WATCH")
    st.caption("See your electricity bill coming before it arrives. "
               "Scan → Track → Predict → Warn → Reduce → Save 🌱")

    cycle = cycle_settings()
    tariff = tariff_settings()
    emission_factor = other_settings()

    if cycle is None:
        st.info("👈 Start by entering your billing cycle details in the sidebar and clicking **Save cycle**.")
        return

    tab_track, tab_predict, tab_save = st.tabs(["📷 Scan & Track", "📈 Predict & Warn", "💡 Reduce & Save"])
    with tab_track:
        scan_and_track(cycle)
    if not cycle.readings:
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
