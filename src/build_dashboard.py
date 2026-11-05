"""
build_dashboard.py — aggregates the clean data and bakes it into dashboard/index.html.

Run from the repo root (after clean.py):
    python src/build_dashboard.py

The dashboard is a single self-contained HTML file, so it can be opened locally
or hosted for free on GitHub Pages.
"""

import json
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "processed" / "deliveries.db"
TEMPLATE = ROOT / "dashboard" / "template.html"
OUT = ROOT / "dashboard" / "index.html"

DIMENSIONS = {
    "traffic": ("traffic", ["Low", "Medium", "High", "Jam"]),
    "slot": ("time_slot", ["Breakfast (6-11)", "Lunch (11-15)", "Evening snack (15-18)",
                           "Dinner (18-22)", "Late night (22-6)"]),
    "stack": ("stack_label", ["Single order", "+1 order", "+2 orders", "+3 orders"]),
    "distance": ("distance_band", ["Under 5 km", "5-10 km", "10-15 km", "15+ km"]),
    "weather": ("weather", ["Sunny", "Windy", "Stormy", "Sandstorms", "Cloudy", "Fog"]),
    "rating": ("rating_band", ["Below 4.0", "4.0-4.4", "4.5-4.7", "4.8-5.0"]),
    "city": ("city_label", None),
}


def load():
    con = sqlite3.connect(DB)
    df = pd.read_sql("SELECT * FROM deliveries", con)
    con.close()
    df["late"] = (df["delivery_min"] > 30).astype(int)
    df["city_label"] = df["city_name"]
    df["stack_label"] = df["multiple_deliveries"].map(
        {0: "Single order", 1: "+1 order", 2: "+2 orders", 3: "+3 orders"})
    df["distance_band"] = pd.cut(df["distance_km"], [0, 5, 10, 15, 100], right=False,
                                 labels=["Under 5 km", "5-10 km", "10-15 km", "15+ km"]).astype("string")
    df["rating_band"] = pd.cut(df["partner_rating"], [0, 4.0, 4.5, 4.8, 5.01], right=False,
                               labels=["Below 4.0", "4.0-4.4", "4.5-4.7", "4.8-5.0"]).astype("string")
    return df


def aggregate(df):
    """For every city (and 'All'), orders / late orders / total minutes per category."""
    out = {"cities": sorted(df["city_name"].unique().tolist()), "dims": {}}
    for key, (col, order) in DIMENSIONS.items():
        g = df.dropna(subset=[col]).groupby(["city_name", col]).agg(
            n=("late", "size"), late=("late", "sum"), mins=("delivery_min", "sum")).reset_index()
        cats = order or sorted(g[col].unique().tolist())
        rows = {}
        for city, sub in g.groupby("city_name"):
            sub = sub.set_index(col)
            rows[city] = [[int(sub.loc[c, "n"]), int(sub.loc[c, "late"]), int(sub.loc[c, "mins"])]
                          if c in sub.index else [0, 0, 0] for c in cats]
        out["dims"][key] = {"cats": cats, "rows": rows}
    out["partners"] = df.groupby("city_name")["partner_id"].nunique().astype(int).to_dict()
    return out


def main():
    data = aggregate(load())
    html = TEMPLATE.read_text().replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    OUT.write_text(html)
    print(f"Wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
