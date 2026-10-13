# ⚡ WATT-WATCH

Smart electricity bill warning and saving assistant for households.

**Scan → Track → Predict → Warn → Reduce → Save** 🌱

WATT-WATCH tracks electricity use from simple meter readings, predicts the
final bill for the billing cycle, warns early if usage is heading into a
costlier tariff slab, and suggests which appliances to cut back to save money.

## Quick start

```bash
# 1. Install Python packages
pip install -r requirements.txt

# 2. (Optional, for reading meter photos) install the Tesseract OCR program
#    Ubuntu/Debian:  sudo apt install tesseract-ocr
#    macOS:          brew install tesseract
#    Windows:        install from the UB Mannheim Tesseract builds, then add it to PATH

# 3. Run the app
streamlit run app.py

# 4. Run the tests
python -m pytest
```

Without Tesseract the app still works: you type the meter reading instead of
scanning it.

## Project layout

| File | What it does |
|------|--------------|
| `app.py` | Streamlit user interface (sidebar + 3 tabs) |
| `wattwatch/config.py` | Default tariff slabs, cycle length, CO2 factor |
| `wattwatch/tariff.py` | Slab-based bill calculator |
| `wattwatch/tracker.py` | Meter readings, units used, saving/loading data |
| `wattwatch/predictor.py` | Usage rate and end-of-cycle bill prediction |
| `wattwatch/alerts.py` | Early warning before crossing a slab limit |
| `wattwatch/appliances.py` | Appliance list, saving plan, savings estimate |
| `wattwatch/ocr.py` | Reads the number from a meter photo |
| `tests/test_wattwatch.py` | Unit tests for the logic above |

A full step-by-step explanation of the code is in [docs/GUIDE.md](docs/GUIDE.md).

## ⚠️ Check the tariff

The default slab rates in `wattwatch/config.py` are an **example** of the
Tamil Nadu domestic bi-monthly tariff. Tariffs are revised from time to time,
so verify them against the current tariff order (TNERC / your distribution
company) and edit them in `config.py` or in the app sidebar.
