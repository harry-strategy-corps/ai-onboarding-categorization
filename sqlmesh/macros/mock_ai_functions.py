"""
Mock AI Functions for Local Spark Development

Integration points for mock UDFs:

1. **Python Models** (primary): Within a Python model's `execute()` function,
   access `context.spark` to register UDFs before running queries. Call
   `register_mock_ai_udfs(spark)` at the top of any Python model that uses
   ai_query() or ai_mask().

2. **Production (Databricks)**: ai_query() and ai_mask() are native Databricks
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
from pyspark.sql.types import StringType


def is_local_gateway() -> bool:
    """Check if we're running on the local gateway (not Databricks)."""
    return os.environ.get("CIQ_ENVIRONMENT_GATEWAY", "local") == "local"


# Ground-truth classifications derived from Bank Plus notebook results and
# manual review. Keys use Silver column names directly (PROD_*) so mock
# output matches what the real LLM returns with responseFormat.
#
# Format: { "code": { "lob", "cat", "type", "name", "code", "confidence" } }
#   lob  → PROD_line_of_business   (L1)
#   cat  → PROD_product_category   (L2 Silver)
#   type → PROD_product_type       (L3 Silver)
#   name → PROD_product_name       (L4)
#   code → PROD_product_code       (L5)

MOCK_DEPOSIT_CLASSIFICATIONS = {
    "01": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "PERSONAL CHECKING", "code": None, "conf": 0.95},
    "02": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "STUDENT CHECKING", "code": None, "conf": 0.94},
    "04": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "PUBLIC FUNDS OTHER", "code": None, "conf": 0.75},
    "07": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "INVESTMENTPLUS CK", "code": None, "conf": 0.88},
    "08": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "BUSINESS MONEY MKT", "code": None, "conf": 0.93},
    "09": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "PERSONAL MM", "code": None, "conf": 0.94},
    "10": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "EMPLOYEE INVESTMENT", "code": None, "conf": 0.82},
    "11": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "NISSAN CHECKING", "code": "AFFINITY", "conf": 0.89},
    "12": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "NISSAN INVESTMENT CK", "code": "AFFINITY", "conf": 0.87},
    "13": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "SAVINGS", "name": "HSA - FAMILY", "code": "HSA", "conf": 0.96},
    "14": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "SAVINGS", "name": "HSA - INDIVIDUAL", "code": "HSA", "conf": 0.96},
    "15": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "OFFICIAL CHECKS", "code": None, "conf": 0.70},
    "16": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "BANKPLUS/ BANCPLUS", "code": None, "conf": 0.85},
    "21": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "FREE BUSINESS CKING", "code": None, "conf": 0.92},
    "23": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "MSB CHECKING", "code": None, "conf": 0.88},
    "25": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "MS IOLTA CHECKING", "code": "IOLTA", "conf": 0.94},
    "26": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "BUSINESS INTEREST CK", "code": None, "conf": 0.90},
    "28": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "ATM CHECKING", "code": None, "conf": 0.87},
    "29": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "MS LOTTERY BUS CKG", "code": None, "conf": 0.85},
    "30": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "LA IOLTA CHECKING", "code": "IOLTA", "conf": 0.94},
    "31": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "WMG MMDA INTEREST CK", "code": None, "conf": 0.86},
    "32": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "WMG MMDA RETIREMENT", "code": None, "conf": 0.89},
    "36": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "PUBLIC FUNDS INT CK", "code": None, "conf": 0.88},
    "38": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "PF MONEY MARKET", "code": None, "conf": 0.87},
    "39": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "AL IOLTA CHECKING", "code": "IOLTA", "conf": 0.94},
    "41": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "LA LOTTERY BUS CKG", "code": None, "conf": 0.85},
    "50": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "PRIMEPLUS CLUB", "code": None, "conf": 0.90},
    "76": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "CREDITPLUS CHECKING", "code": None, "conf": 0.88},
    "89": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "PUBLIC FUNDS SPECIAL", "code": None, "conf": 0.82},
    "B1": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "LEGACY BUSINESS CK", "code": None, "conf": 0.89},
    "B2": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "BUSINESS BASICS CK", "code": None, "conf": 0.90},
    "B3": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "BUSINESS PREMIER CK", "code": None, "conf": 0.91},
    "B4": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "BUSINESS ELITE CK", "code": None, "conf": 0.90},
    "B5": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "COMMERCIAL ANALYSIS", "code": None, "conf": 0.88},
    "C1": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "HIGH YIELD CHECKING", "code": None, "conf": 0.90},
    "C3": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "VALUEPLUS CHECKING", "code": None, "conf": 0.92},
    "C4": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "CAREFREE CHECKING", "code": None, "conf": 0.93},
    "C5": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "VALUEPLUS INTEREST", "code": None, "conf": 0.91},
    "C6": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "VALUEPLUS STUDENT CK", "code": None, "conf": 0.90},
    "C7": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "HY MM PLUS", "code": None, "conf": 0.92},
    "C8": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "HY BUS MM PLUS", "code": None, "conf": 0.91},
    "C9": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "CONTINENTAL TIRE CK", "code": "AFFINITY", "conf": 0.88},
    "D1": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "CT INVESTMENT CK", "code": None, "conf": 0.85},
    "D3": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "CAREFREE CHK GF", "code": None, "conf": 0.91},
    "D4": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "PREMIER MM", "code": None, "conf": 0.92},
    "D5": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "PREMIER BUSINESS MM", "code": None, "conf": 0.91},
    "D6": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "HY MM EMERALD", "code": None, "conf": 0.91},
    "D7": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "HY BUS MM EMERALD", "code": None, "conf": 0.90},
    "D8": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "HY MM DIAMOND", "code": None, "conf": 0.93},
    "D9": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "HY BUS MM DIAMOND", "code": None, "conf": 0.92},
    "E2": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "SAVINGS", "name": "TUITION MONEY MGR", "code": None, "conf": 0.85},
    "E3": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "SAVINGS", "name": "BANKPLUS TUITION", "code": None, "conf": 0.86},
    "F1": {"lob": "WEALTH MANAGEMENT", "cat": "DEPOSITS", "type": "CHECKING", "name": "FIDUCIARY BUS INT CK", "code": None, "conf": 0.88},
    "F2": {"lob": "WEALTH MANAGEMENT", "cat": "DEPOSITS", "type": "CHECKING", "name": "FIDUCIARY PER INT CK", "code": None, "conf": 0.89},
    "F3": {"lob": "WEALTH MANAGEMENT", "cat": "DEPOSITS", "type": "SAVINGS", "name": "FIDUCIARY SAVINGS", "code": None, "conf": 0.90},
    "F4": {"lob": "WEALTH MANAGEMENT", "cat": "DEPOSITS", "type": "SAVINGS", "name": "UTMA SAVINGS", "code": "UGMA/UTMA", "conf": 0.92},
    "H1": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "HY HYBRID INVESTMENT", "code": None, "conf": 0.88},
    "H2": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "BUS HY HYBRID INVEST", "code": None, "conf": 0.87},
    "H3": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "HY HYBRID INVESTMENT", "code": None, "conf": 0.88},
    "H4": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "BUS HY HYBRID INVEST", "code": None, "conf": 0.87},
    "IC": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "INSURED CASH SW CK", "code": None, "conf": 0.86},
    "P1": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "PLATINUM CHECKING", "code": None, "conf": 0.91},
    "P2": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "HY MM TURQUOISE", "code": None, "conf": 0.92},
    "P3": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "MONEY MARKET", "name": "HY BUS MM TURQUOISE", "code": None, "conf": 0.91},
    "P4": {"lob": "BUSINESS", "cat": "DEPOSITS", "type": "CHECKING", "name": "DEBTOR IN POSSESSION", "code": None, "conf": 0.80},
    "S1": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "SAVINGS", "name": "PERSONAL SAVINGS", "code": None, "conf": 0.95},
    "S3": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "CHRISTMAS CLUB - CK", "code": None, "conf": 0.85},
    "S4": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "SAVINGS", "name": "EMPLOYEE CHRISTMAS", "code": None, "conf": 0.86},
    "S5": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "SAVINGS", "name": "CHRISTMAS CLUB", "code": None, "conf": 0.87},
    "S6": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "NISSAN CHRISTMAS CLU", "code": "AFFINITY", "conf": 0.85},
    "S9": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "SAVINGS", "name": "COURT ORDERED SAVING", "code": None, "conf": 0.88},
    "T1": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "SAVINGS", "name": "PER SAV FOR CP $250", "code": None, "conf": 0.89},
    "T2": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "SAVINGS", "name": "PER SAV FOR CP $500", "code": None, "conf": 0.89},
    "T3": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "SAVINGS", "name": "EMPLOYEE SAVINGS", "code": None, "conf": 0.90},
    "T4": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "SAVINGS", "name": "SECURED CC SAVINGS", "code": None, "conf": 0.87},
    "CO": {"lob": "RETAIL", "cat": "DEPOSITS", "type": "CHECKING", "name": "CHARGEOFF CKIG BKWAY", "code": None, "conf": 0.80},
}

MOCK_LOAN_CLASSIFICATIONS = {
    "A1": {"lob": "BUSINESS", "cat": "LOANS", "type": "AGRICULTURAL", "name": "AG RE - FIXED", "code": "FIXED", "conf": 0.93},
    "A2": {"lob": "BUSINESS", "cat": "LOANS", "type": "AGRICULTURAL", "name": "AG RE - VAR", "code": "VARIABLE", "conf": 0.92},
    "A5": {"lob": "BUSINESS", "cat": "LOANS", "type": "AGRICULTURAL", "name": "AG - FIXED", "code": "FIXED", "conf": 0.93},
    "A6": {"lob": "BUSINESS", "cat": "LOANS", "type": "AGRICULTURAL", "name": "AG - VAR", "code": "VARIABLE", "conf": 0.92},
    "B0": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL", "name": "NF NR VAR", "code": "VARIABLE", "conf": 0.85},
    "B1": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL", "name": "BL - FIXED", "code": "FIXED", "conf": 0.90},
    "B2": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL", "name": "BL - VAR", "code": "VARIABLE", "conf": 0.90},
    "B5": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL", "name": "MFR - FIXED", "code": "FIXED", "conf": 0.88},
    "B6": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL", "name": "MFR - VAR", "code": "VARIABLE", "conf": 0.88},
    "B9": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL", "name": "NF NR FIXED", "code": "FIXED", "conf": 0.87},
    "BC": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL REAL ESTATE", "name": "CRE - FIXED", "code": "FIXED", "conf": 0.92},
    "BD": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL REAL ESTATE", "name": "CRE - VAR", "code": "VARIABLE", "conf": 0.91},
    "BG": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL", "name": "TAXABLE LOAN SCM", "code": None, "conf": 0.83},
    "BH": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL", "name": "NON TAXABLE LN SCM", "code": None, "conf": 0.83},
    "BJ": {"lob": "RETAIL", "cat": "LOANS", "type": "PERSONAL", "name": "NON DEP FI VAR", "code": None, "conf": 0.80},
    "BN": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL", "name": "P OR C SEC FIXED", "code": "FIXED", "conf": 0.82},
    "BO": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL", "name": "P OR C SEC VAR", "code": "VARIABLE", "conf": 0.82},
    "BR": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL", "name": "OTH NCL FIXED", "code": "FIXED", "conf": 0.78},
    "BV": {"lob": "WEALTH MANAGEMENT", "cat": "LOANS", "type": "COMMERCIAL", "name": "COMM WEALTH MGMT VAR", "code": None, "conf": 0.80},
    "BW": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL", "name": "DEFICIENCY NOTES", "code": None, "conf": 0.82},
    "C0": {"lob": "RETAIL", "cat": "LOANS", "type": "LINE OF CREDIT", "name": "PLOC PLATINUMPLUS", "code": None, "conf": 0.92},
    "C1": {"lob": "RETAIL", "cat": "LOANS", "type": "LINE OF CREDIT", "name": "PLOC SILVER", "code": None, "conf": 0.91},
    "C4": {"lob": "RETAIL", "cat": "LOANS", "type": "LINE OF CREDIT", "name": "PLOC GOLD", "code": None, "conf": 0.91},
    "C7": {"lob": "RETAIL", "cat": "LOANS", "type": "LINE OF CREDIT", "name": "PLOC PLATINUM", "code": None, "conf": 0.92},
    "CC": {"lob": "RETAIL", "cat": "LOANS", "type": "LINE OF CREDIT", "name": "PLOC MEDICAL RES", "code": None, "conf": 0.88},
    "CG": {"lob": "WEALTH MANAGEMENT", "cat": "LOANS", "type": "LINE OF CREDIT", "name": "CONS WEALTH MGMT", "code": None, "conf": 0.82},
    "CI": {"lob": "RETAIL", "cat": "LOANS", "type": "LINE OF CREDIT", "name": "AL PLOC SPECIAL", "code": None, "conf": 0.86},
    "CJ": {"lob": "RETAIL", "cat": "LOANS", "type": "LINE OF CREDIT", "name": "LA PLOC SPECIAL", "code": None, "conf": 0.86},
    "D1": {"lob": "RETAIL", "cat": "LOANS", "type": "MORTGAGE", "name": "1-4 FRC FIXED", "code": "FIXED", "conf": 0.90},
    "D2": {"lob": "RETAIL", "cat": "LOANS", "type": "MORTGAGE", "name": "1-4 FRC VAR", "code": "VARIABLE", "conf": 0.90},
    "D5": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL REAL ESTATE", "name": "OTH CLD FIXED", "code": "FIXED", "conf": 0.88},
    "D6": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL REAL ESTATE", "name": "OTH CLD VAR", "code": "VARIABLE", "conf": 0.88},
    "D9": {"lob": "BUSINESS", "cat": "LOANS", "type": "COMMERCIAL", "name": "OAKHURST LOANS FIXED", "code": "FIXED", "conf": 0.80},
    "H1": {"lob": "RETAIL", "cat": "LOANS", "type": "HOME EQUITY", "name": "HELOC SILVER", "code": None, "conf": 0.93},
    "H3": {"lob": "RETAIL", "cat": "LOANS", "type": "HOME EQUITY", "name": "HELOC PR SILVER", "code": None, "conf": 0.93},
    "H5": {"lob": "RETAIL", "cat": "LOANS", "type": "HOME EQUITY", "name": "HELOC GOLD", "code": None, "conf": 0.93},
    "H7": {"lob": "RETAIL", "cat": "LOANS", "type": "HOME EQUITY", "name": "HELOC PR GOLD", "code": None, "conf": 0.92},
    "H9": {"lob": "RETAIL", "cat": "LOANS", "type": "HOME EQUITY", "name": "HELOC PLATINUM", "code": None, "conf": 0.93},
    "HA": {"lob": "RETAIL", "cat": "LOANS", "type": "HOME EQUITY", "name": "HELOC PR PLATINUM", "code": None, "conf": 0.92},
    "HC": {"lob": "RETAIL", "cat": "LOANS", "type": "HOME EQUITY", "name": "HELOC PLAT+", "code": None, "conf": 0.93},
    "HE": {"lob": "RETAIL", "cat": "LOANS", "type": "HOME EQUITY", "name": "HELOC PR PLAT+", "code": None, "conf": 0.92},
    "HG": {"lob": "RETAIL", "cat": "LOANS", "type": "HOME EQUITY", "name": "BP PTR NO PR", "code": None, "conf": 0.88},
    "HI": {"lob": "RETAIL", "cat": "LOANS", "type": "HOME EQUITY", "name": "BP PTR PR", "code": None, "conf": 0.88},
    "HK": {"lob": "RETAIL", "cat": "LOANS", "type": "HOME EQUITY", "name": "MS HELOC 365 INT", "code": None, "conf": 0.91},
    "HL": {"lob": "RETAIL", "cat": "LOANS", "type": "HOME EQUITY", "name": "AL HELOC 365 INT", "code": None, "conf": 0.90},
    "HM": {"lob": "RETAIL", "cat": "LOANS", "type": "HOME EQUITY", "name": "LA HELOC 365 INT", "code": None, "conf": 0.90},
    "HN": {"lob": "RETAIL", "cat": "LOANS", "type": "HOME EQUITY", "name": "MS HELOC 365 SPECIAL", "code": None, "conf": 0.90},
    "HO": {"lob": "RETAIL", "cat": "LOANS", "type": "HOME EQUITY", "name": "LA HELOC 365 SPECIAL", "code": None, "conf": 0.89},
    "HQ": {"lob": "RETAIL", "cat": "LOANS", "type": "HOME EQUITY", "name": "FBT HELOC IM1.9", "code": None, "conf": 0.88},
    "HR": {"lob": "RETAIL", "cat": "LOANS", "type": "HOME EQUITY", "name": "FBT HELOC IM2.9", "code": None, "conf": 0.88},
    "L1": {"lob": "RETAIL", "cat": "LOANS", "type": "LINE OF CREDIT", "name": "LOC - FIXED", "code": "FIXED", "conf": 0.90},
    "L2": {"lob": "RETAIL", "cat": "LOANS", "type": "LINE OF CREDIT", "name": "LOC - VAR", "code": "VARIABLE", "conf": 0.90},
    "O1": {"lob": "RETAIL", "cat": "LOANS", "type": "LINE OF CREDIT", "name": "ODP", "code": None, "conf": 0.88},
    "P0": {"lob": "RETAIL", "cat": "LOANS", "type": "PERSONAL", "name": "CREDITBUILDER", "code": None, "conf": 0.90},
    "P1": {"lob": "RETAIL", "cat": "LOANS", "type": "PERSONAL", "name": "IND FIXED", "code": "FIXED", "conf": 0.91},
    "P2": {"lob": "RETAIL", "cat": "LOANS", "type": "PERSONAL", "name": "IND VAR", "code": "VARIABLE", "conf": 0.88},
    "P5": {"lob": "RETAIL", "cat": "LOANS", "type": "AUTO", "name": "IND AUTO FIXED", "code": "FIXED", "conf": 0.93},
    "P9": {"lob": "RETAIL", "cat": "LOANS", "type": "PERSONAL", "name": "CREDITPLUS", "code": None, "conf": 0.88},
    "PB": {"lob": "RETAIL", "cat": "LOANS", "type": "PERSONAL", "name": "CONT TIRE CREDIT BLD", "code": None, "conf": 0.82},
    "R1": {"lob": "RETAIL", "cat": "LOANS", "type": "MORTGAGE", "name": "RES RE - FIXED", "code": "FIXED", "conf": 0.94},
    "R2": {"lob": "RETAIL", "cat": "LOANS", "type": "MORTGAGE", "name": "RES RE - VAR", "code": "VARIABLE", "conf": 0.93},
    "R5": {"lob": "RETAIL", "cat": "LOANS", "type": "MORTGAGE", "name": "RES RE JR LIEN FIXED", "code": "FIXED", "conf": 0.92},
    "R6": {"lob": "RETAIL", "cat": "LOANS", "type": "MORTGAGE", "name": "RES RE JR LIEN VAR", "code": "VARIABLE", "conf": 0.91},
    "R7": {"lob": "RETAIL", "cat": "LOANS", "type": "MORTGAGE", "name": "MORTGAGE CTR RE VAR", "code": "VARIABLE", "conf": 0.88},
    "R9": {"lob": "RETAIL", "cat": "LOANS", "type": "MORTGAGE", "name": "MORTGAGE CTR RE 1ST", "code": None, "conf": 0.90},
    "RA": {"lob": "RETAIL", "cat": "LOANS", "type": "MORTGAGE", "name": "CONSUMER ARM RE VAR", "code": "ARM", "conf": 0.89},
}

_DEFAULT_CLASSIFICATION = {
    "lob": "RETAIL",
    "cat": "DEPOSITS",
    "type": "CHECKING",
    "name": "UNKNOWN PRODUCT",
    "code": None,
    "conf": 0.50,
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
        "confidence": entry["conf"],
    }


def mock_ai_query_fn(model: str, prompt: str) -> str:
    """
    Mock implementation of Databricks ai_query().

    Parses the user prompt section (after "Classify these N product codes:")
    to extract product codes and domains, then returns deterministic
    classifications from the ground-truth lookup tables.
    """
    import re

    classifications = []

    # Only parse the user prompt section — skip the system prompt which
    # contains few-shot examples with product_code= patterns.
    user_section_match = re.search(r"Classify these \d+ product codes:", prompt)
    if user_section_match:
        user_section = prompt[user_section_match.start():]
    else:
        user_section = prompt

    lines = user_section.split("\n")
    for line in lines:
        if not line.strip().startswith("- "):
            continue
        code_match = re.search(r"product_code=(\S+?)(?:,|\s|$)", line)
        domain_match = re.search(r"DOMAIN=(DEPOSIT|LOAN)", line)
        if code_match:
            code = code_match.group(1).strip()
            domain = domain_match.group(1) if domain_match else "DEPOSIT"
            classifications.append(_build_classification_response(code, domain))

    if not classifications:
        classifications.append(_build_classification_response("MOCK", "DEPOSIT"))

    return json.dumps({"classifications": classifications})


def mock_ai_mask_fn(text: str, labels: str = None) -> str:
    """Mock implementation of Databricks ai_mask(). Returns [MASKED] placeholder."""
    if text is None:
        return None
    return "[MASKED]"


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
