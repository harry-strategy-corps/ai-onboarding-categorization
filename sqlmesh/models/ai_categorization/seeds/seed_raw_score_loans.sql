MODEL (
  name ai_categorization.seed_raw_score_loans,
  kind SEED (
    path '../../../seeds/ai_categorization/raw_score_loans_sample.csv'
  ),
  columns (
    ACTYPE TEXT,
    PURCOD INTEGER,
    PurposeDescription TEXT,
    type TEXT,
    LoanTypeDesc TEXT,
    STATUS INTEGER,
    acctno TEXT
  )
);
