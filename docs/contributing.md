# Contributing — How to Work in This Repository

## Prerequisites

- Python 3.13+ (managed via `.python-version`)
- [uv](https://docs.astral.sh/uv/) (recommended) or pip for dependency management
- Access to the StrategyCorp Databricks workspace (for AI Functions testing)
- Access to the StrategyCorp Notion workspace (for taxonomy references)

## Setup

```bash
# Clone the repository
git clone <repo-url>
cd ai-onboarding-categorization

# Create virtual environment and install dependencies
uv sync
# or: python -m venv .venv && source .venv/bin/activate && pip install -e .
```

## Repository Layout

```
ai-onboarding-categorization/
├── docs/                    # Project documentation (architecture, data dictionary, taxonomy)
├── data/                    # Raw Bank Plus CSV files (NOT committed to git)
│   └── analysis/            # Data exploration notes
├── taxonomy/                # Categorization taxonomy artifacts
│   ├── *.json               # Machine-readable taxonomy structures
│   ├── *.md                 # Analysis and ambiguity documentation
│   └── data/                # Ground truth mapping files
├── plans/                   # Sprint plans and phase documentation
├── main.py                  # Entry point
└── pyproject.toml           # Project configuration
```

## Conventions

### Data Files

- Raw CSVs go in `data/`. They are listed in `.gitignore` and must not be committed.
- Ground truth mapping files (like the Master Fee Table) go in `taxonomy/data/`.
- Analysis outputs and exploration notes go in `data/analysis/` or `taxonomy/` depending on whether they describe raw data or taxonomy artifacts.

### Documentation

- High-level project documentation goes in `docs/`.
- Task-specific analysis and working notes go alongside the artifacts they describe (e.g., `taxonomy/transaction_categorization_ambiguities.md`).
- Sprint plans go in `plans/`.

### Naming

- Filenames use `snake_case`.
- CSV files retain their original names from the source system (e.g., `CheckingIQ_Deposit_ALL_012626_rerun.csv`).
- Documentation files use descriptive names (e.g., `bankplus_transaction_data_analysis.md`).

### Branching

- `main` — stable, reviewed work
- Feature branches should follow the Linear ticket convention: `harrisonhoyos/ciqeng-NNN-short-description`

## Key Documentation

| Document | Path | Description |
|----------|------|-------------|
| Project overview | [`README.md`](../README.md) | Project goals, structure, contacts |
| System architecture | [`docs/architecture.md`](architecture.md) | How this project fits into CheckingIQ |
| Data dictionary | [`docs/data_dictionary.md`](data_dictionary.md) | Schema for all raw data files |
| Taxonomy reference | [`docs/taxonomy_overview.md`](taxonomy_overview.md) | Product and transaction categorization hierarchies |
| Phase 1 plan | [`plans/phase1_exploration_setup_plan.md`](../plans/phase1_exploration_setup_plan.md) | Current sprint plan with tasks and contacts |

## Working with Data

### Adding New Raw Data

1. Obtain the CSV extract from Sebastian or the Databricks Bronze layer
2. Place the file in `data/` with its original filename
3. Update `docs/data_dictionary.md` if the schema differs from existing files
4. Run an initial exploration to verify row counts, column types, and nulls

### Adding New Taxonomy Artifacts

1. Extract the taxonomy from its Notion source page
2. Create a structured JSON file in `taxonomy/` for machine-readable use
3. Document any ambiguities in a corresponding `*_ambiguities.md` file
4. Update `docs/taxonomy_overview.md` with the new taxonomy reference

### Adding Ground Truth Mappings

1. Obtain the mapping file from Sid (products) or Mike (transactions/fees)
2. Place the file in `taxonomy/data/`
3. Run a coverage analysis: how many raw codes are covered by the mapping?
4. Document gaps and discrepancies in the analysis files

## Tracking Work

- All work is tracked in [Linear](https://linear.app/strategycorps/) under the **CIQ - Engineering** team
- Issues are linked to the project: *CIQ — Leverage Databricks LLM Capabilities for Initial FI Categorization*
- Use the checklist in each phase plan to track task completion
