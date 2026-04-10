# ppi_eurostat

Download **Producer Price Index (PPI)** data from Eurostat via the SDMX API.

This project provides:
- **`nace_r2.csv`** — A complete list of [NACE Rev.2](https://ec.europa.eu/eurostat/ramon/nomenclatures/index.cfm?TargetUrl=LST_CLS_DLD&StrNom=NACE_REV2&StrLanguageCode=EN) industrial activity categories used by Eurostat, with hierarchical levels and parent-child relationships.
- **`download_ppi.py`** — A Python script that downloads monthly Producer Price Index data from the `STS_INPP_M` Eurostat dataset for all EU/EEA member states and saves the result as a Parquet file.

## Dataset

**Eurostat dataflow:** `STS_INPP_M` — Producer prices in industry, total (monthly data)

| Dimension | Description | Values used |
|-----------|-------------|-------------|
| `freq` | Time frequency | Monthly (`M`) |
| `nace_r2` | NACE Rev.2 activity | All hierarchical categories (levels 1–4) + aggregates |
| `geo` | Geographic area | EU-27 + EA aggregates + all member states |
| `indic_bt` | Business trend indicator | Producer prices (`PRC_PRR`) |
| `s_adj` | Seasonal adjustment | Unadjusted (`NSA`) |
| `unit` | Unit of measure | Index, 2021=100 (`I21`) |

### Countries & areas covered

`EU`, `EA`, `BE`, `BG`, `CZ`, `DK`, `DE`, `EE`, `IE`, `EL`, `ES`, `FR`, `HR`, `IT`, `CY`, `LV`, `LT`, `LU`, `HU`, `MT`, `NL`, `AT`, `PL`, `PT`, `RO`, `SI`, `SK`, `FI`, `SE`

## NACE Rev.2 hierarchy

The `nace_r2.csv` file contains **1,343 categories** across 5 levels:

| Level | Description | Count | Example |
|-------|-------------|-------|---------|
| 0 | Special aggregates | 347 | `TOTAL`, `B-D`, `C10-C12` |
| 1 | Sections (1 letter) | 21 | `A`, `B`, `C`, …, `U` |
| 2 | Divisions (letter + 2 digits) | 88 | `C10`, `C11`, `C24`, … |
| 3 | Groups (letter + 3 digits) | 272 | `C101`, `C102`, `C241`, … |
| 4 | Classes — most granular (letter + 4 digits) | 615 | `C1011`, `C1012`, `C2410`, … |

**Columns:** `concept`, `code`, `name`, `level`, `parent`

## Installation

```bash
pip install sdmx1 pandas pyarrow tenacity
```

## Usage

```bash
python download_ppi.py
```

This will:
1. Load all NACE Rev.2 categories from `nace_r2.csv`
2. Download PPI data for each category from the Eurostat SDMX API
3. Save the combined dataset to `data/ppi_data.parquet`
4. Record the last update timestamp in `data/last_update.txt`

### Output Parquet schema

The output Parquet file contains the following columns (from the SDMX response index):

| Column | Type | Description |
|--------|------|-------------|
| `indic_bt` | string | Business trend indicator |
| `nace_r2` | string | NACE Rev.2 activity code |
| `s_adj` | string | Seasonal adjustment flag |
| `unit` | string | Unit of measure |
| `geo` | string | Geographic entity |
| `TIME_PERIOD` | period | Time period (monthly) |
| `obsValue` | float | Observed value (index) |

## Inspiration

This project is inspired by the [inflation_web](https://github.com/paluigi/inflation_web) data download script, adapted from HICP (Consumer Prices) to PPI (Producer Prices).

## License

MIT