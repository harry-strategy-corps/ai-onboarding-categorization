"""
Mock AI Functions for Local Spark Development

Based on research, there are three integration points for mock UDFs:

1. **Python Models** (primary): Within a Python model's `execute()` function,
   access `context.spark` to register UDFs before running queries. Call
   `register_mock_ai_udfs(spark)` at the top of any Python model that uses
   ai_query() or ai_mask().

2. **sqlmesh test (conftest-style)**: For YAML unit tests, register mocks in
   the test's Spark session setup. See tests/ for examples.

3. **Production (Databricks)**: ai_query() and ai_mask() are native Databricks
   SQL functions — no registration needed. The gateway detection helper
   `is_local_gateway()` prevents mock registration on Databricks.

Usage in a Python model:

    from macros.mock_ai_functions import register_mock_ai_udfs, is_local_gateway

    @model(...)
    def execute(context, ...):
        if is_local_gateway():
            register_mock_ai_udfs(context.spark)

        df = context.spark.sql("SELECT ai_query(...) ...")
        return df
"""

import json
import os
from pyspark.sql.types import StringType, ArrayType


def is_local_gateway() -> bool:
    """Check if we're running on the local gateway (not Databricks)."""
    return os.environ.get("CIQ_ENVIRONMENT_GATEWAY", "local") == "local"


MOCK_DEPOSIT_CLASSIFICATIONS = {
    "01": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "Personal Checking", "code": None},
    "02": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "Student Checking", "code": None},
    "07": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "Investment Checking", "code": None},
    "09": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "Personal Money Market", "code": None},
    "10": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "Employee Investment", "code": None},
    "50": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "PrimePlus Club", "code": None},
    "C3": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "ValuePlus Checking", "code": None},
    "C4": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "Carefree Checking", "code": None},
    "CO": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "Checking (Closed)", "code": None},
    "D3": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "Carefree Checking GF", "code": None},
    "D8": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "HY MM Diamond", "code": None},
    "S1": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "SAVINGS", "name": "Personal Savings", "code": None},
    "B1": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "Business Checking", "code": None},
    "B3": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "Business Checking Plus", "code": None},
    "P1": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "Platinum Checking", "code": None},
    "P2": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "HY MM Turquoise", "code": None},
    "T1": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "SAVINGS", "name": "Personal Savings CP $250", "code": None},
    "T3": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "SAVINGS", "name": "Employee Savings", "code": None},
    "S5": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "SAVINGS", "name": "Christmas Club", "code": None},
    "H1": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "HY Hybrid Investment", "code": None},
    "F1": {"lob": "WEALTH MANAGEMENT", "cat": "DEPOSITS", "type": "CHECKING", "name": "Fiduciary Business Int CK", "code": None},
    "F2": {"lob": "WEALTH MANAGEMENT", "cat": "DEPOSITS", "type": "CHECKING", "name": "Fiduciary Personal Int CK", "code": None},
    "F3": {"lob": "WEALTH MANAGEMENT", "cat": "DEPOSITS", "type": "SAVINGS", "name": "Fiduciary Savings", "code": None},
    "F4": {"lob": "WEALTH MANAGEMENT", "cat": "DEPOSITS", "type": "SAVINGS", "name": "UTMA Savings", "code": "UGMA/UTMA"},
    "08": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "Inactive Checking", "code": None},
}

MOCK_LOAN_CLASSIFICATIONS = {
    "P1": {"lob": "RETAIL", "cat": "LOANS", "type": "PERSONAL", "name": "Individual Fixed", "code": None},
    "R1": {"lob": "RETAIL", "cat": "LOANS", "type": "MORTGAGE", "name": "Residential RE Fixed", "code": None},
    "B1": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL", "name": "Business Loan Fixed", "code": None},
    "A1": {"lob": "BUSINESS", "cat": "LOANS", "type": "AGRICULTURAL", "name": "AG RE Fixed", "code": None},
    "BC": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL REAL ESTATE", "name": "CRE Fixed", "code": None},
    "C7": {"lob": "RETAIL", "cat": "LOANS", "type": "LINE OF CREDIT", "name": "PLOC Platinum", "code": None},
    "HA": {"lob": "RETAIL", "cat": "LOANS", "type": "HOME EQUITY", "name": "HELOC Pr Platinum", "code": None},
    "B2": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL", "name": "Business Loan Var", "code": None},
    "R9": {"lob": "RETAIL", "cat": "LOANS", "type": "MORTGAGE", "name": "Mortgage Ctr RE 1st", "code": None},
    "C4": {"lob": "RETAIL", "cat": "LOANS", "type": "LINE OF CREDIT", "name": "PLOC Gold", "code": None},
    "A5": {"lob": "BUSINESS", "cat": "LOANS", "type": "AGRICULTURAL", "name": "AG Fixed", "code": None},
    "BD": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL REAL ESTATE", "name": "CRE Var", "code": None},
    "B9": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL", "name": "NF NR Fixed", "code": None},
    "BG": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL", "name": "Taxable Loan SCM", "code": None},
    "O1": {"lob": "RETAIL", "cat": "LOANS", "type": "LINE OF CREDIT", "name": "Overdraft Protection", "code": None},
    "P0": {"lob": "RETAIL", "cat": "LOANS", "type": "PERSONAL", "name": "Credit Builder", "code": None},
    "L1": {"lob": "BUSINESS", "cat": "LOANS", "type": "LINE OF CREDIT", "name": "LOC Fixed", "code": None},
    "L2": {"lob": "BUSINESS", "cat": "LOANS", "type": "LINE OF CREDIT", "name": "LOC Var", "code": None},
}

_DEFAULT_CLASSIFICATION = {
    "lob": "RETAIL",
    "cat": "DEPOSITS",
    "type": "CHECKING",
    "name": "Unknown Product",
    "code": None,
}


def _build_classification_response(product_code: str, domain: str = "DEPOSIT") -> dict:
    """Build a single classification dict for a product code using the mock lookup."""
    lookup = MOCK_LOAN_CLASSIFICATIONS if domain == "LOAN" else MOCK_DEPOSIT_CLASSIFICATIONS
    entry = lookup.get(product_code, _DEFAULT_CLASSIFICATION)

    return {
        "PROD_core_system_mapping": product_code,
        "PROD_line_of_business": entry["lob"],
        "PROD_product_category": entry["cat"],
        "PROD_product_type": entry["type"],
        "PROD_product_name": entry["name"],
        "PROD_product_code": entry["code"],
        "confidence": 0.95 if product_code in lookup else 0.50,
    }


def mock_ai_query_fn(model: str, prompt: str) -> str:
    """
    Mock implementation of Databricks ai_query().

    Parses the prompt to extract product codes and returns deterministic
    classifications. When the prompt content can't be parsed, returns a
    single default classification.
    """
    import re

    classifications = []
    code_pattern = re.compile(r"product_code=(\w+)")
    domain_pattern = re.compile(r"DOMAIN=(DEPOSIT|LOAN)")

    matches = code_pattern.findall(prompt)
    domains = domain_pattern.findall(prompt)

    if matches:
        for i, code in enumerate(matches):
            domain = domains[i] if i < len(domains) else "DEPOSIT"
            classifications.append(_build_classification_response(code, domain))
    else:
        classifications.append(_build_classification_response("MOCK", "DEPOSIT"))

    return json.dumps({"classifications": classifications})


def mock_ai_mask_fn(text: str, labels: str = None) -> str:
    """
    Mock implementation of Databricks ai_mask().

    Returns the text with PII-like content replaced by [MASKED].
    For local testing this is a passthrough with a marker.
    """
    if text is None:
        return None
    return f"[MASKED]"


def register_mock_ai_udfs(spark) -> None:
    """
    Register mock ai_query() and ai_mask() UDFs in the given Spark session.

    Call this from Python models when running on the local gateway:

        from macros.mock_ai_functions import register_mock_ai_udfs, is_local_gateway

        if is_local_gateway():
            register_mock_ai_udfs(context.spark)
    """
    spark.udf.register("ai_query", mock_ai_query_fn, StringType())
    spark.udf.register("ai_mask", mock_ai_mask_fn, StringType())
