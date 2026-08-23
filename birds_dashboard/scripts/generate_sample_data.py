"""
Generates a synthetic multi-sheet Excel workbook that mirrors the structure
of the real Bird Species Observation dataset (one sheet per Admin_Unit_Code).

This exists ONLY so the cleaning pipeline and dashboard can be built and
demoed before the real dataset is available. Swap it out for the real file
by pointing scripts/01_clean_data.py at it (see README).
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random

np.random.seed(42)
random.seed(42)

ADMIN_UNITS = {
    "ANTI": "Antietam National Battlefield",
    "CATO": "Catoctin Mountain Park",
    "GWMP": "George Washington Memorial Parkway",
    "ROCR": "Rock Creek Park",
}

LOCATION_TYPES = ["Forest", "Grassland"]

SPECIES = [
    ("Eastern Towhee", "Pipilo erythrophthalmus", "EATO"),
    ("Northern Cardinal", "Cardinalis cardinalis", "NOCA"),
    ("Carolina Wren", "Thryothorus ludovicianus", "CARW"),
    ("American Robin", "Turdus migratorius", "AMRO"),
    ("Red-winged Blackbird", "Agelaius phoeniceus", "RWBL"),
    ("Eastern Meadowlark", "Sturnella magna", "EAME"),
    ("Wood Thrush", "Hylocichla mustelina", "WOTH"),
    ("Blue Jay", "Cyanocitta cristata", "BLJA"),
    ("Grasshopper Sparrow", "Ammodramus savannarum", "GRSP"),
    ("Field Sparrow", "Spizella pusilla", "FISP"),
    ("Ovenbird", "Seiurus aurocapilla", "OVEN"),
    ("Indigo Bunting", "Passerina cyanea", "INBU"),
]

ID_METHODS = ["Singing", "Calling", "Visualization"]
SKY = ["Clear", "Partly Cloudy", "Cloudy/Overcast", "Fog/Mist", "Drizzle"]
WIND = [
    "Calm (< 1 mph) smoke rises vertically",
    "Light air (1-3 mph)",
    "Light breeze (4-7 mph)",
    "Gentle breeze (8-12 mph)",
]
DISTURBANCE = ["No effect on count", "Slight effect", "Moderate effect"]
DISTANCE = ["<= 50 Meters", "50-100 Meters", "> 100 Meters"]
SEX = ["Male", "Female", "Undetermined"]
INTERVALS = ["0-2.5 min", "2.5-5 min", "5-7.5 min", "7.5-10 min"]

def random_date(year):
    start = datetime(year, 5, 1)
    end = datetime(year, 7, 31)
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))

def make_sheet(admin_code, n_rows=180):
    rows = []
    for i in range(n_rows):
        year = random.choice([2021, 2022, 2023, 2024])
        date = random_date(year)
        start_hour = random.randint(5, 9)
        start_min = random.choice([0, 15, 30, 45])
        start_time = f"{start_hour:02d}:{start_min:02d}"
        end_time = f"{start_hour:02d}:{(start_min + 10) % 60:02d}"
        loc_type = random.choice(LOCATION_TYPES)
        species = random.choice(SPECIES)
        is_watchlist = random.random() < 0.15
        rows.append({
            "Admin_Unit_Code": admin_code,
            "Sub_Unit_Code": f"{admin_code}-{random.randint(1,3):02d}",
            "Site_Name": f"{admin_code} Site {random.randint(1,5)}",
            "Plot_Name": f"{admin_code}-P{random.randint(1,12):02d}",
            "Location_Type": loc_type,
            "Year": year,
            "Date": date.strftime("%Y-%m-%d"),
            "Start_Time": start_time,
            "End_Time": end_time,
            "Observer": random.choice(["J. Smith", "A. Lee", "M. Chen", "R. Patel", "K. Brooks"]),
            "Visit": random.randint(1, 4),
            "Interval_Length": random.choice(INTERVALS),
            "ID_Method": random.choice(ID_METHODS),
            "Distance": random.choice(DISTANCE),
            "Flyover_Observed": random.choice([True, False]),
            "Sex": random.choice(SEX),
            "Common_Name": species[0],
            "Scientific_Name": species[1],
            "AcceptedTSN": random.randint(100000, 999999),
            "NPSTaxonCode": f"NPS{random.randint(1000,9999)}",
            "AOU_Code": species[2],
            "PIF_Watchlist_Status": is_watchlist,
            "Regional_Stewardship_Status": random.random() < 0.2,
            "Temperature": round(np.random.normal(70, 8), 1),
            "Humidity": round(np.random.uniform(30, 90), 1),
            "Sky": random.choice(SKY),
            "Wind": random.choice(WIND),
            "Disturbance": random.choice(DISTURBANCE),
            "Initial_Three_Min_Cnt": random.randint(0, 6),
        })
    df = pd.DataFrame(rows)
    # sprinkle a few missing values / dupes, like real field data
    for col in ["Temperature", "Humidity", "Sex"]:
        idx = df.sample(frac=0.03).index
        df.loc[idx, col] = np.nan
    df = pd.concat([df, df.sample(3)], ignore_index=True)  # a few accidental dupes
    return df

if __name__ == "__main__":
    out_path = "/home/claude/bird_dashboard/data/sample_bird_data.xlsx"
    with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
        for code in ADMIN_UNITS:
            make_sheet(code).to_excel(writer, sheet_name=code, index=False)
    print(f"Wrote sample workbook: {out_path}")
