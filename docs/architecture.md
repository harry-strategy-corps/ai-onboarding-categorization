# Architecture — System Context & Integration

## Where This Project Fits

CheckingIQ is a financial analysis platform built on **Azure Databricks** with a **Medallion Architecture** (Bronze → Silver → Gold). This project operates at the **Bronze-to-Silver boundary**, specifically at the point where raw FI data must be transformed into canonical taxonomy values before it can flow into analytics and reporting.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            CheckingIQ Platform                                  │
│                                                                                 │
│  ┌──────────────┐    ┌──────────────────────┐    ┌──────────────────────────┐   │
│  │   Bronze      │    │      Silver           │    │        Gold              │   │
│  │              │    │                      │    │                          │   │
│  │  Raw FI data  │───▶│  Canonical models     │───▶│  Analytics, Scoring,     │   │
│  │  (autoloader) │    │  (SQLMesh)            │    │  Dashboards, Reporting   │   │
│  │              │    │                      │    │                          │   │
│  └──────────────┘    └──────────────────────┘    └──────────────────────────┘   │
│         │                      ▲                                                │
│         │                      │                                                │
│         │            ┌─────────┴──────────┐                                     │
│         │            │  Configuration      │                                     │
│         │            │  Masters             │                                     │
│         │            │                      │                                     │
│         │            │  • product_type_     │                                     │
│         │            │    configuration_    │                                     │
│         │            │    master            │                                     │
│         │            │                      │                                     │
│         │            │  • transaction_code_ │                                     │
│         │            │    mapping_master    │                                     │
│         │            │                      │                                     │
│         │            └──────────▲───────────┘                                     │
│         │                       │                                                │
│         │              TODAY: Manual entry                                        │
│         │              FUTURE: AI-suggested                                       │
│         │                       │                                                │
│  ┌──────▼───────────────────────┴──────────────────────────┐                     │
│  │                                                          │                     │
│  │   AI Onboarding Categorization  ◄── THIS PROJECT         │                     │
│  │                                                          │                     │
│  │   Raw FI data ──▶ AI Functions ──▶ Suggestion Tables     │                     │
│  │                      │                                    │                     │
│  │              ┌───────┴────────┐                           │                     │
│  │              │  Taxonomy      │                           │                     │
│  │              │  Context       │                           │                     │
│  │              │  (prompt)      │                           │                     │
│  │              └────────────────┘                           │                     │
│  └──────────────────────────────────────────────────────────┘                     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Current State (Manual)

1. New FI provides raw data extracts (CSV files from core banking system)
2. Data is ingested into Databricks Bronze layer via Autoloader
3. A domain expert manually reviews each product code and transaction code
4. The expert assigns taxonomy values (Line of Business, Product Type, Category, etc.)
5. Mappings are manually entered into the Silver configuration master tables
6. SQLMesh models consume these tables to transform Bronze data into Silver canonical form

### Target State (AI-Assisted)

1. New FI provides raw data extracts (same as today)
2. Data is ingested into Databricks Bronze layer via Autoloader (same as today)
3. **AI Functions process the raw codes against the taxonomy context** — NEW
4. **Suggestion tables are populated with proposed mappings + confidence scores** — NEW
5. A domain expert reviews suggestions, approves/edits/rejects (workflow out of scope for this project)
6. Approved mappings are written to Silver configuration master tables

### Notebook Pipeline

The AI categorization pipeline runs as a sequence of Databricks notebooks, all persisting
intermediate and final results to Unity Catalog.

```
┌─────────────────────┐     ┌──────────────────────────┐     ┌──────────────────────┐
│  01_prepare_data     │     │  03_categorize_txns       │     │  04_evaluate_accuracy │
│                     │     │                          │     │                      │
│  Master Fee Table ──▶│─GT─▶│  Taxonomy MD + Catalog ──▶│─RES▶│  Results + GT ──▶     │
│  Raw NON_POS/POS  ──▶│─CAT▶│  Batch ai_query()        │     │  Per-layer accuracy  │
│                     │     │  responseFormat JSON      │     │  Volume-weighted     │
│  → ground_truth_    │     │  Token/cost tracking      │     │  Cross-version       │
│    normalized (UC)  │     │  prompt_version metadata  │     │  Failure analysis    │
│  → transaction_     │     │                          │     │                      │
│    code_catalog (UC)│     │  → classification_       │     │  → evaluation_       │
│    (with layers)    │     │    results (UC)           │     │    results (UC)      │
└─────────────────────┘     └──────────────────────────┘     └──────────────────────┘

                            ┌──────────────────────────┐
                            │  02_map_client_schema     │
                            │                          │
                            │  Prototype: AI-based     │
                            │  column mapping for new  │
                            │  FI onboarding           │
                            │                          │
                            │  → client_column_        │
                            │    mappings (UC)         │
                            └──────────────────────────┘
```

### Test Layers

Transaction codes are split into three difficulty layers for incremental testing:

| Layer | Name | Definition | Evaluation |
|-------|------|-----------|------------|
| 1 | Obvious | Codes with exactly 1 mapping in the Master Fee Table | Standard per-level comparison |
| 2 | Ambiguous | Codes with 2+ distinct mappings in the Master Fee Table | Match against ANY valid GT mapping |
| 3 | Unknown | Codes in raw data but absent from the Master Fee Table | Flagged as NEEDS MANUAL REVIEW |

### Unity Catalog Tables

All pipeline data is persisted to Unity Catalog under `ciq-bp_dummy-dev`.`default`:

| Table | Written By | Description |
|-------|-----------|-------------|
| `ground_truth_normalized` | 01_prepare_data | 431 cleaned GT mappings from Master Fee Table |
| `transaction_code_catalog` | 01_prepare_data | ~62 unique TRANCD codes with layer assignment and volume |
| `client_column_mappings` | 02_map_client_schema | AI-proposed column name mappings per client |
| `classification_results` | 03_categorize_transactions | LLM predictions with layer, prompt_version, cost metadata |
| `evaluation_results` | 04_evaluate_accuracy | Per-code match results, failure types, accuracy metrics |

## Silver Target Models

### `product_type_configuration_master`

This is the canonical product mapping table. Each row maps a bank's raw product code to StrategyCorp's product taxonomy.

| Field | Description | Source |
|-------|-------------|--------|
| `PROD_line_of_business` | Level 1 — Retail, Business, Wealth Management | StrategyCorp taxonomy |
| `PROD_product_type` | Level 2 — Deposits, Loans, Services | StrategyCorp taxonomy |
| `PROD_product_category` | Level 3 — Checking, Savings, CDs, Mortgage, HELOC, etc. | StrategyCorp taxonomy |
| `PROD_product_name` | Level 4 — Sub-category (FI-specific) | FI-configurable |
| `PROD_product_code` | Level 5 — Special designation | FI-configurable |
| `PROD_core_system_mapping` | Raw code from the bank's core system | Bank raw data |

**Source model:** [`product_type_configuration_master.sql`](https://github.com/strategycorps-git/checking-iq/blob/develop/data-refinement/sqlmesh/models/silver/product_type_configuration_master.sql)

### `transaction_code_mapping_master`

This is the canonical transaction mapping table. Each row maps a bank's raw transaction code to StrategyCorp's transaction categorization hierarchy.

| Field | Description | Source |
|-------|-------------|--------|
| `TXN_transaction_type` | Level 1 — Account Activity or Fee Item Transactions | StrategyCorp taxonomy |
| `TXN_fee_category` | Level 2 — NSF/OD, Money movement, Account operations, etc. | StrategyCorp taxonomy |
| `TXN_activity_category` | Level 3 — ACH, ATM, Check, Wire, Debit card, etc. | StrategyCorp taxonomy |
| `TXN_channel` | Level 4 — Direct Deposit, POS, Domestic, International, etc. | StrategyCorp taxonomy |
| `TXN_subtype` | Level 5 — Descoped (currently unused) | — |
| `TXN_include_in_scoring` | Boolean — whether this transaction counts in customer scoring | Derived from taxonomy rules |

**Source model:** [`transaction_code_mapping_master.sql`](https://github.com/strategycorps-git/checking-iq/blob/develop/data-refinement/sqlmesh/models/silver/transaction_code_mapping_master.sql)

## Databricks AI Functions

This project uses two Databricks AI Functions:

| Function | How It Works | Use Case |
|----------|-------------|----------|
| `ai_query()` | Sends a free-form prompt to a served foundation model with `responseFormat` for structured JSON output | Primary — multi-level hierarchical classification with taxonomy context |
| `ai_classify()` | Classifies input text into one of N predefined categories | Optional comparison — flat classification for individual levels |

**Primary choice:** `ai_query()` with `responseFormat` parameter (Databricks Runtime 15.4+). This enforces a JSON schema on the LLM response, eliminating manual output parsing. The `responseFormat` approach is cleaner and more reliable than post-hoc string cleanup.

### Prerequisites

- **Azure Private Link** must be enabled on the Databricks workspace for Model Serving endpoints to be accessible
- **Databricks Runtime 15.4 LTS or above** (current workspace runs Runtime 17)
- **US East region** confirmed for model serving availability

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Data Platform | Azure Databricks |
| Data Architecture | Medallion (Bronze → Silver → Gold) |
| Data Transformation | SQLMesh |
| Data Ingestion | Autoloader |
| AI Functions | `ai_query()` with `responseFormat` (Databricks built-in) |
| Foundation Models | Databricks-hosted (Claude Opus 4.6 — current) |
| Result Persistence | Unity Catalog (`ciq-bp_dummy-dev`.`default`) |
| Test Client Core System | Jack Henry SilverLake |
| This Repository | Python 3.13, Databricks notebooks |
