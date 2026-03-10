"""
Single source of truth for the product categorization pipeline.

The column mapping between notebook output names and Silver model column names
is the #1 source of bugs. Levels 2 and 3 are SWAPPED between the notebook
convention and the Silver `product_type_configuration_master` schema:

    Notebook "product_type"     → Silver "PROD_product_category"   (L2)
    Notebook "product_category" → Silver "PROD_product_type"       (L3)

All downstream models import from this module rather than defining their own
column names.
"""

# ── Column Mapping ────────────────────────────────────────────────
# Notebook output name → Silver column name
# WARNING: L2 and L3 names are SWAPPED between notebook and Silver.
COLUMN_MAPPING = {
    "line_of_business":    "PROD_line_of_business",     # L1
    "product_type":        "PROD_product_category",     # L2 — SWAPPED
    "product_category":    "PROD_product_type",         # L3 — SWAPPED
    "product_subcategory": "PROD_product_name",         # L4
    "product_special":     "PROD_product_code",         # L5
    "product_code":        "PROD_core_system_mapping",  # Raw code
}

# Reverse mapping: Silver column → notebook column (for parsing LLM output)
SILVER_TO_NOTEBOOK = {v: k for k, v in COLUMN_MAPPING.items()}

# ── AI Configuration ─────────────────────────────────────────────
AI_MODEL = "databricks-claude-sonnet-4-6"
CLASSIFICATION_BATCH_SIZE = 30
AI_QUERY_MAX_RETRIES = 3
PROMPT_VERSION = "v1.0"

# ── Review Status Values ─────────────────────────────────────────
REVIEW_STATUS_PENDING = "PENDING_REVIEW"
REVIEW_STATUS_APPROVED = "APPROVED"
REVIEW_STATUS_REJECTED = "REJECTED"
REVIEW_STATUS_MANUAL = "REQUIRES_MANUAL_MAPPING"
REVIEW_STATUS_FAILED = "NEEDS_MANUAL_REVIEW"

# ── Valid Taxonomy Values ─────────────────────────────────────────
# L1: Only RETAIL and BUSINESS are accepted in output.
# WEALTH MANAGEMENT is valid from the LLM but gets flagged for manual review.
VALID_LINE_OF_BUSINESS = {"RETAIL", "BUSINESS"}

# L2 (Silver: PROD_product_category)
VALID_PRODUCT_CATEGORY = {"DEPOSITS", "LOANS", "SERVICES"}

# L3 examples — not exhaustive because L3 values are more varied
VALID_PRODUCT_TYPE_DEPOSITS = {
    "CHECKING",
    "CHECKING (DDA)",
    "SAVINGS",
    "MONEY MARKET",
    "CERTIFICATES OF DEPOSIT (CDS)",
}

VALID_PRODUCT_TYPE_LOANS = {
    "MORTGAGE",
    "MORTGAGE LOANS",
    "HELOC",
    "HELOCS (HOME EQUITY LINES OF CREDIT)",
    "HOME EQUITY",
    "CREDIT CARD",
    "PERSONAL",
    "PERSONAL LOANS",
    "AUTO",
    "AUTO LOANS",
    "STUDENT",
    "STUDENT LOANS",
    "LINE OF CREDIT",
    "COMMERCIAL",
    "COMMERCIAL REAL ESTATE",
    "AGRICULTURAL",
    "REAL ESTATE",
    "RECEIVABLES-BASED",
    "EQUIPMENT FINANCING",
}

# ── Silver Schema Defaults ────────────────────────────────────────
DEFAULT_PROD_STATUS = "ACTIVE"

# Purpose codes that indicate Business line of business
BUSINESS_PURPOSE_CODES = {3, 4, 5, 6, 9}
# Purpose codes that indicate Retail line of business
RETAIL_PURPOSE_CODES = {1, 2}
