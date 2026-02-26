# Bank Plus Raw Data — Transaction Categorization Analysis

**Date:** 2026-02-25
**Objective:** Determine which raw data files and fields are relevant for testing AI Functions-based transaction categorization.

---

## 1. Available Raw Data Files

| File | Rows | Purpose | Relevant for Txn Categorization? |
|------|-----:|---------|:---:|
| `CheckingIQ_NON_POS_Daily_012626_rerun.csv` | 187,823 | Non-POS daily transactions (ACH, ATM, wires, transfers, checks, fees) | **YES — Primary** |
| `CheckingIQ_POS_Daily_012626_rerun.csv` | 355,690 | POS (point-of-sale) debit card transactions | **YES — Primary** |
| `CheckingIQ_Deposit_ALL_012626_rerun.csv` | 302,574 | Deposit account master (ACTYPE, SCCODE) | YES — for product context |
| `CheckingIQ_Loan_13Month_All_012626_rerun.csv` | 388,177 | Loan account master (ACTYPE, PURCOD) | YES — for product context |
| `CheckingIQ_CD_All_012626_rerun.csv` | 22,497 | CD account master | Low — few transaction codes |
| `CheckingIQ_CI_All_012626_rerun.csv` | 207,177 | Customer information (CFCLAS) | Context only |
| `CheckingIQ_Relationship_All_012626_rerun.csv` | 409,769 | CIF-to-Account relationships | Context only |
| `CheckingIQ_OnlineBanking_Daily_012626_rerun.csv` | 147,582 | Online banking login status | Not relevant |

### Also Available

| File | Location | Purpose |
|------|----------|---------|
| `Master Fee Table(Master).csv` | `taxonomy/data/` | **Mike's mapping sheet** — already has 431 transaction codes mapped to the 4-level categorization hierarchy. This is our ground truth. |

---

## 2. Transaction Files — Schema

### NON_POS (`CheckingIQ_NON_POS_Daily`)

| Column | Description | Example |
|--------|-------------|---------|
| `ACCTNO` | Account number (masked) | SAA98604011 |
| `status` | Account status (all = 1) | 1 |
| **`TRANCD`** | **Transaction code — the key field for categorization** | 183 |
| `description` | Usually empty for NON_POS | *(blank)* |
| `TRDATE` | Transaction date | 2026-01-26 |
| `AMT` | Transaction amount | 258.20 |
| `EFHDS1` | **Extended description line 1 — contains the real description** | "AC- PAY PLUS" |
| `EFHDS2` | Extended description line 2 | "HCCLAIMPMT" |
| `Account#` | Internal account number | 4820664011 |
| `PostingDate` | Posting date | 2026-01-26 |

### POS (`CheckingIQ_POS_Daily`)

Same schema as NON_POS, plus:

| Column | Description | Example |
|--------|-------------|---------|
| `description` | **Populated for POS** — contains the transaction type | "POS Debit - DDA" |
| `MerchantCategory` | MCC code (merchant category code) | 5542 |
| `MerchantName` | Merchant name | "MURPHY7565ATWALMART" |

---

## 3. Transaction Code Inventory

### NON_POS — 58 unique `TRANCD` values

| TRANCD | Count | Description (from EFHDS1 patterns) | Likely Category |
|-------:|------:|-------------------------------------|-----------------|
| 183 | 99,289 | ACH Debit | Money movement > ACH |
| 163 | 29,832 | ACH Credit | Money movement > ACH |
| 227 | 13,995 | ATM Withdrawal | Money movement > ATM |
| 144 | 8,162 | Web Transfer to DDA | Money movement > Transfers |
| 83 | 7,356 | JH Card RoundUp Withdrawal | Money movement > Debit card? |
| 141 | 6,830 | Web Transfer from DDA | Money movement > Transfers |
| 222 | 4,956 | ATM Deposit | Money movement > ATM |
| 299 | 4,777 | ATM Service Charge | **Fee item** > All others > ATM |
| 223 | 2,812 | POS Credit | Money movement > Debit card |
| 142 | 2,535 | Web Transfer from Savings | Money movement > Transfers |
| 146 | 1,339 | Transfer to Loan | Money movement > Transfers |
| 145 | 1,111 | Transfer to Savings | Money movement > Transfers |
| 56 | 890 | Zelle Debit | Money movement > Transfers |
| 6 | 867 | Zelle Credit | Money movement > Transfers |
| 42 | 735 | RTP Credit (Venmo, etc.) | Money movement > Transfers? |
| 644 | 411 | Transfer to DDA (auto) | Money movement > Transfers |
| 333 | 41 | Account Service Fee | **Fee item** > Service Charges |
| 67 | 70 | Wire Fee | **Fee item** > All others > Wire |
| 34 | 64 | Wire In | Money movement > Wire |
| 46 | 5 | Wire Out | Money movement > Wire |
| 66 | 51 | Internal Transfer / Wire Out | Money movement > Wire/Transfers |
| *(+37 more)* | | | |

### POS — 4 unique `TRANCD` values

| TRANCD | Count | Description | Category |
|-------:|------:|-------------|----------|
| 228 | 179,084 | POS Debit - DDA | Money movement > Debit card > POS |
| 229 | 155,060 | POS Pre-Authorized Debit - DDA | Money movement > Debit card > POS |
| 240 | 18,640 | POS Recurring Debit | Money movement > Debit card > POS |
| 223 | 2,906 | POS Credit | Money movement > Debit card |

---

## 4. Coverage Against Master Fee Table (Ground Truth)

**Result: 54 out of 61 unique raw codes are already mapped in the Master Fee Table (88.5% coverage).**

### 7 Uncovered Codes

These codes appear in the raw data but are **NOT** in the Master Fee Table:

| TRANCD | Occurrences | Pattern from EFHDS1 | Probable Category | Notes |
|-------:|------------:|----------------------|-------------------|-------|
| **34** | 64 | "WIRE-IN ..." | Non-fee > Money movement > Wire | Incoming wire transfer |
| **42** | 735 | "RTP deposit from VENMO / Whatnot / etc." | Non-fee > Money movement > Transfers? | Real-Time Payment (RTP) — newer payment rail, likely not in original mapping |
| **44** | 10 | "FedNow deposit from ..." | Non-fee > Money movement > Transfers? | FedNow — newest payment rail (launched 2023), definitely not in original mapping |
| **46** | 5 | "WIRE-OUT ..." | Non-fee > Money movement > Wire | Outgoing wire transfer |
| **66** | 51 | "INTERNAL TRF" / "WIRE-OUT" | Non-fee > Money movement > Wire/Transfers | Mixed — sometimes internal transfer, sometimes wire |
| **67** | 70 | "WIRE Out Fee" / "WIRE In Fee" | **Fee item** > All others > Money movement > Wire | Wire fee — this is a fee, not account activity |
| **83** | 7,356 | "JHC R/U" (Jack Henry Card RoundUp) | Non-fee > Money movement > Debit card? | Card round-up savings feature — unclear taxonomy placement |

**Key observations:**
- Codes **42** (RTP) and **44** (FedNow) are **newer payment rails** that didn't exist when the Master Fee Table was originally built. This is exactly the kind of gap AI Functions should help fill.
- Code **83** (JH Card RoundUp) is high volume (7,356 txns) and ambiguous — it could be Debit card activity or an Internal transfer.
- Code **67** is clearly a Wire Fee and should be in Block B (Fee Item Transactions).

---

## 5. Key Findings for AI Functions Strategy

### What to Upload to Databricks for Initial Testing

**Recommended approach — start with the transaction code catalog, not the full transaction files:**

1. **Extract unique `TRANCD` + sample descriptions** — Only 61 unique codes across both files. This is small enough for a single AI Function call or small batch.

2. **Use the Master Fee Table as ground truth** — 54 codes already mapped. Use these as:
   - Few-shot examples in the prompt (pick ~10-15 representative ones)
   - Validation set to measure accuracy (run AI Function on codes it already knows, compare output to Fee Table mapping)

3. **Test on the 7 uncovered codes** — These are the real value-add. If the AI can correctly categorize Wire In (34), Wire Out (46), RTP (42), FedNow (44), Wire Fee (67), Internal Transfer (66), and Card RoundUp (83), it proves the concept.

### Recommended Test Data for Databricks

```
Upload to Databricks:
├── transaction_code_catalog.csv          # 61 rows: TRANCD, sample descriptions, volume
├── master_fee_table_ground_truth.csv     # 54 mapped codes with 4-level categories
├── transaction_categorization_taxonomy.json  # Full taxonomy for prompt context
└── (optional) sample_transactions.csv    # 100-500 sample rows for end-to-end test
```

### Block A vs Block B Determination

From the data analysis, the **fee vs. non-fee distinction** can be inferred from:

1. **The transaction code itself** — Certain codes are inherently fee codes:
   - `299` (ATM Service Charge) → Fee item
   - `333` (Account Service Fee) → Fee item
   - `334` (Fee Code refund) → Fee item
   - `67` (Wire Fee) → Fee item

2. **The Master Fee Table already labels this** — The `Scoring Category 1` column contains "Non-fee item" or "Fee item/Fee Item"

3. **Some codes map to BOTH blocks** — Codes like `15`, `49`, `62`, `110`, `145`, `150`, `155`, `240`, `641`, `642`, `646` have multiple mappings in the Fee Table (one non-fee row and one that maps to Account Operations). This means a single TRANCD can have different categorizations depending on context (likely the account type or specific sub-description).

**This multi-mapping is the hardest part for the LLM** — it needs context beyond just the transaction code to pick the right mapping.

---

## 6. Ambiguity: Codes with Multiple Mappings

These codes have 2+ entries in the Master Fee Table with **different categorizations**:

| TRANCD | Mapping 1 | Mapping 2 | Disambiguation Needed |
|-------:|-----------|-----------|----------------------|
| 15 | Money movement > Deposits | Account Operations > N/A ("Initial Deposit - CD") | Account type (CD vs. DDA) |
| 49 | Money movement > ACH | Account Operations ("Reverse CD Deposit") | Account type |
| 62 | Money movement > Withdrawals | Account Operations ("Closing Redemption - CD") | Account type |
| 110 | Money movement > Transfers ("Safe Deposit") | Account Operations ("SEP Contribution") | Description context |
| 145 | Money movement > Transfers | Account Operations ("Rollover Conversion - CD") | Account type |
| 150 | Money movement > Deposits | Account Operations ("IRA Distribution") | Account type |
| 155 | Account Operations > Interest ("CD Interest") | Account Operations ("IRA Dist to Roth") | Description context |
| 240 | Money movement > Debit card ("POS Recurring") | Account Operations ("Reverse Recharacterization") | Description context |
| 641 | Money movement > Transfers | Account Operations ("Auto Transfer") | Description context |
| 642 | Money movement > Transfers | Account Operations ("Auto Transfer") | Description context |
| 646 | Money movement > Transfers | Account Operations ("Auto Transfer to Savings") | Description context |

**Impact:** For these ~11 codes, the AI Function will need EFHDS1/EFHDS2 description context plus potentially the account type to pick the correct mapping. Simple code-only classification won't work for these.

---

## 7. Next Steps

1. **Create a `transaction_code_catalog.csv`** with all 61 codes + descriptions for upload to Databricks
2. **Select 10-15 few-shot examples** from the Master Fee Table for prompt engineering
3. **Design the AI Function prompt** using the taxonomy JSON + few-shot examples
4. **Test on the 7 uncovered codes** first (smallest, highest-value test)
5. **Then test on all 54 covered codes** and compare vs. ground truth
6. **Discuss multi-mapping codes** with Sid/Mike — clarify disambiguation rules
