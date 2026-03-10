"""
Prompt builder for the product classification pipeline.

Builds the system prompt (taxonomy-embedded), user prompt (per-batch), and
the structured JSON response schema — all using Silver column names directly
so that LLM output requires minimal post-processing.

Adapted from notebooks/products/02_categorize_products.ipynb with the following
changes for the SQLMesh pipeline:
  - Output schema uses Silver column names (PROD_*) instead of notebook names
  - Removed Bank Plus–specific hardcoded overrides (WM trust codes, CD rules)
  - Removed CD classification rules (CDs are out of scope)
  - Generic few-shot examples that work across FIs
  - Batch prompt accepts a list of dicts instead of a pandas DataFrame
"""

import json
import os
from pathlib import Path
from typing import Optional

from models.ai_categorization._constants import PROMPT_VERSION


def _load_taxonomy() -> str:
    """Load the product categorization taxonomy markdown file."""
    candidates = [
        Path(__file__).parent.parent.parent / "taxonomy" / "product_categorization_taxonomy.md",
        Path("taxonomy") / "product_categorization_taxonomy.md",
        Path("sqlmesh") / "taxonomy" / "product_categorization_taxonomy.md",
    ]
    for path in candidates:
        if path.exists():
            return path.read_text()
    raise FileNotFoundError(
        f"Taxonomy file not found. Searched: {[str(p) for p in candidates]}"
    )


def build_system_prompt(taxonomy_text: Optional[str] = None) -> str:
    """
    Build the system prompt with the full taxonomy embedded.

    The prompt instructs the LLM to return classifications using Silver column
    names directly (PROD_*), eliminating the need for column-name mapping in
    post-processing.
    """
    if taxonomy_text is None:
        taxonomy_text = _load_taxonomy()

    return f"""You are a product categorization engine for US community banks and financial institutions.
Given a list of product codes with descriptions and context, classify each into the
StrategyCorp product taxonomy below.

{taxonomy_text}

### Classification Rules

1. **Line of Business (Level 1) — `PROD_line_of_business`:**
   Determine whether the product belongs to Retail or Business.
   - **RETAIL** — consumer/individual banking products (personal checking, savings,
     consumer loans, mortgages, HELOCs, auto loans, etc.)
   - **BUSINESS** — commercial/business banking products (business checking, commercial
     loans, treasury management, commercial real estate, agricultural loans, etc.)
   - **WEALTH MANAGEMENT** — trust, fiduciary, investment, and securities products.
     Classify as WEALTH MANAGEMENT ONLY when the product name or code explicitly
     indicates fiduciary, trust, or securities management (keywords: FIDUCIARY, TRUST,
     UTMA, UGMA, IRA, ESTATE).
   - For loans: use PURCOD (purpose code) when available:
     - 01, 02 → RETAIL
     - 03, 04, 05, 06, 09 → BUSINESS
     - 07, 08, 10, 11 → use product description context

2. **Product Category (Level 2) — `PROD_product_category`:**
   One of: DEPOSITS, LOANS, SERVICES.
   Determined by the product domain (DEPOSIT → DEPOSITS, LOAN → LOANS).

3. **Product Type (Level 3) — `PROD_product_type`:**
   The specific product type within the category. Use these strings:
   - Deposits: CHECKING, SAVINGS, MONEY MARKET
   - Loans: MORTGAGE, HOME EQUITY, LINE OF CREDIT, PERSONAL, AUTO,
     COMMERCIAL, COMMERCIAL REAL ESTATE, AGRICULTURAL, REAL ESTATE,
     RECEIVABLES-BASED, EQUIPMENT FINANCING

4. **Product Name (Level 4) — `PROD_product_name`:**
   Derive from the product description — the distinguishing feature within its
   Level 3 type (e.g., "Premium", "Basic", "Interest Bearing", "Platinum").
   Use null if no meaningful distinction can be made.

5. **Product Code (Level 5) — `PROD_product_code`:**
   Special designation evident from the product name (e.g., HSA, UTMA, ARM, Fixed).
   Use null for most products.

6. **Output values MUST be UPPERCASED** (e.g., "RETAIL" not "Retail", "DEPOSITS" not "Deposits").

7. Use null for any level if no mapping fits. Do not guess.

8. `confidence`: 0.0 to 1.0 — your certainty in the classification.

### Few-Shot Examples

Input: product_code=CK, DESC="Personal Checking", DOMAIN=DEPOSIT
Output: {{{{
  "PROD_core_system_mapping": "CK",
  "PROD_line_of_business": "RETAIL",
  "PROD_product_category": "DEPOSITS",
  "PROD_product_type": "CHECKING",
  "PROD_product_name": "PERSONAL CHECKING",
  "PROD_product_code": null,
  "confidence": 0.95
}}}}

Input: product_code=R1, DESC="Residential RE Fixed", DOMAIN=LOAN, PURCOD=2, PURPOSE="Real Estate — Residential"
Output: {{{{
  "PROD_core_system_mapping": "R1",
  "PROD_line_of_business": "RETAIL",
  "PROD_product_category": "LOANS",
  "PROD_product_type": "MORTGAGE",
  "PROD_product_name": "RESIDENTIAL RE FIXED",
  "PROD_product_code": "FIXED",
  "confidence": 0.93
}}}}

Input: product_code=B1, DESC="Business Checking", DOMAIN=DEPOSIT
Output: {{{{
  "PROD_core_system_mapping": "B1",
  "PROD_line_of_business": "BUSINESS",
  "PROD_product_category": "DEPOSITS",
  "PROD_product_type": "CHECKING",
  "PROD_product_name": "BUSINESS CHECKING",
  "PROD_product_code": null,
  "confidence": 0.92
}}}}

Input: product_code=MM, DESC="Money Market Savings", DOMAIN=DEPOSIT
Output: {{{{
  "PROD_core_system_mapping": "MM",
  "PROD_line_of_business": "RETAIL",
  "PROD_product_category": "DEPOSITS",
  "PROD_product_type": "MONEY MARKET",
  "PROD_product_name": "MONEY MARKET SAVINGS",
  "PROD_product_code": null,
  "confidence": 0.94
}}}}

Input: product_code=BC, DESC="CRE Fixed", DOMAIN=LOAN, PURCOD=4, PURPOSE="Business — Commercial"
Output: {{{{
  "PROD_core_system_mapping": "BC",
  "PROD_line_of_business": "BUSINESS",
  "PROD_product_category": "LOANS",
  "PROD_product_type": "COMMERCIAL REAL ESTATE",
  "PROD_product_name": "CRE FIXED",
  "PROD_product_code": "FIXED",
  "confidence": 0.91
}}}}

Input: product_code=C7, DESC="PLOC Platinum", DOMAIN=LOAN, PURCOD=1, PURPOSE="Personal/Household"
Output: {{{{
  "PROD_core_system_mapping": "C7",
  "PROD_line_of_business": "RETAIL",
  "PROD_product_category": "LOANS",
  "PROD_product_type": "LINE OF CREDIT",
  "PROD_product_name": "PLOC PLATINUM",
  "PROD_product_code": null,
  "confidence": 0.90
}}}}
"""


def build_user_prompt(product_codes: list[dict]) -> str:
    """
    Build the user prompt for a batch of product codes.

    Each dict in product_codes should have:
      - product_code: str — the raw product code (e.g., "CK", "01")
      - product_description: str — human-readable name (may be empty)
      - product_domain: str — "DEPOSIT" or "LOAN"
      - purpose_code: optional str/int — loan purpose code
      - purpose_description: optional str — purpose code description
      - loan_type_code: optional str — loan type code
      - loan_type_desc: optional str — loan type description
    """
    lines = []
    for item in product_codes:
        code = str(item.get("product_code", "")).strip()
        desc = str(item.get("product_description", "")).strip()
        if desc in ("", "nan", "None", "(unknown)", "null"):
            desc = "(no description)"
        domain = str(item.get("product_domain", "DEPOSIT")).strip()

        parts = [
            f"product_code={code}",
            f'DESC="{desc}"',
            f"DOMAIN={domain}",
        ]

        purcod = item.get("purpose_code")
        if purcod is not None and str(purcod).strip() not in ("", "nan", "None"):
            parts.append(f"PURCOD={purcod}")

        purpose_desc = item.get("purpose_description")
        if purpose_desc is not None and str(purpose_desc).strip() not in ("", "nan", "None"):
            parts.append(f'PURPOSE="{str(purpose_desc).strip()}"')

        loan_type = item.get("loan_type_desc")
        if loan_type is not None and str(loan_type).strip() not in ("", "nan", "None"):
            parts.append(f'LOAN_TYPE="{str(loan_type).strip()}"')

        lines.append(", ".join(parts))

    codes_text = "\n".join(f"  - {line}" for line in lines)
    return (
        f"Classify these {len(product_codes)} product codes:\n"
        f"{codes_text}\n\n"
        f'Return a JSON object with a "classifications" array containing one '
        f"entry per product code. Use the EXACT output schema specified."
    )


# ── Response Schema ───────────────────────────────────────────────
# Uses Silver column names directly so LLM output maps 1:1 to the target schema.
RESPONSE_SCHEMA = {
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
                            "PROD_line_of_business":    {"type": "string"},
                            "PROD_product_category":    {"type": "string"},
                            "PROD_product_type":        {"type": "string"},
                            "PROD_product_name":        {"type": ["string", "null"]},
                            "PROD_product_code":        {"type": ["string", "null"]},
                            "confidence":               {"type": "number"},
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

RESPONSE_SCHEMA_STR = json.dumps(RESPONSE_SCHEMA)


def build_full_prompt(product_codes: list[dict], taxonomy_text: Optional[str] = None) -> str:
    """Build the complete prompt (system + user) for an ai_query() call."""
    system = build_system_prompt(taxonomy_text)
    user = build_user_prompt(product_codes)
    return system + "\n\n" + user
