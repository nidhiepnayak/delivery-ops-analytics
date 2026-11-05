"""
clean.py — turns the raw food-delivery export into an analysis-ready table.

Run from the repo root:
    python src/clean.py

Outputs:
    data/processed/deliveries_clean.csv
    data/processed/deliveries.db   (SQLite, table: deliveries)
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "food_delivery_raw.csv"
OUT_DIR = ROOT / "data" / "processed"

# City code (prefix of the delivery-partner ID) -> city name
CITY_NAMES = {
    "JAP": "Jaipur", "RANCHI": "Ranchi", "BANG": "Bengaluru", "SUR": "Surat",
    "HYD": "Hyderabad", "MUM": "Mumbai", "MYS": "Mysuru", "COIMB": "Coimbatore",
    "VAD": "Vadodara", "INDO": "Indore", "CHEN": "Chennai", "PUNE": "Pune",
    "AGR": "Agra", "LUDH": "Ludhiana", "KNP": "Kanpur", "ALH": "Prayagraj",
    "DEH": "Dehradun", "GOA": "Goa", "AURG": "Aurangabad", "KOC": "Kochi",
    "KOL": "Kolkata", "BHP": "Bhopal",
}


def haversine_km(lat1, lon1, lat2, lon2):
    """Straight-line distance between two points on Earth, in km."""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def time_slot(hour):
    if pd.isna(hour):
        return np.nan
    if 6 <= hour < 11:
        return "Breakfast (6-11)"
    if 11 <= hour < 15:
        return "Lunch (11-15)"
    if 15 <= hour < 18:
        return "Evening snack (15-18)"
    if 18 <= hour < 22:
        return "Dinner (18-22)"
    return "Late night (22-6)"


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()

    # 1. Strip stray whitespace and turn the literal string "NaN" into real missing values
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype("string").str.strip().replace({"NaN": pd.NA, "": pd.NA})

    # 2. Fix messy text formats
    df["Time_taken(min)"] = df["Time_taken(min)"].str.extract(r"(\d+)")[0].astype(int)
    df["Weatherconditions"] = df["Weatherconditions"].str.replace("conditions ", "", regex=False)
    df["Weatherconditions"] = df["Weatherconditions"].replace({"NaN": pd.NA})
    df["City"] = df["City"].replace({"Metropolitian": "Metropolitan"})

    # 3. Correct data types
    for col in ["Delivery_person_Age", "Delivery_person_Ratings", "multiple_deliveries"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 4. Drop impossible values (ages under 18, ratings above the 5-star scale)
    df.loc[df["Delivery_person_Age"] < 18, "Delivery_person_Age"] = np.nan
    df.loc[df["Delivery_person_Ratings"] > 5, "Delivery_person_Ratings"] = np.nan

    # 5. Coordinates: negative values are sign errors; zeros are missing
    coord_cols = ["Restaurant_latitude", "Restaurant_longitude",
                  "Delivery_location_latitude", "Delivery_location_longitude"]
    df[coord_cols] = df[coord_cols].abs()
    bad_coords = (df["Restaurant_latitude"] < 1) | (df["Restaurant_longitude"] < 1)
    dist = haversine_km(df["Restaurant_latitude"], df["Restaurant_longitude"],
                        df["Delivery_location_latitude"], df["Delivery_location_longitude"])
    df["distance_km"] = np.where(bad_coords, np.nan, dist.round(2))

    # 6. Dates and times
    df["order_date"] = pd.to_datetime(df["Order_Date"], format="%d-%m-%Y")
    df["weekday"] = df["order_date"].dt.day_name()
    ordered = pd.to_datetime(df["Time_Orderd"], format="%H:%M:%S", errors="coerce")
    picked = pd.to_datetime(df["Time_Order_picked"], format="%H:%M:%S", errors="coerce")
    df["order_hour"] = ordered.dt.hour
    wait = (picked - ordered).dt.total_seconds() / 60
    wait = wait.where(wait >= 0, wait + 24 * 60)  # orders that cross midnight
    df["pickup_wait_min"] = wait
    df["time_slot"] = df["order_hour"].apply(time_slot)

    # 7. Partner city from the partner ID (e.g. BANGRES18DEL02 -> BANG -> Bengaluru)
    df["city_code"] = df["Delivery_person_ID"].str.split("RES").str[0]
    df["city_name"] = df["city_code"].map(CITY_NAMES)

    # 8. Tidy column names
    df = df.rename(columns={
        "ID": "order_id", "Delivery_person_ID": "partner_id",
        "Delivery_person_Age": "partner_age", "Delivery_person_Ratings": "partner_rating",
        "Weatherconditions": "weather", "Road_traffic_density": "traffic",
        "Vehicle_condition": "vehicle_condition", "Type_of_order": "order_type",
        "Type_of_vehicle": "vehicle_type", "multiple_deliveries": "multiple_deliveries",
        "Festival": "festival", "City": "area_type", "Time_taken(min)": "delivery_min",
    })

    keep = ["order_id", "partner_id", "city_code", "city_name", "area_type",
            "partner_age", "partner_rating", "order_date", "weekday", "order_hour",
            "time_slot", "pickup_wait_min", "weather", "traffic", "vehicle_type",
            "vehicle_condition", "order_type", "multiple_deliveries", "festival",
            "distance_km", "delivery_min"]
    return df[keep]


def main():
    raw = pd.read_csv(RAW)
    df = clean(raw)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_DIR / "deliveries_clean.csv", index=False)

    db = sqlite3.connect(OUT_DIR / "deliveries.db")
    sql_df = df.copy()
    sql_df["order_date"] = sql_df["order_date"].dt.strftime("%Y-%m-%d")
    sql_df.to_sql("deliveries", db, if_exists="replace", index=False)
    db.close()

    print(f"Raw rows: {len(raw):,}  ->  clean rows: {len(df):,}")
    print("Missing values after cleaning:")
    print(df.isna().sum()[df.isna().sum() > 0].to_string())


if __name__ == "__main__":
    main()
