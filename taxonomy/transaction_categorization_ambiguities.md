# Transaction Categorization — Ambiguities & Discussion Points

**Source:** [Transaction Categorization (Notion)](https://www.notion.so/Transaction-Categorization-29aee9c706058019b945e43894af3396)
**Date:** 2026-02-25

---

## Structural Ambiguities

### 1. Block B Level Nesting Is Shifted Compared to Block A

In **Block A**, the hierarchy is:
```
Level 1 → Level 2 → Level 3 → Level 4
Account Activity → Money movement → ACH → Direct Deposit
```

In **Block B**, the same logical concepts appear but nested one level deeper:
```
Level 1 → Level 2 → Level 3 → Level 4
Fee Item Transactions → All others → Money movement → ACH
```

"Money movement" is Level 2 in Block A but Level 3 in Block B. "ACH" is Level 3 in Block A but Level 4 in Block B. This means the **same semantic concept occupies different hierarchy levels depending on the block**.

**Impact on LLM:** The model needs to understand that the mapping rules are block-specific. A raw transaction code for "ACH fee" should map to Block B > All others > Money movement > ACH, not to Block A's ACH path.

**Question for Sid/Mike:** Is this intentional? Should the LLM treat Block A and Block B as completely independent classification trees?

---

### 2. `include_in_scoring` Not Defined for Block B

Block A has explicit scoring inclusion rules:
- **Include:** NSF/OD, Money movement (and children)
- **Exclude:** Account operations, Miscellaneous, Unclassified

Block B has **no scoring rules defined** in the Notion spec.

**Question for Sid/Mike:** Does `include_in_scoring` apply to Fee Item Transactions at all? If yes, which fee categories should be included? If not, should the field be NULL or FALSE for all Block B rows?

---

### 3. Level 5 — Descoped but Structurally Present

Level 5 ("Merchant Category") is struck through in the Notion table for Debit card and Credit Card under Block A. It's listed as descoped.

However, the column still appears in Block B's header row (not struck through).

**Question for Sid/Mike:** Is Level 5 completely descoped for both blocks? Should the silver model schema drop this column, or keep it as NULL for future use?

---

## Category-Level Ambiguities

### 4. "All others" in Block B Is a Catch-All with Sub-structure

Block B Level 2 has "All others" which then breaks down into Money movement and Account operations at Level 3. This is unusual because "All others" implies a residual/catch-all, but it actually contains specific structured sub-categories.

**Question:** When a fee transaction doesn't fit NSF/OD, Service Charges, or Interchange, does it always go to "All others"? Or is "All others" only for fee transactions related to money movement and account operations?

**RESOLVED (Mike, 2026-02-26):** Yes, "All others" is the catch-all for everything outside the big three revenue categories (NSF/OD, Service Charges, Interchange). The reason those three are top-level is that they represent the majority of non-interest income in US banking. "All others" contains fees that individually don't generate significant revenue. This structure maps directly to how StrategyCorp presents fee income breakdowns in the UI reporting cards.

---

### 5. NSF/OD Appears in Both Blocks

NSF/OD is a Level 2 category in **both** Block A and Block B. A single bank event (e.g., an overdraft) could generate:
- An Account Activity entry (the overdraft event itself — Block A)
- A Fee Item Transaction entry (the OD fee charged — Block B)

**Question for Sid/Mike:** When classifying a raw transaction code, how do we determine which block it belongs to? Is it based on the transaction code itself, the presence of a fee amount, or some other field in the raw data?

**RESOLVED (Mike, 2026-02-26):** Block A and Block B are determined by **separate transaction codes** in the core banking system. A single banking event (e.g., ATM withdrawal) generates two independent records: one for the activity ($50 withdrawal — Block A) and one for the fee ($3.00 ATM fee — Block B). The transaction codes used for assessing fees typically indicate they're fee items in their naming convention. In the Master Fee Table, fee transactions have values in the "Fee Item Description" and "Internal Fee Item Code" columns, while non-fee transactions show "N/A" in those fields.

---

### 6. ATM Level 4 Options Are Ambiguous for Fee vs. Non-Fee

In Block A, ATM has three Level 4 subtypes: "3rd party (foreign)", "FI owned", "Sponsored (e.g., Allpoint)".

In Block B under All others > Money movement > ATM, there are **no Level 4 subtypes**.

**Question:** For ATM fees, should the LLM attempt to classify the ATM type (foreign/owned/sponsored) at Level 4, or is that only relevant for non-fee ATM activity?

---

### 7. "Integration" and "Operational" Under Account Operations Are Vague

These Level 3 categories have no Level 4 breakdown and no further description:
- **Integration** — What does this mean? System integration events? Third-party platform transactions?
- **Operational** — How does this differ from "Miscellaneous"?

**Impact on LLM:** Without clear definitions, the model will struggle to distinguish between Integration, Operational, and Miscellaneous. This could become a "dumping ground" that reduces classification accuracy.

**Question for Sid/Mike:** Can we get definitions or examples for these categories? If they're rarely used, should they be merged?

**PARTIALLY RESOLVED (Mike, 2026-02-26):** Mike was unclear on the "Integration" label specifically and asked for a follow-up call. However, reviewing the ground truth data reveals that **Integration** maps to internet/online banking platform activity logging (inquiries, alerts, downloads, statement views — "Int Bnking" prefixed codes), and **Operational** maps to administrative corrections and system adjustments (encoding errors, accrual adjustments, translation codes). **Miscellaneous** (at Level 2) is used for business banking, cash management, investment sweeps, and other specialized transactions. Mike confirmed the model should use the common names provided in each category to match transaction codes. If the model can't match a code, it goes to **Unclassified** — not Miscellaneous or Operational.

**Key clarification from Mike:** The goal is 80% automated mapping. Codes the model can't match should be Unclassified, not force-fitted. The banker reviews those manually.

---

### 8. Debit Card vs. Credit Card — Where Do Multi-Channel Transactions Go?

Both Debit card and Credit Card have "POS (point of sale)" as their only Level 4 option. But transactions can occur outside POS (e.g., online, recurring bill pay, phone order).

**Question:** Are non-POS debit/credit card transactions classified differently? Or does "POS" here function as a catch-all for all card-present and card-not-present transactions?

---

### 9. "Memo posting" Is An Operational Concept, Not a Transaction Type

Memo posting typically refers to a temporary hold or pending transaction (e.g., a debit card authorization that hasn't settled yet). It's more of a **transaction state** than a **transaction type**.

**Question:** Does "Memo posting" refer to:
- (a) The act of posting a memo/hold (an operational event), or
- (b) A specific type of transaction code that banks use for temporary entries?

This distinction matters because the same underlying transaction (e.g., a debit card purchase) could be classified as "Debit card > POS" AND as "Memo posting" at different points in its lifecycle.

---

## Data Model Considerations

### 10. Transaction Code → Two Possible Blocks

A single raw transaction code from a bank could potentially map to either Block A or Block B (or both, as with NSF/OD). The taxonomy doesn't specify how to make this determination.

**Recommendation:** The raw data likely has a field (amount sign, fee flag, transaction type indicator) that distinguishes fee from non-fee entries. This should be identified in Task 1 when exploring the Bank Plus raw data.

---

## Summary of Open Questions (Priority Order)

| # | Question | Ask | Priority | Status |
|---|----------|-----|----------|--------|
| 1 | How to determine Block A vs Block B from raw data? | Sid/Mike | P0 | **RESOLVED** — separate transaction codes; fee items identified by naming convention and Fee Item Description field |
| 2 | Does `include_in_scoring` apply to Block B? | Sid | P0 | Open |
| 3 | Is the level nesting shift between blocks intentional? | Sid | P1 | **RESOLVED** — intentional; "All others" is a Level 2 fee-reporting grouping |
| 4 | Definitions for "Integration" and "Operational"? | Mike | P1 | **PARTIALLY RESOLVED** — ground truth clarifies both; Mike wants follow-up call on "Integration" |
| 5 | Is Level 5 fully descoped for both blocks? | Sid | P2 | Open |
| 6 | What does "Memo posting" cover exactly? | Mike | P2 | Open |
| 7 | Does "POS" cover all card transactions or only card-present? | Mike | P2 | Open |
| 8 | Should ATM subtypes apply to fee ATM transactions? | Mike | P2 | Open |
