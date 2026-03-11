"""
Seed script: transforms Bank Plus raw CSV data into the silver.account_history
table schema and uploads it to Databricks Unity Catalog.

Also creates an empty silver.product_type_configuration_master table so the
product_mapping.py model's LEFT JOIN finds zero existing categorizations
(forcing classification of all product codes).

Data transformation logic mirrors notebooks/products/01_prepare_product_data.ipynb:
  - Deposits: product code = SCCODE, description from DDA Types lookup
  - Loans: product code = `type`, description from LoanTypeDesc (raw) or Loan Types lookup
  - Account deduplication for loans (monthly snapshots)
  - Status mapping from numeric core banking codes to ACTIVE/DORMANT/CLOSED

Usage:
    # Ensure .env has DATABRICKS_HOST, WAREHOUSE_HTTP_PATH, CLIENT_ID, CLIENT_SECRET
    python scripts/seed_account_history.py

Prerequisites:
    pip install "databricks-sql-connector" "databricks-sdk" pandas python-dotenv
"""
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from databricks import sql as dbsql
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "bank-plus-data" / "raw"
SOT_DIR = PROJECT_ROOT / "data" / "bank-plus-data" / "source-of-truth" / "products"

CATALOG = "ciq-bp_dummy-dev"
SILVER_SCHEMA = "silver"
SUGGESTIONS_SCHEMA = "suggestions"

DEPOSIT_CSV = next(RAW_DIR.glob("CheckingIQ_Deposit_ALL_*.csv"))
LOAN_CSV = next(RAW_DIR.glob("CheckingIQ_Loan_13Month_All_*.csv"))
DDA_TYPES_CSV = SOT_DIR / "Product catalog(DDA Types).csv"
LOAN_TYPES_CSV = SOT_DIR / "Product catalog(Loan Types).csv"

INSERT_BATCH_SIZE = 500

# ── Status Mappings ──────────────────────────────────────────────
# Source: Account Status(Account Status Mapping).csv
# DD (Deposits):
#   0=Escheat(Closed), 1=Active, 2=Closed, 3=Dormant,
#   4=New(Active), 5=Pending Closed(Dormant), 6=Restricted(Dormant),
#   7=Do Not Post(Dormant), 8=Charge-Off(Closed), 9=Post No Credits(Active)
# LN (Loans):
#   1=Active, 2=Closed, 3=Matured(Dormant), 4=New(Active),
#   5=No Accrual(Dormant), 6=Freeze w/Accr(Dormant),
#   7=Freeze w/no Accr(Dormant), 8=Charge-Off(Closed)

DEPOSIT_STATUS_MAP = {
    0: "CLOSED", 1: "ACTIVE", 2: "CLOSED", 3: "DORMANT",
    4: "ACTIVE", 5: "DORMANT", 6: "DORMANT",
    7: "DORMANT", 8: "CLOSED", 9: "ACTIVE",
}

LOAN_STATUS_MAP = {
    1: "ACTIVE", 2: "CLOSED", 3: "DORMANT", 4: "ACTIVE",
    5: "DORMANT", 6: "DORMANT", 7: "DORMANT", 8: "CLOSED",
}


def _load_dda_lookup() -> dict[str, str]:
    """Load DDA Types lookup: SCCODE -> description.

    Mirrors notebook Section B: reference lookup loading.
    """
    df = pd.read_csv(DDA_TYPES_CSV, encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].str.strip()
    code_col, desc_col = df.columns[0], df.columns[1]
    return dict(zip(df[code_col].astype(str), df[desc_col]))


def _load_loan_lookup() -> dict[str, str]:
    """Load Loan Types lookup: JHA TYPE -> description.

    Mirrors notebook Section B: reference lookup loading.
    """
    df = pd.read_csv(LOAN_TYPES_CSV, encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]
    df = df.dropna(subset=[df.columns[0]])
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].str.strip()
    code_col, desc_col = df.columns[0], df.columns[1]
    return dict(zip(df[code_col].astype(str), df[desc_col]))


def _build_deposit_df(dda_lookup: dict[str, str]) -> pd.DataFrame:
    """Transform raw deposit CSV into account_history schema.

    Mirrors notebook Cell 16:
      - ACTYPE is always "D"; real product code is SCCODE
      - All statuses included (product_mapping.py classifies regardless of status)
    """
    logger.info("Reading deposit CSV: %s", DEPOSIT_CSV.name)
    df = pd.read_csv(DEPOSIT_CSV, encoding="latin-1", low_memory=False)
    df.columns = [c.strip() for c in df.columns]

    df["STATUS"] = pd.to_numeric(df["STATUS"], errors="coerce")
    df["SCCODE"] = df["SCCODE"].astype(str).str.strip()
    df["ACCTNO"] = df["ACCTNO"].astype(str).str.strip()

    df_dedup = df.drop_duplicates(subset=["ACCTNO"])
    logger.info("Deposits: %d raw rows -> %d unique accounts", len(df), len(df_dedup))

    return pd.DataFrame({
        "AccountIdentifier": df_dedup["ACCTNO"].values,
        "ProductInstanceReference": df_dedup["SCCODE"].values,
        "ProductInstanceDescription": df_dedup["SCCODE"].map(dda_lookup).fillna("(unknown)").values,
        "BranchLocationReference": (
            df_dedup["AccountBranch"].astype(str).str.strip().values
            if "AccountBranch" in df_dedup.columns
            else None
        ),
        "AccountOpeningDate": pd.to_datetime(
            df_dedup["Account_opened_date"], errors="coerce", format="mixed"
        ).dt.strftime("%Y-%m-%d").values,
        "AccountClosingDate": pd.to_datetime(
            df_dedup["account_close_date"] if "account_close_date" in df_dedup.columns else None,
            errors="coerce", format="mixed",
        ).dt.strftime("%Y-%m-%d").values if "account_close_date" in df_dedup.columns else None,
        "AccountStatus": df_dedup["STATUS"].map(DEPOSIT_STATUS_MAP).fillna("ACTIVE").values,
        "InterestRate": None,
        "MinimumBalance": None,
        "effective_ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    })


def _build_loan_df(loan_lookup: dict[str, str]) -> pd.DataFrame:
    """Transform raw loan CSV into account_history schema.

    Mirrors notebook Cell 17:
      - ACTYPE is always "L"; real product code is `type` column
      - Deduplicate by (acctno, type) since raw data has monthly snapshots
      - Description = LoanTypeDesc from raw data, fallback to Loan Types lookup
    """
    logger.info("Reading loan CSV: %s", LOAN_CSV.name)
    df = pd.read_csv(LOAN_CSV, encoding="latin-1", low_memory=False)
    df.columns = [c.strip() for c in df.columns]

    df["STATUS"] = pd.to_numeric(df["STATUS"], errors="coerce")
    df["type"] = df["type"].astype(str).str.strip()
    df["acctno"] = df["acctno"].astype(str).str.strip()

    df_dedup = df.drop_duplicates(subset=["acctno", "type"])
    logger.info("Loans: %d raw rows -> %d unique account-type combos", len(df), len(df_dedup))

    description = df_dedup["LoanTypeDesc"].astype(str).str.strip()
    description = description.where(
        ~description.isin(["", "nan", "None"]),
        df_dedup["type"].map(loan_lookup).fillna("(unknown)"),
    )

    return pd.DataFrame({
        "AccountIdentifier": df_dedup["acctno"].values,
        "ProductInstanceReference": df_dedup["type"].values,
        "ProductInstanceDescription": description.values,
        "BranchLocationReference": (
            df_dedup["Branch"].astype(str).str.strip().values
            if "Branch" in df_dedup.columns
            else None
        ),
        "AccountOpeningDate": pd.to_datetime(
            df_dedup["DATOPN"] if "DATOPN" in df_dedup.columns else None,
            errors="coerce", format="mixed",
        ).dt.strftime("%Y-%m-%d").values if "DATOPN" in df_dedup.columns else None,
        "AccountClosingDate": None,
        "AccountStatus": df_dedup["STATUS"].map(LOAN_STATUS_MAP).fillna("ACTIVE").values,
        "InterestRate": pd.to_numeric(
            df_dedup["RATE"] if "RATE" in df_dedup.columns else None,
            errors="coerce",
        ).values if "RATE" in df_dedup.columns else None,
        "MinimumBalance": None,
        "effective_ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    })


def _sample_preserving_codes(df: pd.DataFrame, max_per_code: int = 50) -> pd.DataFrame:
    """Downsample to at most max_per_code rows per ProductInstanceReference.

    Keeps the dataset manageable for INSERT uploads (~5K rows instead of ~340K)
    while preserving all unique product codes and enough rows for meaningful
    volume / description samples in product_mapping.py.
    """
    return df.groupby("ProductInstanceReference", group_keys=False).head(max_per_code).reset_index(drop=True)


def _get_connection():
    """Connect to Databricks using a Personal Access Token (PAT)."""
    load_dotenv(PROJECT_ROOT / ".env")

    host = os.environ.get("DATABRICKS_HOST")
    http_path = os.environ.get("WAREHOUSE_HTTP_PATH")
    token = os.environ.get("DATABRICKS_TOKEN")

    missing = [name for name, val in [
        ("DATABRICKS_HOST", host),
        ("WAREHOUSE_HTTP_PATH", http_path),
        ("DATABRICKS_TOKEN", token),
    ] if not val]
    if missing:
        logger.error("Missing environment variables: %s", ", ".join(missing))
        sys.exit(1)

    logger.info("Connecting to Databricks at %s", host)

    return dbsql.connect(
        server_hostname=host,
        http_path=http_path,
        access_token=token,
    )


def _execute_sql(cursor, statement: str):
    logger.debug("SQL: %s", statement[:200])
    cursor.execute(statement)


def _upload_dataframe(cursor, table_fqn: str, df: pd.DataFrame):
    """Upload a pandas DataFrame to a Databricks table using INSERT batches."""
    columns = list(df.columns)
    col_list = ", ".join(columns)
    total = len(df)
    uploaded = 0

    for start in range(0, total, INSERT_BATCH_SIZE):
        batch = df.iloc[start : start + INSERT_BATCH_SIZE]
        rows_sql = []
        for _, row in batch.iterrows():
            vals = []
            for col in columns:
                v = row[col]
                if pd.isna(v) or v is None or str(v) in ("nan", "None", "NaT", ""):
                    vals.append("NULL")
                elif isinstance(v, (int, float)):
                    vals.append(str(v))
                else:
                    escaped = str(v).replace("'", "''")
                    vals.append(f"'{escaped}'")
            rows_sql.append(f"({', '.join(vals)})")

        insert_sql = (
            f"INSERT INTO {table_fqn} ({col_list}) VALUES\n"
            + ",\n".join(rows_sql)
        )
        _execute_sql(cursor, insert_sql)
        uploaded += len(batch)
        logger.info("  Uploaded %d / %d rows to %s", uploaded, total, table_fqn)


def main():
    dda_lookup = _load_dda_lookup()
    loan_lookup = _load_loan_lookup()
    logger.info("Loaded %d DDA type descriptions, %d loan type descriptions",
                len(dda_lookup), len(loan_lookup))

    df_deposits = _build_deposit_df(dda_lookup)
    df_loans = _build_loan_df(loan_lookup)

    df_all = pd.concat([df_deposits, df_loans], ignore_index=True)
    logger.info("Combined (full): %d total rows, %d unique product codes",
                len(df_all), df_all["ProductInstanceReference"].nunique())

    status_counts = df_all["AccountStatus"].value_counts()
    logger.info("Account status distribution:\n%s", status_counts.to_string())

    df_all = _sample_preserving_codes(df_all, max_per_code=50)
    logger.info("After sampling (max 50 per code): %d rows, %d unique codes",
                len(df_all), df_all["ProductInstanceReference"].nunique())

    conn = _get_connection()
    cursor = conn.cursor()

    try:
        ah_table = f"`{CATALOG}`.`{SILVER_SCHEMA}`.account_history"
        ptcm_table = f"`{CATALOG}`.`{SILVER_SCHEMA}`.product_type_configuration_master"

        logger.info("Creating schemas if not exist...")
        _execute_sql(cursor, f"CREATE SCHEMA IF NOT EXISTS `{CATALOG}`.`{SILVER_SCHEMA}`")
        _execute_sql(cursor, f"CREATE SCHEMA IF NOT EXISTS `{CATALOG}`.`{SUGGESTIONS_SCHEMA}`")

        logger.info("Creating account_history table: %s", ah_table)
        _execute_sql(cursor, f"DROP TABLE IF EXISTS {ah_table}")
        _execute_sql(cursor, f"""
            CREATE TABLE {ah_table} (
                AccountIdentifier STRING NOT NULL,
                ProductInstanceReference STRING,
                ProductInstanceDescription STRING,
                BranchLocationReference STRING,
                AccountOpeningDate DATE,
                AccountClosingDate DATE,
                AccountStatus STRING,
                InterestRate DECIMAL(8,5),
                MinimumBalance DECIMAL(18,2),
                effective_ts TIMESTAMP,
                valid_from TIMESTAMP,
                valid_to TIMESTAMP
            )
        """)

        logger.info("Uploading %d rows to account_history...", len(df_all))
        _upload_dataframe(cursor, ah_table, df_all)

        row_count = cursor.execute(f"SELECT COUNT(*) FROM {ah_table}").fetchone()[0]
        code_count = cursor.execute(
            f"SELECT COUNT(DISTINCT ProductInstanceReference) FROM {ah_table}"
        ).fetchone()[0]
        logger.info(
            "Verification: %d rows, %d unique product codes in account_history",
            row_count, code_count,
        )

        logger.info("Creating empty product_type_configuration_master: %s", ptcm_table)
        _execute_sql(cursor, f"DROP TABLE IF EXISTS {ptcm_table}")
        _execute_sql(cursor, f"""
            CREATE TABLE {ptcm_table} (
                PROD_product_type_id STRING,
                PROD_core_system_mapping STRING,
                PROD_line_of_business STRING,
                PROD_product_category STRING,
                PROD_product_type STRING,
                PROD_product_name STRING,
                PROD_product_code STRING,
                PROD_status STRING,
                PROD_balance_requires_abs BOOLEAN,
                PROD_created_date TIMESTAMP,
                PROD_modified_date TIMESTAMP
            )
        """)
        logger.info("Empty product_type_configuration_master created.")

        logger.info("")
        logger.info("=== Seed complete! ===")
        logger.info("  Catalog:  %s", CATALOG)
        logger.info("  Table:    %s (%d rows, %d unique codes)", ah_table, row_count, code_count)
        logger.info("  Table:    %s (empty)", ptcm_table)
        logger.info("  Schemas:  %s, %s", SILVER_SCHEMA, SUGGESTIONS_SCHEMA)
        logger.info("")
        logger.info("Next steps:")
        logger.info("  cd sqlmesh")
        logger.info("  sqlmesh --gateway databricks_dev info")
        logger.info("  sqlmesh --gateway databricks_dev plan --select-model \"suggestions.product_mapping\"")

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
