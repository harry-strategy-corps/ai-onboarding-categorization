MODEL (
  name ai_categorization.seed_raw_score_deposits,
  kind SEED (
    path '../../../seeds/ai_categorization/raw_score_deposits_sample.csv'
  ),
  columns (
    ACTYPE TEXT,
    SCCODE TEXT,
    STATUS INTEGER,
    ACCTNO TEXT,
    DDPSCOD TEXT
  )
);
