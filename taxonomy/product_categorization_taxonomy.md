# Product Categorization Taxonomy

**Source:** [Product Categories (Notion)](https://www.notion.so/Product-Categories-2a9ee9c7060580cb86dffe5fa46d9980)  
**Target Table:** `product_type_configuration_master`  
**Last Updated:** 2026-02-26

---

## Purpose

When a new financial institution (FI) is onboarded onto CheckingIQ / MonetizeIQ, their raw product codes must be normalized into StrategyCorp's canonical product taxonomy. This taxonomy drives:

- **Dashboard reporting** — product mix analysis, balance composition, growth metrics
- **Customer scoring** — relationship depth indicators, cross-sell opportunity identification
- **Revenue analysis** — fee income attribution by product line
- **Scalability** — a single classification structure that works across all FIs regardless of core banking system

### AI Model Goal

The AI model should **pre-map ~80% of a bank's product codes** into this taxonomy, leaving the remainder flagged for manual review. A typical FI has ~80 deposit/DDA codes and ~60 loan codes. If the model maps the majority automatically, it dramatically reduces onboarding effort.

When the model **cannot confidently categorize** a product code, it must be flagged for manual review — never force-fitted into a wrong category.

---

## Hierarchy Overview

The taxonomy has **5 levels**. Levels 1–3 are **StrategyCorp-defined** (canonical across all FIs). Levels 4–5 are **FI-configurable** (each bank customizes to match their internal nomenclature).

| Level | Name | Configuration | Silver Model Field | Description |
|-------|------|---------------|-------------------|-------------|
| **Level 1** | Line of Business | StrategyCorp-defined | `PROD_line_of_business` | Retail, Business, or Wealth Management |
| **Level 2** | Type | StrategyCorp-defined | `PROD_product_type` | Deposits, Loans, Services, Securities, Cash Management |
| **Level 3** | Category | StrategyCorp-defined | `PROD_product_category` | Checking, Savings, CDs, Mortgage, HELOC, etc. |
| **Level 4** | Sub-category | FI-configurable | `PROD_product_name` | Basic, Premium, Jumbo, Small Business, etc. |
| **Level 5** | Special | FI-configurable | `PROD_product_code` | ARM, Fixed, Custodial, <$1M, >$1M, etc. |

All level names are **dynamic** — the FI can rename them in the UI to mirror their internal terminology (e.g., rename "Line of Business" to "Division" or "Category" to "Product Family").

```
Level 1: Line of Business          (StrategyCorp-defined)
  └─ Level 2: Type                 (StrategyCorp-defined)
       └─ Level 3: Category        (StrategyCorp-defined)
            └─ Level 4: Sub-category   (FI-configurable)
                 └─ Level 5: Special    (FI-configurable)
```

---

## Level 1 — Line of Business

| Value | Description |
|-------|-------------|
| **Retail** | Consumer/individual banking products and services |
| **Business** | Commercial/business banking products, services, and treasury management |
| **Wealth Management** | Trust, fiduciary, investment, and securities products |

---

## Retail

The Retail line of business covers all consumer/individual banking products.

### Retail > Deposits

#### Category: Checking (DDA)

| Sub-category | Special | Example Products |
|-------------|---------|-----------------|
| **Basic** | — | Basic Checking |
| **Premium** | — | Premium Checking |
| **BaZing** | — | Good Checking, Better Checking, Best Checking |
| — | **Custodial** | UGMA, UTMA |

#### Category: Savings

| Sub-category | Special | Example Products |
|-------------|---------|-----------------|
| **Basic** | — | Basic Savings |
| **Premium** | — | Premium Savings, Money Market |
| — | **Government** | Health Savings Accounts (HSAs), Educational Savings Accounts |

#### Category: Certificates of Deposit (CDs)

| Sub-category | Special | Example Products |
|-------------|---------|-----------------|
| — | **<$1M** | 6 month, 1 year, 18 month, 2 year, 3 year, 4 year, 5 year |
| — | **>$1M** | 6 month, 1 year, 18 month, 2 year, 3 year, 4 year, 5 year |

---

### Retail > Loans

#### Category: Mortgage Loans

| Sub-category | Special | Example Products |
|-------------|---------|-----------------|
| **Jumbo** | ARM | 1-year ARM |
| **Jumbo** | Fixed | 15-year fixed |
| **Jumbo** | Fixed-to-ARM | 5-year FTA |
| **Conforming** | ARM | 1-year ARM |
| **Conforming** | Fixed | 15-year fixed |
| **Conforming** | Fixed-to-ARM | 5-year FTA |

#### Category: HELOCs (Home Equity Lines of Credit)

**Example Products:** 30-year HELOC, 30-year SHELOC (Segmented HELOC)

#### Category: Credit Card

| Sub-category | Example Products |
|-------------|-----------------|
| **Cash Back** | Gold, Platinum |
| **Travel** | Gold, Platinum |

#### Category: Personal Loans

**Example Products:** 3 year, 5 year

#### Category: Auto Loans

**Example Products:** 3 year, 5 year, 7 year

#### Category: Student Loans

**Example Products:** 30-year

---

### Retail > Services

| Category | Description |
|----------|-------------|
| **Online Banking** | Internet banking platform access |
| **Mobile Banking** | Mobile app banking access |
| **Bill Pay** | Online bill payment service |
| **Overdraft** | Overdraft protection service |
| **Mobile Deposits** | Mobile check deposit capability |
| **Person-to-Person Payments (P2P)** | Peer-to-peer payment services (e.g., Zelle) |
| **Debit Cards** | Debit card issuance and management |
| **Safe Deposit Boxes** | Physical safe deposit box rental |

---

## Business

The Business line of business covers commercial/business banking products, including Cash Management Services (Treasury Management).

### Business > Deposits

#### Category: Checking (DDA)

| Sub-category | Example Products |
|-------------|-----------------|
| **Small Business** | Small Business Checking |
| **Corporate** | Corporate Checking |
| **Analyzed** | Business Analysis Checking |
| **Non-Profit** | Non-profit Checking |

#### Category: Savings

| Sub-category | Example Products |
|-------------|-----------------|
| **Small Business** | Small Business Savings |
| **Corporate** | Business Money Market |

#### Category: Certificates of Deposit (CDs)

| Sub-category | Special | Example Products |
|-------------|---------|-----------------|
| — | **<$1M** | 6 month, 1 year, 18 month, 2 year, 3 year, 4 year, 5 year |
| — | **>$1M** | 6 month, 1 year, 18 month, 2 year, 3 year, 4 year, 5 year |

---

### Business > Loans

| Category | Special | Example Products |
|----------|---------|-----------------|
| **Real Estate** | ARM | 1-year ARM |
| **Real Estate** | Fixed | 15-year fixed |
| **Real Estate** | Fixed-to-ARM | 5-year FTA |
| **Receivables-Based** | ARM | 6-month ARM, 1-year ARM |
| **Line of Credit** | ARM | 6-month ARM, 1-year ARM |
| **Equipment Financing** | ARM | 6-month ARM, 1-year ARM |
| **Credit Card** | — | Gold, Platinum |

---

### Business > Cash Management Services (Treasury Management)

Cash Management Services (AKA Treasury Management) is a specialized Product Type available only under the Business line of business. These are operational banking services — not deposit or loan products — that businesses use to manage their cash flow, payments, and receivables.

| Category | Description |
|----------|-------------|
| **Online Banking** | Business internet banking platform |
| **Mobile Banking** | Business mobile banking app |
| **ACH** | Automated Clearing House origination and receipt |
| **Wire (Domestic)** | Domestic wire transfer services |
| **SWIFT Wires (International)** | International wire transfer services |
| **Overdraft** | Business overdraft protection |
| **Remote Deposit Capture** | Scanning and depositing checks remotely |
| **Debit Cards** | Business debit card issuance |
| **Positive Pay** | Check fraud prevention — verifying checks against issued list |
| **Account Reconciliation** | Automated reconciliation of bank and book records |
| **Target Balance Accounts** | AKA Zero Balance Accounts — auto-sweep to maintain target balance |
| **Sweeps** | Automated sweep of excess funds to investment or interest-bearing accounts |
| **Controlled Disbursement Accounts** | Early notification of daily check presentment for cash planning |
| **Payroll** | Payroll processing and distribution |
| **Collections** | Receivables collection services |
| **Lockbox** | Mail-based payment processing at a bank facility |
| **Armored Car** | Secure cash pickup and delivery |
| **Cash Vault** | Cash management and coin/currency ordering |
| **Merchant Services** | Card point-of-sale processing services |
| **Transaction Monitoring** | Real-time or batch monitoring of account transactions |
| **Foreign Currency Exchange (FX)** | Foreign exchange transaction services |

---

## Wealth Management

The Wealth Management line of business covers trust, fiduciary, investment, and securities products.

### Wealth Management > Securities

#### Category: Transaction

| Sub-category | Example Products |
|-------------|-----------------|
| **Trading** | Cash Management Account |
| **Retirement** | Traditional IRA, Roth IRA, 401k |

#### Category: Loans

**Example Products:** Margin

---

## Raw Data Input Fields

The AI model uses these fields from the raw data files as inputs for product classification:

| Data Source | File | Key Field | Context Fields | Description |
|------------|------|-----------|---------------|-------------|
| **Deposits** | `CheckingIQ_Deposit_ALL` | `ACTYPE` | `SCCODE`, `DDPSCOD` | Product type code (CK, MM, SV, etc.) |
| **Loans** | `CheckingIQ_Loan_13Month_All` | `ACTYPE` | `PURCOD`, `PurposeDescription`, `type`, `LoanTypeDesc` | Loan type code + purpose code for consumer/business distinction |
| **CDs** | `CheckingIQ_CD_All` | `ACTYPE` | `ARGPRDCOD`, `CDTERM`, `Term_Code` | CD type code + term information |
| **Customers** | `CheckingIQ_CI_All` | `CFCLAS` | — | Customer class code (Individual, Business, Corporation, etc.) |

### Purpose Codes (PURCOD) — Consumer vs Business Indicator

| Code | Description | Maps to LoB |
|------|-------------|-------------|
| 01 | Personal/Household | Retail |
| 02 | Real Estate — Residential | Retail |
| 03 | Real Estate — Commercial | Business |
| 04 | Business — Commercial | Business |
| 05 | Farm — Real Estate | Business |
| 06 | Farm — Non-Real Estate | Business |
| 07 | Government | Context-dependent |
| 08 | Foreign | Context-dependent |
| 09 | Financial Institution | Business |
| 10 | Tax Exempt / Non-Profit | Context-dependent |
| 11 | Other | Context-dependent |

---

## Classification Rules for the AI Model

1. **First determine Line of Business** (Retail, Business, or Wealth Management):
   - Use customer class codes (`CFCLAS`): I = Individual → Retail; B, C, P = Business → Business; T, E, F = Wealth Management
   - Use loan purpose codes (`PURCOD`): 01–02 → Retail; 03–06, 09 → Business
   - Public Funds and Government accounts are ambiguous — flag for manual review if uncertain

2. **Then classify the Product Type** (Level 2):
   - Deposits: ACTYPE codes indicating DDA, savings, money market, or CD products
   - Loans: ACTYPE codes indicating mortgage, HELOC, credit card, personal, auto, student, or commercial loan products
   - Services: Non-deposit, non-loan products and capabilities (Retail only)
   - Cash Management Services: Treasury/operational services (Business only)
   - Securities: Investment and brokerage products (Wealth Management only)

3. **Then determine the Category** (Level 3) within the Product Type based on the specific ACTYPE and its description.

4. **Sub-category and Special** (Levels 4–5) are FI-configurable:
   - Propose when the raw data provides enough context (e.g., product description contains "Jumbo", "Premium", "HSA")
   - Leave blank when insufficient information — the FI user will fill these in

5. **Each product code maps to exactly one path** in the taxonomy tree. There is no multi-label classification.

6. **Retail and Business share some Categories** (Checking, Savings, CDs) but have different Sub-categories and different Loan structures. The LoB distinction must be made before Category assignment.

7. **Wealth Management** has its own unique structure (Securities > Transaction/Loans) that does not overlap with Retail/Business patterns.

---

## Output Schema

For each product code, the model should produce:

| Field | Description | Example (Retail Deposit) | Example (Business Loan) |
|-------|-------------|--------------------------|------------------------|
| `PROD_line_of_business` (Level 1) | Line of Business | Retail | Business |
| `PROD_product_type` (Level 2) | Product Type | Deposits | Loans |
| `PROD_product_category` (Level 3) | Category | Checking | Real Estate |
| `PROD_product_name` (Level 4) | Sub-category | Premium | — |
| `PROD_product_code` (Level 5) | Special | — | Fixed |
| `PROD_core_system_mapping` | Raw bank code (input) | CK | BG |

---

## Key Differences from Transaction Taxonomy

| Aspect | Product Taxonomy | Transaction Taxonomy |
|--------|-----------------|---------------------|
| **Levels** | 5 levels (all active) | 4 active levels (Level 5 descoped) |
| **Structure** | Single tree with 3 LoB branches | Two independent blocks (Block A / Block B) |
| **Canonical levels** | 1–3 (StrategyCorp-defined) | All 4 levels are StrategyCorp-defined |
| **FI-configurable** | Levels 4–5 (Sub-category, Special) | None (all canonical) |
| **Dynamic labels** | All level names can be renamed by FI | Fixed level names |
| **Scoring** | No include_in_scoring equivalent | include_in_scoring is a key derived field |
| **Input fields** | ACTYPE, PURCOD, CFCLAS | TRANCD, EFHDS1, EFHDS2 |
| **Target table** | `product_type_configuration_master` | `transaction_code_mapping_master` |
