# Phase 1 — Exploration & Setup Plan

## CIQ - Leverage Databricks LLM Capabilities for Initial FI Categorization

**Project:** [Linear Project](https://linear.app/strategycorps/project/ciq-leverage-databricks-llm-capabilities-for-initial-fi-categorization-bcd8c02f129d/overview)
**Owner:** Harrison Hoyos
**Sprint:** Feb 25 – Feb 28, 2026
**Status:** In Progress

---

## Objective

Complete all prerequisite exploration, data access, and infrastructure setup required before building the Product and Transaction Suggestion Models. By the end of this phase we should have:

- Access to Bank Plus raw data in Databricks
- A clear understanding of both categorization taxonomies (Products & Transactions)
- The manual mapping from Bank Plus as our validation ground truth
- Azure Private Link enabled (or ticket raised and tracked)
- A documented evaluation of Databricks AI Functions with a recommendation on which to use

---

## Task 1 — Obtain Access to Bank Plus Raw Data

**Contact:** Sebastian (Data Engineering)

### What to get

| Dataset | Description | Approx. Size |
|---------|-------------|--------------|
| DDA Types | Service Charge Codes + Descriptions | ~80 codes |
| Loan Types | JHA Type + Description | ~60 codes |
| Transaction Codes | Raw transaction codes (if already ingested) | TBD |
| Purpose Codes | Loan purpose mapping (codes 1-11, Consumer vs Business) | 11 codes |
| Class Codes (CFCLAS) | Customer classification (Individual, Business, Corporation, etc.) | ~19 codes |

### Steps

1. Reach out to Sebastian to identify exact table locations in the Databricks raw/bronze layer
2. Confirm read access to the workspace and catalog
3. Run initial exploratory queries — understand data shape, volume, nulls, and quality
4. Document table names, full schemas, and row counts
5. Check if transaction history data is available (not just code catalogs)

### Output

- Table inventory with schema definitions
- Sample data extracts (5-10 rows per table)
- Notes on data quality issues or gaps
- Confirmation that all Bank Plus glossary codes from Notion match what's in Databricks

### Reference

[BankPlus Legend Glossaries (Notion)](https://www.notion.so/BankPlus-Legend-Glossaries-2f6ee9c7060580abb3a2c0bd9c3dca09) — contains the full product catalog, loan types, purpose codes, class codes, account statuses, branches, and relationship types as provided by the bank.

---

## Task 2 — Review Categorization Specifications

**References:**
- [Product Categories (Notion)](https://www.notion.so/Product-Categories-2a9ee9c7060580cb86dffe5fa46d9980)
- [Transaction Categorization (Notion)](https://www.notion.so/Transaction-Categorization-29aee9c706058019b945e43894af3396)

### 2a. Product Categories Taxonomy

Document the full hierarchy — this becomes the LLM's "answer space":

| Level | Field | Owner | Example Values |
|-------|-------|-------|----------------|
| 1 | Line of Business | StrategyCorp | Retail, Business, Wealth Management |
| 2 | Type | StrategyCorp | Deposits, Loans, Services |
| 3 | Category | StrategyCorp | Checking, Savings, CDs, Mortgage loans, HELOCs, Credit Card, Personal loans, Auto loans, Student loans |
| 4 | Sub-category | FI-configurable | Basic, Premium, BaZing, Small Business, Corporate, Analyzed, Non-Profit, Jumbo, Conforming, Cash Back, Travel |
| 5 | Special | FI-configurable | Custodial, Government, <$1M, >$1M, ARM, Fixed, Fixed-to-ARM |

Key notes:
- Levels 1-3 are canonical (defined by StrategyCorp, same across all banks)
- Levels 4-5 are bank-specific (each FI customizes)
- Business template includes **Cash Management Services** (Treasury) with ~20 service sub-categories (ACH, Wire, Lockbox, Payroll, etc.)
- The **core_system_mapping** field maps back to the bank's original product code

### 2b. Transaction Categorization Taxonomy

Document the 4-level hierarchy (Level 5 was descoped) across both blocks:

**Block A — Account Activity (Non-Fee Transactions):**
- Level 1 (Transaction Type): "Account Activity"
- Level 2 (Fee Category): NSF/OD | Money movement | Account operations | Miscellaneous | Unclassified
- Level 3 (Activity Category): ACH | ATM | Check | Internal transfer | Wire | Debit card | Credit Card | Closing | Fraud & stop payment | Memo posting | Interest | Govt & Tax | Integration | Operational
- Level 4 (Channel/Subtype): Direct Deposit | 3rd party/FI owned/Sponsored | Domestic/International | POS

**Block B — Fee Item Transactions:**
- Level 1: "Fee Item Transactions"
- Level 2: NSF/OD | All others | Service Charges | Interchange | Unclassified
- Level 3/4: Money movement sub-categories (ACH, ATM, Wire, Transfers) | Account operations > Miscellaneous

**Critical field — `include_in_scoring`:**
- **Include:** NSF/OD, Money movement and all children
- **Exclude:** Account operations, Miscellaneous, Unclassified

### Output

- Two structured reference documents (markdown or JSON) — one per taxonomy — formatted and ready to paste into LLM prompt context
- List of edge cases and ambiguities to discuss with Sid/Mike
- Mapping of Bank Plus keywords to taxonomy values (e.g., "CK" → Checking, "MM" → Money Market → Savings > Premium, "HSA" → Savings > Government)

---

## Task 3 — Obtain Manual Mapping as Ground Truth

**Contacts:** Sid Ganesh (product mapping), Mike Young (fee/transaction mapping)

### What to request

| Asset | From | Format |
|-------|------|--------|
| Product mapping for DDA types | Sid | Excel/CSV with code → LoB/Type/Category/Sub-category |
| Product mapping for Loan types | Sid | Excel/CSV with code → LoB/Type/Category |
| Fee Category mapping sheet | Mike | [SharePoint link](https://strategycorps-my.sharepoint.com/:x:/p/mike_young/IQAbndd8Wd6YQ6KyUXI5B5MgAQtoYwBDWGiFr3EY5zswnYo) |
| Transaction code mapping | Sid/Mike | If available — raw txn codes → 4-level hierarchy |

### Steps

1. Request all available mappings from Sid and Mike
2. Import into Databricks as reference/lookup tables
3. Analyze coverage: how many of the ~80 DDA codes and ~60 Loan codes have complete mappings?
4. Identify unmapped codes — these are where the LLM adds the most value
5. Cross-reference with the Bank Plus glossary in Notion to confirm consistency

### Output

- Manual mapping files loaded as Databricks tables (or accessible CSVs in workspace)
- Coverage report: X/80 DDA codes mapped, Y/60 Loan codes mapped
- List of discrepancies between manual mapping and Notion glossary (if any)

---

## Task 4 — Enable Azure Private Link on Databricks Workspace

**Contacts:** Hugo, Gonzalo, Tiago (Infrastructure)

### Context

From the project standup meeting:
- Databricks AI Functions (`ai_query`, `ai_categorize`) require Model Serving endpoints
- Model Serving requires **Azure Private Link** to be enabled on the workspace
- Current runtime version is 17 (compatible)
- US East region is confirmed for model serving
- This is the only infrastructure blocker

### Steps

1. Create a ticket/Slack message to the infrastructure team requesting Azure Private Link enablement
2. Specify: needed for Databricks Model Serving endpoints and AI Functions
3. Include alternative path (per Sid): create a new workspace with Private Link pre-enabled if easier
4. Set expectation: this must be resolved before Phase 2 can begin
5. Follow up daily until resolved

### Output

- Ticket created and assigned
- Azure Private Link enabled and verified (or new workspace provisioned)
- Confirmation that Model Serving endpoints are accessible from the workspace

---

## Task 5 — Explore Databricks AI Functions

**Pre-requisite:** Azure Private Link must be enabled (Task 4). Start documentation work in parallel.

### 5a. Research and Document

Compare the two main AI Functions:

| Aspect | `ai_categorize()` | `ai_query()` |
|--------|-------------------|---------------|
| Purpose | Classifies input into predefined categories | Sends free-form prompts to a served model |
| Multi-level hierarchy | May be too rigid — designed for flat classification | Fully flexible — can handle complex prompts with taxonomy context |
| Prompt customization | Limited | Full control over system prompt, context, and few-shot examples |
| Cost | TBD — check per-call pricing | TBD — depends on model and token usage |
| Best for | Simple single-level classification | Our use case (multi-level hierarchical mapping with context) |

Key questions to answer:
- Which foundation models are available as serving endpoints? (DBRX, Llama, Claude, etc.)
- What are token limits per call?
- Can we pass the full taxonomy (~2-3 pages of context) in the prompt?
- What is batch throughput and rate limiting?
- What is the cost estimate for processing ~150 product codes + transaction codes?

### 5b. Hands-on Experiments (once Private Link is live)

1. **Test `ai_categorize`** with 5-10 DDA codes against a flat list of product categories
2. **Test `ai_query`** with the same codes but including the full taxonomy as prompt context + few-shot examples from the manual mapping
3. Compare results on:
   - Accuracy (correct taxonomy assignment)
   - Handling of ambiguous cases (chargeoff codes, public funds, UTMA, etc.)
   - Latency per call
   - Cost per call
4. Test with Loan types as well to validate cross-product generalization

### 5c. Inventory Model Serving Endpoints

1. List all available endpoints in the workspace
2. Note model versions, capabilities, and any restrictions
3. Evaluate if a custom serving endpoint is needed or existing ones suffice for MVP

### 5d. (Optional Bonus) Jack Henry Sandbox Data

**Contact:** Cliff (for API keys)

Per standup discussion:
- Jack Henry represents ~33% of the market
- Sandbox contains default product and transaction codes
- Useful as second training/validation dataset

Steps:
1. Get API keys from Cliff
2. Pull default code catalogs from sandbox
3. Compare with Bank Plus data (also on Jack Henry SilverLake)

### Output

- Documented comparison of `ai_categorize` vs `ai_query` with clear recommendation
- Inventory of available serving endpoints
- Cost estimate for batch processing
- Initial accuracy results from small-scale test (5-10 codes)
- (Optional) Jack Henry default codes extracted

---

## Dependencies & Contacts

| Person | Role | Needed For | Priority |
|--------|------|------------|----------|
| Sebastian | Data Engineering | Raw data access in Databricks | P0 — Blocks everything |
| Sid Ganesh | Project Lead | Manual mapping ground truth, scope decisions | P0 — Blocks validation |
| Mike Young | Business/Domain | Fee categorization mapping sheet | P1 — Needed for transactions |
| Hugo / Tiago / Gonzalo | Infrastructure | Azure Private Link enablement | P0 — Blocks AI Functions |
| Cliff | JH Integration | Jack Henry sandbox API keys | P2 — Nice to have for Phase 1 |
| Herber de Ruijter | Stakeholder | Strategic direction, core system context | As needed |

---

## Known Edge Cases to Investigate

These Bank Plus products don't map cleanly to the taxonomy and will test the LLM's limits:

| Code | Description | Challenge |
|------|-------------|-----------|
| CF/CG/CO/CS | Chargeoff accounts (Fraud/Bankruptcy) | Account states, not products — probably exclude |
| C9 | CONTINENTAL TIRE CK | Sponsor-specific product — sub-category unclear |
| E1/E2/E3 | TUITION RESERVE/MONEY MGR/BANKPLUS TUITION | Educational product — Savings > Government? Or custom? |
| IC | INSURED CASH SW CK | Cash sweep — Checking or Savings? |
| P4 | DEBTOR IN POSSESSION | Bankruptcy legal product — edge case |
| 04/36/38/88/89 | PUBLIC FUNDS variants | Government accounts — not cleanly Retail or Business |
| 31/32 | WMG MMDA variants | Wealth Management deposits — maps to WM LoB |
| F1/F2/F3 | FIDUCIARY accounts | Trust/Fiduciary — Wealth Management? |
| BG/BH | Taxable/Non-Taxable Loan SCM | Unusual loan types — need Mike's input |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Azure Private Link takes > 1 week | Blocks AI Functions exploration entirely | Start documentation and prompt design in parallel; escalate to Sid if delayed |
| Manual mapping incomplete | No ground truth for some codes | Use domain knowledge + Notion specs to create expected mappings for subset |
| Raw data not yet ingested in Databricks | Blocks data exploration | Use Notion glossary data as proxy; work with Sebastian to prioritize ingestion |
| `ai_categorize` too rigid for multi-level hierarchy | May force pivot to `ai_query` only | Design prompts for `ai_query` as primary path; treat `ai_categorize` as experimental |
| Sebastian unavailable | Delays data access | Escalate through Sid; check if Herber has alternative access paths |

---

## Definition of Done

- [ ] Read access to Bank Plus raw tables in Databricks confirmed and documented
- [ ] Both categorization taxonomies converted to structured LLM prompt context documents
- [ ] Manual mapping ground truth obtained, loaded, and coverage analyzed
- [ ] Azure Private Link ticket created, assigned, and tracked
- [ ] `ai_categorize` and `ai_query` evaluated with documented recommendation
- [ ] Available model serving endpoints inventoried with capabilities noted
- [ ] Phase 2 approach decided: which AI function + which model + prompt strategy
- [ ] All findings documented in this plan (updated) or linked notebook

---

## What Comes Next (Phase 2 Preview)

Once Phase 1 is complete, Phase 2 will focus on building the **Product Suggestion Model**:

1. Design the prompt with full taxonomy context + few-shot examples from manual mapping
2. Process all ~80 DDA codes and ~60 Loan codes through the LLM
3. Write suggestions to a staging table with confidence scores
4. Validate against manual mapping — target >= 80% accuracy
5. Iterate on prompt design until accuracy target is met

Phase 3 will repeat the same pattern for the **Transaction Suggestion Model**.
