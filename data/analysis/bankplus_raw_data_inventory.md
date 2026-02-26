# Bank Plus Raw Data Inventory — Transaction Categorization Focus

**Date:** 2026-02-25
**Purpose:** Identify which raw data files and fields are relevant for initial transaction categorization with AI Functions.

---

## Files Available

| File | Rows | Type | Relevant for Txn Categorization? |
|------|------|------|----------------------------------|
| `CheckingIQ_NON_POS_Daily_121925.csv` | 169,168 | **Transactions** | **YES — Primary file** |
| `CheckingIQ_Deposit_ALL_012626.csv` | 302,574 | Account-level deposit data | Indirectly (provides ACTYPE to link txns to products) |
| `CheckingIQ_Loan_13Month_All_121725.csv` | 389,448 | Loan account snapshots | No (product categorization, not transactions) |
| `CheckingIQ_CD_All_121725.csv` | 22,136 | CD account data | No |
| `CheckingIQ_Relationship_All_122625.csv` | 409,301 | CIF-to-account relationships | No (supplementary) |
| `CheckingIQ_CI_All_122625.csv` | 208,290 | Customer information | No (supplementary) |
| `CheckingIQ_OnlineBanking_Daily_012626_rerun.csv` | 147,582 | Online banking status | No |

---

## Primary File: `CheckingIQ_NON_POS_Daily_121925.csv`

### Schema

| Column | Description | Example |
|--------|-------------|---------|
| `ACCTNO` | Masked account number | `DAB40136312` |
| `status` | Account status (1=Active, 2=Closed, 6=Restricted, 8=Charge-Off) | `1` |
| `TRANCD` | **Transaction code (numeric)** — the key field to categorize | `163` |
| `description` | Always empty in this file | _(empty)_ |
| `TRDATE` | Transaction date | `2025-12-19` |
| `AMT` | Transaction amount (always positive) | `3560.87` |
| `EFHDS1` | **Description line 1** — primary contextual clue | `AC- OAKLEY TRUCKING` |
| `EFHDS2` | **Description line 2** — secondary context | `PY12/19/25` |
| `Account#` | Actual account number | `4522016312` |
| `PostingDate` | Posting date | `2025-12-19` |

### Key Observations

1. **`description` column is always empty** — no help there
2. **`AMT` is always positive** — no debit/credit indicator from sign
3. **`EFHDS1` + `EFHDS2` are the ONLY contextual clues** — these free-text descriptions are what the LLM will use alongside `TRANCD`
4. **`status` is mostly 1** (Active: 169,050 / Charge-Off: 71 / Restricted: 26 / Closed: 21)

---

## Transaction Code Catalog (60 unique TRANCDs)

### Proposed Taxonomy Mapping Based on Description Analysis

#### Money Movement — ACH (Block A > Money movement > ACH)
| TRANCD | Count | EFHDS1 Patterns | Proposed L3 | Notes |
|--------|-------|-----------------|-------------|-------|
| **163** | 67,505 | `AC- AARP...`, `AC- PAYROLL USPS`, named payees | ACH | ACH credits — Direct Deposit candidates when `AC-` prefix |
| **183** | 62,902 | `AC- INTUIT...`, `AC- K-LOVE`, named payees | ACH | ACH debits — recurring payments, bill pay |
| **8** | 14 | `Invalid ACH Routing Number`, `Account Closed` | ACH | ACH returns — error/rejection |
| **59** | 16 | `Insufficient Funds`, `ORIGINATED ACH ITEM RETURNED` | ACH | ACH returns — NSF/originated returns |

#### Money Movement — ATM (Block A > Money movement > ATM)
| TRANCD | Count | EFHDS1 Patterns | Proposed L3 | Proposed L4 |
|--------|-------|-----------------|-------------|-------------|
| **227** | 7,280 | `ATM W/D 1232...`, `1534 WEST PEACE ST` | ATM | Withdrawal (FI owned vs 3rd party unclear from data) |
| **237** | 146 | `ATM W/D 1821...`, `509 LAKELAND PLACE` | ATM | Withdrawal (different code — possibly foreign ATM?) |
| **242** | 10 | `ATM TFR 0915...` | ATM | ATM Transfer |
| **261** | 4 | `ATM TFR 1142...` | ATM | ATM Transfer (different direction?) |
| **283** | 10 | `ATM TFR 0915...` | ATM | ATM Transfer |
| **287** | 4 | `ATM TFR 1846...` | ATM | ATM Transfer |
| **299** | 2,326 | `W/D SVC 0014...`, addresses | ATM | ATM Withdrawal (service withdrawal?) |

#### Money Movement — Wire (Block A > Money movement > Wire)
| TRANCD | Count | EFHDS1 Patterns | Proposed L3 | Proposed L4 |
|--------|-------|-----------------|-------------|-------------|
| **34** | 160 | `WIRE-IN 2025353...` | Wire | Domestic (incoming) |
| **46** | 10 | `WIRE-OUT 2025353...` | Wire | Domestic (outgoing) |
| **66** | 126 | `WIRE-OUT 2025353...` | Wire | Domestic (outgoing) |
| **67** | 172 | `WIRE In Fee`, `WIRE Out Fee` | Wire | **FEE — Block B?** |

#### Money Movement — Internal Transfer / Payment
| TRANCD | Count | EFHDS1 Patterns | Proposed L3 |
|--------|-------|-----------------|-------------|
| **103** | 31 | `TRANSFER REQUEST`, `ITM TRANSFER REQUEST` | Internal transfer / payment |
| **104** | 35 | `TRANSFER REQUEST`, `F/P LOC ADV TRANS` | Internal transfer / payment |
| **113** | 157 | `Telephone transfer`, `Loan Payment` | Internal transfer / payment |
| **114** | 152 | `TRANSFER REQUEST`, `Telephone Transfer` | Internal transfer / payment |
| **141** | 6,940 | `Web Xfer From/To: ...DDA` | Internal transfer / payment |
| **142** | 1,481 | `Web Xfer From/To: ...Savings` | Internal transfer / payment |
| **143** | 80 | `Web Xfer From/To: ...Loan` | Internal transfer / payment |
| **144** | 6,196 | `Web Xfer From/To: ...DDA/Savings` | Internal transfer / payment |
| **145** | 1,834 | `Web Xfer From/To: ...DDA`, `Transfer to Savings` | Internal transfer / payment |
| **146** | 545 | `Web Xfer From/To: ...`, `Transfer to Loan` | Internal transfer / payment |
| **147** | 19 | `FUNDING CD...`, `Transfer to CD` | Internal transfer / payment |
| **149** | 385 | `Web Xfer From/To: ...`, `Transfer to Christmas Club` | Internal transfer / payment |
| **150** | 35 | `Deposit from CD` | Internal transfer / payment |
| **641** | 299 | `Transfer from DDA` | Internal transfer / payment |
| **642** | 74 | `Transfer from Savings` | Internal transfer / payment |
| **643** | 21 | `Transfer from Loan` | Internal transfer / payment |
| **644** | 373 | `Transfer to DDA` | Internal transfer / payment |
| **646** | 16 | `Transfer to Loan` | Internal transfer / payment |
| **741** | 40 | `Investment Sweep From DDA` | Internal transfer / payment |
| **744** | 40 | `Investment Sweep to DDA` | Internal transfer / payment |
| **918** | 18 | `Trnsfr Frm Act Ending in...` | Internal transfer / payment |
| **919** | 18 | `Trnsfr Frm Act Ending in...` | Internal transfer / payment |
| **928** | 1 | `Trnsfr Frm Act Ending in...` | Internal transfer / payment |
| **929** | 1 | `Trnsfr Frm Act Ending in...` | Internal transfer / payment |

#### Money Movement — Debit Card
| TRANCD | Count | EFHDS1 Patterns | Proposed L3 | Proposed L4 |
|--------|-------|-----------------|-------------|-------------|
| **83** | 2,868 | `JHC R/U 0909...`, `Card# 3289` | Debit card | POS (card reversals/usage) |
| **222** | 2,776 | `PMT CRD 0750...` | Debit card | POS (card payment) |
| **223** | 1,643 | `WAL-MART #0155`, `AMAZON MKTPLACE`, `TARGET.COM` | Debit card | POS (retail purchases) |
| **70** | 1 | `Prov Credit Reversal POS Dispu` | Debit card | POS (dispute reversal) |

#### Money Movement — P2P / Real-Time Payments
| TRANCD | Count | EFHDS1 Patterns | Proposed L3 |
|--------|-------|-----------------|-------------|
| **6** | 733 | `ZELLE ...` (outgoing) | ACH (or new sub-category?) |
| **56** | 713 | `ZELLE ...` (incoming) | ACH (or new sub-category?) |
| **42** | 522 | `RTP deposit from...`, `Credit via Trustly` | ACH (Real-Time Payments) |
| **44** | 11 | `FedNow deposit from...` | ACH (FedNow) |
| **9** | 63 | `AC- BANKPLUS`, named individuals | ACH or Internal transfer |

#### Account Operations — NSF/OD
| TRANCD | Count | EFHDS1 Patterns | Proposed L2 |
|--------|-------|-----------------|-------------|
| **14** | 53 | `Refund NSF/OD Fee...` | NSF/OD |

#### Account Operations
| TRANCD | Count | EFHDS1 Patterns | Proposed L3 |
|--------|-------|-----------------|-------------|
| **15** | 78 | `ck# posted to wrong`, `CHGOFF PAID IN FULL`, `CS TRANSFER` | Operational (corrections/adjustments) |
| **62** | 47 | `Cash Adv Balance`, branch names | Operational (cash advance) |
| **63** | 5 | `ck# l/a ... s/b`, `FRESH START PMT`, `RTN` | Operational (corrections) |
| **110** | 13 | `Safe Deposit Rental Payment` | Account operations > Miscellaneous |
| **155** | 22 | `CD Interest` | Interest |
| **157** | 5 | `Distribution from IRA` | Operational |
| **161** | 1 | `VISA SETTLEMENT PRC392` | Operational (card settlement) |
| **916** | 1 | `Missing Documentation/ID` | Operational |

#### Fee Item Transactions (Block B candidates)
| TRANCD | Count | EFHDS1 Patterns | Proposed Block B Category |
|--------|-------|-----------------|--------------------------|
| **67** | 172 | `WIRE In Fee`, `WIRE Out Fee` | Fee > All others > Money movement > Wire |
| **333** | 30 | `LEVY`, `RETURNED MAIL FEE`, `LOST CHECKCARD FEE`, `FOCH ANNUAL FEE` | Fee > All others > Account operations > Misc |
| **334** | 4 | `Wire Fee Refund`, `SERVICE CHARGE REFUND` | Fee > Service Charges (refund) |

---

## Critical Findings

### 1. No Fee/Non-Fee Flag in the Data
There is **no explicit field** that marks a transaction as Block A (Account Activity) vs Block B (Fee Item Transaction). The `TRANCD` itself is the only discriminator. Based on analysis:
- **TRANCD 67** (wire fees), **333** (misc fees), **334** (fee refunds) are clearly fees
- All others appear to be account activity (non-fee)
- **This mapping is inferred, not explicit** — needs validation with Sid/Mike

### 2. Zelle and RTP Are Not in the Taxonomy
The taxonomy lists ACH, ATM, Check, Internal transfer, Wire, Debit card, Credit Card as Level 3 options. But Bank Plus has significant volume in:
- **Zelle** (TRANCDs 6, 56 — ~1,446 txns)
- **RTP** (TRANCD 42 — 522 txns)
- **FedNow** (TRANCD 44 — 11 txns)

**Question:** Should these map to ACH, or do they need new Level 3 categories?

### 3. No Credit Card Transactions in This File
The file is called "NON_POS" — there may be a separate POS file not included in the data folder. Credit Card (Level 3) has no representation here.

### 4. All Amounts Are Positive
Cannot distinguish debits from credits based on `AMT`. The `TRANCD` itself implies direction (e.g., 163=ACH credit, 183=ACH debit).

### 5. `description` Column Is Always Empty
The `EFHDS1` and `EFHDS2` fields are the actual transaction descriptions, not the `description` column.

---

## What to Upload to Databricks for Initial AI Functions Testing

### Recommended: Transaction Code Catalog (Lightweight)

For the **initial categorization test**, we don't need the full 169K transaction records. What we need is a **distinct catalog of transaction codes with representative descriptions**:

```sql
-- Pseudo-query: extract unique TRANCD + sample descriptions
SELECT DISTINCT
    TRANCD,
    FIRST(EFHDS1) as sample_description_1,
    COUNT(*) as transaction_count
FROM raw_non_pos_daily
GROUP BY TRANCD
ORDER BY TRANCD
```

This gives us **60 unique transaction codes** — a perfect small dataset for initial AI Function testing.

### Supplementary: Full Transaction File

For accuracy validation after initial mapping, upload the full `CheckingIQ_NON_POS_Daily_121925.csv` to verify the LLM's categorization works across the variety of descriptions within each TRANCD.

### Data Not Yet Available

| Missing Data | Why It Matters | Action |
|--------------|----------------|--------|
| POS transactions file | Contains debit card POS and possibly credit card txns | Ask Sebastian |
| Fee/service charge transactions | May be in a separate feed for Block B | Ask Sebastian |
| Transaction code master table | Official SilverLake code definitions | Ask Sebastian / check JH documentation |
