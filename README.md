# Uganda Road Traffic Crash Data Warehouse (2011–2020)

MIT725 Data Warehousing and Data Mining — CAT 1.

Source: *Causes of road traffic crashes in Uganda, 2011–2020* (Uganda Police annual crime reports), supplied as course material.

## Contents

| Path | What it is |
|---|---|
| `data/causes-of-road-traffic-crashes-in-uganda-2011-2020.xlsx` | Raw file as supplied |
| `data/uganda_crash_causes_clean_wide.csv` | Cleaned table, one row per Year × Cause (Fatal, Serious, Minor, Total, Factor, Flag) |
| `data/uganda_crash_causes_clean_long.csv` | Tidy version: Year, Cause, Factor, Severity, Crashes, Flag |
| `data/uganda_crashes_by_factor.csv` | One row per year with Population_Behavior, Road_Environment, Motor_Vehicle_Condition, Unattributed, Total_Road_Traffic_Accidents |
| `clean_data.py` | Reproducible cleaning script (raw xlsx → the three CSVs) |
| `CAT1_analysis.ipynb` | Loads the CSVs from this repo's raw GitHub URLs and builds the correlation heatmap |
| `figures/` | Heatmap and trend chart |

## Cleaning steps

1. Reshaped the two-row-header, year-by-block layout into tidy tables.
2. **2012 Careless Pedestrian** was a duplicate of the 2012 alcohol row (15/87/114/216). Replaced with values recovered from the official 2012 column totals: 216/508/355/1,079.
3. **2020 Dazzled by Lights**: Minor recorded as 0. Corrected to 7 using the row total (20) and the Minor column total.
4. **2011 Dangerous Loading** was blank. Derived as 281 (official 2011 total minus all other causes).
5. **2016 Defective Mechanical Condition** was not reported. Interpolated from 2015 and 2017 (482) so the vehicle-condition series has no false dip. Total_Road_Traffic_Accidents keeps the official figure.
6. **Other Causes 2016–2019** were not reported. Set to 0 because the official totals reconcile without them.
7. Six 2016 rows where Fatal+Serious+Minor ≠ Total by ±1: kept the Total and flagged the row.
8. 2011 is published as totals only, so the severity split is left missing.
9. Renamed `DMC` → `Defective Mechanical Condition`, standardised types, and added a `Flag` column documenting every change.

Every yearly total is checked against the official totals row (`assert` in `clean_data.py`).

## Factor grouping

* **Population_Behavior**: careless driving, reckless driving, over-speeding, drink-driving, careless pedestrian, passenger falls from vehicle
* **Motor_Vehicle_Condition**: defective mechanical condition, over-loading, dangerous loading
* **Road_Environment**: obstacle on carriageway, dazzled by lights
* **Unattributed** (in the total only): unknown cause, other causes
