# AI Onboarding Categorization

**Automated product and transaction categorization for financial institution onboarding using Databricks AI Functions.**

| | |
|---|---|
| **Linear Project** | [CIQENG — Leverage Databricks LLM Capabilities for Initial FI Categorization](https://linear.app/strategycorps/project/ciq-leverage-databricks-llm-capabilities-for-initial-fi-categorization-bcd8c02f129d/overview) |
| **Platform** | CheckingIQ (Azure Databricks, Medallion Architecture) |
| **Test Client** | Bank Plus (Jack Henry SilverLake core) |
| **Owner** | Harrison Hoyos |
| **Status** | Phase 1 — Exploration & Setup |

---

## Problem

When a new financial institution (FI) is onboarded onto CheckingIQ, their raw product codes and transaction codes must be mapped to StrategyCorp's internal canonical taxonomy. This mapping feeds the Silver layer models (`product_type_configuration_master` and `transaction_code_mapping_master`) that drive all downstream analytics, scoring, and reporting.

Today this mapping is **entirely manual** — a subject-matter expert reviews each code, interprets its meaning, and assigns the correct taxonomy values across multiple hierarchy levels. For a typical FI this involves ~80 deposit/DDA codes, ~60 loan codes, and hundreds of transaction codes. It is slow, error-prone, and the single biggest bottleneck to Day-1 time-to-value.

## Solution

Use **Databricks AI Functions** (`ai_query`, `ai_classify`) to build two LLM-powered suggestion models that take raw FI data and propose draft mappings against the canonical taxonomy:

1. **Product Suggestion Model** — maps raw product codes/descriptions → `product_type_configuration_master` fields (Line of Business, Product Type, Category, Sub-category, Special)
2. **Transaction Suggestion Model** — maps raw transaction codes/descriptions → `transaction_code_mapping_master` fields (Transaction Type, Fee Category, Activity Category, Channel, Subtype, Include in Scoring)

The output is a set of **staged suggestion tables** with proposed mappings and confidence scores, ready for human review.

## Test Case

Bank Plus is the first FI used to develop and validate the models. We have:

- **Raw data** — 13 CSV files from the Jack Henry SilverLake core system (deposits, loans, CDs, transactions, relationships, customer information)
- **Ground truth** — A Master Fee Table with 431 transaction codes already mapped to the 4-level categorization hierarchy
- **Glossary** — The [BankPlus Legend Glossaries](https://www.notion.so/BankPlus-Legend-Glossaries-2f6ee9c7060580abb3a2c0bd9c3dca09) in Notion, containing the full product catalog, loan types, purpose codes, class codes, and branch information

---

## Repository Structure

```
ai-onboarding-categorization/
├── README.md                          # This file
├── pyproject.toml                     # Python project configuration
├── main.py                           # Entry point (placeholder)
│
├── docs/                             # Project documentation
│   ├── architecture.md               # System context, integration with CheckingIQ
│   ├── data_dictionary.md            # Schema reference for all raw data files
│   ├── taxonomy_overview.md          # Categorization taxonomy reference
│   └── contributing.md               # How to work in this repository
│
├── data/                             # Raw Bank Plus data (CSV, not committed)
│   ├── CheckingIQ_Deposit_ALL_*.csv
│   ├── CheckingIQ_Loan_13Month_All_*.csv
│   ├── CheckingIQ_CD_All_*.csv
│   ├── CheckingIQ_NON_POS_Daily_*.csv
│   ├── CheckingIQ_POS_Daily_*.csv
│   ├── CheckingIQ_CI_All_*.csv
│   ├── CheckingIQ_Relationship_All_*.csv
│   ├── CheckingIQ_OnlineBanking_Daily_*.csv
│   └── analysis/                     # Data exploration notes
│       └── bankplus_raw_data_inventory.md
│
├── taxonomy/                         # Categorization taxonomy artifacts
│   ├── transaction_categorization_taxonomy.json
│   ├── transaction_categorization_ambiguities.md
│   ├── bankplus_transaction_data_analysis.md
│   └── data/
│       └── Master Fee Table(Master).csv
│
└── plans/                            # Sprint plans and phase documentation
    └── phase1_exploration_setup_plan.md
```

---

## Phased Approach

### Phase 1 — Exploration & Setup (current)

Establish data access, understand both taxonomies, obtain ground truth mappings, enable Azure Private Link, and evaluate Databricks AI Functions.

**Key deliverables:**
- Raw data access confirmed in Databricks
- Transaction and Product taxonomies structured as JSON for LLM prompt context
- Manual mapping ground truth loaded and coverage analyzed
- `ai_query` vs `ai_classify` evaluated with recommendation

**Linear ticket:** [CIQENG-981](https://linear.app/strategycorps/issue/CIQENG-981)

### Phase 2 — Product Suggestion Model

Design prompts with full taxonomy context + few-shot examples, process all ~80 DDA codes and ~60 loan codes, write suggestions to staging tables, validate against manual mappings (target ≥ 80% accuracy).

### Phase 3 — Transaction Suggestion Model

Same pattern for transaction codes using the Master Fee Table as ground truth.

---

## Key References

| Resource | Link |
|----------|------|
| CheckingIQ Architecture | [Solution Design](https://github.com/strategycorps-git/checking-iq/blob/develop/Architecture/SolutionDesign.md) |
| Silver Product Model | [`product_type_configuration_master.sql`](https://github.com/strategycorps-git/checking-iq/blob/develop/data-refinement/sqlmesh/models/silver/product_type_configuration_master.sql) |
| Silver Transaction Model | [`transaction_code_mapping_master.sql`](https://github.com/strategycorps-git/checking-iq/blob/develop/data-refinement/sqlmesh/models/silver/transaction_code_mapping_master.sql) |
| Databricks AI Functions | [Documentation](https://docs.databricks.com/aws/en/large-language-models/ai-functions) |
| Product Categories (taxonomy) | [Notion](https://www.notion.so/Product-Categories-2a9ee9c7060580cb86dffe5fa46d9980) |
| Transaction Categorization (taxonomy) | [Notion](https://www.notion.so/Transaction-Categorization-29aee9c706058019b945e43894af3396) |
| Bank Plus Glossaries | [Notion](https://www.notion.so/BankPlus-Legend-Glossaries-2f6ee9c7060580abb3a2c0bd9c3dca09) |
| Fee Category Mapping (Mike Young) | [SharePoint](https://strategycorps-my.sharepoint.com/:x:/p/mike_young/IQAbndd8Wd6YQ6KyUXI5B5MgAQtoYwBDWGiFr3EY5zswnYo) |

---

## Contacts

| Person | Role | Area |
|--------|------|------|
| Harrison Hoyos | Engineer (owner) | Model development, AI Functions |
| Sid Ganesh | Project Lead | Product mapping ground truth, scope |
| Mike Young | Business/Domain | Fee/transaction mapping |
| Sebastian | Data Engineering | Raw data access in Databricks |
| Hugo / Tiago / Gonzalo | Infrastructure | Azure Private Link enablement |
| Cliff | JH Integration | Jack Henry sandbox API keys |
| Herber de Ruijter | Stakeholder | Strategic direction |
