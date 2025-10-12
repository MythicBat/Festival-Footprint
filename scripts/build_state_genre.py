# scripts/build_state_genre.py
import math
import pandas as pd
from pathlib import Path

STATE_TOTALS = Path("data/festivals_by_state_2022_23.csv")
GENRE_PCT    = Path("data/festival_genres_percent.csv")
OUTPUT       = Path("data/festivals_by_state_genre.csv")

# ---------- load state totals ----------
st = pd.read_csv(STATE_TOTALS)
cols = {c.lower().strip(): c for c in st.columns}
state_col = cols.get("state_territory") or cols.get("state") or list(st.columns)[0]
count_col = cols.get("festival_count") or cols.get("count") or list(st.columns)[1]
st = st.rename(columns={state_col: "state", count_col: "festival_count"})
st["festival_count"] = pd.to_numeric(st["festival_count"], errors="coerce").fillna(0).astype(int)

# ---------- load genre percentages ----------
gp = pd.read_csv(GENRE_PCT)
gp_cols = {c.lower().strip(): c for c in gp.columns}

has_state = "state" in gp_cols.values() or "state_territory" in gp_cols.values()
genre_col = gp_cols.get("genre") or list(gp.columns)[0]
pct_col   = gp_cols.get("percent") or gp_cols.get("percentage") or list(gp.columns)[1]

if has_state:
    # per-state percentages
    s_col = gp_cols.get("state") or gp_cols.get("state_territory")
    gp = gp.rename(columns={s_col: "state", genre_col: "genre", pct_col: "percent"})
    gp["percent"] = pd.to_numeric(gp["percent"], errors="coerce")
    # normalize per state (sum → 1)
    gp["percent"] = gp["percent"] / gp.groupby("state")["percent"].transform("sum")
else:
    # national percentages → will be applied to every state
    gp = gp.rename(columns={genre_col: "genre", pct_col: "percent"})
    gp["percent"] = pd.to_numeric(gp["percent"], errors="coerce")
    total = gp["percent"].sum()
    if not math.isclose(total, 1.0, rel_tol=1e-3) and not math.isclose(total, 100.0, rel_tol=1e-2):
        # normalize if not 1 or 100
        gp["percent"] = gp["percent"] / total
    elif math.isclose(total, 100.0, rel_tol=1e-2):
        gp["percent"] = gp["percent"] / 100.0
    # broadcast to all states
    gp["key"] = 1
    st_tmp = st[["state"]].copy()
    st_tmp["key"] = 1
    gp = st_tmp.merge(gp, on="key").drop(columns="key")

# ---------- compute integer counts with largest remainder per state ----------
rows = []
for state, block in gp.groupby("state"):
    total_state = int(st.loc[st["state"] == state, "festival_count"].sum())
    if total_state == 0:
        continue

    # initial floor allocation
    block = block.copy()
    block["raw"] = block["percent"] * total_state
    block["base"] = block["raw"].apply(math.floor).astype(int)
    remainder = total_state - int(block["base"].sum())

    # distribute remaining +1 to the largest fractional parts
    block["frac"] = block["raw"] - block["base"]
    block = block.sort_values("frac", ascending=False)
    block.iloc[:remainder, block.columns.get_loc("base")] += 1

    # output rows
    for _, r in block.iterrows():
        rows.append({"state": state, "genre": r["genre"], "count": int(r["base"])})

out = pd.DataFrame(rows).sort_values(["state", "genre"])
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUTPUT, index=False)

print(f"✅ Wrote {OUTPUT} ({len(out)} rows)")
print("States:", ", ".join(sorted(out['state'].unique())))
print("Genres:", ", ".join(sorted(out['genre'].unique())))
