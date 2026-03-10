MODEL (
  name ai_categorization.seed_bankplus_product_catalog,
  kind SEED (
    path '../../../seeds/ai_categorization/bankplus_product_catalog.csv'
  ),
  columns (
    product_code TEXT,
    product_description TEXT,
    product_domain TEXT,
    source_table TEXT,
    purpose_code TEXT,
    purpose_description TEXT,
    loan_type_desc TEXT,
    account_count INTEGER
  ),
  tags ['ai_categorization']
);
