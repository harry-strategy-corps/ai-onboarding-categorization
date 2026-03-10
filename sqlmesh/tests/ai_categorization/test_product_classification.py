"""
Unit tests for Section 3: MVP Classification Model.

Tests the post-processing logic from product_classification_suggestions.py
without requiring Spark. Validates:
  - Silver column mapping correctness (L2/L3 swap)
  - UPPERCASE normalization
  - SHA2 hash generation for PROD_product_type_id
  - review_status logic (WM → REQUIRES_MANUAL_MAPPING, normal → PENDING_REVIEW)
  - PROD_balance_requires_abs logic (LOANS → True, DEPOSITS → False)
  - Failed batch handling (NEEDS_MANUAL_REVIEW)
  - Mock AI function prompt parsing and response format
  - Output schema completeness
  - Batch construction from catalog records
  - End-to-end classification flow with mocks

Run from the sqlmesh/ directory:
    cd sqlmesh && python -m pytest tests/ai_categorization/test_product_classification.py -v
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models.ai_categorization._constants import (
    AI_MODEL,
    DEFAULT_PROD_STATUS,
    PROMPT_VERSION,
    REVIEW_STATUS_FAILED,
    REVIEW_STATUS_MANUAL,
    REVIEW_STATUS_PENDING,
    VALID_LINE_OF_BUSINESS,
)
from models.ai_categorization._prompt_builder import (
    RESPONSE_SCHEMA,
    build_full_prompt,
    build_user_prompt,
)
from models.ai_categorization.product_classification_suggestions import (
    _build_failed_row,
    _build_output_row,
)
from macros.mock_ai_functions import (
    MOCK_DEPOSIT_CLASSIFICATIONS,
    MOCK_LOAN_CLASSIFICATIONS,
    mock_ai_query_fn,
)


# ── Output Row Construction Tests ─────────────────────────────────


class TestBuildOutputRow:
    """Test the _build_output_row function that transforms LLM output to Silver format."""

    NOW_TS = "2026-03-09T12:00:00+00:00"

    def _make_cls(self, **overrides):
        base = {
            "PROD_core_system_mapping": "CK",
            "PROD_line_of_business": "RETAIL",
            "PROD_product_category": "DEPOSITS",
            "PROD_product_type": "CHECKING",
            "PROD_product_name": "Personal Checking",
            "PROD_product_code": None,
            "confidence": 0.95,
        }
        base.update(overrides)
        return base

    def _make_catalog_rec(self, **overrides):
        base = {
            "product_code": "CK",
            "product_domain": "DEPOSIT",
            "source_table": "raw_score_deposits",
            "account_count": 15000,
        }
        base.update(overrides)
        return base

    def test_basic_deposit_classification(self):
        row = _build_output_row(self._make_cls(), self._make_catalog_rec(), self.NOW_TS)
        assert row["PROD_core_system_mapping"] == "CK"
        assert row["PROD_line_of_business"] == "RETAIL"
        assert row["PROD_product_category"] == "DEPOSITS"
        assert row["PROD_product_type"] == "CHECKING"
        assert row["PROD_product_name"] == "PERSONAL CHECKING"
        assert row["PROD_product_code"] is None
        assert row["confidence"] == 0.95

    def test_uppercase_normalization(self):
        cls = self._make_cls(
            PROD_line_of_business="retail",
            PROD_product_category="deposits",
            PROD_product_type="checking",
            PROD_product_name="personal checking",
        )
        row = _build_output_row(cls, self._make_catalog_rec(), self.NOW_TS)
        assert row["PROD_line_of_business"] == "RETAIL"
        assert row["PROD_product_category"] == "DEPOSITS"
        assert row["PROD_product_type"] == "CHECKING"
        assert row["PROD_product_name"] == "PERSONAL CHECKING"

    def test_sha2_hash_generation(self):
        row = _build_output_row(self._make_cls(), self._make_catalog_rec(), self.NOW_TS)
        expected_hash = hashlib.sha256("CK".encode("utf-8")).hexdigest()
        assert row["PROD_product_type_id"] == expected_hash
        assert len(row["PROD_product_type_id"]) == 64

    def test_deposits_balance_requires_abs_false(self):
        row = _build_output_row(self._make_cls(), self._make_catalog_rec(), self.NOW_TS)
        assert row["PROD_balance_requires_abs"] is False

    def test_loans_balance_requires_abs_true(self):
        cls = self._make_cls(
            PROD_core_system_mapping="R1",
            PROD_product_category="LOANS",
            PROD_product_type="MORTGAGE",
        )
        catalog = self._make_catalog_rec(product_code="R1", product_domain="LOAN")
        row = _build_output_row(cls, catalog, self.NOW_TS)
        assert row["PROD_balance_requires_abs"] is True

    def test_review_status_pending_for_retail(self):
        row = _build_output_row(self._make_cls(), self._make_catalog_rec(), self.NOW_TS)
        assert row["review_status"] == REVIEW_STATUS_PENDING

    def test_review_status_pending_for_business(self):
        cls = self._make_cls(PROD_line_of_business="BUSINESS")
        row = _build_output_row(cls, self._make_catalog_rec(), self.NOW_TS)
        assert row["review_status"] == REVIEW_STATUS_PENDING

    def test_review_status_manual_for_wealth_management(self):
        cls = self._make_cls(PROD_line_of_business="WEALTH MANAGEMENT")
        row = _build_output_row(cls, self._make_catalog_rec(), self.NOW_TS)
        assert row["review_status"] == REVIEW_STATUS_MANUAL

    def test_review_status_manual_for_unknown_lob(self):
        cls = self._make_cls(PROD_line_of_business="UNKNOWN")
        row = _build_output_row(cls, self._make_catalog_rec(), self.NOW_TS)
        assert row["review_status"] == REVIEW_STATUS_MANUAL

    def test_status_is_active(self):
        row = _build_output_row(self._make_cls(), self._make_catalog_rec(), self.NOW_TS)
        assert row["PROD_status"] == DEFAULT_PROD_STATUS

    def test_ai_model_populated(self):
        row = _build_output_row(self._make_cls(), self._make_catalog_rec(), self.NOW_TS)
        assert row["ai_model"] == AI_MODEL

    def test_prompt_version_populated(self):
        row = _build_output_row(self._make_cls(), self._make_catalog_rec(), self.NOW_TS)
        assert row["prompt_version"] == PROMPT_VERSION

    def test_timestamps_populated(self):
        row = _build_output_row(self._make_cls(), self._make_catalog_rec(), self.NOW_TS)
        assert row["PROD_created_date"] == self.NOW_TS
        assert row["PROD_modified_date"] == self.NOW_TS
        assert row["processing_timestamp"] == self.NOW_TS

    def test_catalog_metadata_preserved(self):
        row = _build_output_row(self._make_cls(), self._make_catalog_rec(), self.NOW_TS)
        assert row["product_domain"] == "DEPOSIT"
        assert row["source_table"] == "raw_score_deposits"
        assert row["account_count"] == 15000

    def test_nullable_product_code_preserved(self):
        cls = self._make_cls(PROD_product_code="HSA")
        row = _build_output_row(cls, self._make_catalog_rec(), self.NOW_TS)
        assert row["PROD_product_code"] == "HSA"

    def test_null_confidence_defaults_to_zero(self):
        cls = self._make_cls(confidence=None)
        row = _build_output_row(cls, self._make_catalog_rec(), self.NOW_TS)
        assert row["confidence"] == 0.0


# ── Output Schema Completeness ────────────────────────────────────


class TestOutputSchema:
    """Verify all required columns are present in output rows."""

    REQUIRED_COLUMNS = {
        "PROD_product_type_id",
        "PROD_line_of_business",
        "PROD_product_category",
        "PROD_product_type",
        "PROD_product_name",
        "PROD_product_code",
        "PROD_status",
        "PROD_core_system_mapping",
        "PROD_balance_requires_abs",
        "PROD_created_date",
        "PROD_modified_date",
        "processing_timestamp",
        "review_status",
        "confidence",
        "ai_model",
        "prompt_version",
        "product_domain",
        "source_table",
        "account_count",
    }

    def test_output_row_has_all_columns(self):
        cls = {
            "PROD_core_system_mapping": "CK",
            "PROD_line_of_business": "RETAIL",
            "PROD_product_category": "DEPOSITS",
            "PROD_product_type": "CHECKING",
            "PROD_product_name": "Checking",
            "PROD_product_code": None,
            "confidence": 0.95,
        }
        catalog = {"product_domain": "DEPOSIT", "source_table": "raw_score_deposits", "account_count": 100}
        row = _build_output_row(cls, catalog, "2026-01-01T00:00:00")
        assert set(row.keys()) == self.REQUIRED_COLUMNS

    def test_failed_row_has_all_columns(self):
        item = {"product_code": "XX", "product_domain": "DEPOSIT"}
        row = _build_failed_row(item, "2026-01-01T00:00:00")
        assert set(row.keys()) == self.REQUIRED_COLUMNS


# ── Failed Row Tests ──────────────────────────────────────────────


class TestBuildFailedRow:
    """Test the _build_failed_row function for batch failures."""

    def test_failed_review_status(self):
        item = {"product_code": "XX", "product_domain": "DEPOSIT"}
        row = _build_failed_row(item, "2026-01-01T00:00:00")
        assert row["review_status"] == REVIEW_STATUS_FAILED

    def test_failed_confidence_zero(self):
        item = {"product_code": "XX", "product_domain": "DEPOSIT"}
        row = _build_failed_row(item, "2026-01-01T00:00:00")
        assert row["confidence"] == 0.0

    def test_failed_taxonomy_columns_null(self):
        item = {"product_code": "XX", "product_domain": "DEPOSIT"}
        row = _build_failed_row(item, "2026-01-01T00:00:00")
        assert row["PROD_line_of_business"] is None
        assert row["PROD_product_category"] is None
        assert row["PROD_product_type"] is None
        assert row["PROD_product_name"] is None
        assert row["PROD_product_code"] is None

    def test_failed_still_has_hash(self):
        item = {"product_code": "XX", "product_domain": "DEPOSIT"}
        row = _build_failed_row(item, "2026-01-01T00:00:00")
        expected = hashlib.sha256("XX".encode("utf-8")).hexdigest()
        assert row["PROD_product_type_id"] == expected

    def test_failed_still_has_model_metadata(self):
        item = {"product_code": "XX", "product_domain": "DEPOSIT"}
        row = _build_failed_row(item, "2026-01-01T00:00:00")
        assert row["ai_model"] == AI_MODEL
        assert row["prompt_version"] == PROMPT_VERSION


# ── Mock AI Function Tests ────────────────────────────────────────


class TestMockAiQuery:
    """Test that mock_ai_query_fn correctly parses prompts and returns classifications."""

    def test_single_deposit_code(self):
        prompt = "  - product_code=01, DESC=\"PERSONAL CHECKING\", DOMAIN=DEPOSIT"
        result = json.loads(mock_ai_query_fn(AI_MODEL, prompt))
        assert len(result["classifications"]) == 1
        cls = result["classifications"][0]
        assert cls["PROD_core_system_mapping"] == "01"
        assert cls["PROD_line_of_business"] == "RETAIL"
        assert cls["PROD_product_category"] == "DEPOSITS"

    def test_single_loan_code(self):
        prompt = "  - product_code=R1, DESC=\"Res RE - Fixed\", DOMAIN=LOAN"
        result = json.loads(mock_ai_query_fn(AI_MODEL, prompt))
        cls = result["classifications"][0]
        assert cls["PROD_core_system_mapping"] == "R1"
        assert cls["PROD_product_category"] == "LOANS"
        assert cls["PROD_product_type"] == "MORTGAGE"

    def test_wealth_management_deposit(self):
        prompt = "  - product_code=F1, DESC=\"FIDUCIARY BUS INT CK\", DOMAIN=DEPOSIT"
        result = json.loads(mock_ai_query_fn(AI_MODEL, prompt))
        cls = result["classifications"][0]
        assert cls["PROD_line_of_business"] == "WEALTH MANAGEMENT"

    def test_wealth_management_loan(self):
        prompt = "  - product_code=BV, DESC=\"Comm Wealth Mgmt Var\", DOMAIN=LOAN"
        result = json.loads(mock_ai_query_fn(AI_MODEL, prompt))
        cls = result["classifications"][0]
        assert cls["PROD_line_of_business"] == "WEALTH MANAGEMENT"

    def test_batch_of_multiple_codes(self):
        prompt = (
            "  - product_code=01, DESC=\"PERSONAL CHECKING\", DOMAIN=DEPOSIT\n"
            "  - product_code=B1, DESC=\"LEGACY BUSINESS CK\", DOMAIN=DEPOSIT\n"
            "  - product_code=R1, DESC=\"Res RE - Fixed\", DOMAIN=LOAN\n"
        )
        result = json.loads(mock_ai_query_fn(AI_MODEL, prompt))
        assert len(result["classifications"]) == 3

    def test_unknown_code_gets_default(self):
        prompt = "  - product_code=ZZZ, DESC=\"Unknown\", DOMAIN=DEPOSIT"
        result = json.loads(mock_ai_query_fn(AI_MODEL, prompt))
        cls = result["classifications"][0]
        assert cls["confidence"] == 0.50

    def test_response_uses_silver_column_names(self):
        prompt = "  - product_code=01, DESC=\"PERSONAL CHECKING\", DOMAIN=DEPOSIT"
        result = json.loads(mock_ai_query_fn(AI_MODEL, prompt))
        cls = result["classifications"][0]
        assert "PROD_core_system_mapping" in cls
        assert "PROD_line_of_business" in cls
        assert "PROD_product_category" in cls
        assert "PROD_product_type" in cls
        assert "PROD_product_name" in cls
        assert "PROD_product_code" in cls
        assert "confidence" in cls


# ── L2/L3 Mapping Validation in Mock Data ─────────────────────────


class TestMockDataL2L3Mapping:
    """Verify that the mock data uses the correct Silver column naming
    (L2 = cat = PROD_product_category, L3 = type = PROD_product_type)."""

    def test_deposit_checking_code_01(self):
        entry = MOCK_DEPOSIT_CLASSIFICATIONS["01"]
        assert entry["cat"] == "DEPOSITS"
        assert entry["type"] == "CHECKING"

    def test_deposit_money_market_code_09(self):
        entry = MOCK_DEPOSIT_CLASSIFICATIONS["09"]
        assert entry["cat"] == "DEPOSITS"
        assert entry["type"] == "MONEY MARKET"

    def test_loan_mortgage_code_R1(self):
        entry = MOCK_LOAN_CLASSIFICATIONS["R1"]
        assert entry["cat"] == "LOANS"
        assert entry["type"] == "MORTGAGE"

    def test_loan_heloc_code_H1(self):
        entry = MOCK_LOAN_CLASSIFICATIONS["H1"]
        assert entry["cat"] == "LOANS"
        assert entry["type"] == "HOME EQUITY"

    def test_loan_line_of_credit_C7(self):
        entry = MOCK_LOAN_CLASSIFICATIONS["C7"]
        assert entry["cat"] == "LOANS"
        assert entry["type"] == "LINE OF CREDIT"

    def test_all_deposits_have_cat_deposits(self):
        for code, entry in MOCK_DEPOSIT_CLASSIFICATIONS.items():
            assert entry["cat"] == "DEPOSITS", (
                f"Deposit code {code} has cat='{entry['cat']}', expected 'DEPOSITS'"
            )

    def test_all_loans_have_cat_loans(self):
        for code, entry in MOCK_LOAN_CLASSIFICATIONS.items():
            assert entry["cat"] == "LOANS", (
                f"Loan code {code} has cat='{entry['cat']}', expected 'LOANS'"
            )


# ── End-to-End Classification Flow (without Spark) ────────────────


class TestEndToEndClassification:
    """Test the full flow: prompt → mock ai_query → output row."""

    def test_deposit_end_to_end(self):
        items = [{"product_code": "01", "product_description": "PERSONAL CHECKING", "product_domain": "DEPOSIT"}]
        prompt = build_full_prompt(items)
        raw_result = mock_ai_query_fn(AI_MODEL, prompt)
        parsed = json.loads(raw_result)
        cls = parsed["classifications"][0]
        catalog_rec = {"product_domain": "DEPOSIT", "source_table": "raw_score_deposits", "account_count": 1177}
        row = _build_output_row(cls, catalog_rec, "2026-01-01T00:00:00")

        assert row["PROD_core_system_mapping"] == "01"
        assert row["PROD_line_of_business"] == "RETAIL"
        assert row["PROD_product_category"] == "DEPOSITS"
        assert row["PROD_product_type"] == "CHECKING"
        assert row["PROD_balance_requires_abs"] is False
        assert row["review_status"] == REVIEW_STATUS_PENDING

    def test_loan_end_to_end(self):
        items = [{
            "product_code": "R1", "product_description": "Res RE - Fixed",
            "product_domain": "LOAN", "purpose_code": "11", "purpose_description": "Agriculture",
            "loan_type_desc": "Res RE - Fixed",
        }]
        prompt = build_full_prompt(items)
        raw_result = mock_ai_query_fn(AI_MODEL, prompt)
        parsed = json.loads(raw_result)
        cls = parsed["classifications"][0]
        catalog_rec = {"product_domain": "LOAN", "source_table": "raw_score_loans", "account_count": 55577}
        row = _build_output_row(cls, catalog_rec, "2026-01-01T00:00:00")

        assert row["PROD_core_system_mapping"] == "R1"
        assert row["PROD_line_of_business"] == "RETAIL"
        assert row["PROD_product_category"] == "LOANS"
        assert row["PROD_product_type"] == "MORTGAGE"
        assert row["PROD_balance_requires_abs"] is True
        assert row["review_status"] == REVIEW_STATUS_PENDING

    def test_wealth_management_flagged(self):
        items = [{"product_code": "F1", "product_description": "FIDUCIARY BUS INT CK", "product_domain": "DEPOSIT"}]
        prompt = build_full_prompt(items)
        raw_result = mock_ai_query_fn(AI_MODEL, prompt)
        parsed = json.loads(raw_result)
        cls = parsed["classifications"][0]
        catalog_rec = {"product_domain": "DEPOSIT", "source_table": "raw_score_deposits", "account_count": 9}
        row = _build_output_row(cls, catalog_rec, "2026-01-01T00:00:00")

        assert row["PROD_line_of_business"] == "WEALTH MANAGEMENT"
        assert row["review_status"] == REVIEW_STATUS_MANUAL

    def test_full_batch_produces_correct_count(self):
        items = [
            {"product_code": "01", "product_description": "PERSONAL CHECKING", "product_domain": "DEPOSIT"},
            {"product_code": "B1", "product_description": "LEGACY BUSINESS CK", "product_domain": "DEPOSIT"},
            {"product_code": "R1", "product_description": "Res RE - Fixed", "product_domain": "LOAN"},
            {"product_code": "F1", "product_description": "FIDUCIARY BUS INT CK", "product_domain": "DEPOSIT"},
        ]
        prompt = build_full_prompt(items)
        raw_result = mock_ai_query_fn(AI_MODEL, prompt)
        parsed = json.loads(raw_result)
        assert len(parsed["classifications"]) == 4


# ── Mock Coverage Tests ───────────────────────────────────────────


class TestMockCoverage:
    """Verify mock data covers all product codes in the seed catalog."""

    @pytest.fixture
    def catalog_codes(self):
        """Load product codes from the seed CSV."""
        csv_path = Path(__file__).parent.parent.parent / "seeds" / "ai_categorization" / "bankplus_product_catalog.csv"
        codes = {"DEPOSIT": set(), "LOAN": set()}
        with open(csv_path) as f:
            header = f.readline()
            for line in f:
                parts = line.strip().split(",")
                code = parts[0]
                domain = parts[2]
                codes[domain].add(code)
        return codes

    def test_all_deposit_codes_in_mock(self, catalog_codes):
        missing = catalog_codes["DEPOSIT"] - set(MOCK_DEPOSIT_CLASSIFICATIONS.keys())
        assert not missing, (
            f"Deposit codes in catalog but missing from mock: {sorted(missing)}"
        )

    def test_all_loan_codes_in_mock(self, catalog_codes):
        missing = catalog_codes["LOAN"] - set(MOCK_LOAN_CLASSIFICATIONS.keys())
        assert not missing, (
            f"Loan codes in catalog but missing from mock: {sorted(missing)}"
        )
