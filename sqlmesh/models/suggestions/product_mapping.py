"""
SQLMesh Python Model: Product Mapping Suggestions

Reads ProductInstanceReference (product code) and ProductInstanceDescription
from silver.account_history, builds an in-memory product catalog of distinct codes,
classifies all codes via ai_query() (Claude) into the StrategyCorp product taxonomy,
and writes mapping suggestions to the suggestions schema.

Processing steps:
  1. Load uncategorized product codes from silver.account_history by LEFT JOINing
     against silver.product_type_configuration_master and keeping unmatched rows.
  2. Aggregate in Spark SQL: GROUP BY product_code to produce a compact catalog
     with description samples, volume, and account status distribution per code.
  3. Collect the catalog to the driver (bounded by number of distinct codes).
  4. Batch-classify codes via ai_query() (Claude) with structured JSON output
     and retry logic.
  5. Validate LLM response completeness — any codes the LLM omits are recorded
     as ERROR rows.
  6. Post-process: UPPERCASE, SHA2 hash, review_status, PROD_status derivation,
     balance_requires_abs.
  7. Return the final DataFrame with explicit PySpark schema.

The output schema aligns with product_type_configuration_master in silver,
plus metadata columns (confidence, review_status, ai_model, prompt_version).
"""
import hashlib
import json
import logging
import math
import re
import time
import typing as t
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pyspark.sql import DataFrame
from pyspark.sql.types import (
    BooleanType,
    DecimalType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)
from sqlglot import exp as sqlglot_exp
from sqlmesh import ExecutionContext, model
from sqlmesh.core.model.kind import ModelKindName

BATCH_SIZE = 30
MODEL_NAME = "databricks-claude-sonnet-4-5"
PROMPT_VERSION = "v2.0"
N_SAMPLES = 3
MAX_RETRIES = 3
MAX_DESC_LENGTH = 200

VALID_LINE_OF_BUSINESS = {"RETAIL", "BUSINESS"}

ACCOUNT_STATUS_TO_PROD_STATUS = {
    "ACTIVE": "ACTIVE",
    "CLOSED": "INACTIVE",
    "DORMANT": "INACTIVE",
}


def _get_output_schema() -> StructType:
    return StructType([
        StructField("PROD_product_type_id", StringType(), False),
        StructField("PROD_line_of_business", StringType(), True),
        StructField("PROD_product_category", StringType(), True),
        StructField("PROD_product_type", StringType(), True),
        StructField("PROD_product_name", StringType(), True),
        StructField("PROD_product_code", StringType(), True),
        StructField("PROD_status", StringType(), False),
        StructField("PROD_core_system_mapping", StringType(), False),
        StructField("PROD_balance_requires_abs", BooleanType(), False),
        StructField("PROD_created_date", TimestampType(), False),
        StructField("PROD_modified_date", TimestampType(), False),
        StructField("processing_timestamp", TimestampType(), False),
        StructField("review_status", StringType(), False),
        StructField("confidence", DecimalType(10, 6), True),
        StructField("ai_model", StringType(), True),
        StructField("prompt_version", StringType(), True),
        StructField("description_samples", StringType(), True),
        StructField("volume", LongType(), True),
    ])


@model(
    "@suggestions_schema.product_mapping",
    tags=["@tenant_catalog"],
    kind=dict(name=ModelKindName.FULL),
    grain=["PROD_product_type_id"],
    cron="@weekly",
    start="2025-06-30",
    description="AI-generated product code classification suggestions using Claude via ai_query(). "
    "Reads ProductInstanceReference and ProductInstanceDescription from silver.account_history, "
    "builds a product catalog, and classifies into the StrategyCorp product taxonomy aligned with "
    "product_type_configuration_master.",
    depends_on=[
        "@silver_schema.account_history",
        "@silver_schema.product_type_configuration_master",
    ],
    columns={
        "PROD_product_type_id": "string",
        "PROD_line_of_business": "string",
        "PROD_product_category": "string",
        "PROD_product_type": "string",
        "PROD_product_name": "string",
        "PROD_product_code": "string",
        "PROD_status": "string",
        "PROD_core_system_mapping": "string",
        "PROD_balance_requires_abs": "boolean",
        "PROD_created_date": "timestamp",
        "PROD_modified_date": "timestamp",
        "processing_timestamp": "timestamp",
        "review_status": "string",
        "confidence": "decimal(10,6)",
        "ai_model": "string",
        "prompt_version": "string",
        "description_samples": "string",
        "volume": "bigint",
    },
    audits=(
        ("not_null", {"columns": [
            sqlglot_exp.column("PROD_product_type_id"),
            sqlglot_exp.column("PROD_core_system_mapping"),
            sqlglot_exp.column("PROD_status"),
            sqlglot_exp.column("review_status"),
        ]}),
        ("unique_combination_of_columns", {
            "columns": [sqlglot_exp.column("PROD_product_type_id")],
        }),
        ("accepted_values", {
            "column": sqlglot_exp.column("PROD_status"),
            "is_in": ("ACTIVE", "INACTIVE", "DISCONTINUED"),
        }),
        ("accepted_values", {
            "column": sqlglot_exp.column("review_status"),
            "is_in": (
                "PENDING_REVIEW", "REQUIRES_MANUAL_MAPPING",
                "NEEDS_MANUAL_REVIEW", "APPROVED", "REJECTED",
            ),
        }),
        ("accepted_range", {
            "column": sqlglot_exp.column("confidence"),
            "min_v": 0,
            "max_v": 1,
        }),
    ),
)
def execute(
    context: ExecutionContext,
    start: datetime,
    end: datetime,
    execution_time: datetime,
    **kwargs: t.Any,
) -> DataFrame:
    logger = logging.getLogger(__name__)
    spark = context.spark

    silver = context.var("silver_schema")
    ah_table = context.resolve_table(f"{silver}.account_history")
    ptcm_table = context.resolve_table(f"{silver}.product_type_configuration_master")
    logger.info(
        "Loading uncategorized product codes from %s (excluding codes in %s)",
        ah_table, ptcm_table,
    )

    n_samples = N_SAMPLES
    catalog = spark.sql(f"""
        WITH uncategorized AS (
            SELECT
                TRIM(CAST(ah.ProductInstanceReference AS STRING)) AS product_code,
                TRIM(CAST(ah.ProductInstanceDescription AS STRING)) AS product_description,
                UPPER(TRIM(CAST(ah.AccountStatus AS STRING))) AS account_status
            FROM {ah_table} ah
            LEFT JOIN {ptcm_table} m
              ON UPPER(TRIM(CAST(ah.ProductInstanceReference AS STRING)))
                 = UPPER(TRIM(m.PROD_core_system_mapping))
            WHERE m.PROD_product_type_id IS NULL
              AND ah.ProductInstanceReference IS NOT NULL
              AND TRIM(ah.ProductInstanceReference) <> ''
        ),
        codes AS (
            SELECT product_code,
                   COUNT(*) AS volume,
                   CASE
                       WHEN SUM(CASE WHEN account_status = 'ACTIVE' THEN 1 ELSE 0 END) > 0
                       THEN 'ACTIVE'
                       ELSE 'INACTIVE'
                   END AS prod_status
            FROM uncategorized
            GROUP BY product_code
        ),
        desc_ranked AS (
            SELECT product_code,
                   product_description,
                   COUNT(*) AS desc_count,
                   ROW_NUMBER() OVER (
                       PARTITION BY product_code
                       ORDER BY COUNT(*) DESC
                   ) AS rn
            FROM uncategorized
            WHERE product_description IS NOT NULL
              AND TRIM(product_description) <> ''
            GROUP BY product_code, product_description
        )
        SELECT c.product_code,
               COLLECT_LIST(STRUCT(dr.product_description, dr.desc_count)) AS desc_samples,
               c.volume,
               c.prod_status
        FROM codes c
        LEFT JOIN desc_ranked dr
          ON c.product_code = dr.product_code
          AND dr.rn <= {n_samples}
        GROUP BY c.product_code, c.volume, c.prod_status
    """).toPandas()

    if catalog.empty:
        logger.warning("No uncategorized product codes found — returning empty result")
        return spark.createDataFrame([], _get_output_schema())

    catalog["description_samples"] = catalog["desc_samples"].apply(_format_descriptions)
    catalog = catalog.drop(columns=["desc_samples"])
    logger.info("Built catalog: %d unique product codes", len(catalog))

    taxonomy_path = Path(__file__).resolve().parent / "product_categorization_taxonomy.md"
    if not taxonomy_path.exists():
        raise FileNotFoundError(f"Taxonomy file not found: {taxonomy_path}")
    taxonomy_md = taxonomy_path.read_text()

    system_prompt = _build_system_prompt(taxonomy_md)
    response_schema_str = json.dumps(_response_schema())

    all_results: list[dict] = []
    n_batches = math.ceil(len(catalog) / BATCH_SIZE)
    logger.info(
        "Classifying %d codes in %d batches (batch_size=%d)",
        len(catalog), n_batches, BATCH_SIZE,
    )

    for i in range(n_batches):
        batch = catalog.iloc[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
        results = _classify_batch_with_retry(
            spark, batch, system_prompt, response_schema_str,
            logger, i + 1, n_batches,
        )
        all_results.extend(results)

    df = pd.DataFrame(all_results)
    logger.info(
        "Classification complete: %d total codes, %d errors",
        len(df),
        len(df[df["review_status"] == "NEEDS_MANUAL_REVIEW"]),
    )

    return spark.createDataFrame(df, _get_output_schema())


# ── helpers ──────────────────────────────────────────────────────


def _format_descriptions(desc_list: list) -> str:
    """Format a struct array of (product_description, desc_count) into
    a pipe-separated string with counts."""
    if not desc_list:
        return "(no description)"
    parts = []
    for item in desc_list:
        desc = str(item["product_description"]).strip()
        cnt = item["desc_count"]
        if desc and desc not in ("nan", "None"):
            parts.append(f"{desc} ({cnt:,})")
    return " | ".join(parts) if parts else "(no description)"


def _sanitize_description(text: str) -> str:
    """Strip control characters and truncate to prevent prompt injection."""
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
    text = text.replace("\\", "\\\\")
    return text[:MAX_DESC_LENGTH]


def _derive_prod_status(status_series: pd.Series) -> str:
    """Derive PROD_status for a product code from its accounts' AccountStatus values.

    If ANY account is ACTIVE the product is ACTIVE (the product is still offered).
    If all accounts are CLOSED/DORMANT the product is INACTIVE (no longer in use).
    Falls back to ACTIVE for unknown status values.
    """
    statuses = status_series.astype(str).str.strip().str.upper()
    if (statuses == "ACTIVE").any():
        return "ACTIVE"
    mapped = statuses.map(ACCOUNT_STATUS_TO_PROD_STATUS)
    if mapped.isna().all():
        return "ACTIVE"
    return mapped.dropna().mode().iloc[0] if not mapped.dropna().empty else "ACTIVE"


def _build_system_prompt(taxonomy_md: str) -> str:
    return f"""You are a product categorization engine for US community banks and financial institutions.
Given a list of product codes with descriptions, classify each into the StrategyCorp product taxonomy below.

{taxonomy_md}

### Classification Rules

1. **Line of Business (Level 1) — `PROD_line_of_business`:**
   Determine whether the product belongs to Retail, Business, or Wealth Management.
   - **RETAIL** — consumer/individual banking products (personal checking, savings,
     consumer loans, mortgages, HELOCs, auto loans, etc.)
   - **BUSINESS** — commercial/business banking products (business checking, commercial
     loans, treasury management, commercial real estate, agricultural loans, etc.)
   - **WEALTH MANAGEMENT** — trust, fiduciary, investment, and securities products.
     Classify as WEALTH MANAGEMENT ONLY when the product name or code explicitly
     indicates fiduciary, trust, or securities management (keywords: FIDUCIARY, TRUST,
     UTMA, UGMA, IRA, ESTATE).

2. **Product Category (Level 2) — `PROD_product_category`:**
   One of: DEPOSITS, LOANS, SERVICES.
   Determined by the product nature (checking/savings/MM = DEPOSITS, mortgage/HELOC/personal/auto = LOANS).

3. **Product Type (Level 3) — `PROD_product_type`:**
   The specific product type within the category. Use these strings:
   - Deposits: CHECKING, SAVINGS, MONEY MARKET
   - Loans: MORTGAGE, HOME EQUITY, LINE OF CREDIT, PERSONAL, AUTO,
     COMMERCIAL, COMMERCIAL REAL ESTATE, AGRICULTURAL, REAL ESTATE,
     RECEIVABLES-BASED, EQUIPMENT FINANCING

4. **Product Name (Level 4) — `PROD_product_name`:**
   Derive from the product description — the distinguishing feature within its
   Level 3 type (e.g., "PREMIUM", "BASIC", "INTEREST BEARING", "PLATINUM").
   Use null if no meaningful distinction can be made.

5. **Product Code (Level 5) — `PROD_product_code`:**
   Special designation evident from the product name (e.g., HSA, UTMA, ARM, FIXED).
   Use null for most products.

6. **Output values MUST be UPPERCASED** (e.g., "RETAIL" not "Retail", "DEPOSITS" not "Deposits").

7. Use null for any level if no mapping fits. Do not guess.

8. `confidence`: 0.0 to 1.0 — your certainty in the classification.

### Few-Shot Examples

Input: product_code=CK, SAMPLES="Personal Checking (15,000)"
Output: {{{{
  "PROD_core_system_mapping": "CK",
  "PROD_line_of_business": "RETAIL",
  "PROD_product_category": "DEPOSITS",
  "PROD_product_type": "CHECKING",
  "PROD_product_name": "PERSONAL CHECKING",
  "PROD_product_code": null,
  "confidence": 0.95
}}}}

Input: product_code=R1, SAMPLES="Residential RE Fixed (55,577)"
Output: {{{{
  "PROD_core_system_mapping": "R1",
  "PROD_line_of_business": "RETAIL",
  "PROD_product_category": "LOANS",
  "PROD_product_type": "MORTGAGE",
  "PROD_product_name": "RESIDENTIAL RE FIXED",
  "PROD_product_code": "FIXED",
  "confidence": 0.93
}}}}

Input: product_code=B1, SAMPLES="Business Checking (17,978)"
Output: {{{{
  "PROD_core_system_mapping": "B1",
  "PROD_line_of_business": "BUSINESS",
  "PROD_product_category": "DEPOSITS",
  "PROD_product_type": "CHECKING",
  "PROD_product_name": "BUSINESS CHECKING",
  "PROD_product_code": null,
  "confidence": 0.92
}}}}

Input: product_code=MM, SAMPLES="Money Market Savings (1,132)"
Output: {{{{
  "PROD_core_system_mapping": "MM",
  "PROD_line_of_business": "RETAIL",
  "PROD_product_category": "DEPOSITS",
  "PROD_product_type": "MONEY MARKET",
  "PROD_product_name": "MONEY MARKET SAVINGS",
  "PROD_product_code": null,
  "confidence": 0.94
}}}}

Input: product_code=BC, SAMPLES="CRE Fixed (14,402)"
Output: {{{{
  "PROD_core_system_mapping": "BC",
  "PROD_line_of_business": "BUSINESS",
  "PROD_product_category": "LOANS",
  "PROD_product_type": "COMMERCIAL REAL ESTATE",
  "PROD_product_name": "CRE FIXED",
  "PROD_product_code": "FIXED",
  "confidence": 0.91
}}}}

Input: product_code=F1, SAMPLES="Fiduciary Bus Int Ck (9)"
Output: {{{{
  "PROD_core_system_mapping": "F1",
  "PROD_line_of_business": "WEALTH MANAGEMENT",
  "PROD_product_category": "DEPOSITS",
  "PROD_product_type": "CHECKING",
  "PROD_product_name": "FIDUCIARY BUSINESS INTEREST CHECKING",
  "PROD_product_code": null,
  "confidence": 0.88
}}}}
"""


def _response_schema() -> dict:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "product_classifications",
            "schema": {
                "type": "object",
                "properties": {
                    "classifications": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "PROD_core_system_mapping": {"type": "string"},
                                "PROD_line_of_business": {"type": "string"},
                                "PROD_product_category": {"type": "string"},
                                "PROD_product_type": {"type": "string"},
                                "PROD_product_name": {"type": ["string", "null"]},
                                "PROD_product_code": {"type": ["string", "null"]},
                                "confidence": {"type": "number"},
                            },
                            "required": [
                                "PROD_core_system_mapping",
                                "PROD_line_of_business",
                                "PROD_product_category",
                                "PROD_product_type",
                                "PROD_product_name",
                                "PROD_product_code",
                                "confidence",
                            ],
                        },
                    },
                },
                "required": ["classifications"],
            },
            "strict": True,
        },
    }


def _build_user_prompt(batch_df: pd.DataFrame) -> str:
    lines = []
    for _, row in batch_df.iterrows():
        desc = _sanitize_description(str(row["description_samples"]).strip())
        if desc in ("nan", "", "None"):
            desc = "(no description)"
        code = row["product_code"]
        vol = row["volume"]
        lines.append(f'product_code={code}, SAMPLES="{desc}", VOLUME={vol}')

    codes_text = "\n".join(f"  - {line}" for line in lines)
    return (
        f"Classify these {len(batch_df)} product codes:\n\n"
        f"SAMPLES contains the top {N_SAMPLES} most frequent product descriptions for this code\n"
        "with occurrence counts. Use the PATTERNS across samples to determine the\n"
        "product type — don't rely on any single sample.\n\n"
        f"{codes_text}\n\n"
        'Return a JSON object with a "classifications" array containing one '
        "entry per product code. Use the EXACT output schema specified."
    )


def _classify_batch_with_retry(
    spark,
    batch_df: pd.DataFrame,
    system_prompt: str,
    response_schema_str: str,
    logger: logging.Logger,
    batch_num: int,
    total_batches: int,
) -> list[dict]:
    """Classify a batch with retry logic and completeness validation."""
    for attempt in range(MAX_RETRIES):
        try:
            results = _classify_batch(spark, batch_df, system_prompt, response_schema_str)
            returned_codes = {r["PROD_core_system_mapping"] for r in results}
            sent_codes = {str(row["product_code"]).strip().upper() for _, row in batch_df.iterrows()}
            missing = sent_codes - returned_codes
            if missing:
                logger.warning(
                    "Batch %d/%d: LLM omitted %d codes: %s",
                    batch_num, total_batches, len(missing), missing,
                )
                for _, row in batch_df.iterrows():
                    if str(row["product_code"]).strip().upper() in missing:
                        results.append(_error_row(row, "LLM omitted this code from response"))
            logger.info("Batch %d/%d: classified %d codes", batch_num, total_batches, len(results))
            return results
        except Exception as exc:
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** (attempt + 1)
                logger.warning(
                    "Batch %d/%d attempt %d failed, retrying in %ds: %s",
                    batch_num, total_batches, attempt + 1, wait, exc,
                )
                time.sleep(wait)
            else:
                logger.error(
                    "Batch %d/%d failed after %d attempts: %s",
                    batch_num, total_batches, MAX_RETRIES, exc,
                )
                error_results = []
                for _, row in batch_df.iterrows():
                    error_results.append(_error_row(row, str(exc)))
                return error_results
    return []


def _classify_batch(
    spark,
    batch_df: pd.DataFrame,
    system_prompt: str,
    response_schema_str: str,
) -> list[dict]:
    """Send one batch of codes to ai_query and parse the structured response.

    Threat model for SQL string construction:
    - MODEL_NAME is a module-level constant (not user input).
    - Escaped content originates from internal bank product descriptions
      (trusted source, not external user input).
    - Single-quote escaping via replace("'", "''") is the standard Spark SQL
      mechanism for string literals and is sufficient for this context.
    - ai_query() interprets its arguments as opaque strings, not executable SQL.
    """
    user_prompt = _build_user_prompt(batch_df)
    full_prompt = system_prompt + "\n" + user_prompt
    escaped = full_prompt.replace("'", "''")
    escaped_schema = response_schema_str.replace("'", "''")

    query = (
        f"SELECT ai_query('{MODEL_NAME}', '{escaped}', "
        f"responseFormat => '{escaped_schema}') as result"
    )

    result_raw = spark.sql(query).collect()[0]["result"]
    parsed = json.loads(result_raw)
    classifications = parsed.get("classifications", [])

    now_ts = datetime.now(timezone.utc)
    batch_lookup = batch_df.set_index("product_code").to_dict(orient="index")

    results = []
    for cls in classifications:
        raw_code = str(cls.get("PROD_core_system_mapping", "")).strip().upper()
        meta = batch_lookup.get(
            str(cls.get("PROD_core_system_mapping", "")).strip(), {}
        )

        lob = str(cls.get("PROD_line_of_business", "")).strip().upper()
        category = str(cls.get("PROD_product_category", "")).strip().upper()
        prod_type = str(cls.get("PROD_product_type", "")).strip().upper()
        prod_name = cls.get("PROD_product_name")
        prod_code = cls.get("PROD_product_code")

        if prod_name is not None:
            prod_name = str(prod_name).strip().upper()
        if prod_code is not None:
            prod_code = str(prod_code).strip().upper()

        if lob not in VALID_LINE_OF_BUSINESS:
            review_status = "REQUIRES_MANUAL_MAPPING"
        else:
            review_status = "PENDING_REVIEW"

        type_id = hashlib.sha256(raw_code.encode("utf-8")).hexdigest()[:32]

        confidence = cls.get("confidence", 0.0)
        if confidence is None:
            confidence = 0.0

        results.append({
            "PROD_product_type_id": type_id,
            "PROD_line_of_business": lob,
            "PROD_product_category": category,
            "PROD_product_type": prod_type,
            "PROD_product_name": prod_name,
            "PROD_product_code": prod_code,
            "PROD_status": meta.get("prod_status", "ACTIVE"),
            "PROD_core_system_mapping": raw_code,
            "PROD_balance_requires_abs": category == "LOANS",
            "PROD_created_date": now_ts,
            "PROD_modified_date": now_ts,
            "processing_timestamp": now_ts,
            "review_status": review_status,
            "confidence": float(confidence),
            "ai_model": MODEL_NAME,
            "prompt_version": PROMPT_VERSION,
            "description_samples": meta.get("description_samples", ""),
            "volume": meta.get("volume", 0),
        })

    return results


def _error_row(row: pd.Series, error_msg: str) -> dict:
    """Create an error row so failed codes are visible in the output table."""
    raw_code = str(row["product_code"]).strip().upper()
    type_id = hashlib.sha256(raw_code.encode("utf-8")).hexdigest()[:32]
    now_ts = datetime.now(timezone.utc)

    return {
        "PROD_product_type_id": type_id,
        "PROD_line_of_business": None,
        "PROD_product_category": None,
        "PROD_product_type": None,
        "PROD_product_name": None,
        "PROD_product_code": None,
        "PROD_status": row.get("prod_status", "ACTIVE"),
        "PROD_core_system_mapping": raw_code,
        "PROD_balance_requires_abs": False,
        "PROD_created_date": now_ts,
        "PROD_modified_date": now_ts,
        "processing_timestamp": now_ts,
        "review_status": "NEEDS_MANUAL_REVIEW",
        "confidence": 0.0,
        "ai_model": MODEL_NAME,
        "prompt_version": PROMPT_VERSION,
        "description_samples": f"ERROR: {error_msg[:200]}",
        "volume": row.get("volume", 0),
    }
