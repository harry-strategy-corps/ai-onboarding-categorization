"""
Product Classification Suggestions — Step 2 (MVP)

A SQLMesh Python model that:
  1. Reads the product catalog (hardcoded Bank Plus seed for MVP)
  2. Batches product codes (CLASSIFICATION_BATCH_SIZE per batch)
  3. Calls ai_query() with the taxonomy prompt + responseFormat schema
  4. Parses the JSON response and explodes into individual rows
  5. Applies Silver column naming, UPPERCASE normalization, SHA2 hashing
  6. Sets review_status (PENDING_REVIEW, REQUIRES_MANUAL_MAPPING)
  7. Outputs Silver-aligned rows for the ai_product_suggestions table

On local gateway: mock UDFs return deterministic results.
On Databricks: real ai_query() calls Sonnet for classification.
"""

import typing as t
import json
import hashlib
import math
from datetime import datetime, timezone

import pandas as pd
from sqlmesh import ExecutionContext, model
from sqlmesh.core.model.kind import ModelKindName

from models.ai_categorization._constants import (
    AI_MODEL,
    CLASSIFICATION_BATCH_SIZE,
    DEFAULT_PROD_STATUS,
    PROMPT_VERSION,
    REVIEW_STATUS_FAILED,
    REVIEW_STATUS_MANUAL,
    REVIEW_STATUS_PENDING,
    VALID_LINE_OF_BUSINESS,
)
from models.ai_categorization._prompt_builder import (
    RESPONSE_SCHEMA_STR,
    build_full_prompt,
)


@model(
    "ai_categorization.product_classification_suggestions",
    kind=dict(name=ModelKindName.FULL),
    columns={
        "PROD_product_type_id": "TEXT",
        "PROD_line_of_business": "TEXT",
        "PROD_product_category": "TEXT",
        "PROD_product_type": "TEXT",
        "PROD_product_name": "TEXT",
        "PROD_product_code": "TEXT",
        "PROD_status": "TEXT",
        "PROD_core_system_mapping": "TEXT",
        "PROD_balance_requires_abs": "BOOLEAN",
        "PROD_created_date": "TEXT",
        "PROD_modified_date": "TEXT",
        "processing_timestamp": "TEXT",
        "review_status": "TEXT",
        "confidence": "DOUBLE",
        "ai_model": "TEXT",
        "prompt_version": "TEXT",
        "product_domain": "TEXT",
        "source_table": "TEXT",
        "account_count": "INT",
    },
    tags=["ai_categorization"],
)
def execute(
    context: ExecutionContext,
    start: datetime,
    end: datetime,
    execution_time: datetime,
    **kwargs: t.Any,
) -> pd.DataFrame:
    from macros.mock_ai_functions import is_local_gateway, register_mock_ai_udfs

    spark = context.spark

    if is_local_gateway():
        register_mock_ai_udfs(spark)

    physical_table = context.resolve_table("ai_categorization.seed_bankplus_product_catalog")
    catalog_df = context.fetchdf(f"SELECT * FROM {physical_table}")

    catalog_records = catalog_df.to_dict("records")
    n_batches = math.ceil(len(catalog_records) / CLASSIFICATION_BATCH_SIZE)
    now_ts = datetime.now(timezone.utc).isoformat()

    all_rows: list[dict] = []

    for batch_idx in range(n_batches):
        batch_start = batch_idx * CLASSIFICATION_BATCH_SIZE
        batch_end = batch_start + CLASSIFICATION_BATCH_SIZE
        batch = catalog_records[batch_start:batch_end]

        prompt_items = []
        for rec in batch:
            prompt_items.append({
                "product_code": str(rec.get("product_code", "")).strip(),
                "product_description": str(rec.get("product_description", "")).strip(),
                "product_domain": str(rec.get("product_domain", "DEPOSIT")).strip(),
                "purpose_code": rec.get("purpose_code"),
                "purpose_description": rec.get("purpose_description"),
                "loan_type_desc": rec.get("loan_type_desc"),
            })

        full_prompt = build_full_prompt(prompt_items)

        try:
            classifications = _call_ai_query(spark, full_prompt)
        except Exception:
            for item in prompt_items:
                all_rows.append(_build_failed_row(item, now_ts))
            continue

        catalog_lookup = {
            str(r.get("product_code", "")).strip(): r for r in batch
        }

        for cls in classifications:
            raw_code = str(cls.get("PROD_core_system_mapping", "")).strip()
            catalog_rec = catalog_lookup.get(raw_code, {})
            all_rows.append(_build_output_row(cls, catalog_rec, now_ts))

    df = pd.DataFrame(all_rows)
    df.columns = [c.lower() for c in df.columns]
    return df


def _call_ai_query(spark, prompt: str) -> list[dict]:
    """Execute ai_query() via Spark SQL and parse the JSON response."""
    escaped_prompt = prompt.replace("\\", "\\\\").replace("'", "\\'")
    escaped_schema = RESPONSE_SCHEMA_STR.replace("\\", "\\\\").replace("'", "\\'")

    query = f"""
    SELECT ai_query(
        '{AI_MODEL}',
        '{escaped_prompt}'
    ) AS result
    """

    result_row = spark.sql(query).collect()[0]
    raw_json = result_row["result"]

    parsed = json.loads(raw_json)
    return parsed.get("classifications", [])


def _build_output_row(cls: dict, catalog_rec: dict, now_ts: str) -> dict:
    """Transform a single LLM classification into a Silver-aligned output row."""
    raw_code = str(cls.get("PROD_core_system_mapping", "")).strip().upper()
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
        review_status = REVIEW_STATUS_MANUAL
    else:
        review_status = REVIEW_STATUS_PENDING

    balance_requires_abs = category == "LOANS"

    type_id = hashlib.sha256(raw_code.encode("utf-8")).hexdigest()

    confidence = cls.get("confidence", 0.0)
    if confidence is None:
        confidence = 0.0

    return {
        "PROD_product_type_id": type_id,
        "PROD_line_of_business": lob,
        "PROD_product_category": category,
        "PROD_product_type": prod_type,
        "PROD_product_name": prod_name,
        "PROD_product_code": prod_code,
        "PROD_status": DEFAULT_PROD_STATUS,
        "PROD_core_system_mapping": raw_code,
        "PROD_balance_requires_abs": balance_requires_abs,
        "PROD_created_date": now_ts,
        "PROD_modified_date": now_ts,
        "processing_timestamp": now_ts,
        "review_status": review_status,
        "confidence": float(confidence),
        "ai_model": AI_MODEL,
        "prompt_version": PROMPT_VERSION,
        "product_domain": str(catalog_rec.get("product_domain", "")).strip().upper(),
        "source_table": str(catalog_rec.get("source_table", "")).strip(),
        "account_count": int(catalog_rec.get("account_count", 0) or 0),
    }


def _build_failed_row(item: dict, now_ts: str) -> dict:
    """Build a placeholder row for a product code that failed classification."""
    raw_code = str(item.get("product_code", "")).strip().upper()
    type_id = hashlib.sha256(raw_code.encode("utf-8")).hexdigest()

    return {
        "PROD_product_type_id": type_id,
        "PROD_line_of_business": None,
        "PROD_product_category": None,
        "PROD_product_type": None,
        "PROD_product_name": None,
        "PROD_product_code": None,
        "PROD_status": DEFAULT_PROD_STATUS,
        "PROD_core_system_mapping": raw_code,
        "PROD_balance_requires_abs": False,
        "PROD_created_date": now_ts,
        "PROD_modified_date": now_ts,
        "processing_timestamp": now_ts,
        "review_status": REVIEW_STATUS_FAILED,
        "confidence": 0.0,
        "ai_model": AI_MODEL,
        "prompt_version": PROMPT_VERSION,
        "product_domain": str(item.get("product_domain", "")).strip().upper(),
        "source_table": "",
        "account_count": 0,
    }
