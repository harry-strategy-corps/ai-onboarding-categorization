MODEL (
  name ai_categorization.ai_product_suggestions,
  kind FULL,
  tags ['ai_categorization']
);

SELECT
    PROD_product_type_id,
    PROD_line_of_business,
    PROD_product_category,
    PROD_product_type,
    PROD_product_name,
    PROD_product_code,
    PROD_status,
    PROD_core_system_mapping,
    PROD_balance_requires_abs,
    PROD_created_date,
    PROD_modified_date,
    processing_timestamp,
    review_status,
    confidence,
    ai_model,
    prompt_version,
    product_domain,
    source_table,
    account_count
FROM ai_categorization.product_classification_suggestions
