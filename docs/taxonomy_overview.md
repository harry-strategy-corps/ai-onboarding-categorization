# Taxonomy Overview — Product & Transaction Categorization

This document provides a consolidated reference for both categorization taxonomies used by StrategyCorp's CheckingIQ platform. These taxonomies define the "answer space" that the AI Functions must map raw FI data into.

**Canonical source documents:**
- [Product Categories (Notion)](https://www.notion.so/Product-Categories-2a9ee9c7060580cb86dffe5fa46d9980)
- [Transaction Categorization (Notion)](https://www.notion.so/Transaction-Categorization-29aee9c706058019b945e43894af3396)

---

## 1. Product Categories Taxonomy

The product taxonomy classifies every banking product into a 5-level hierarchy. Levels 1–3 are **canonical** (defined by StrategyCorp, consistent across all FIs). Levels 4–5 are **FI-configurable** (each bank can customize).

### Hierarchy

```
Level 1: Line of Business          (StrategyCorp-defined)
  └─ Level 2: Product Type         (StrategyCorp-defined)
       └─ Level 3: Category        (StrategyCorp-defined)
            └─ Level 4: Sub-category   (FI-configurable)
                 └─ Level 5: Special    (FI-configurable)
```

### Level 1 — Line of Business

| Value | Description |
|-------|-------------|
| **Retail** | Consumer/individual banking products |
| **Business** | Commercial/business banking products |
| **Wealth Management** | Trust, fiduciary, investment products |

### Level 2 — Product Type

| Value | Applies To |
|-------|-----------|
| **Deposits** | Retail, Business, Wealth Management |
| **Loans** | Retail, Business |
| **Services** | Business (Cash Management / Treasury) |

### Level 3 — Category

| Product Type | Categories |
|-------------|------------|
| **Deposits** | Checking, Savings, CDs, Money Market |
| **Loans** | Mortgage, HELOC, Credit Card, Personal Loans, Auto Loans, Student Loans, Commercial Loans |
| **Services** | ACH, Wire, Lockbox, Payroll, Remote Deposit, Positive Pay, Account Reconciliation, Sweep, Zero Balance Account, Merchant Services, *(~20 total)* |

### Level 4 — Sub-category (FI-configurable examples)

| Category | Example Sub-categories |
|----------|----------------------|
| Checking | Basic, Premium, BaZing, Student, Senior, Non-Profit |
| Savings | Regular, Money Market, HSA, Christmas Club |
| CDs | Standard, Jumbo, IRA |
| Mortgage | Conforming, Jumbo, FHA, VA |
| Business Checking | Small Business, Corporate, Analyzed, Non-Profit |

### Level 5 — Special (FI-configurable examples)

Examples: Custodial, Government, <$1M, >$1M, ARM, Fixed, Fixed-to-ARM

### Key Notes for LLM Prompt Design

1. The LLM must always propose Levels 1–3 (canonical). Levels 4–5 should be proposed when the raw data provides enough context, but are optional.
2. The `core_system_mapping` field maps back to the bank's original product code — this is the **input** to the model.
3. Business products include **Cash Management Services** (Treasury) with ~20 specialized service sub-categories that are distinct from standard deposit/loan products.
4. Some products are ambiguous across Lines of Business:
   - Public Funds accounts → could be Retail or Business
   - Wealth Management deposits → separate LoB, not Retail
   - Fiduciary/Trust accounts → Wealth Management

---

## 2. Transaction Categorization Taxonomy

The transaction taxonomy classifies every bank transaction into a 4-level hierarchy (Level 5 was descoped). It is split into two independent classification blocks.

### Purpose of Each Level

| Level | Name | Purpose |
|-------|------|---------|
| Level 1 | Transaction Type | Differentiates fee vs. non-fee transactions |
| Level 2 | Fee/Activity Category | Used for non-interest income calculations and reporting |
| Level 3 | Activity Category | Used for detailed scoring and offers monitoring |
| Level 4 | Channel/Subtype | Used for granular transaction monitoring |

### Block A — Account Activity (Non-Fee Transactions)

These are the actual banking activities performed by the customer, not charges.

```
Account Activity (Level 1)
├── NSF/OD (Level 2)                          ← INCLUDE in scoring
│
├── Money movement (Level 2)                  ← INCLUDE in scoring
│   ├── ACH (Level 3)
│   │   └── Direct Deposit (Level 4, if available)
│   ├── ATM (Level 3)
│   │   ├── 3rd party / foreign (Level 4)
│   │   ├── FI owned (Level 4)
│   │   └── Sponsored, e.g. Allpoint (Level 4)
│   ├── Check (Level 3)
│   ├── Internal transfer / payment (Level 3)
│   ├── Wire (Level 3)
│   │   ├── Domestic (Level 4)
│   │   └── International (Level 4)
│   ├── Debit card (Level 3)
│   │   └── POS / point of sale (Level 4)
│   └── Credit Card (Level 3)
│       └── POS / point of sale (Level 4)
│
├── Account operations (Level 2)              ← EXCLUDE from scoring
│   ├── Closing (Level 3)
│   ├── Fraud & stop payment (Level 3)
│   ├── Memo posting (Level 3)
│   ├── Interest (Level 3)
│   ├── Govt. & Tax (Level 3)
│   ├── Integration (Level 3)
│   └── Operational (Level 3)
│
├── Miscellaneous (Level 2)                   ← EXCLUDE from scoring
│
└── Unclassified (Level 2)                    ← EXCLUDE from scoring
```

### Block B — Fee Item Transactions

These are fee-charging transactions that generate non-interest income.

```
Fee Item Transactions (Level 1)
├── NSF/OD (Level 2)
│
├── All others (Level 2)
│   ├── Money movement (Level 3)
│   │   ├── ACH (Level 4)
│   │   ├── ATM (Level 4)
│   │   ├── Wire (Level 4)
│   │   └── Transfers / payments (Level 4)
│   └── Account operations (Level 3)
│       └── Miscellaneous (Level 4)
│
├── Service Charges (Level 2)
│
├── Interchange (Level 2)
│
└── Unclassified (Level 2)
```

### `include_in_scoring` Rules

This boolean field determines whether a categorized transaction counts toward customer scoring calculations.

| Block | Category | Include in Scoring |
|-------|----------|:--:|
| A | NSF/OD | **YES** |
| A | Money movement (all children) | **YES** |
| A | Account operations (all children) | NO |
| A | Miscellaneous | NO |
| A | Unclassified | NO |
| B | *(all categories)* | **Not defined** — needs clarification |

### Structural Difference Between Blocks

The hierarchy levels shift between Block A and Block B. The same semantic concept sits at different levels:

| Concept | Block A Level | Block B Level |
|---------|:---:|:---:|
| Money movement | 2 | 3 |
| ACH | 3 | 4 |
| ATM | 3 | 4 |
| Wire | 3 | 4 |
| Account operations | 2 | 3 |

This means the LLM must treat each block as an **independent classification tree**. A prompt must not assume that "Level 3 = Activity Category" universally.

---

## 3. How the Two Taxonomies Connect

The transaction categorization depends on the **product context**:

- A transaction code like `299` (ATM Service Charge) on a **Checking** account maps differently than on a **Savings** account if fee schedules differ.
- The `ACTYPE` from the Deposit/Loan file tells the LLM **what kind of account** the transaction occurred on.
- Some transaction codes in the Master Fee Table have **multiple mappings** — the correct one depends on whether the account is a DDA, Savings, CD, or Loan.

```
Raw Transaction → TRANCD + EFHDS1/EFHDS2 + Account's ACTYPE
                       │
                       ▼
              Transaction Taxonomy
              (Block A or Block B, Levels 1-4)
                       │
                       ▼
              Product Taxonomy
              (needed for context on ambiguous codes)
```

---

## 4. Open Ambiguities

A full list of ambiguities is maintained in [`taxonomy/transaction_categorization_ambiguities.md`](../taxonomy/transaction_categorization_ambiguities.md). The highest-priority items are:

| # | Ambiguity | Impact | Status |
|---|-----------|--------|--------|
| 1 | No explicit fee/non-fee flag in raw data | Cannot auto-determine Block A vs B | Open — ask Sid/Mike |
| 2 | `include_in_scoring` undefined for Block B | Silver model field may be NULL for all fees | Open — ask Sid |
| 3 | Newer payment rails (RTP, FedNow, Zelle) not in taxonomy | No Level 3 category exists for these | Open — ask Sid |
| 4 | "Integration" and "Operational" have no definitions | LLM cannot distinguish them reliably | Open — ask Mike |
| 5 | 11 transaction codes have multiple mappings in Fee Table | Need disambiguation rules (account type, description) | Open — ask Sid/Mike |

---

## 5. Structured Taxonomy Files

| File | Format | Purpose |
|------|--------|---------|
| `taxonomy/transaction_categorization_taxonomy.json` | JSON | Machine-readable transaction taxonomy — ready for LLM prompt context |
| `taxonomy/data/Master Fee Table(Master).csv` | CSV | Ground truth mapping: 431 transaction codes → 4-level categories |
| `taxonomy/transaction_categorization_ambiguities.md` | Markdown | Documented ambiguities and open questions |
| `taxonomy/bankplus_transaction_data_analysis.md` | Markdown | Analysis of raw data vs. taxonomy coverage |
