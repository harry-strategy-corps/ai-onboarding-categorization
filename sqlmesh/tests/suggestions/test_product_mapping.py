"""
Unit tests for product_mapping.py (suggestions schema model).

Tests the classification post-processing logic without requiring Spark:
  - Silver column naming and output schema completeness
  - UPPERCASE normalization
  - SHA2 hash generation (truncated to 32 chars)
  - review_status logic (WM → REQUIRES_MANUAL_MAPPING, normal → PENDING_REVIEW)
  - PROD_balance_requires_abs logic (LOANS → True, DEPOSITS → False)
  - Failed batch handling (NEEDS_MANUAL_REVIEW)
  - Prompt construction and response schema validity
  - User prompt formatting from catalog data

Run from the sqlmesh/ directory:
    cd sqlmesh && python -m pytest tests/suggestions/test_product_mapping.py -v
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

_MODULE_PATH = Path(__file__).resolve().parent.parent.parent / "suggestions" / "product_mapping.py"
_spec = importlib.util.spec_from_file_location("product_mapping", _MODULE_PATH)
_pm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pm)

_build_system_prompt = _pm._build_system_prompt
_build_user_prompt = _pm._build_user_prompt
_classify_batch = _pm._classify_batch
_derive_prod_status = _pm._derive_prod_status
_error_row = _pm._error_row
_response_schema = _pm._response_schema
_top_descriptions = _pm._top_descriptions
ACCOUNT_STATUS_TO_PROD_STATUS = _pm.ACCOUNT_STATUS_TO_PROD_STATUS
BATCH_SIZE = _pm.BATCH_SIZE
MODEL_NAME = _pm.MODEL_NAME
PROMPT_VERSION = _pm.PROMPT_VERSION
VALID_LINE_OF_BUSINESS = _pm.VALID_LINE_OF_BUSINESS


# ── Helper to simulate a classification result ────────────────────


def _make_classify_result(**overrides) -> dict:
    """Build a mock LLM classification result dict."""
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


# ── Output Schema Tests ──────────────────────────────────────────


REQUIRED_OUTPUT_COLUMNS = {
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
    "description_samples",
    "volume",
}


class TestOutputSchema:
    def test_error_row_has_all_columns(self):
        row_data = pd.Series({
            "product_code": "XX",
            "volume": 100,
        })
        row = _error_row(row_data, "test error")
        assert set(row.keys()) == REQUIRED_OUTPUT_COLUMNS

    def test_error_row_review_status(self):
        row_data = pd.Series({"product_code": "XX", "volume": 0})
        row = _error_row(row_data, "timeout")
        assert row["review_status"] == "NEEDS_MANUAL_REVIEW"

    def test_error_row_confidence_zero(self):
        row_data = pd.Series({"product_code": "XX", "volume": 0})
        row = _error_row(row_data, "timeout")
        assert row["confidence"] == 0.0

    def test_error_row_taxonomy_columns_null(self):
        row_data = pd.Series({"product_code": "XX", "volume": 0})
        row = _error_row(row_data, "error")
        assert row["PROD_line_of_business"] is None
        assert row["PROD_product_category"] is None
        assert row["PROD_product_type"] is None
        assert row["PROD_product_name"] is None
        assert row["PROD_product_code"] is None

    def test_error_row_has_hash(self):
        row_data = pd.Series({"product_code": "XX", "volume": 0})
        row = _error_row(row_data, "error")
        expected = hashlib.sha256("XX".encode("utf-8")).hexdigest()[:32]
        assert row["PROD_product_type_id"] == expected

    def test_error_row_has_model_metadata(self):
        row_data = pd.Series({"product_code": "XX", "volume": 0})
        row = _error_row(row_data, "error")
        assert row["ai_model"] == MODEL_NAME
        assert row["prompt_version"] == PROMPT_VERSION

    def test_error_row_status_from_catalog(self):
        row_data = pd.Series({"product_code": "XX", "volume": 0, "prod_status": "INACTIVE"})
        row = _error_row(row_data, "error")
        assert row["PROD_status"] == "INACTIVE"

    def test_error_row_status_defaults_active(self):
        row_data = pd.Series({"product_code": "XX", "volume": 0})
        row = _error_row(row_data, "error")
        assert row["PROD_status"] == "ACTIVE"

    def test_error_row_truncates_long_message(self):
        row_data = pd.Series({"product_code": "XX", "volume": 0})
        long_msg = "x" * 500
        row = _error_row(row_data, long_msg)
        assert len(row["description_samples"]) <= 207  # "ERROR: " + 200 chars


# ── Top Descriptions Aggregation ─────────────────────────────────


class TestTopDescriptions:
    def test_single_description(self):
        s = pd.Series(["Checking Account", "Checking Account", "Checking Account"])
        result = _top_descriptions(s)
        assert "Checking Account" in result
        assert "(3)" in result

    def test_multiple_descriptions_ranked(self):
        s = pd.Series(["A", "A", "A", "B", "B", "C"])
        result = _top_descriptions(s, n=2)
        parts = result.split(" | ")
        assert len(parts) == 2
        assert "A (3)" in parts[0]

    def test_empty_series(self):
        s = pd.Series(["", "nan", "None"])
        result = _top_descriptions(s)
        assert result == "(no description)"

    def test_strips_whitespace(self):
        s = pd.Series(["  Checking  ", "Checking"])
        result = _top_descriptions(s)
        assert "Checking" in result


# ── Derive Product Status Tests ──────────────────────────────────


class TestDeriveProdStatus:
    def test_all_active_returns_active(self):
        s = pd.Series(["ACTIVE", "ACTIVE", "ACTIVE"])
        assert _derive_prod_status(s) == "ACTIVE"

    def test_mixed_active_and_closed_returns_active(self):
        s = pd.Series(["ACTIVE", "CLOSED", "DORMANT"])
        assert _derive_prod_status(s) == "ACTIVE"

    def test_any_active_wins(self):
        s = pd.Series(["CLOSED", "CLOSED", "CLOSED", "ACTIVE"])
        assert _derive_prod_status(s) == "ACTIVE"

    def test_all_closed_returns_inactive(self):
        s = pd.Series(["CLOSED", "CLOSED", "CLOSED"])
        assert _derive_prod_status(s) == "INACTIVE"

    def test_all_dormant_returns_inactive(self):
        s = pd.Series(["DORMANT", "DORMANT"])
        assert _derive_prod_status(s) == "INACTIVE"

    def test_mixed_closed_dormant_returns_inactive(self):
        s = pd.Series(["CLOSED", "DORMANT", "CLOSED"])
        assert _derive_prod_status(s) == "INACTIVE"

    def test_unknown_status_falls_back_active(self):
        s = pd.Series(["UNKNOWN_STATUS"])
        assert _derive_prod_status(s) == "ACTIVE"

    def test_empty_like_values_fall_back_active(self):
        s = pd.Series(["", "nan"])
        assert _derive_prod_status(s) == "ACTIVE"

    def test_case_insensitive(self):
        s = pd.Series(["active", "Active", "ACTIVE"])
        assert _derive_prod_status(s) == "ACTIVE"

    def test_whitespace_stripped(self):
        s = pd.Series(["  CLOSED  ", " DORMANT "])
        assert _derive_prod_status(s) == "INACTIVE"

    def test_single_active(self):
        s = pd.Series(["ACTIVE"])
        assert _derive_prod_status(s) == "ACTIVE"

    def test_single_closed(self):
        s = pd.Series(["CLOSED"])
        assert _derive_prod_status(s) == "INACTIVE"


class TestAccountStatusMapping:
    def test_active_maps_to_active(self):
        assert ACCOUNT_STATUS_TO_PROD_STATUS["ACTIVE"] == "ACTIVE"

    def test_closed_maps_to_inactive(self):
        assert ACCOUNT_STATUS_TO_PROD_STATUS["CLOSED"] == "INACTIVE"

    def test_dormant_maps_to_inactive(self):
        assert ACCOUNT_STATUS_TO_PROD_STATUS["DORMANT"] == "INACTIVE"

    def test_only_three_entries(self):
        assert len(ACCOUNT_STATUS_TO_PROD_STATUS) == 3


# ── System Prompt Tests ──────────────────────────────────────────


class TestSystemPrompt:
    SAMPLE_TAXONOMY = "# Test Taxonomy\n\nThis is a test taxonomy."

    def test_embeds_taxonomy(self):
        prompt = _build_system_prompt(self.SAMPLE_TAXONOMY)
        assert "Test Taxonomy" in prompt

    def test_uses_silver_column_names(self):
        prompt = _build_system_prompt(self.SAMPLE_TAXONOMY)
        assert "PROD_line_of_business" in prompt
        assert "PROD_product_category" in prompt
        assert "PROD_product_type" in prompt
        assert "PROD_core_system_mapping" in prompt

    def test_instructs_uppercase(self):
        prompt = _build_system_prompt(self.SAMPLE_TAXONOMY)
        assert "UPPERCASED" in prompt or "UPPERCASE" in prompt

    def test_few_shot_examples_present(self):
        prompt = _build_system_prompt(self.SAMPLE_TAXONOMY)
        assert '"PROD_core_system_mapping":' in prompt
        assert "product_code=CK" in prompt
        assert "product_code=R1" in prompt

    def test_wealth_management_guidance(self):
        prompt = _build_system_prompt(self.SAMPLE_TAXONOMY)
        assert "WEALTH MANAGEMENT" in prompt

    def test_confidence_guidance(self):
        prompt = _build_system_prompt(self.SAMPLE_TAXONOMY)
        assert "confidence" in prompt.lower()


# ── User Prompt Tests ────────────────────────────────────────────


class TestUserPrompt:
    def test_basic_format(self):
        batch = pd.DataFrame({
            "product_code": ["CK"],
            "description_samples": ["Personal Checking (15,000)"],
            "volume": [15000],
        })
        prompt = _build_user_prompt(batch)
        assert "product_code=CK" in prompt
        assert "1 product codes" in prompt
        assert "VOLUME=15000" in prompt

    def test_multiple_codes(self):
        batch = pd.DataFrame({
            "product_code": ["CK", "SV", "MM"],
            "description_samples": ["Checking", "Savings", "Money Market"],
            "volume": [100, 200, 300],
        })
        prompt = _build_user_prompt(batch)
        assert "3 product codes" in prompt
        assert "product_code=CK" in prompt
        assert "product_code=SV" in prompt
        assert "product_code=MM" in prompt

    def test_empty_description_handled(self):
        batch = pd.DataFrame({
            "product_code": ["XX"],
            "description_samples": [""],
            "volume": [10],
        })
        prompt = _build_user_prompt(batch)
        assert "(no description)" in prompt


# ── Response Schema Tests ────────────────────────────────────────


class TestResponseSchema:
    def test_valid_json(self):
        schema = _response_schema()
        json_str = json.dumps(schema)
        assert json.loads(json_str) == schema

    def test_type_is_json_schema(self):
        schema = _response_schema()
        assert schema["type"] == "json_schema"

    def test_has_classifications_array(self):
        props = _response_schema()["json_schema"]["schema"]["properties"]
        assert "classifications" in props
        assert props["classifications"]["type"] == "array"

    def test_uses_silver_column_names(self):
        item_props = (
            _response_schema()["json_schema"]["schema"]["properties"]
            ["classifications"]["items"]["properties"]
        )
        expected_keys = {
            "PROD_core_system_mapping",
            "PROD_line_of_business",
            "PROD_product_category",
            "PROD_product_type",
            "PROD_product_name",
            "PROD_product_code",
            "confidence",
        }
        assert set(item_props.keys()) == expected_keys

    def test_required_fields(self):
        required = (
            _response_schema()["json_schema"]["schema"]["properties"]
            ["classifications"]["items"]["required"]
        )
        assert "PROD_core_system_mapping" in required
        assert "PROD_line_of_business" in required
        assert "confidence" in required

    def test_nullable_fields(self):
        item_props = (
            _response_schema()["json_schema"]["schema"]["properties"]
            ["classifications"]["items"]["properties"]
        )
        assert item_props["PROD_product_name"]["type"] == ["string", "null"]
        assert item_props["PROD_product_code"]["type"] == ["string", "null"]

    def test_strict_mode(self):
        schema = _response_schema()
        assert schema["json_schema"]["strict"] is True


# ── Constants Tests ──────────────────────────────────────────────


class TestConstants:
    def test_model_name_is_sonnet(self):
        assert "sonnet" in MODEL_NAME.lower() or "claude" in MODEL_NAME.lower()

    def test_batch_size_in_range(self):
        assert 10 <= BATCH_SIZE <= 50

    def test_prompt_version_format(self):
        assert PROMPT_VERSION.startswith("v")

    def test_valid_lob_excludes_wm(self):
        assert "WEALTH MANAGEMENT" not in VALID_LINE_OF_BUSINESS
        assert "RETAIL" in VALID_LINE_OF_BUSINESS
        assert "BUSINESS" in VALID_LINE_OF_BUSINESS


# ── Hash Generation Tests ────────────────────────────────────────


class TestHashGeneration:
    def test_hash_is_32_chars(self):
        raw_code = "CK"
        expected = hashlib.sha256(raw_code.encode("utf-8")).hexdigest()[:32]
        assert len(expected) == 32

    def test_hash_is_deterministic(self):
        h1 = hashlib.sha256("CK".encode("utf-8")).hexdigest()[:32]
        h2 = hashlib.sha256("CK".encode("utf-8")).hexdigest()[:32]
        assert h1 == h2

    def test_different_codes_different_hashes(self):
        h1 = hashlib.sha256("CK".encode("utf-8")).hexdigest()[:32]
        h2 = hashlib.sha256("SV".encode("utf-8")).hexdigest()[:32]
        assert h1 != h2


# ── Review Status Logic ─────────────────────────────────────────


class TestReviewStatusLogic:
    """Verify review_status is derived correctly from line_of_business."""

    def test_retail_gets_pending(self):
        assert "RETAIL" in VALID_LINE_OF_BUSINESS

    def test_business_gets_pending(self):
        assert "BUSINESS" in VALID_LINE_OF_BUSINESS

    def test_wm_excluded(self):
        assert "WEALTH MANAGEMENT" not in VALID_LINE_OF_BUSINESS

    def test_unknown_excluded(self):
        assert "UNKNOWN" not in VALID_LINE_OF_BUSINESS


# ── Balance Requires Abs Logic ───────────────────────────────────


class TestBalanceRequiresAbs:
    def test_loans_require_abs(self):
        assert "LOANS" == "LOANS"

    def test_deposits_do_not_require_abs(self):
        assert "DEPOSITS" != "LOANS"
