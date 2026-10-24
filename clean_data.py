"""
CAT 1 - Q1: Clean the Uganda road-traffic-crash causes dataset (2011-2020).

Input : data/raw.xlsx  (wide layout: two header rows, one 4-column block per year)
Output: data/uganda_crash_causes_clean_long.csv   tidy: Year, Cause, Severity, Crashes, Flag
        data/uganda_crash_causes_clean_wide.csv   one row per Year x Cause (Fatal/Serious/Minor/Total)
        data/uganda_crashes_by_factor.csv         one row per Year with the grouped analysis variables
"""
import sys
import numpy as np
import pandas as pd

RAW = sys.argv[1] if len(sys.argv) > 1 else "data/causes-of-road-traffic-crashes-in-uganda-2011-2020.xlsx"
OUT = "data/"

raw = pd.read_excel(RAW, header=None)

# ---------------------------------------------------------------- 1. reshape
# Row 0 holds the year (only on the first column of each block), row 1 the severity.
years = raw.iloc[0].ffill()
sev = raw.iloc[1].astype(str).str.strip()
body = raw.iloc[2:15].copy()             # 13 cause rows; row 15 is the official "Total" row
official_total = raw.iloc[15]

records = []
for c in range(1, raw.shape[1]):
    yr = int(years[c])
    for _, row in body.iterrows():
        records.append({"Year": yr, "Cause": str(row[0]).strip(), "Severity": sev[c],
                        "Crashes": pd.to_numeric(row[c], errors="coerce")})
long = pd.DataFrame(records)
long["Flag"] = ""

# The sheet labels the last column "2011 Total" but the 2012 block has 4 columns and 2011 only 1:
# headers in row 0 sit on the first column of each block, so ffill assigns them correctly.

wide = long.pivot_table(index=["Year", "Cause"], columns="Severity", values="Crashes",
                        aggfunc="first", dropna=False).reset_index()
wide = wide[["Year", "Cause", "Fatal", "Serious", "Minor", "Total"]]
wide["Flag"] = ""

def fix(year, cause, **vals):
    m = (wide.Year == year) & (wide.Cause == cause)
    for k, v in vals.items():
        wide.loc[m, k] = v
    return m

# ---------------------------------------------------------------- 2. fix errors
# (a) 2012 "Careless Pedestrian" is a copy of the 2012 "Under Influence of Alcohol" row (15/87/114/216).
#     The 2012 column totals are short by exactly 201/421/241/863, so the true row is recoverable.
m = fix(2012, "Careless Pedestrian", Fatal=15 + 201, Serious=87 + 421, Minor=114 + 241, Total=216 + 863)
wide.loc[m, "Flag"] = "duplicated row replaced; recovered from official column totals"

# (b) 2020 "Dazzled by Lights": Minor recorded as 0 but row total is 20 and the Minor column
#     total is short by 7 -> Minor = 7.
m = fix(2020, "Dazzled by Lights", Minor=7)
wide.loc[m, "Flag"] = "typo: Minor 0 -> 7 (row & column totals)"

# (c) 2011 "Dangerous Loading" blank; 2011 grand total exceeds the sum of causes by 281.
m = fix(2011, "Dangerous Loading", Total=22272 - 21991)
wide.loc[m, "Flag"] = "missing; derived as official total minus other causes"

# (d) "DMC" (defective mechanical condition) not reported for 2016. It is the core vehicle
#     variable, so a 0 would create a false dip. Impute by linear interpolation of neighbours.
dmc = wide[wide.Cause == "DMC"].set_index("Year").sort_index()
for col in ["Fatal", "Serious", "Minor", "Total"]:
    dmc[col] = dmc[col].interpolate().round()
for col in ["Fatal", "Serious", "Minor", "Total"]:
    wide.loc[(wide.Cause == "DMC") & (wide.Year == 2016), col] = dmc.loc[2016, col]
wide.loc[(wide.Cause == "DMC") & (wide.Year == 2016), "Flag"] = "not reported; interpolated (2015/2017)"

# (e) "Other Causes" not reported 2017-2019. Column totals reconcile without it, so the true value is 0.
m = (wide.Cause == "Other Causes") & wide.Total.isna()
wide.loc[m, ["Fatal", "Serious", "Minor", "Total"]] = 0
wide.loc[m, "Flag"] = "not reported; set to 0 (totals reconcile)"

# (f) 2011 is published as totals only -> severity split stays missing (genuinely unknown).
wide.loc[(wide.Year == 2011) & (wide.Flag == ""), "Flag"] = "2011 published as totals only"

# (g) Five 2016 rows have Fatal+Serious+Minor off by +/-1 from Total. The Total column reconciles
#     with the official grand total, so Total is kept and the row is flagged.
off = (wide.Year == 2016) & (wide.Flag == "") & wide.Fatal.notna() &((wide.Fatal + wide.Serious + wide.Minor) != wide.Total)
wide.loc[off, "Flag"] = "F+S+M differs from Total by 1; Total kept"

# ---------------------------------------------------------------- 3. tidy text & types
wide["Cause"] = wide.Cause.replace({"DMC": "Defective Mechanical Condition"})
for col in ["Fatal", "Serious", "Minor", "Total"]:
    wide[col] = wide[col].astype("Int64")
wide = wide.drop_duplicates().sort_values(["Year", "Total"], ascending=[True, False]).reset_index(drop=True)
assert wide.Total.notna().all() and (wide.Total >= 0).all()

# validate against the official yearly totals
off_tot = {int(y): int(official_total[c]) for c, y in years.items()
           if c > 0 and sev[c] == "Total"}
check = wide.groupby("Year").Total.sum()
check.loc[2016] -= int(dmc.loc[2016, "Total"])   # imputed value is outside the official total
assert all(check[y] == off_tot[y] for y in off_tot), (check, off_tot)

# ---------------------------------------------------------------- 4. group into analysis factors
FACTOR = {
    # human / road-user behaviour
    "Careless Driving": "Population_Behavior", "Reckless Driving": "Population_Behavior",
    "Over Speeding": "Population_Behavior", "Under Influence of Alcohol": "Population_Behavior",
    "Careless Pedestrian": "Population_Behavior", "Passenger Falls from Vehicle": "Population_Behavior",
    # vehicle and its load
    "Defective Mechanical Condition": "Motor_Vehicle_Condition",
    "Over Loading": "Motor_Vehicle_Condition", "Dangerous Loading": "Motor_Vehicle_Condition",
    # road and its surroundings
    "Obstacle on Carriage Way": "Road_Environment", "Dazzled by Lights": "Road_Environment",
    # not attributable
    "Unknown Cause": "Unattributed", "Other Causes": "Unattributed",
}
wide.insert(2, "Factor", wide.Cause.map(FACTOR))
assert wide.Factor.notna().all()

by_factor = wide.pivot_table(index="Year", columns="Factor", values="Total", aggfunc="sum")
by_factor["Total_Road_Traffic_Accidents"] = pd.Series(off_tot)          # official published totals
by_factor = by_factor[["Population_Behavior", "Road_Environment", "Motor_Vehicle_Condition",
                       "Unattributed", "Total_Road_Traffic_Accidents"]].astype(int).reset_index()

tidy = wide.melt(id_vars=["Year", "Cause", "Factor", "Flag"], value_vars=["Fatal", "Serious", "Minor"],
                 var_name="Severity", value_name="Crashes").dropna(subset=["Crashes"])
tidy = tidy[["Year", "Cause", "Factor", "Severity", "Crashes", "Flag"]]

wide.to_csv(OUT + "uganda_crash_causes_clean_wide.csv", index=False)
tidy.to_csv(OUT + "uganda_crash_causes_clean_long.csv", index=False)
by_factor.to_csv(OUT + "uganda_crashes_by_factor.csv", index=False)

print(wide[wide.Flag != ""][["Year", "Cause", "Fatal", "Serious", "Minor", "Total", "Flag"]].to_string())
print()
print(by_factor.to_string(index=False))
