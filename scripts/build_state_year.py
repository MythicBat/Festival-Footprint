# scripts/build_state_year.py
import pandas as pd
from pathlib import Path

INPUT = Path("data/festivals_by_state_2022_23.csv")
OUTPUT = Path("data/festivals_by_state_year.csv")

# --- Load FY2022–23 totals (for shares) ---
df = pd.read_csv(INPUT)

# Normalize headers (edit if your columns differ)
cols = {c.lower().strip(): c for c in df.columns}
state_col = cols.get("state_territory") or cols.get("state") or list(df.columns)[0]
count_col = cols.get("festival_count") or cols.get("count") or list(df.columns)[1]

df = df.rename(columns={state_col: "state", count_col: "festival_count"})
df["festival_count"] = pd.to_numeric(df["festival_count"], errors="coerce").fillna(0).astype(int)

# Compute state shares from FY22–23
baseline_total = int(df["festival_count"].sum())
shares = (df.set_index("state")["festival_count"] / baseline_total).to_dict()

# Year index (tweak if you want)
year_index = {
    2016: 0.85,
    2017: 0.90,
    2018: 0.96,
    2019: 1.00,
    2020: 0.45,
    2021: 0.60,
    2022: 0.85,
    2023: 1.00,
}

# Allocate totals to states
rows = []
for year, idx in year_index.items():
    national_total = round(baseline_total * idx)
    for st, share in shares.items():
        rows.append({
            "year": year,
            "state": st,                         # keep your exact state labels
            "festival_count": int(round(national_total * share))
        })

out = pd.DataFrame(rows).sort_values(["year", "state"])

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUTPUT, index=False)

print(f"✅ Wrote {OUTPUT} ({len(out)} rows)")
print(f"Baseline total (FY22–23): {baseline_total}")
print("States:", ", ".join(sorted(shares.keys())))
