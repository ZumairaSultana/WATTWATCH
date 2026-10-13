# WATT-WATCH — Step-by-step implementation guide

This guide walks through how the project is built, in the same order as the
app's flow: **Scan → Track → Predict → Warn → Reduce → Save**.

Each step lives in its own small module inside `wattwatch/`, and `app.py`
connects them to the Streamlit interface. The modules do not import
Streamlit, so they can be tested on their own (`python -m pytest`).

---

## Step 0 — Setup

```bash
pip install -r requirements.txt     # streamlit, pandas, numpy, pillow, pytesseract, pytest
sudo apt install tesseract-ocr      # optional, only needed to read meter photos
streamlit run app.py
```

`requirements.txt` lists the Python packages. `packages.txt` lists the
system package (`tesseract-ocr`) for hosts such as Streamlit Community Cloud
that install apt packages from that file.

---

## Step 1 — Settings and the tariff (`config.py`, `tariff.py`)

### Why this comes first
Every other step (prediction, warning, savings) needs to turn **units** into
**rupees**, so the bill calculator is the foundation.

### How slab billing works
Tamil Nadu domestic bills are *telescopic*: each unit is charged at the rate
of the slab it falls into. With the example slabs in `config.py`

| Units | Rate (Rs/unit) |
|-------|----------------|
| 0 – 100 | 0 (free) |
| 101 – 400 | 4.80 |
| 401 – 500 | 6.45 |
| 501 – 600 | 8.55 |
| ... | ... |

a 450-unit bill is `100×0 + 300×4.80 + 50×6.45 = Rs 1,762.50`.

> ⚠️ These rates are an example. Tariffs change, so check the current tariff
> order before relying on the numbers. They can be edited in `config.py` or
> live in the app sidebar.

### The code
- `Slab(upto, rate)` — one row of the table. The last slab has `upto = math.inf`.
- `Tariff(slabs, fixed_charge)` — checks in `__post_init__` that limits are
  increasing, rates aren't negative, and the last slab is open-ended, so a
  mistyped tariff fails loudly instead of giving a wrong bill.
- `Tariff.from_rows(rows)` — builds a tariff from `(upto, rate)` pairs; an
  empty limit means "no limit". The sidebar table uses this.
- `slab_breakdown(units, tariff)` — the core loop:

  ```python
  lower = 0
  for slab in tariff.slabs:
      if units <= lower: break
      in_slab = min(units, slab.upto) - lower   # units that fall in this slab
      ... amount = in_slab * slab.rate
      lower = slab.upto
  ```
- `calculate_bill(units, tariff)` — sum of the slab amounts + fixed charge.
- `tariff.boundaries` — the finite slab limits `[100, 400, 500, ...]`, used by
  the warning step.

---

## Step 2 — Scan the meter (`ocr.py`)

### Goal
Let the user upload a photo of the meter and pull out the reading.

### The code
1. **`preprocess(image)`** prepares the photo for OCR:
   - `ImageOps.exif_transpose` — fixes phone photos that are stored sideways.
   - grayscale → enlarge to ~1000 px wide (Tesseract reads larger text better)
     → `autocontrast` → `MedianFilter(3)` to remove speckle noise
     → threshold to pure black/white.
2. **`read_meter(image)`** runs Tesseract twice — on the image and on its
   inverse — because some displays are dark-on-light and others
   light-on-dark. The `tessedit_char_whitelist=0123456789.` option tells
   Tesseract to only output digits and a decimal point.
3. **`parse_reading(text)`** finds every number in the OCR text with a regular
   expression and keeps the one with the most digits (the reading is usually
   the longest number on the display).
4. Errors (Tesseract missing, no number found) are returned in
   `OcrResult.error` instead of crashing, so the user can just type the value.

### Limitation
OCR on real meter displays (glare, angle, 7-segment digits) is not always
accurate. That is why the app puts the detected value into an **editable
box** and the user confirms it before saving.

---

## Step 3 — Track usage (`tracker.py`)

### Goal
Store readings for the current billing cycle and compute units used.

### The code
- `Reading(day, value)` — one meter reading.
- `Cycle(start_date, start_reading, length_days, readings)` — the billing
  cycle. The start reading is the one printed on the last bill.
  - `points()` — start reading + all readings, sorted by date.
  - `units_used()` — `latest reading − start reading`.
  - `add_reading(day, value)` — validates before saving: the date must be after
    the cycle start, and because a meter only counts **up**, a reading can't be
    lower than an earlier one or higher than a later one. Adding a second
    reading on the same date replaces the first.
  - `usage_table()` — units and units/day between consecutive readings (shown
    as the table in the app).
- `save_cycle` / `load_cycle` — store the cycle as JSON in `data/cycle.json`,
  so readings survive restarting the app.

> Note: meter roll-over (e.g. 99999 → 00000) is not handled.

---

## Step 4 — Predict the bill (`predictor.py`)

### Idea
Plot meter reading against day: for a household with a steady routine it is
close to a straight line. The **slope** of that line is units per day.

### The code
- `daily_usage_rate(points, recent=5)` uses the last 5 readings:
  - 2 readings → `slope = (reading2 − reading1) / (days between)`.
  - 3+ readings → least-squares straight line with `numpy.polyfit(x, y, 1)`;
    the first returned value is the slope. Using several points smooths out a
    single unusual day. Using only *recent* points lets the estimate follow
    changes (e.g. summer AC use).
- `predict_cycle(cycle, tariff)`:

  ```text
  days_elapsed    = latest reading date − cycle start
  days_left       = cycle length − days_elapsed
  projected_units = units_so_far + daily_rate × days_left
  projected_bill  = calculate_bill(projected_units)
  ```

### Worked example (default tariff)
Cycle start reading 5000; on day 28 the meter reads 5330.
- Units so far = 330 → bill so far = 230 × 4.80 = Rs 1,104.
- Rate ≈ 11.8 units/day, 32 days left → projected ≈ 330 + 11.8 × 32 ≈ 707 units.
- Projected bill ≈ Rs 3,970.

---

## Step 5 — Early warning (`alerts.py`)

### Goal
Warn **before** usage crosses into a costlier slab.

### The code
`check_slab_alert(prediction, tariff)`:
1. Find slab limits between "now" and "projected":
   `crossing = [b for b in boundaries if units_so_far < b < projected_units]`.
2. Nothing crossed → **safe**.
3. Otherwise:
   - `next_limit = crossing[0]` — the first limit you'll hit;
     `days_until_cross = (next_limit − units_so_far) / daily_rate`.
   - `target = crossing[-1]` — the nearest limit *below* the projection: the
     smallest cut that avoids a slab jump.
   - `units_to_cut = projected − target`.
   - `money_at_stake = bill(projected) − bill(target)`.
4. Level: **critical** if two or more limits will be crossed or the next one is
   ≤ 7 days away (`CRITICAL_DAYS` in `config.py`); otherwise **warning**.

In the example above (330 units now, 707 projected) the limits 400, 500 and
600 are all ahead, so it is **critical**: cross 400 in about 6 days, cut about
107 units to stay at or below 600.

---

## Step 6 — Select appliances and hours (`appliances.py`)

- `APPLIANCE_CATALOG` — common appliances with **typical** wattages and hours
  (approximate; the real wattage is on the appliance label). The user ticks
  what they use and edits watts, quantity and hours in the app.
- `Appliance.daily_kwh = watts × quantity × hours ÷ 1000` (1 kWh = 1 unit).
- `essential=True` (fridge, Wi-Fi router, mixer) means "never suggest cutting
  this".

The app also compares the appliance total with the meter's units/day, so the
user can see whether their list roughly explains their real usage.

---

## Step 7 — Saving plan (`make_saving_plan`)

### Goal
Save `target_daily_kwh` units per day with the fewest hours of lost comfort.

Daily target = `units_to_cut ÷ days_left` (from Step 5), or 10% of usage if
there is no slab risk. The user can change it.

### Algorithm (greedy)
1. Take non-essential appliances, sorted by power (kW) — highest first. One
   hour of a 2 kW geyser saves as much as 20 hours of a 100 W TV.
2. For each appliance:
   - cut only what is still needed: `needed = remaining ÷ kW` (rounded up to
     half-hours),
   - but at most `max_cut_fraction` (default 50%) of its hours, so the plan
     stays realistic,
   - subtract the saving from `remaining`.
3. Stop once the target is met. If all appliances hit their cap first,
   `plan.target_met` is `False` and the app says how much is still missing.

Because cuts are rounded to half-hours, the plan can slightly overshoot the
target.

---

## Step 8 — See savings (`estimate_savings`)

If the plan is followed for the rest of the cycle:

```text
units_saved   = daily saving × days_left
new_units     = projected_units − units_saved
money_saved   = bill(projected_units) − bill(new_units)
CO2 avoided   = units_saved × emission factor (kg CO2 per kWh)
```

Because of the slabs, the money saved per unit is the **highest** slab rate
you were heading into — that's why avoiding a slab jump pays off most.

The emission factor (default 0.71 kg/kWh) is approximate for the Indian
grid; check the latest CEA CO2 Baseline Database and update it in the sidebar.

---

## Step 9 — The Streamlit app (`app.py`)

- **Sidebar**
  1. *Billing cycle* form → creates/updates the `Cycle` and saves it.
  2. *Tariff* table (`st.data_editor`) → `Tariff.from_rows`; if the table is
     invalid the app shows an error and falls back to the default tariff.
  3. *Emission factor*.
- **Tab "Scan & Track"** — photo upload → `read_meter` → the result is put into
  `st.session_state.reading_input`, which pre-fills the reading box; the form
  calls `cycle.add_reading` and `save_cycle`. Then the usage table.
- **Tab "Predict & Warn"** — `predict_cycle` + `check_slab_alert` → metrics,
  a coloured alert (`st.success` / `st.warning` / `st.error`), a line chart of
  actual vs projected units with the slab limit, and the slab breakdown.
- **Tab "Reduce & Save"** — appliance table → `make_saving_plan` →
  `estimate_savings` → suggestions table and savings metrics.

`st.session_state` keeps the cycle between Streamlit reruns (Streamlit re-runs
the whole script on every click), and `data/cycle.json` keeps it between app
restarts.

---

## Step 10 — Tests (`tests/test_wattwatch.py`)

`python -m pytest` checks each step with a simple tariff whose results are
easy to verify by hand: telescopic billing, invalid tariffs, reading
validation, save/load, usage rate, projection, all three alert levels, the
saving plan (biggest appliance first, caps, essentials untouched), savings,
and OCR number parsing.

---

## Ideas for extending the project
- Tariff rules where the total consumption changes the price of the lower
  slabs too (not just the units above the limit). If the current tariff
  order or subsidy rules work this way, extend `calculate_bill`.
- Multiple households / user login, with a database instead of a JSON file.
- A trained digit recogniser for 7-segment meter displays to improve OCR.
- SMS/WhatsApp reminders to take a reading every few days.
