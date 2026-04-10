"""
Download Harmonised Producer Price Index (PPI) data from Eurostat via SDMX API.

This script downloads monthly Producer Price Index data for EU/EEA countries
from the Eurostat STS_INPP_M dataset (Producer prices in industry, total - monthly data).
It uses the NACE Rev.2 classification for industrial categories and saves the
combined data as a Parquet file.

Inspired by: https://github.com/paluigi/inflation_web/blob/main/data_download.py

Requirements:
    pip install sdmx1 pandas pyarrow tenacity
"""

import sdmx
import pandas as pd
import time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from tenacity import retry, stop_after_attempt, wait_random_exponential


# ===========================
# CONFIGURATION
# ===========================

DATAFLOW_ID = "STS_INPP_M"
OUTPUT_DIR = Path("data")
CATEGORIES_FILE = Path("nace_r2.csv")
OUTPUT_FILE = OUTPUT_DIR / "ppi_data.parquet"

FREQ = "M"
START_PERIOD = "2000-01"

# Countries and areas: EU-27 + Euro area aggregates (same as reference script)
GEO_KEY = "EU+EA+BE+BG+CZ+DK+DE+EE+IE+EL+ES+FR+HR+IT+CY+LV+LT+LU+HU+MT+NL+AT+PL+PT+RO+SI+SK+FI+SE"

# Price indicator and seasonal adjustment
INDIC_BT_KEY = "PRC_PRR"  # Producer prices
S_ADJ_KEY = "NSA"         # Neither seasonally adjusted nor calendar adjusted
UNIT_KEY = "I21"          # Index, 2021=100


# ===========================
# SDMX CLIENT
# ===========================

client = sdmx.Client("ESTAT")


# ===========================
# DOWNLOAD FUNCTION
# ===========================

@retry(stop=stop_after_attempt(7), wait=wait_random_exponential(multiplier=1, max=60), reraise=True)
def download_data(nace_code, dimensions, freq, start_period, dataflow_id):
    """Download data for a specific NACE Rev.2 category and return DataFrame."""

    # Detect dimensions dynamically
    freq_dim = next(d for d in dimensions if d.id.lower() == "freq")
    geo_dim = next(d for d in dimensions if d.id.lower() == "geo")
    nace_dim = next(d for d in dimensions if "nace" in d.id.lower())
    indic_bt_dim = next((d for d in dimensions if "indic_bt" in d.id.lower()), None)
    s_adj_dim = next((d for d in dimensions if d.id.lower() == "s_adj"), None)
    unit_dim = next((d for d in dimensions if "unit" in d.id.lower()), None)

    key = {
        freq_dim.id: freq,
        nace_dim.id: nace_code,
        geo_dim.id: GEO_KEY,
    }
    if indic_bt_dim:
        key[indic_bt_dim.id] = INDIC_BT_KEY
    if s_adj_dim:
        key[s_adj_dim.id] = S_ADJ_KEY
    if unit_dim:
        key[unit_dim.id] = UNIT_KEY

    response = client.get(
        resource_type="data",
        resource_id=dataflow_id,
        key=key,
        params={
            "startPeriod": start_period,
        },
    )

    data = response.data

    if data is None:
        print(f"  No data found for {nace_code}")
        return None

    df = sdmx.to_pandas(data)

    if df.empty:
        print(f"  Empty dataset for {nace_code}")
        return None

    df = df.reset_index()
    print(f"  Downloaded data for {nace_code}")

    time.sleep(0.3)
    return df


# ===========================
# MAIN
# ===========================

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load NACE categories
    print("Loading NACE R2 categories...")
    code_map = pd.read_csv(CATEGORIES_FILE)
    # Include hierarchical categories (level >= 1) and relevant aggregates (level 0)
    # Filter to codes that are most likely available in the PPI dataset:
    # - All level 1-4 hierarchical codes
    # - Key aggregates (TOTAL, TOT)
    codes_to_download = code_map[
        (code_map["level"] >= 1) | (code_map["code"].isin(["TOTAL", "TOT"]))
    ]["code"].tolist()
    print(f"  {len(codes_to_download)} categories to download")

    # Get data structure
    print("Downloading data structure...")
    try:
        dsd_response = client.get(
            resource_type="datastructure",
            resource_id=DATAFLOW_ID,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to download DSD: {e}")

    dsd = dsd_response.structure[DATAFLOW_ID]
    dimensions = list(dsd.dimensions.components)

    print(f"  Dimensions: {[d.id for d in dimensions]}")

    # Download loop
    all_data = []
    errors = []

    for i, nace_code in enumerate(codes_to_download):
        print(f"\nProcessing {i + 1}/{len(codes_to_download)}: {nace_code}")
        try:
            df = download_data(
                nace_code, dimensions, FREQ, START_PERIOD, DATAFLOW_ID
            )
            if df is not None:
                all_data.append(df)
        except Exception as e:
            print(f"  Error for {nace_code}: {e}")
            errors.append((nace_code, str(e)))
            continue

    # Save to Parquet
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df = combined_df.drop_duplicates(keep="last")
        # Drop constant dimensions
        combined_df = combined_df.drop(columns=["freq"], errors="ignore")

        combined_df.to_parquet(OUTPUT_FILE, index=False)
        print(f"\nSaved {len(combined_df)} rows to {OUTPUT_FILE}")
    else:
        print("\nNo data to process.")

    # Summary
    if errors:
        print(f"\n{len(errors)} errors encountered:")
        for code, err in errors:
            print(f"  {code}: {err}")

    # Save last update date
    update_file = OUTPUT_DIR / "last_update.txt"
    now = datetime.now(ZoneInfo("Europe/Rome"))
    update_file.write_text(now.strftime("%Y-%m-%d %H:%M %Z"))
    print(f"\nSaved last update date to {update_file}")
    print("All processing complete.")


if __name__ == "__main__":
    main()
