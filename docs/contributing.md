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
├── data/
│   ├── bank-plus-data/
│   │   ├── raw/             # Raw CSVs from Bank Plus (NOT committed to git)
│   │   └── source-of-truth/ # Master Fee Table ground truth files
│   ├── results/             # Deprecated — results stored in Unity Catalog
│   └── taxonomy/            # Taxonomy documentation (md files only)
├── notebooks/               # Databricks notebooks (01–04)
├── main.py                  # Entry point
└── pyproject.toml           # Project configuration
```

## Conventions

### Data Files

- Raw CSVs go in `data/bank-plus-data/raw/`. They are listed in `.gitignore` and must not be committed.
- Ground truth mapping files (like the Master Fee Table) go in `data/bank-plus-data/source-of-truth/`.
- Taxonomy documentation (markdown) goes in `data/taxonomy/`.
- All pipeline results are persisted to Unity Catalog, not locally.

### Documentation

- High-level project documentation goes in `docs/`.
- Sprint plans go in `docs/plans/`.

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
| Phase 1 plan | [`docs/plans/`](plans/) | Sprint plans and phase documentation |

## Working with Data

### Adding New Raw Data

1. Obtain the CSV extract from Sebastian or the Databricks Bronze layer
2. Place the file in `data/` with its original filename
3. Update `docs/data_dictionary.md` if the schema differs from existing files
4. Run an initial exploration to verify row counts, column types, and nulls

### Adding New Taxonomy Artifacts

1. Extract the taxonomy from its Notion source page
2. Create a markdown file in `data/taxonomy/` for LLM prompt context
3. Update `docs/taxonomy_overview.md` with the new taxonomy reference

### Adding Ground Truth Mappings

1. Obtain the mapping file from Sid (products) or Mike (transactions/fees)
2. Place the file in `data/bank-plus-data/source-of-truth/`
3. Run notebook `01_prepare_data` to normalize and load into Unity Catalog
4. Run notebook `04_evaluate_accuracy` to check coverage against existing predictions

## Tracking Work

- All work is tracked in [Linear](https://linear.app/strategycorps/) under the **CIQ - Engineering** team
- Issues are linked to the project: *CIQ — Leverage Databricks LLM Capabilities for Initial FI Categorization*
- Use the checklist in each phase plan to track task completion
