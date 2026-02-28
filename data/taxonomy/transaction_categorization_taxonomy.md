# Transaction Categorization Taxonomy

**Source:** [Transaction Categorization (Notion)](https://www.notion.so/Transaction-Categorization-29aee9c706058019b945e43894af3396)  
**Ground Truth:** Master Fee Table (BankPlus — Jack Henry SilverLake)  
**Last Updated:** 2026-02-26

---

## Purpose

When a new financial institution (FI) is onboarded onto CheckingIQ / MonetizeIQ, their raw transaction and fee codes must be normalized into StrategyCorp's canonical taxonomy. This taxonomy drives:

- **Dashboard reporting** — non-interest income breakdowns, fee revenue cards
- **Customer scoring** — primacy indicators, offer monitoring
- **Scalability** — a single classification structure that works across all FIs regardless of core banking system

### AI Model Goal

The AI model should **pre-map ~80% of a bank's transaction codes** into this taxonomy, leaving ~20% as "Unclassified" for the banker to manually review. A typical FI has ~300 transaction codes. If the model maps 240 and leaves 60 unclassified, it dramatically reduces onboarding effort.

When the model **cannot confidently categorize** a transaction code, it must be placed in **Unclassified** — never force-fitted into a wrong category. The banker will see a dashboard showing "X mapped / Y unmapped" and can review from there.

When **new transaction codes** are added post-onboarding, they go into Unclassified automatically and trigger an exception report for the FI user to classify.

---

## Hierarchy Overview

The taxonomy has **4 active levels** (Level 5 — Merchant Category — is descoped).

| Level | Purpose | Example |
|-------|---------|---------|
| **Level 1 (Category 1)** | Differentiates fee vs non-fee transactions | "Non-fee item" vs "Fee item" |
| **Level 2 (Category 2)** | Non-interest income calculations and reporting; include/exclude from scoring | "Money movement", "NSF/OD", "Service Charges" |
| **Level 3 (Category 3)** | Detailed scoring and offers monitoring | "ACH", "ATM", "Check", "Wire" |
| **Level 4 (Category 4)** | Channel / subtype granularity | "Direct Deposit", "3rd party (foreign)", "POS" |

The taxonomy splits into **two independent classification trees** (blocks):

- **Block A — Non-fee item (Account Activity) Transactions** — the actual banking activities
- **Block B — Fee item Transactions** — fee-charging events that generate non-interest income

---

## How Block A vs Block B Is Determined

A single banking event can generate **two independent transaction records** with **separate transaction codes**:

1. **The account activity** (Block A) — e.g., a $50 ATM withdrawal
2. **The fee charge** (Block B) — e.g., a $3.00 ATM fee assessed for that withdrawal

In the core banking system these are **independent items with separate transaction codes**. The distinction is made by:

- **Transaction code naming convention** — fee item codes typically indicate they are fees in their description (e.g., "ATM Service Charge" vs "ATM Withdrawal")
- **Fee Item Description / Internal Fee Item Code fields** — fee transactions have values in these columns; non-fee transactions show "N/A"
- The model should use the **transaction description text** as the primary signal for classification

---

## Block A — Non-fee item (Account Activity) Transactions

These are the actual banking activities performed by or on behalf of the customer. They are used for customer scoring, offer monitoring, and activity reporting.

### Scoring Rule

- **Include in customer scoring:** NSF/OD, Money movement (and all children)
- **Do NOT include in customer scoring:** Account operations (and all children), Misc, Unclassified

---

### Level 2: NSF/OD

> Bounced check or overdraft events (the activity itself, not the fee)

**Include in scoring:** Yes

**Common transaction names:**
- NSF Item Paid
- OD Balance Credit
- ODP Payment
- Return Item Credit
- Returned Deposited Items / Returned Cashed Items

---

### Level 2: Money movement

> Transfers, withdrawals, deposits — all forms of money moving in/out of accounts

**Include in scoring:** Yes

#### Level 3: ACH

> Automated Clearing House transactions

**Level 4 options:** Direct Deposit (if available)

**Common transaction names:**
- ACH Credit / ACH Debit
- ACH Auto Transfer Credit / Debit
- ACH Chargeback
- ACH Credit Back Item
- Single ACH credit/debit transaction

#### Level 3: ATM

> ATM deposits, withdrawals, and transfers

**Level 4 options:** 3rd party (foreign), FI owned, Sponsored (e.g., Allpoint)

**Common transaction names:**
- ATM Withdrawal / ATM Deposit
- ATM Transfer DDA to Savings / Savings to DDA
- ATM Credit Reversal / Debit Reversal
- ITM Deposit / ITM-ATM Deposit

#### Level 3: Check

> Check-based transactions

**Common transaction names:**
- Check (On Us) / Check (Regular Inclearings) / Check (ForcePay)
- Check deposit credit
- Check 21 substitute
- Check clearing/payment
- Official Check
- Contract Collection Check
- Misc check activity

#### Level 3: Transfers & Payments

> Account-to-account transfers, loan payments, bill pay, P2P

**Common transaction names:**
- Transfer from/to DDA, Savings, CD, Loan, G/L
- Automatic Loan Payment
- Epay Credit / Debit
- Zelle Credit / Debit
- Telephone Transfer Credit / Debit
- Voice Response Credit / Debit
- In Person Transfer
- Fresh Start Advance / AFT Payment
- Credit card payment, Credit line payment
- IRA Transfer
- Safe Deposit Rental Payment
- Debt Protection Payment

#### Level 3: Deposits

> Direct deposits and other credit entries to accounts

**Common transaction names:**
- Deposit (general)
- Mobile Deposit
- Savings Deposit / Savings Force Pay Deposit
- HSA Contribution (Current Year / Prior Year / Rollover)
- Account Funding Transaction Credit
- POD Credit/Deposit
- Dividend distribution
- Loan disbursement
- Contract Collection Deposit

#### Level 3: Withdrawals

> Cash withdrawals and other debit entries from accounts

**Common transaction names:**
- MMD/Savings/Club Withdrawal
- HSA Distribution / Transfer Withdrawal / Direct Transfer
- Descriptive Debit (EFT) / Force Pay Debit
- Automatic Cash Advance
- POD Bank Initiated Debit
- Single item debit / Single automated debit

#### Level 3: Wire

> Domestic and international wire transfers

**Level 4 options:** Domestic, International

**Common transaction names:**
- Wire Transfer Credit / Debit
- Foreign Wire (Incoming / Outgoing) — various methods (Callback, In Person, Internet)
- Foreign Wire Settlement In / Out
- Domestic wire (Outgoing)
- Int Bnking doing a single/repeat wire

#### Level 3: Debit Card

> Debit card point-of-sale and recurring transactions

**Level 4 options:** POS (point of sale)

*Note: Used in interchange income calculations. All card transactions (PIN, signature, pre-authorized, recurring) map here.*

**Common transaction names:**
- POS Credit/Debit - DDA / Savings
- POS Debit-PIN-DDA / POS Debit-Signature-DDA
- POS Pre-Authorized Debit
- POS Recurring Debit

#### Level 3: Credit Card

> Credit card transactions

**Level 4 options:** POS (point of sale)

---

### Level 2: Account operations

> Internal bank operations — NOT included in customer scoring

#### Level 3: Closing

**Common transaction names:**
- Closing entry (create check / deposit funds / deposited / zero balance / credit balance / credit transfer / funds transfer)
- Closing Withdrawal
- Closing Entry: Accrued int paid / Increase YTD int / Reduce accrued
- Christmas Club Closing Entry
- HSA Death Distribution

#### Level 3: Fraud & Stop Payment

**Common transaction names:**
- Chargeback / Chargeback Item
- Check stop payment
- Check fraud adjustment
- Check hold placement
- Stop Payment Order
- Stop Payment Returned Item

#### Level 3: Memo Posting

> Temporary holds, pending transactions, and memo-level accounting entries

**Common transaction names:**
- Pre-auth Memo Hold / Clear Pre-Auth Memo Hold
- Memo Credit / Memo Debit

#### Level 3: Interest

**Common transaction names:**
- Interest Deposit / Interest earned / Interest charged
- CD Interest
- Interest Rate Change
- Interest Transfer Credit / Debit
- Interest Withheld (Checking / Savings / CD / etc.)
- Increase/Decrease Accrued Interest
- Increase/Decrease YTD Interest Paid
- Bond/CD interest
- Bonus/Annual Cash Back
- R360 interest adjustments
- Print Interest Check

#### Level 3: Govt. & Tax

**Common transaction names:**
- Federal withholding / State withholding
- Federal/State Interest Withheld
- Increase/Decrease YTD Fed/State Withholding
- Garnishment
- Levy

#### Level 3: Integration

> Internet/online banking platform activity logging (inquiries, alerts, downloads — not money-moving transactions)

**Common transaction names:**
- Int Bnking current day inquiry
- Int Bnking history inquiry
- Int Bnking prior day inquiry
- Int Bnking view of statement
- Int Bnking downloading file
- Int Bnking adding a stop
- Int Bnking inquiring on a stop
- Int Bnking E-mail alert credit
- Int Bnking text alert credit
- Insured Cash Sweeps (ICS) Debit / Deposit
- Int to Bal/Raise YTD (EFT Only)

#### Level 3: Operational

**Common transaction names:**
- Encoding Error Credit/Debit Adjustment
- Correction to previous deposit
- Contract Collection Reversal
- Debit/Credit Accrual Adjustment
- Credit Back Item
- Do Not Use - Translation Code
- Quick Statement Per Page

---

### Level 2: Misc

> Business banking, custom accounts, cash management, investment sweeps, and other specialized transactions that don't fit standard categories. Not included in customer scoring.

*Note: This is effectively "Business Banking & Custom" per the ground truth naming.*

**Common transaction names:**
- 3rd Party Sweeps Credit / Debit
- Account Reconciliation Credit
- Accounts Payable Payment
- Business Mobile Deposit
- Cash Management Credit / Debit
- Investment Sweep From/To DDA / Savings
- Investment purchase / sale proceeds
- Mutual fund investment / sale
- Electronic Data Interchange (EDI) credit / debit
- ZBA credit/debit transfer
- RDC Deposit
- Syndication Credit / Debit
- Trade-related credit / debit
- Trust account activity
- Dealer disbursement credit / debit
- Lease security transactions
- Stockholder Dividend Deposit
- Int Bnking ACH batch / file upload / items
- Int Bnking ARP file upload
- Int Bnking uploading pos pay / recon

---

### Level 2: Unclassified

> Transaction codes that the model cannot confidently map to any other category. These are flagged for manual banker review.

---

## Block B — Fee item Transactions

Fee-charging transactions that generate **non-interest income** for the FI. These are the fee counterparts to Block A activities.

### Why This Structure Exists

The majority of non-interest (fee) income in US banking comes from three sources:
1. **NSF/OD fees** — charges for bounced checks and overdrafts
2. **Service Charges** — monthly account maintenance fees
3. **Interchange** — debit card usage fees charged to retailers

These three are broken out as top-level Level 2 categories because they represent the biggest revenue lines. Everything else is grouped under **"All Others"** because those fees individually don't generate significant revenue. This structure directly maps to how StrategyCorp presents fee income breakdowns in the UI reporting cards.

### Level Nesting Difference from Block A

Block B has one extra nesting level compared to Block A for the "All Others" bucket:

```
Block A: Level 1 → Level 2      → Level 3 → Level 4
         Non-fee item → Money movement → ACH     → Direct Deposit

Block B: Level 1 → Level 2      → Level 3         → Level 4
         Fee item → All Others   → Money movement  → ACH
```

This shift is intentional — "All Others" is a Level 2 grouping for fee reporting, and the sub-categories beneath it mirror Block A's structure one level deeper.

---

### Level 2: NSF/OD

> Fees charged for bounced checks and overdrafts

**Common transaction names:**
- Insufficient Funds Charge
- Overdraft Item Charge / Overdraft Fee / Overdraft Interest Charge
- Continuous Overdraft Charge
- Non-Sufficient Funds Fee - Items Returned
- Overdraft fee waiver / Overdraft Fee Reversal
- Refund NSF Paid/Return Fee (STD/YTD)
- Refund OD Accrual Fee (STD/YTD)
- Uncollected Funds Charge
- Returned/bounced check / Return Check / Return Item Fee / Return Check Fee
- Reverse NSF/OD Item Charge

---

### Level 2: All Others

> All fees that are NOT NSF/OD, Service Charges, or Interchange. Grouped here because they don't individually generate significant revenue.

#### Level 3: Money movement

> Fees charged for money-moving activities

##### Level 4: ACH

**Common transaction names:**
- ACH Chargeback Fee

##### Level 4: ATM

**Common transaction names:**
- ATM Service Charge / ATM Transaction Charge / ATM Fee
- ATM Service Charge Reversal
- ATM fee refund / ATM Fee Reimbursement
- Balance inquiry fee at foreign ATM
- Withdrawal at non-BankPlus ATM
- Bonus/Annual ATM Surcharge Refund
- R360 ATM Surcharge Adjustment / Refund
- Bonus/Annual Reward ATM Adjust

##### Level 4: Wire

**Common transaction names:**
- Wire Transfer Fee
- Foreign Wire Fee (Incoming / Outgoing)
- Wire transfer charge

##### Level 4: Transfers & Payments

**Common transaction names:**
- FX transaction fee / Currency Exchange Fee
- Voice Response Transaction Fee
- Redeposit Fee
- Telephone Transfer Fee

#### Level 3: Account operations

> Misc operational fees

##### Level 4: Misc

**Common transaction names (general account operations fees):**
- Chargeback Fee / Chargeback Item Fee
- Check image/order/stop payment fees
- Close Account Fee
- Collection Item Fee / Counter Check Fee
- Credit Back Fee
- Dormant Fee / Monthly Dormant Fee
- Escheated Account Fee
- Excess MMD transaction charge
- Fax Per Page / Image Fee
- Int Bnking Bill Pay (cycle/enroll/item fee)
- Int Bnking E-mail/text alert fee
- Lost Debit Card Fee / Debit Card Fee
- Paper Statement Charge / Statement Fee
- Account research fee / Research Per Hour/Page
- Safe Deposit Box (Drilling/Late/Re-Key) Fee
- Return Mail Processing Fee
- Stop Payment Charge
- Bad Address Fee
- Multiple Statement Copy/Cycle Fee
- Notary Fee
- Sales Tax on Service Charge
- HB Transaction Fee

**Common transaction names (business/commercial):**
- Account Analysis Bill Fee / Charge
- Account Reconciliation
- ACH Block
- Daily Uncollected Balance Fee
- Check verification service / Positive Pay
- Sweep Transaction Charge
- Trading commission / Brokerage Commission
- Transit Fee in Service Charge
- R360 Non-Qualification Fee
- Securities custody fee / Custody Fee

---

### Level 2: Service Charges

> Monthly account maintenance fees and recurring service charges

**Common transaction names:**
- Service Charge (general)
- Account Service Fee
- Monthly service charge
- Annual account fee / Annual Fee
- Base/Balance/Credit/Debit/Item/Local/On Us Fee in Service Charge
- Bank Admin Fee in Service Charge
- Box rental fee / Safe Deposit Box Annual Rental Fee
- Int Bnking Service Charge
- Per Item Service Charge
- Minimum Fee Debit to S/C
- Fee reversal/waiver / Service Charge Reversal
- R360 Fee Adjustment Credit/Debit / Refund
- Balance Credit in Service Charge
- Rewards Service Charge Refund

---

### Level 2: Interchange

> Debit card usage service fees charged to retailers when they accept cards as a form of payment. Revenue from card-present and card-not-present transactions.

*Note: No common transaction names observed in ground truth data — this category may be populated from a different data source (card network settlement data).*

---

### Level 2: Unclassified

> Fee transactions that cannot be confidently mapped. Flagged for banker review.

---

## CD Transactions

CD (Certificate of Deposit) transactions exist in the ground truth data but are mapped to **Account operations** at Level 2 and are **not included in customer scoring**. These cover IRA operations, CD interest, CD closing/redemption, memo entries, and other CD-specific accounting.

The model should classify CD-related transaction codes under **Block A > Account operations** with no further Level 3/4 breakdown (N/A).

---

## Classification Rules for the AI Model

1. **First classify into Block A (Non-fee item) or Block B (Fee item)** based on the transaction description. Fee items typically contain words like "fee", "charge", "surcharge", "penalty", "service charge", "reversal" (of a fee).

2. **Then classify down the hierarchy** (Level 2 → Level 3 → Level 4) within the assigned block.

3. **Refunds/Reversals of fees:** Any transaction that is a "Refund" or "Reversal" of a fee (e.g., "NSF Fee Refund" or "Refund NSF/OD Fee") must be classified under **Block A > Money movement > Deposits**, as this is money returned to the customer's account.

4. **If the transaction code naming convention does not match any provided category names, map to Unclassified** in the appropriate block. Do not guess.

5. **Each transaction code maps to exactly one path** in the taxonomy tree. There is no multi-label classification.

6. **Block A and Block B are independent trees.** The same semantic concept (e.g., "ACH") can appear in both blocks at different hierarchy levels. The block assignment determines which tree to traverse.

7. **`include_in_scoring`** only applies to Block A:
   - `true` for NSF/OD and Money movement (all children)
   - `false` for Account operations, Misc, Unclassified
   - Block B does not have scoring rules — its purpose is fee income reporting

---

## Output Schema

For each transaction code, the model should produce:

| Field | Description | Example (Non-fee item) | Example (Fee item) |
|-------|-------------|-------------------|---------------|
| `category_1` (Level 1) | Block assignment | Non-fee item | Fee item |
| `category_2` (Level 2) | Primary category | Money movement | All others |
| `category_3` (Level 3) | Sub-category | ACH | Money movement |
| `category_4` (Level 4) | Detail | Direct Deposit | ACH |
| `include_in_scoring` | Scoring flag (Block A only) | true | N/A |
| `credit_debit` | Transaction direction | Credit | Debit |
