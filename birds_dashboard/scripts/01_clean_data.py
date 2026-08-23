"""
Bird Species Observation Analysis — Data Cleaning & Consolidation
"""
import argparse
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BOOL_COLS = [
    "Flyover_Observed", "PIF_Watchlist_Status", "Regional_Stewardship_Status",
    "Initial_Three_Min_Cnt", "Previously_Obs",
]
NUMERIC_COLS = ["Temperature", "Humidity", "Visit", "AcceptedTSN"]
STRING_COLS = [
    "Admin_Unit_Code", "Sub_Unit_Code", "Site_Name", "Plot_Name", "Location_Type",
    "Observer", "Interval_Length", "ID_Method", "Distance", "Sex", "Common_Name",
    "Scientific_Name", "NPSTaxonCode", "AOU_Code", "Sky", "Wind", "Disturbance",
]
COLUMN_ALIASES = {"TaxonCode": "NPSTaxonCode"}


def load_all_sheets(paths):
    frames = []
    for path in paths:
        xls = pd.ExcelFile(path)
        for sheet_name in xls.sheet_names:
            df = xls.parse(sheet_name)
            if df.empty:
                continue
            df = df.rename(columns=COLUMN_ALIASES)
            if "Admin_Unit_Code" not in df.columns:
                df["Admin_Unit_Code"] = sheet_name
            else:
                df["Admin_Unit_Code"] = df["Admin_Unit_Code"].fillna(sheet_name)
            df["Source_File"] = Path(path).name
            frames.append(df)
        print(f"  {Path(path).name}: {len(xls.sheet_names)} sheets")
    if not frames:
        raise ValueError(f"No non-empty sheets found in {paths}")
    combined = pd.concat(frames, ignore_index=True, sort=False)
    print(f"Loaded {len(frames)} sheets total, {len(combined)} raw rows.")
    return combined


def clean(df):
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    before = len(df)
    df = df.drop_duplicates()
    print(f"Dropped {before - len(df)} exact duplicate rows.")

    for col in STRING_COLS:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Month"] = df["Date"].dt.month
        df["Season"] = df["Month"].map(_month_to_season)

    if "Year" in df.columns:
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
        if "Date" in df.columns:
            df["Year"] = df["Year"].fillna(df["Date"].dt.year)
        df["Year"] = df["Year"].astype("Int64")

    for col in BOOL_COLS:
        if col in df.columns:
            df[col] = _to_bool(df[col])

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "Location_Type" in df.columns:
        df["Location_Type"] = df["Location_Type"].str.title()

    for col in ["Sex", "Sky", "Wind", "Disturbance", "ID_Method"]:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown")

    if "Scientific_Name" in df.columns:
        before = len(df)
        df = df.dropna(subset=["Scientific_Name"])
        print(f"Dropped {before - len(df)} rows with no species identified.")

    if "Temperature" in df.columns:
        df["Temperature_Outlier"] = ~df["Temperature"].between(-20, 120) & df["Temperature"].notna()
    if "Humidity" in df.columns:
        df["Humidity_Outlier"] = ~df["Humidity"].between(0, 100) & df["Humidity"].notna()

    df = df.reset_index(drop=True)
    df.insert(0, "Observation_ID", df.index + 1)
    return df


def _month_to_season(month):
    if pd.isna(month):
        return np.nan
    month = int(month)
    return {12: "Winter", 1: "Winter", 2: "Winter",
            3: "Spring", 4: "Spring", 5: "Spring",
            6: "Summer", 7: "Summer", 8: "Summer",
            9: "Fall", 10: "Fall", 11: "Fall"}[month]


def _to_bool(series):
    mapping = {
        "true": True, "false": False, "yes": True, "no": False,
        "1": True, "0": False, "1.0": True, "0.0": False,
    }
    def convert(v):
        if pd.isna(v):
            return pd.NA
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(v)
        return mapping.get(str(v).strip().lower(), pd.NA)
    return series.map(convert)


def write_outputs(df, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "cleaned_bird_data.csv"
    db_path = out_dir / "bird_observations.db"

    df.to_csv(csv_path, index=False)
    print(f"Wrote cleaned CSV: {csv_path} ({len(df)} rows)")

    conn = sqlite3.connect(db_path)
    db_df = df.copy()
    for col in BOOL_COLS + ["Temperature_Outlier", "Humidity_Outlier"]:
        if col in db_df.columns:
            db_df[col] = db_df[col].astype("boolean").astype("Int64")
    if "Date" in db_df.columns:
        db_df["Date"] = db_df["Date"].dt.strftime("%Y-%m-%d")
    db_df.to_sql("observations", conn, if_exists="replace", index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_admin_unit ON observations(Admin_Unit_Code);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_location_type ON observations(Location_Type);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_species ON observations(Scientific_Name);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_year ON observations(Year);")
    conn.commit()
    conn.close()
    print(f"Wrote SQLite DB: {db_path} (table: observations)")


def main():
    parser = argparse.ArgumentParser(description="Clean and consolidate bird observation data.")
    parser.add_argument("--input", type=str, nargs="+", default=["data/sample_bird_data.xlsx"])
    parser.add_argument("--outdir", type=str, default="data")
    args = parser.parse_args()

    input_paths = [Path(p) for p in args.input]
    missing = [p for p in input_paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"ERROR: input file not found: {p}", file=sys.stderr)
        sys.exit(1)

    raw = load_all_sheets(input_paths)
    cleaned = clean(raw)
    write_outputs(cleaned, Path(args.outdir))

    print("\nSummary:")
    print(f"  Rows: {len(cleaned)}")
    print(f"  Admin units: {sorted(cleaned['Admin_Unit_Code'].dropna().unique().tolist())}")
    print(f"  Species: {cleaned['Scientific_Name'].nunique()}")
    print(f"  Years: {sorted(cleaned['Year'].dropna().unique().tolist())}")


if __name__ == "__main__":
    main()
