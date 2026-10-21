# WATT-WATCH — Submission form answers

## Title of the idea

WATT-WATCH: Smart Electricity Bill Warning and Saving Assistant for Households

## Selected national theme

[Choose from your competition's list — best fits: Sustainable / Clean Energy, Smart Automation, or Clean & Green Technology]

## Selected solution track

[Choose from your competition's list — best fits: Energy Efficiency / Smart Energy Management, or Software / Web Application]

## Problem statement

Households in Tamil Nadu are billed every two months on a slab tariff, where each extra unit costs more once usage crosses a slab limit. Families have no simple way to track their usage during the billing cycle, so they discover a costly slab jump only when the bill arrives, when it is too late to act.

## Description of the problem

Domestic electricity in Tamil Nadu is billed on a bi-monthly, slab-based ("telescopic") tariff. Each unit is charged at the rate of the slab it falls into, and the rate rises as total consumption grows. Under the domestic (LT IA) rates used in our prototype, based on TNERC Tariff Order No. 6 of 2025, a unit costs Rs 4.80 up to 400 units, Rs 6.45 from 401 to 500 units, Rs 8.55 from 501 to 600 units, and more in the higher slabs. A unit in the 401–500 slab therefore costs about 34% more than a unit below 400, and a unit in the 501–600 slab about 78% more.

This makes the last part of the billing cycle decisive. In our prototype's calculation, which applies the slab rates with the first 100 units free under the Government subsidy, the energy charge for 400 units is Rs 1,440, for 500 units Rs 2,085, and for 600 units Rs 2,940. A family using a little more than usual, for example during a hot month with more air-conditioner use, can move into a costlier slab without noticing.

The core problem is a lack of timely information:

1. **No tracking during the cycle.** The meter is in the house, but almost no family reads it regularly or knows how many units they have used since the last bill.
2. **No prediction.** Even a family that reads the meter cannot easily work out what the final bill will be at the current rate of use.
3. **No early warning.** There is nothing that tells a household, days or weeks in advance, that it is heading into a more expensive slab.
4. **No practical guidance.** Generic energy-saving tips do not say which of the family's own appliances to use less, by how many hours, and how much that would save.

As a result, households react only after the bill arrives, when the units are already consumed and the higher slab rate already applies. The information that could have changed their behaviour existed all along on their own meter, but it was never turned into a timely, understandable warning.

Existing approaches do not close this gap. The bill itself is a record of the past cycle. Smart meters and home energy monitors can show live usage, but they need extra hardware and installation, and they do not translate usage into a slab-aware bill forecast with a household-specific saving plan.

There is therefore a need for a simple, low-cost tool that uses the meter a household already has, predicts the bill before it arrives, warns before a slab jump, and tells the family exactly what to change.

## Description of the proposed solution

WATT-WATCH is a web application that helps households see their electricity bill coming before it arrives. It follows a simple flow: **Scan → Track → Predict → Warn → Reduce → Save**. It needs no extra hardware: only the household's existing meter and a phone or computer with a browser.

**1. Scan the meter.** The user uploads a photo of the meter or types the reading. For photos, the app cleans the image (grayscale, enlarge, contrast, noise removal, black-and-white) and uses Tesseract OCR, restricted to digits, to read the number. Because OCR can make mistakes on real meter displays, the detected number is always shown to the user to confirm or correct before it is saved.

**2. Track usage.** Each reading is stored with its date. Units used so far in the billing cycle are calculated as the latest reading minus the reading at the start of the cycle (the reading on the last bill). Units are always calculated, never typed, which prevents errors. The app also rejects impossible readings, such as a reading lower than the previous one, since a meter only counts up.

**3. Predict the bill.** The app estimates the household's rate of use (units per day) as the slope of a straight line fitted to recent readings using least squares. It then predicts the units at the end of the 60-day cycle as units so far plus units per day times days left, and calculates the predicted bill using the slab tariff.

**4. Warn early.** The app checks which slab limits lie between the units used so far and the predicted units. If a costlier slab will be crossed, it shows a clear warning: roughly how many days remain before the limit is crossed, the predicted units and bill, how many units must be cut to stay within the cheaper slab, and how much money that would save. The free-units limit is ignored, so the app only warns about slabs that actually cost more. Warnings are marked as critical when the next limit is seven days away or less, or when more than one limit will be crossed.

**5. Reduce usage with a saving plan.** The user selects the appliances they use (for example air conditioner, water heater, motor pump, television, fans), with wattage and daily hours. Typical wattages are pre-filled and can be changed to match each appliance's label. The daily energy of each appliance is calculated as watts × quantity × hours ÷ 1000. The app then builds a saving plan: it cuts hours from the most power-hungry, non-essential appliances first, because one hour of a 2,000 W water heater saves as much energy as 20 hours of a 100 W television. To keep the plan realistic, no appliance is cut by more than half of its hours, and essential appliances such as the refrigerator are never cut.

**6. See the savings.** The app shows the units and money saved over the rest of the cycle and the new predicted bill. Because savings are calculated with the slab tariff, they reflect the higher price of the units that are avoided.

**Billing and records.** At the end of a cycle, the app generates a bill from the recorded readings and stores it with a payment status (Paid, Unpaid or Pending), so the household keeps a history across cycles.

**Technology.** WATT-WATCH is built in Python. The web interface uses Streamlit and opens with a welcome pop-up that explains the four main steps, followed by four tabs: Scan & Track, Predict & Warn, Reduce & Save, and Bills. Data is stored in an SQLite database with three linked tables: Household, EB_Meter (meter readings) and Electricity_Bill. The tariff slabs are kept in one configuration file and can also be edited in the app, so the tool can be updated when the tariff is revised. The calculation logic is covered by 33 automated tests.

**Worked example (prototype, sample household).** A sample household that used 300 units in the previous cycle records a new reading showing 160 units used in the first 18 days of the current cycle (about 8.9 units per day). WATT-WATCH predicts about 533 units and a bill of about Rs 2,370 for the cycle, and warns that the household will cross 400 units in about 27 days. It advises cutting about 33 units to stay within 500 units. The saving plan suggests reducing the water heater from one hour to half an hour a day, which saves about 42 units and Rs 341 over the rest of the cycle and keeps the household below the 500-unit slab.

**Current status.** A working prototype has been built and demonstrated using sample household records. Next steps are a pilot with real households over full billing cycles to measure prediction accuracy, testing OCR on real meter photos, adding a Tamil-language interface and reading reminders, and an installable mobile version.

## Expected impact

**For households: lower bills through timely action.** The main impact is financial. By predicting the bill weeks in advance and warning before a slab limit is crossed, WATT-WATCH gives families time to change their behaviour while it still makes a difference. Because units above each slab limit are charged at a higher rate, avoiding a slab jump saves more than an equal reduction elsewhere. In our prototype example, reducing water-heater use by half an hour a day saved about Rs 341 in one cycle and kept the household below the 500-unit slab.

**Awareness and better habits.** Regularly reading the meter and seeing units per day makes electricity use visible. The appliance-level saving plan turns general advice into specific actions ("use the water heater for 30 minutes instead of an hour"), which households are more likely to follow. Over time, this can build lasting energy-saving habits.

**Accessible and low-cost.** WATT-WATCH needs no smart meter, sensor or installation. It works with the meter every household already has and runs in any web browser on a phone or computer. This makes it suitable for households that cannot afford or access smart-metering devices.

**Benefits beyond the household.** When many households reduce avoidable consumption, overall demand on the electricity grid falls. Lower electricity use also means less fuel burned for generation, which helps reduce the environmental impact of power use.

**Scalable and adaptable.** The tariff is stored as a simple editable table, so the tool can be updated when tariffs change and adapted to other states or consumer categories with slab-based billing. The same database and logic could support a community, apartment association or distribution company running awareness programmes across many households.

**Measurable outcomes.** In a pilot, impact can be measured by comparing predicted and actual bills (prediction accuracy), counting slab crossings avoided, and recording units and money saved per household per cycle.

## Concept Note in PDF format

See `WATT-WATCH_Concept_Note.pdf` (generated from this content, under 10 MB).

## Supporting documents

- Presentation slides: `docs/presentation/WATT-WATCH_Presentation.pdf`
- App screenshots: `docs/presentation/screenshots/`
- Source code: https://github.com/ZumairaSultana/WATTWATCH (branch `claude/code-implementation-guide-fqx9ks`)

## Video link

Upload `docs/presentation/WATT-WATCH_Demo.mp4` to YouTube (Unlisted) or Google Drive (Anyone with the link → Viewer) and paste the link here.
