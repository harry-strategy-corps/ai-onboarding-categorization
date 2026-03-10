"""
Unit tests for Section 2: Constants, Column Mapping & Taxonomy Prompt.

Validates:
  - Column mapping (L2/L3 swap) is correct
  - All Silver column names follow the PROD_* convention
  - Review status constants are defined
  - Prompt builder produces valid prompts with embedded taxonomy
  - Response schema is valid JSON Schema
  - User prompt correctly formats product codes
  - UPPERCASE normalization helpers
  - balance_requires_abs logic

Run from the sqlmesh/ directory:
    cd sqlmesh && python -m pytest tests/ai_categorization/test_column_mapping.py -v
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models.ai_categorization._constants import (
    AI_MODEL,
    AI_QUERY_MAX_RETRIES,
    BUSINESS_PURPOSE_CODES,
    CLASSIFICATION_BATCH_SIZE,
    COLUMN_MAPPING,
    DEFAULT_PROD_STATUS,
    PROMPT_VERSION,
    RETAIL_PURPOSE_CODES,
    REVIEW_STATUS_APPROVED,
    REVIEW_STATUS_FAILED,
    REVIEW_STATUS_MANUAL,
    REVIEW_STATUS_PENDING,
    REVIEW_STATUS_REJECTED,
    SILVER_TO_NOTEBOOK,
    VALID_LINE_OF_BUSINESS,
    VALID_PRODUCT_CATEGORY,
)
from models.ai_categorization._prompt_builder import (
    RESPONSE_SCHEMA,
    RESPONSE_SCHEMA_STR,
    build_full_prompt,
    build_system_prompt,
    build_user_prompt,
)


# ── Column Mapping Tests ─────────────────────────────────────────


class TestColumnMapping:
    """Validate the notebook → Silver column mapping, especially the L2/L3 swap."""

    def test_mapping_has_all_six_keys(self):
        expected_keys = {
            "line_of_business",
            "product_type",
            "product_category",
            "product_subcategory",
            "product_special",
            "product_code",
        }
        assert set(COLUMN_MAPPING.keys()) == expected_keys

    def test_all_values_are_prod_prefixed(self):
        for notebook_name, silver_name in COLUMN_MAPPING.items():
            assert silver_name.startswith("PROD_"), (
                f"Silver column for '{notebook_name}' should start with 'PROD_', "
                f"got '{silver_name}'"
            )

    def test_l1_mapping(self):
        assert COLUMN_MAPPING["line_of_business"] == "PROD_line_of_business"

    def test_l2_swap_product_type_maps_to_category(self):
        """The critical L2 swap: notebook 'product_type' → Silver 'PROD_product_category'."""
        assert COLUMN_MAPPING["product_type"] == "PROD_product_category", (
            "L2 SWAP ERROR: notebook 'product_type' must map to 'PROD_product_category', "
            f"got '{COLUMN_MAPPING['product_type']}'"
        )

    def test_l3_swap_product_category_maps_to_type(self):
        """The critical L3 swap: notebook 'product_category' → Silver 'PROD_product_type'."""
        assert COLUMN_MAPPING["product_category"] == "PROD_product_type", (
            "L3 SWAP ERROR: notebook 'product_category' must map to 'PROD_product_type', "
            f"got '{COLUMN_MAPPING['product_category']}'"
        )

    def test_l2_does_not_map_to_product_type(self):
        """Negative test: ensure the intuitive-but-wrong mapping is NOT present."""
        assert COLUMN_MAPPING["product_type"] != "PROD_product_type"

    def test_l3_does_not_map_to_product_category(self):
        """Negative test: ensure the intuitive-but-wrong mapping is NOT present."""
        assert COLUMN_MAPPING["product_category"] != "PROD_product_category"

    def test_l4_mapping(self):
        assert COLUMN_MAPPING["product_subcategory"] == "PROD_product_name"

    def test_l5_mapping(self):
        assert COLUMN_MAPPING["product_special"] == "PROD_product_code"

    def test_raw_code_mapping(self):
        assert COLUMN_MAPPING["product_code"] == "PROD_core_system_mapping"

    def test_reverse_mapping_is_consistent(self):
        for notebook_name, silver_name in COLUMN_MAPPING.items():
            assert SILVER_TO_NOTEBOOK[silver_name] == notebook_name

    def test_reverse_mapping_has_same_size(self):
        assert len(SILVER_TO_NOTEBOOK) == len(COLUMN_MAPPING)


# ── Constants Tests ───────────────────────────────────────────────


class TestConstants:
    def test_ai_model_is_sonnet(self):
        assert "sonnet" in AI_MODEL.lower()

    def test_batch_size_in_range(self):
        assert 25 <= CLASSIFICATION_BATCH_SIZE <= 50

    def test_retry_count(self):
        assert AI_QUERY_MAX_RETRIES == 3

    def test_prompt_version_format(self):
        assert PROMPT_VERSION.startswith("v")

    def test_review_statuses_are_uppercase(self):
        for status in [
            REVIEW_STATUS_PENDING,
            REVIEW_STATUS_APPROVED,
            REVIEW_STATUS_REJECTED,
            REVIEW_STATUS_MANUAL,
            REVIEW_STATUS_FAILED,
        ]:
            assert status == status.upper(), f"Review status '{status}' must be UPPERCASE"

    def test_valid_lob_excludes_wealth_management(self):
        assert "WEALTH MANAGEMENT" not in VALID_LINE_OF_BUSINESS
        assert "RETAIL" in VALID_LINE_OF_BUSINESS
        assert "BUSINESS" in VALID_LINE_OF_BUSINESS

    def test_valid_product_category_no_cds(self):
        for cat in VALID_PRODUCT_CATEGORY:
            assert "CD" not in cat.upper(), f"CDs should be excluded, found: {cat}"

    def test_default_status_is_active(self):
        assert DEFAULT_PROD_STATUS == "ACTIVE"

    def test_purpose_codes_no_overlap(self):
        assert RETAIL_PURPOSE_CODES & BUSINESS_PURPOSE_CODES == set()


# ── Balance Requires Abs Logic ────────────────────────────────────


class TestBalanceRequiresAbs:
    """PROD_balance_requires_abs should be TRUE for LOANS, FALSE for DEPOSITS."""

    @staticmethod
    def balance_requires_abs(product_category: str) -> bool:
        return product_category.upper() == "LOANS"

    def test_loans_require_abs(self):
        assert self.balance_requires_abs("LOANS") is True

    def test_deposits_do_not_require_abs(self):
        assert self.balance_requires_abs("DEPOSITS") is False

    def test_services_do_not_require_abs(self):
        assert self.balance_requires_abs("SERVICES") is False

    def test_case_insensitive(self):
        assert self.balance_requires_abs("loans") is True
        assert self.balance_requires_abs("Loans") is True


# ── Prompt Builder Tests ──────────────────────────────────────────


class TestPromptBuilder:
    SAMPLE_TAXONOMY = "# Test Taxonomy\n\nThis is a test taxonomy."

    def test_system_prompt_embeds_taxonomy(self):
        prompt = build_system_prompt(self.SAMPLE_TAXONOMY)
        assert "Test Taxonomy" in prompt
        assert "product categorization engine" in prompt.lower()

    def test_system_prompt_uses_silver_column_names(self):
        prompt = build_system_prompt(self.SAMPLE_TAXONOMY)
        assert "PROD_line_of_business" in prompt
        assert "PROD_product_category" in prompt
        assert "PROD_product_type" in prompt
        assert "PROD_core_system_mapping" in prompt

    def test_system_prompt_instructs_uppercase(self):
        prompt = build_system_prompt(self.SAMPLE_TAXONOMY)
        assert "UPPERCASED" in prompt or "UPPERCASE" in prompt

    def test_system_prompt_few_shot_examples_use_silver_names(self):
        prompt = build_system_prompt(self.SAMPLE_TAXONOMY)
        assert '"PROD_core_system_mapping":' in prompt
        assert '"PROD_line_of_business":' in prompt

    def test_system_prompt_includes_purpose_code_guidance(self):
        prompt = build_system_prompt(self.SAMPLE_TAXONOMY)
        assert "PURCOD" in prompt

    def test_system_prompt_mentions_wealth_management_flagging(self):
        prompt = build_system_prompt(self.SAMPLE_TAXONOMY)
        assert "WEALTH MANAGEMENT" in prompt


class TestUserPrompt:
    def test_basic_deposit(self):
        codes = [{"product_code": "CK", "product_description": "Checking", "product_domain": "DEPOSIT"}]
        prompt = build_user_prompt(codes)
        assert "product_code=CK" in prompt
        assert 'DESC="Checking"' in prompt
        assert "DOMAIN=DEPOSIT" in prompt
        assert "1 product codes" in prompt

    def test_loan_with_purpose_code(self):
        codes = [{
            "product_code": "01",
            "product_description": "Commercial RE",
            "product_domain": "LOAN",
            "purpose_code": "02",
            "purpose_description": "Real Estate",
            "loan_type_desc": "CRE Fixed",
        }]
        prompt = build_user_prompt(codes)
        assert "product_code=01" in prompt
        assert "PURCOD=02" in prompt
        assert 'PURPOSE="Real Estate"' in prompt
        assert 'LOAN_TYPE="CRE Fixed"' in prompt

    def test_missing_description_replaced(self):
        codes = [{"product_code": "XX", "product_description": "", "product_domain": "DEPOSIT"}]
        prompt = build_user_prompt(codes)
        assert "(no description)" in prompt

    def test_batch_size(self):
        codes = [
            {"product_code": f"C{i}", "product_description": f"Code {i}", "product_domain": "DEPOSIT"}
            for i in range(5)
        ]
        prompt = build_user_prompt(codes)
        assert "5 product codes" in prompt

    def test_optional_fields_omitted_when_none(self):
        codes = [{
            "product_code": "SV",
            "product_description": "Savings",
            "product_domain": "DEPOSIT",
            "purpose_code": None,
            "purpose_description": None,
        }]
        prompt = build_user_prompt(codes)
        assert "PURCOD" not in prompt
        assert "PURPOSE" not in prompt


class TestFullPrompt:
    def test_combines_system_and_user(self):
        taxonomy = "# Test"
        codes = [{"product_code": "CK", "product_description": "Checking", "product_domain": "DEPOSIT"}]
        prompt = build_full_prompt(codes, taxonomy)
        assert "product categorization engine" in prompt.lower()
        assert "product_code=CK" in prompt


# ── Response Schema Tests ─────────────────────────────────────────


class TestResponseSchema:
    def test_schema_is_valid_json(self):
        parsed = json.loads(RESPONSE_SCHEMA_STR)
        assert parsed == RESPONSE_SCHEMA

    def test_schema_type_is_json_schema(self):
        assert RESPONSE_SCHEMA["type"] == "json_schema"

    def test_schema_has_classifications_array(self):
        props = RESPONSE_SCHEMA["json_schema"]["schema"]["properties"]
        assert "classifications" in props
        assert props["classifications"]["type"] == "array"

    def test_schema_item_uses_silver_column_names(self):
        item_props = RESPONSE_SCHEMA["json_schema"]["schema"]["properties"]["classifications"]["items"]["properties"]
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

    def test_schema_required_fields(self):
        required = RESPONSE_SCHEMA["json_schema"]["schema"]["properties"]["classifications"]["items"]["required"]
        assert "PROD_core_system_mapping" in required
        assert "PROD_line_of_business" in required
        assert "confidence" in required

    def test_schema_nullable_fields(self):
        item_props = RESPONSE_SCHEMA["json_schema"]["schema"]["properties"]["classifications"]["items"]["properties"]
        assert item_props["PROD_product_name"]["type"] == ["string", "null"]
        assert item_props["PROD_product_code"]["type"] == ["string", "null"]

    def test_schema_non_nullable_fields(self):
        item_props = RESPONSE_SCHEMA["json_schema"]["schema"]["properties"]["classifications"]["items"]["properties"]
        assert item_props["PROD_core_system_mapping"]["type"] == "string"
        assert item_props["PROD_line_of_business"]["type"] == "string"
        assert item_props["confidence"]["type"] == "number"

    def test_schema_is_strict(self):
        assert RESPONSE_SCHEMA["json_schema"]["strict"] is True


# ── Integration: Column Mapping + Response Schema Alignment ───────


class TestMappingSchemaAlignment:
    """Ensure the response schema and column mapping are aligned."""

    def test_schema_output_keys_match_silver_columns(self):
        """Response schema keys should be a subset of Silver column names from COLUMN_MAPPING."""
        schema_keys = set(
            RESPONSE_SCHEMA["json_schema"]["schema"]["properties"]["classifications"]["items"]["properties"].keys()
        )
        silver_columns = set(COLUMN_MAPPING.values())
        silver_columns.add("confidence")  # confidence is a metadata field, not in mapping
        assert schema_keys.issubset(silver_columns), (
            f"Schema keys not in Silver columns: {schema_keys - silver_columns}"
        )

    def test_all_silver_columns_in_schema(self):
        """All Silver column names from COLUMN_MAPPING should be in the response schema."""
        schema_keys = set(
            RESPONSE_SCHEMA["json_schema"]["schema"]["properties"]["classifications"]["items"]["properties"].keys()
        )
        silver_columns = set(COLUMN_MAPPING.values())
        assert silver_columns.issubset(schema_keys), (
            f"Silver columns missing from schema: {silver_columns - schema_keys}"
        )
