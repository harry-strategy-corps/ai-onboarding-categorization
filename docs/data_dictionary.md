# Data Dictionary — Bank Plus Raw Data

**Core System:** Jack Henry SilverLake
**Client:** Bank Plus
**Data Date:** January 26, 2026 (rerun extracts)
**File Format:** CSV (comma-delimited)

---

## File Inventory

| # | File | Rows | Frequency | Description |
|:-:|------|-----:|-----------|-------------|
| 1 | `CheckingIQ_Deposit_ALL_*.csv` | 302,574 | Snapshot | All deposit accounts (DDA, Savings, Money Market) |
| 2 | `CheckingIQ_Deposit_Daily_*.csv` | 3,190 | Daily delta | New/changed deposit accounts |
| 3 | `CheckingIQ_Loan_13Month_All_*.csv` | 388,177 | Snapshot | All loan accounts (13-month window) |
| 4 | `CheckingIQ_Loan_Daily_*.csv` | 432 | Daily delta | New/changed loan accounts |
| 5 | `CheckingIQ_CD_All_*.csv` | 22,497 | Snapshot | All CD accounts |
| 6 | `CheckingIQ_CD_Daily_*.csv` | 214 | Daily delta | New/changed CD accounts |
| 7 | `CheckingIQ_NON_POS_Daily_*.csv` | 187,823 | Daily | Non-POS transactions (ACH, ATM, wire, transfer, check, fee) |
| 8 | `CheckingIQ_POS_Daily_*.csv` | 355,690 | Daily | POS transactions (debit card) |
| 9 | `CheckingIQ_CI_All_*.csv` | 207,177 | Snapshot | Customer information (CIF master) |
| 10 | `CheckingIQ_CI_Daily_*.csv` | 887 | Daily delta | New/changed customer records |
| 11 | `CheckingIQ_Relationship_All_*.csv` | 409,769 | Snapshot | CIF-to-Account relationships |
| 12 | `CheckingIQ_Relationship_Daily_*.csv` | 123 | Daily delta | New/changed relationships |
| 13 | `CheckingIQ_OnlineBanking_Daily_*.csv` | 147,582 | Daily | Online banking login status |

### Relevance to AI Categorization

| Relevance | Files |
|-----------|-------|
| **Primary — transaction categorization** | NON_POS_Daily, POS_Daily |
| **Primary — product categorization** | Deposit_ALL, Loan_13Month_All, CD_All |
| **Context — account type lookup** | Deposit (ACTYPE, SCCODE), Loan (ACTYPE, PURCOD) |
| **Context — customer classification** | CI (CFCLAS) |
| **Not directly relevant** | Relationship, OnlineBanking |

---

## Schema Definitions

### 1. Deposit Accounts (`CheckingIQ_Deposit_ALL`)

Account-level data for all deposit products (checking, savings, money market).

| Column | Type | Description | Example | Notes |
|--------|------|-------------|---------|-------|
| `ACCTNO` | string | Masked account number | `DAB40136312` | Anonymized |
| `Account1` | string | Alternative account identifier | `4522016312` | |
| `STATUS` | string | Account status code | `1` | See status codes below |
| `STATUSdescription` | string | Status description | `Active` | |
| `DDMASTBranch` | string | Master branch number | `0100` | |
| `current_balance` | decimal | Current balance | `3456.78` | |
| `customer_id` | string | CIF number | `000123456` | Links to CI file |
| `Account_opened_date` | date | Date account was opened | `2019-03-15` | |
| `Online Status Flag` | string | Online banking enrollment | `Y` / `N` | |
| `AccountBranch` | string | Account branch | `0100` | |
| **`ACTYPE`** | string | **Product type code** | `CK`, `MM`, `SV` | **Key field for product categorization** |
| `account_close_date` | date | Close date (if closed) | `2025-11-01` | Null if active |
| `DateLastMaintenance` | date | Last maintenance date | `2026-01-26` | |
| `DDPSCOD` | string | Product sub-code | | |
| **`SCCODE`** | string | **Service charge code** | `01`, `12` | **Links to fee schedule** |

**Account Status Codes:**

| Code | Description |
|------|-------------|
| 1 | Active |
| 2 | Closed |
| 3 | Dormant |
| 6 | Restricted |
| 8 | Charge-Off |

---

### 2. Loan Accounts (`CheckingIQ_Loan_13Month_All`)

Account-level data for all loan products across a 13-month window.

| Column | Type | Description | Example | Notes |
|--------|------|-------------|---------|-------|
| `acctno` | string | Masked account number | `LAB12345678` | |
| `cifno` | string | CIF number | `000654321` | Links to CI file |
| `ORGAMT` | decimal | Original loan amount | `250000.00` | |
| `CBAL` | decimal | Current balance | `187543.21` | |
| `ORGDT` | date | Origination date | `2022-06-15` | |
| `MATDT` | date | Maturity date | `2052-06-15` | |
| `DATOPN` | date | Date opened | `2022-06-15` | |
| `STATUS` | string | Loan status | `1` | |
| **`ACTYPE`** | string | **Loan type code** | `01`, `A1`, `BG` | **Key field for product categorization** |
| `RATE` | decimal | Interest rate | `6.750` | |
| `LFMDT` | date | Last financial maintenance date | `2026-01-15` | |
| `JhaPostingDate` | date | JHA posting date | `2026-01-26` | |
| **`PURCOD`** | string | **Purpose code (1-11)** | `01` | **Consumer vs Business indicator** |
| `PurposeDescription` | string | Purpose description | `Personal/Household` | |
| `type` | string | Loan type code | `01` | |
| `LoanTypeDesc` | string | Loan type description | `CONSUMER SECURED` | |
| `Branch` | string | Branch number | `0100` | |

**Purpose Codes:**

| Code | Description | Classification |
|------|-------------|----------------|
| 01 | Personal/Household | Consumer |
| 02 | Real Estate — Residential | Consumer |
| 03 | Real Estate — Commercial | Business |
| 04 | Business — Commercial | Business |
| 05 | Farm — Real Estate | Business |
| 06 | Farm — Non-Real Estate | Business |
| 07 | Government | Government |
| 08 | Foreign | Other |
| 09 | Financial Institution | Business |
| 10 | Tax Exempt / Non-Profit | Other |
| 11 | Other | Other |

---

### 3. CD Accounts (`CheckingIQ_CD_All`)

Account-level data for certificates of deposit.

| Column | Type | Description | Example | Notes |
|--------|------|-------------|---------|-------|
| `ACCTNO` | string | Masked account number | `CDA98765432` | |
| `STATUS` | string | Account status | `1` | |
| `ActualAccount` | string | Actual account number | `4440098765` | |
| **`ACTYPE`** | string | **CD type code** | `01`, `02` | **Key field for product categorization** |
| `DateOpened` | date | Date opened | `2024-01-15` | |
| `CIFNO` | string | CIF number | `000111222` | |
| `cbal` | decimal | Current balance | `50000.00` | |
| `YTDINT` | decimal | Year-to-date interest | `1250.00` | |
| `RATE` | decimal | Interest rate | `4.500` | |
| `CDTERM` | integer | CD term (months) | `12` | |
| `Term_Code` | string | Term code | `M` | M=Monthly |
| `ORGBAL` | decimal | Original balance | `50000.00` | |
| `ARGPRDCOD` | string | Product code | | |
| `MaturityDate` | date | Maturity date | `2025-01-15` | |
| `Branch` | string | Branch number | `0100` | |

---

### 4. Non-POS Transactions (`CheckingIQ_NON_POS_Daily`)

Daily transaction feed for all non-POS activity: ACH, ATM, wires, transfers, checks, fees, account operations.

| Column | Type | Description | Example | Notes |
|--------|------|-------------|---------|-------|
| `ACCTNO` | string | Masked account number | `SAA98604011` | |
| `status` | string | Account status | `1` | Mostly `1` (active) |
| **`TRANCD`** | string | **Transaction code (numeric)** | `183` | **Primary key for transaction categorization** |
| `description` | string | Transaction description | *(empty)* | **Always empty** in this file |
| `TRDATE` | date | Transaction date | `2026-01-26` | |
| `AMT` | decimal | Transaction amount | `258.20` | **Always positive** — no debit/credit sign |
| **`EFHDS1`** | string | **Extended description line 1** | `AC- PAY PLUS` | **Primary contextual clue for the LLM** |
| **`EFHDS2`** | string | **Extended description line 2** | `HCCLAIMPMT` | **Secondary contextual clue** |
| `Account#` | string | Internal account number | `4820664011` | |
| `PostingDate` | date | Posting date | `2026-01-26` | |

**Key observations:**
- The `description` column is always empty — `EFHDS1` and `EFHDS2` carry the actual descriptions
- `AMT` is always positive — debit vs. credit is determined by the `TRANCD` code itself (e.g., 163=ACH credit, 183=ACH debit)
- 58 unique `TRANCD` values in the current extract
- This file contains both **non-fee** (Block A) and **fee** (Block B) transactions — there is no explicit flag to distinguish them

---

### 5. POS Transactions (`CheckingIQ_POS_Daily`)

Daily transaction feed for point-of-sale debit card activity.

| Column | Type | Description | Example | Notes |
|--------|------|-------------|---------|-------|
| `ACCTNO` | string | Masked account number | `SAC51536479` | |
| `status` | string | Account status | `1` | |
| **`TRANCD`** | string | **Transaction code** | `228` | Only 4 unique values |
| **`description`** | string | **Transaction description** | `POS Debit - DDA` | **Populated** (unlike NON_POS) |
| `TRDATE` | date | Transaction date | `2026-01-26` | |
| `AMT` | decimal | Transaction amount | `38.60` | |
| `EFHDS1` | string | Merchant/location info | `MURPHY7565ATWALMART` | |
| `EFHDS2` | string | POS terminal details | `POS DEB 1041 01/23/26 11499597` | |
| `Account#` | string | Internal account number | `4320386479` | |
| `PostingDate` | date | Posting date | `2026-01-26` | |
| **`MerchantCategory`** | string | **MCC code** | `5542` | Merchant Category Code (4 digits) |
| **`MerchantName`** | string | **Merchant name** | `MURPHY7565ATWALMART` | |

**POS Transaction Codes:**

| TRANCD | Count | Description |
|-------:|------:|-------------|
| 228 | 179,084 | POS Debit - DDA |
| 229 | 155,060 | POS Pre-Authorized Debit - DDA |
| 240 | 18,640 | POS Recurring Debit |
| 223 | 2,906 | POS Credit (refunds/reversals) |

All POS transactions map to: **Non-fee item → Money movement → Debit card → POS**

---

### 6. Customer Information (`CheckingIQ_CI_All`)

CIF (Customer Information File) master data.

| Column | Type | Description | Example | Notes |
|--------|------|-------------|---------|-------|
| `CFCIF#` | string | CIF number | `000123456` | Primary key |
| `CFNA1` | string | Name line 1 | `SMITH JOHN` | |
| `CFNA2` | string | Name line 2 | | |
| `CFNA3` | string | Name line 3 | | |
| `CFCITY` | string | City | `JACKSON` | |
| `CFSTAT` | string | State | `MS` | |
| `CFZIP` | string | ZIP code | `39201` | |
| `CFBRNN` | string | Branch number | `0100` | |
| `date_of_birth` | date | Date of birth | `1985-03-15` | |
| `DateDeceased` | date | Date deceased | | Null if alive |
| `DateEntered` | date | Date entered into system | `2010-06-01` | |
| `DateLastMaintenance` | date | Last maintenance date | `2026-01-26` | |
| **`CFCLAS`** | string | **Customer class code** | `I`, `B`, `C` | **Individual, Business, Corporation, etc.** |
| `DeceasedCustomerFlag` | string | Deceased flag | `N` | |

**Customer Class Codes (CFCLAS):**

| Code | Description |
|------|-------------|
| I | Individual |
| B | Business (Sole Proprietor) |
| C | Corporation |
| P | Partnership |
| G | Government |
| N | Non-Profit |
| T | Trust |
| E | Estate |
| F | Fiduciary |
| *(~19 total)* | See BankPlus Legend Glossaries |

---

### 7. Relationships (`CheckingIQ_Relationship_All`)

Maps CIF numbers to accounts, establishing which customer owns which accounts.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `CIF` | string | CIF number | `000123456` |
| `Relationship` | string | Relationship type | `Primary`, `Joint` |
| `AccountType` | string | Account type indicator | `D` (Deposit), `L` (Loan), `C` (CD) |
| `AccountNumber` | string | Account number | `4522016312` |

---

### 8. Online Banking (`CheckingIQ_OnlineBanking_Daily`)

Online banking enrollment and login activity.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `customer_id` | string | CIF number | `000123456` |
| `customer_name` | string | Customer name | `JOHN SMITH` |
| `Online Status Flag` | string | Enrollment status | `Y` / `N` |
| `processingDate` | date | Processing date | `2026-01-26` |
| `Last online Login Date` | date | Last login | `2026-01-25` |

---

## Ground Truth Reference

### Master Fee Table (`data/bank-plus-data/source-of-truth/Master Fee Table(Master).csv`)

This is the manually-created mapping sheet (from Mike Young) that serves as ground truth for transaction categorization. It maps Bank Plus external transaction codes to the 4-level categorization hierarchy.

| Column | Description | Example |
|--------|-------------|---------|
| `External Transaction Description` | Human-readable transaction name | `ACH Debit` |
| `External Transaction Code` | Bank's raw transaction code | `183` |
| `Fee Item Description` | Fee description (if applicable) | `N/A` |
| `Internal Fee Item Code` | Internal fee code (if applicable) | `N/A` |
| `Credit / Debit` | Transaction direction | `Debit` |
| `Scoring Category 1` | **Level 1** — Transaction Type | `Non-fee item` |
| `Scoring Category 2` | **Level 2** — Fee/Activity Category | `Money Movement` |
| `Scoring Category 3` | **Level 3** — Activity Category | `ACH` |
| `Scoring Category 4` | **Level 4** — Channel/Subtype | `N/A` |

**Coverage statistics:**
- 431 unique external transaction codes mapped
- 792 total rows (some codes have multiple mappings depending on context)
- 54 of 61 raw data codes are covered (88.5%)
- 7 raw codes are not yet mapped (RTP, FedNow, Wire In/Out, Wire Fee, Internal Transfer, JH Card RoundUp)
