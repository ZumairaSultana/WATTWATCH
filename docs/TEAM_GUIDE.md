# WATT-WATCH — Beginner guide for a 3-person team

> **Short on time?** Use [2_DAY_PLAN.md](2_DAY_PLAN.md) instead — a compressed
> plan with separate step-by-step work for each person.

This guide assumes you have **never** done a project like this before. Follow
the parts in order. Every command is typed in a **terminal** (a window where
you type commands instead of clicking).

> Written for **Windows**. Mac/Linux differences are noted where they matter.

**Contents**
1. [What you are building](#part-1--what-you-are-building)
2. [Who does what](#part-2--who-does-what)
3. [Setup on every laptop](#part-3--setup-on-every-laptop-all-3-people)
4. [How to work together with Git](#part-4--how-to-work-together-with-git)
5. [Understanding the database](#part-5--understanding-the-database)
6. [Person 1 tasks — Database & Billing](#part-6--person-1-database--billing)
7. [Person 2 tasks — Scanning & Prediction](#part-7--person-2-scanning--prediction)
8. [Person 3 tasks — App, Saving plan & Demo](#part-8--person-3-app-saving-plan--demo)
9. [Real-world testing](#part-9--real-world-testing-all-3)
10. [Report & presentation](#part-10--report--presentation)
11. [Troubleshooting](#part-11--troubleshooting)
12. [Glossary](#part-12--glossary)

---

## Part 1 — What you are building

WATT-WATCH is a **web app** (it opens in a browser) that helps families avoid
high electricity bills:

```
Scan meter → Track units → Predict bill → Warn before slab jump → Reduce usage → See savings
```

It has **5 tabs**:

| Tab | What it does |
|---|---|
| 🏠 Households | Table of all households and their latest meter reading |
| 📷 Scan & Track | Upload a meter photo or type the reading; see all readings |
| 📈 Predict & Warn | Predicted units and bill for the cycle, and a warning before a costlier slab |
| 💡 Reduce & Save | Pick appliances and hours → a saving plan and money saved |
| 🧾 Bills | Generate a bill for the cycle and mark it Paid / Unpaid / Pending |

All data is stored in a **database** file: `data/wattwatch.db`. It starts with
the **10 sample households** from "Household EB Meter Database" (Arun, Kumar,
Priya, …).

**Code files and what they do**

| File | Job |
|---|---|
| `app.py` | The screens (sidebar + 5 tabs) |
| `wattwatch/schema.sql` | Creates the 3 database tables |
| `wattwatch/sample_data.py` | The 10 sample households |
| `wattwatch/db.py` | Saves and reads households, readings and bills |
| `wattwatch/config.py` | Tariff slab rates and other settings |
| `wattwatch/tariff.py` | Calculates the bill from units |
| `wattwatch/ocr.py` | Reads the number from a meter photo |
| `wattwatch/tracker.py` | Units used in the current cycle |
| `wattwatch/predictor.py` | Predicts end-of-cycle units and bill |
| `wattwatch/alerts.py` | Warns before a slab jump |
| `wattwatch/appliances.py` | Appliance list and saving plan |
| `tests/` | Automatic checks that the calculations are right |

---

## Part 2 — Who does what

Split the work so each person **owns different files**. Then you never
overwrite each other's work.

| | Person 1 — Database & Billing | Person 2 — Scanning & Prediction | Person 3 — App, Saving plan & Demo |
|---|---|---|---|
| **Files** | `schema.sql`, `sample_data.py`, `db.py`, `tariff.py`, `config.py` | `ocr.py`, `tracker.py`, `predictor.py`, `alerts.py` | `app.py`, `appliances.py` |
| **Main job** | Database, tariff check, bills | OCR accuracy, prediction accuracy | Screens, appliances, phone test, putting it online, demo |
| **Results for report** | ER diagram, SQL queries, bill check table | OCR accuracy %, prediction error % | Screenshots, saving plan examples, live link |
| **Presents** | Database & billing | Scan, predict, warn | App demo & saving plan |

**Everyone** must still understand the whole app — examiners can ask anyone
about any part.

**Suggested schedule** (stretch or shrink to fit your deadline):

| Week | All together | Person 1 | Person 2 | Person 3 |
|---|---|---|---|---|
| 1 | Part 3 setup, read this guide and `docs/GUIDE.md` | Learn the database (Part 5) | Collect meter photos | Explore the app, list UI issues |
| 2 | Start home testing (Part 9) | Verify tariff, bill check table | OCR accuracy test | Check appliance wattages |
| 3 | Keep taking readings | SQL queries, ER diagram | Improve OCR, re-test | Phone test, put app online |
| 4 | Compare predicted vs actual bill | Report: database & billing | Report: OCR & prediction | Report: app & saving plan, slides |
| 5 | Practise presentation & demo 3 times | | | |

⚠️ A Tamil Nadu billing cycle is about 2 months, so start **home testing
(Part 9) early**.

---

## Part 3 — Setup on every laptop (all 3 people)

### Step 3.1 — Install Python
1. Go to **python.org → Downloads** and download the latest Python 3.
2. Run the installer. On the **first screen tick "Add python.exe to PATH"**. ⚠️ Don't skip this.
3. Click **Install Now**.

### Step 3.2 — Install Git
1. Go to **git-scm.com → Download for Windows**.
2. Run the installer and keep clicking **Next** (the default options are fine).

### Step 3.3 — Install VS Code (code editor)
Download from **code.visualstudio.com** and install.

### Step 3.4 — Check everything works
1. Press the **Windows key**, type **cmd**, press Enter. This opens **Command Prompt**.
   (Use Command Prompt, not PowerShell — it avoids a common permission error.)
2. Type each line and press Enter:
   ```
   python --version
   git --version
   ```
   Each should print a version number. If it says *"not recognized"*, reinstall
   that program (for Python, remember the PATH box). If `python` doesn't work,
   try `py --version`; if that works, type `py` instead of `python` everywhere below.

### Step 3.5 — Tell Git who you are (once per laptop)
```
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```
Use the same email as your GitHub account.

### Step 3.6 — GitHub accounts (once)
1. Each person creates a free account on **github.com**.
2. **The repo owner**: open the repo → **Settings → Collaborators → Add people** → add the other two.
3. The other two accept the invitation sent to their email.

### Step 3.7 — Put the code on the main branch (repo owner, once)
The code is currently on a branch called `claude/code-implementation-guide-fqx9ks`.
Move it to `main` so everyone gets it:
1. On github.com open the repo → **Pull requests** → **New pull request**.
2. **base:** `main`, **compare:** `claude/code-implementation-guide-fqx9ks`.
3. **Create pull request** → **Merge pull request** → **Confirm merge**.

### Step 3.8 — Download the project (each person)
In Command Prompt:
```
cd %USERPROFILE%\Documents
git clone -b claude/code-implementation-guide-fqx9ks https://github.com/ZumairaSultana/WATTWATCH.git
cd WATTWATCH
```
- `cd` = "change directory" (go into a folder).
- `git clone` = download the project, still linked to GitHub.
- The first time, a window may ask you to **sign in to GitHub** — do it.

### Step 3.9 — Create a virtual environment (each person)
A **virtual environment** is a private box for this project's packages.
```
python -m venv venv
venv\Scripts\activate
```
You will now see **`(venv)`** at the start of the line.
- Mac/Linux: `source venv/bin/activate`
- ⚠️ Run `venv\Scripts\activate` **every time** you open a new Command Prompt for this project.

### Step 3.10 — Install the packages
```
pip install -r requirements.txt
```
`pip` downloads the libraries listed in `requirements.txt` (Streamlit, pandas, …).
Takes a few minutes the first time.

### Step 3.11 — (Optional) Install Tesseract for photo scanning
Only needed to read meter **photos**. Without it you just type the reading.
1. Search the web for **"Tesseract UB Mannheim"** and download the Windows installer.
2. Install it. If the app later says *"Tesseract not found"*, ask for help — it
   usually means the install folder isn't on PATH.

### Step 3.12 — Run the app
```
streamlit run app.py
```
Your browser opens at **http://localhost:8501** (*localhost* = "this computer").
To stop the app: click the Command Prompt window and press **Ctrl + C**.

### Step 3.13 — Run the tests
Open a **second** Command Prompt, go to the folder, activate venv, then:
```
cd %USERPROFILE%\Documents\WATTWATCH
venv\Scripts\activate
python -m pytest
```
You should see **`32 passed`**. Run this before every push.

### Step 3.14 — Try the app once (5 minutes)
1. **🏠 Households** — see the 10 sample households.
2. Sidebar → pick **H001 - Arun**.
3. **🧾 Bills** → **Generate bill for this cycle** (bills Arun's 150 sample units).
4. **📷 Scan & Track** → type a reading higher than 1400 (e.g. 1480) → **Add reading**.
5. **📈 Predict & Warn** → see the prediction and warning.
6. **💡 Reduce & Save** → tick some appliances → see the saving plan.
7. Sidebar → **➕ Add a household** → add your own home.

> To start over with fresh sample data: sidebar → **Database** → tick
> *I understand* → **Reset to sample data**.

---

## Part 4 — How to work together with Git

Think of Git as **"save points + sharing"**:
- **commit** = a save point on your laptop
- **push** = upload your save points to GitHub
- **pull** = download your teammates' save points
- **branch** = your own copy to work on without disturbing others
- **pull request (PR)** = asking the team to add your branch to `main`

### The routine — every time you work

```
git checkout main                ← go to the shared version
git pull                         ← get teammates' latest work
git checkout -b ocr-accuracy     ← make YOUR branch (pick a clear name)

   ... edit your files in VS Code ...
   ... python -m pytest  (must pass!) ...

git add .                        ← pick all changed files
git commit -m "Improve OCR for dim photos"   ← save point with a message
git push -u origin ocr-accuracy  ← upload your branch
```

Then on **github.com**:
1. A yellow bar appears: **Compare & pull request** → click it.
2. Write what you changed → **Create pull request**.
3. A **teammate** reads it (**Files changed** tab) and clicks **Merge pull request**.
4. Everyone then runs `git checkout main` and `git pull`.

### Golden rules
1. **Pull before you start.**
2. **Only edit your own files** (Part 2). If you must touch someone else's file, tell them first.
3. **Never push if `pytest` fails.**
4. **Small, frequent commits** with clear messages.
5. **Never commit `data/wattwatch.db`** — it's ignored on purpose (`.gitignore`),
   so each person has their own test data.

---

## Part 5 — Understanding the database

A **database** stores data in **tables** (like Excel sheets) that are linked
together. We use **SQLite**: the whole database is one file
(`data/wattwatch.db`), built into Python, no server to install.

### The 3 tables (from "Household EB Meter Database")

```
Household                 EB_Meter                          Electricity_Bill
───────────               ─────────────────────             ──────────────────
House_ID  (PK) ◄──┐       Meter_ID (PK)                ┌──► Bill_ID (PK)
Consumer_Number   ├────── House_ID (FK)                │    House_ID (FK) ──► Household
Household_Name    │       Meter_Number                 │    Billing_Period
Address           │       Previous_Reading             │    Units_Consumed
Connection_Type   │       Current_Reading              │    Bill_Amount
                  │       Units_Consumed               │    Payment_Status
                  │       Reading_Date                 │
                  │       Previous_Reading_Date  (added)
                  │       Bill_ID (FK, added) ─────────┘
```

- **PK (Primary Key)** = the column that uniquely identifies a row (no two households have the same `House_ID`).
- **FK (Foreign Key)** = a column that points to a row in another table (`EB_Meter.House_ID` says which household a reading belongs to).
- **One household → many readings → many bills.**

### Two columns we added (and why)
| Column | Why |
|---|---|
| `Previous_Reading_Date` | The PDF only has the date of the *current* reading. To predict usage per day we need the start date too. |
| `Bill_ID` | Tells which bill a reading was included in. **Empty (NULL) = not billed yet = current cycle.** |

### How the data flows
1. **Add reading** → a new `EB_Meter` row. Previous reading is copied from the
   last row; `Units_Consumed = Current − Previous` is calculated (never typed).
2. **Predict** → all `EB_Meter` rows with no `Bill_ID` form the current cycle.
3. **Generate bill** → adds up those rows' units → one new `Electricity_Bill`
   row → stamps its `Bill_ID` on those readings. The next cycle starts.

### Sample data note
The PDF has no reading **dates**, so the app **assumes** Aug 1 → Sep 30, 2026
for the sample readings (`wattwatch/sample_data.py`). Say this in your report.
The names and numbers are **fictional** — don't present them as real customers.

### Look inside the database yourself
1. Install **DB Browser for SQLite** (free, from **sqlitebrowser.org**).
2. **Open Database** → `WATTWATCH\data\wattwatch.db`.
3. **Browse Data** tab → pick a table to see its rows.
4. **Execute SQL** tab → try the queries in Part 6.
5. ⚠️ **Close the database in DB Browser before using the app**, otherwise the
   app may say *"database is locked"*.

---

## Part 6 — Person 1: Database & Billing

**Your files:** `wattwatch/schema.sql`, `sample_data.py`, `db.py`, `tariff.py`, `config.py`

### Task 1.1 — Understand the database (week 1)
- Read Part 5 and `schema.sql` (it's short).
- Open the database in DB Browser and find Arun's reading.
- Be able to explain: primary key, foreign key, why `Units_Consumed` is calculated.

### Task 1.2 — Verify the tariff ⚠️ (most important)
The slab rates in `config.py` are an **example and not confirmed**.
1. Find the **current Tamil Nadu domestic tariff** on the official TNPDCL /
   TNERC websites (the tariff order).
2. Compare with `DEFAULT_SLABS` in `wattwatch/config.py`.
3. If different, update the numbers, run `python -m pytest`, and push (Part 4).
4. Note the source and date in your report.

### Task 1.3 — Bill check table
1. Collect 2–3 **real old bills** from your families.
2. For each, note units and amount, then check the calculator:
   ```
   python -c "from wattwatch.tariff import Tariff, calculate_bill; from wattwatch import config; print(calculate_bill(450, Tariff.from_rows(config.DEFAULT_SLABS)))"
   ```
   (replace 450 with the bill's units)
3. Table for the report:

   | Bill | Units | Real amount | App amount | Difference | Reason |
   |---|---|---|---|---|---|

### Task 1.4 — SQL queries for the report
Run these in DB Browser → **Execute SQL**, screenshot the results:
```sql
-- All households
SELECT * FROM Household;

-- Total units recorded per household
SELECT h.House_ID, h.Household_Name, SUM(m.Units_Consumed) AS Total_Units
FROM EB_Meter m JOIN Household h ON h.House_ID = m.House_ID
GROUP BY h.House_ID ORDER BY Total_Units DESC;

-- Households above 200 units in their latest reading period
SELECT House_ID, Units_Consumed FROM EB_Meter WHERE Units_Consumed > 200;

-- Bills not paid yet
SELECT * FROM Electricity_Bill WHERE Payment_Status <> 'Paid';
```

### Task 1.5 — Add your real homes (with permission)
Add your 3 homes as households in the app (sidebar → **Add a household**).
Only use real consumer numbers/addresses with your family's permission —
otherwise use made-up ones.

### Task 1.6 — Draw the ER diagram
Redraw the diagram from Part 5 neatly (draw.io is free) for the report.

---

## Part 7 — Person 2: Scanning & Prediction

**Your files:** `wattwatch/ocr.py`, `tracker.py`, `predictor.py`, `alerts.py`

### Task 2.1 — Understand the logic (week 1)
Read Steps 2–5 in `docs/GUIDE.md`. Be able to explain:
- **OCR**: photo → black & white → Tesseract reads digits → longest number.
- **Prediction**: units per day (slope of a straight line through recent readings) × days left.
- **Warning**: which slab limits lie between "now" and "predicted", and days until the next one.

### Task 2.2 — OCR accuracy test
1. Install Tesseract (Step 3.11).
2. Take **15–20 photos** of real meter displays: bright/dim, straight/tilted, close/far.
3. Upload each in **📷 Scan & Track** → **Read number from photo** (don't save it).
4. Record:

   | Photo | Real reading | App read | Correct? | Notes (glare, angle…) |
   |---|---|---|---|---|

5. **Accuracy = correct ÷ total × 100.** Example: 12 of 20 → 60%.

### Task 2.3 — Improve OCR and re-test
Ideas to try in `ocr.py` (change one thing at a time, re-test, compare):
- Crop photos close to the display before uploading — does accuracy improve?
- Change the black/white threshold (`128` in `preprocess`).
- Change Tesseract's `--psm 6` to `--psm 7` (treat image as one line of text).

Report before vs after accuracy. **A low number reported honestly is fine** —
it explains why the app lets users correct the reading.

### Task 2.4 — Prediction accuracy (with Part 9 data)
For each home: predicted units vs actual units at the end of the cycle.
**Error % = |predicted − actual| ÷ actual × 100.**

---

## Part 8 — Person 3: App, Saving plan & Demo

**Your files:** `app.py`, `wattwatch/appliances.py`

### Task 3.1 — Understand the screens (week 1)
Click through every tab. Open `app.py` and find the function for each tab
(`households_tab`, `scan_and_track`, `predict_and_warn`, `reduce_and_save`, `bills_tab`).

### Task 3.2 — Check appliance wattages
1. Look at the **sticker/label** on appliances at home (AC, geyser, fridge, motor, TV…). Note the **W (watts)**.
2. If only amps (A) are shown: watts ≈ 230 × amps (rough estimate).
3. Update `APPLIANCE_CATALOG` in `appliances.py` if the typical values are far off.

### Task 3.3 — Test on a phone
1. Laptop and phone on the **same Wi-Fi**.
2. When `streamlit run app.py` starts, it prints a **Network URL** (`http://192.168.x.x:8501`).
3. Open it on the phone. Note anything hard to use; fix small things in `app.py`.
   (If the phone can't connect, Windows Firewall may be blocking it.)

### Task 3.4 — Put it online for the demo
**Streamlit Community Cloud** can host it free: sign in with GitHub, choose the
repo, branch `main`, file `app.py`. Follow Streamlit's current docs for exact steps.
⚠️ Online, the database may be reset when the app restarts — fine for a demo,
not for long-term storage.

### Task 3.5 — Screenshots & demo script
Take screenshots of every tab for the report, and write the demo script
(Part 10).

---

## Part 9 — Real-world testing (all 3)

Each person tests at home for one billing cycle:
1. Add your home as a household (Task 1.5).
2. First reading: **📷 Scan & Track** asks for your meter number and the
   reading + date printed on your **last bill**, then today's reading.
3. Every **3–4 days**: read the meter, add the reading.
4. When the **real bill** arrives: click **Generate bill** in 🧾 Bills, then fill in:

   | Home | Predicted units (mid-cycle) | Actual units | App bill | Real bill | Error % |
   |---|---|---|---|---|---|

This table is the **strongest proof** your project works. If you don't have
time for a full cycle, test a shorter period and say so.

---

## Part 10 — Report & presentation

### Report structure
(Check your college's required format first — this is a common one.)
1. Abstract
2. Introduction — the slab billing problem
3. Objectives
4. Existing system — people only learn usage when the bill arrives
5. Proposed system — WATT-WATCH and its flow
6. System design — architecture, **ER diagram**, table descriptions
7. Modules — one section per person's files
8. Methods — bill calculation, prediction, warning, saving plan
9. Results — bill check table, OCR accuracy, prediction error, screenshots, SQL query results
10. Limitations — OCR accuracy, example tariff, assumed sample dates, no meter rollover
11. Future work — mobile app, logins, SMS reminders, better OCR
12. Conclusion
13. References — only sources you actually used

### Slides (about 12)
Problem → Solution → Flow → Architecture & database → Person 1's part →
Person 2's part → Person 3's part → Results → Live demo → Limitations → Future → Thank you

### Demo script (practise 3 times)
1. **Households** tab — "Here are our households from the database."
2. Pick a household → **Scan & Track** → upload a meter photo → read → add reading.
3. **Predict & Warn** — "It predicts X units and warns us before the next slab."
4. **Reduce & Save** — tick appliances → "Cutting AC by 1 hour saves Rs Y."
5. **Bills** — generate a bill, mark it Paid.

**Backup:** record a screen video of the demo in case the laptop or internet fails.

### Questions to prepare for
- Why a straight line for prediction? *Daily usage is fairly steady; we use recent readings so it adapts.*
- Why cut the biggest appliances first? *One hour of a 2000 W geyser saves as much as 20 hours of a 100 W TV.*
- What if OCR reads wrong? *The user sees and corrects the number before saving.*
- Why SQLite? *Built into Python, a single file, no server — enough for a household app.*
- Why is `Units_Consumed` calculated, not typed? *Prevents mistakes; the tip in the database document says the same.*
- What if the tariff changes? *Rates are in `config.py` and editable in the sidebar.*

---

## Part 11 — Troubleshooting

| Problem | Fix |
|---|---|
| `python` is not recognized | Reinstall Python with **Add to PATH** ticked, or use `py` |
| `(venv)` missing | Run `venv\Scripts\activate` |
| PowerShell says "running scripts is disabled" | Use **Command Prompt** (cmd) instead |
| `ModuleNotFoundError` | venv not active, or run `pip install -r requirements.txt` again |
| `database is locked` | Close the database in DB Browser, restart the app |
| Want fresh data | Sidebar → Database → Reset to sample data (or delete `data\wattwatch.db`) |
| `git push` rejected | Run `git pull` first, then push again |
| Merge conflict | Don't panic — ask the teammate who edited the same file, decide together which lines to keep |
| Tests fail after your change | Read the error; undo your last change and try again |
| Anything else | Copy the **exact** error message and ask for help |

---

## Part 12 — Glossary

| Word | Meaning |
|---|---|
| Terminal / Command Prompt | Window where you type commands |
| Repository (repo) | The project folder on GitHub |
| Clone | Download the repo to your laptop |
| Branch | Your own working copy |
| Commit | A save point |
| Push / Pull | Upload to / download from GitHub |
| Pull request (PR) | Asking to add your branch into `main` |
| Virtual environment (venv) | Private box for the project's packages |
| pip | Python's package installer |
| localhost | "This computer" |
| Database | Organised data in linked tables |
| SQLite | A database stored in a single file |
| Table / Row / Column | Sheet / one record / one field |
| Primary key (PK) | Unique ID of a row |
| Foreign key (FK) | Column that links to another table's row |
| SQL | The language for asking a database questions |
| OCR | Reading text/numbers from a picture |
| Slab | A range of units charged at one rate |
