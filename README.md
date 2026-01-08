# AntiPatternLoggingML

A toolkit to collect, extract, and analyze logging usage and logging-related code snippets from GitHub repositories — focused on finding logging anti-patterns in machine learning code.

The repository provides a CLI (implemented in `main.py`) with commands to:
- collect repository metadata (archived/accessibility) from CSV lists of repos
- merge collected metadata files
- clone repositories
- convert Jupyter notebooks to Python
- extract Python files that contain logging/library calls
- clean leading comments before import statements
- build a JSON dataset of logging snippets
- analyze and summarize logging datasets
- sample unique functions and snippets by library and log level
- run an LLM-based logging smell analysis

This README explains setup, usage examples for each CLI command, and tips for working with the pipeline.

---

## Requirements

- Python 3.10 or newer
- Recommended: create and activate a virtual environment

Install core dependencies (approximate list used by the project):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install pandas gitpython nbconvert nbformat openpyxl
```

If you prefer, create a `requirements.txt` with these packages and install using `pip install -r requirements.txt`.

Note: the project uses `pandas` to read/write CSV/Excel files and `GitPython` (`git`) to clone repositories.

---

## Project layout

- `main.py` - CLI entrypoint. Implements multiple subcommands (see Usage).
- `data/` - default data folder (configured in `config/constant.py`).
- `data_collection/` - modules to collect repos, extract logging files, analyze datasets, and sample snippets.
- `util/` - logging and utility helpers.
- `logs/` - default log file location (`logs/app.log`).

Open `config/constant.py` if you want to change the default paths.

---

## Quick usage

Run a CLI command like this (PowerShell examples):

```powershell
# show help for the CLI
python main.py -h

# show help for a specific command
python main.py collect -h
```

All commands accept options; each command has sensible defaults defined in `main.py` (many default to paths inside `data/` and `logs/app.log`).

### Common commands and examples

1) Collect GitHub repository metadata

```powershell
python main.py collect --data_folder data --log_file logs/app.log
```

This will find `*.csv` files inside `data/`, read repository names, query GitHub (via `data_collection.get_repo_infos`) to collect `accessible` and `archived` info, and write per-file outputs suffixed with `_with_archived.csv`.

2) Merge archived results

```powershell
python main.py merge_archived --data_folder data --output_file merged_archived_dataset.csv
```

Concatenates all `*_with_archived.csv` files, removes duplicates, and writes a merged CSV.

3) Clone repositories from merged CSV

```powershell
python main.py clone_repos --input_file data\merged_archived_dataset.csv --output_dir data\cloned_repos
```

Only clones repositories listed in the CSV. If the CSV contains `accessible` or `archived` columns, the CLI filters to `accessible == True` and `archived == False`.

4) Convert notebooks to Python files

```powershell
python main.py convert_notebooks --root_dir data\cloned_repos
```

Searches `root_dir` for `.ipynb` files and produces `.py` exports alongside them.

5) Extract Python files with logging/library calls

```powershell
python main.py extract_logging_files --root_dir data\cloned_repos --output_dir data\logging_files
```

Uses AST helpers to identify files with library/logging calls and copies them (preserving repo-relative structure) into `data/logging_files`.

6) Remove header comments before imports

```powershell
python main.py clean_comments --root_dir data\logging_files
```

Removes comment lines that occur before the first import statement in each `.py` file — useful to reduce noise before parsing.

7) Create a JSON dataset of logging snippets

```powershell
python main.py create_logging_json_dataset --root_dir data\logging_files --output_file data\logging_dataset.json
```

Walks `root_dir`, extracts logging-related functions/snippets via `data_collection.ast_helpers.extract_all_logging_files` and writes a structured JSON dataset.

8) Analyze the logging dataset (write metrics to CSV)

```powershell
python main.py analyze_logging_dataset --json_path data\logging_dataset.json --csv_path data\logging_dataset_metrics.csv
```

9) Filter the logging dataset (keep only relevant fields/functions)

```powershell
python main.py filter_logging_dataset --input_json data\logging_dataset.json --output_json data\logging_dataset_filtered_function.json
```

10) Summarize the filtered dataset

```powershell
python main.py summarize_logging_dataset --json_path data\logging_dataset_filtered_function.json --csv_path data\logging_dataset_summary.csv
```

11) Summarize unique functions per logging library and log level

```powershell
python main.py summarize_unique_functions --json_path data\logging_dataset_filtered_function.json --csv_path data\logging_dataset_unique_functions.csv
```

12) Sample snippets by library and level

```powershell
python main.py sample_snippets --input_csv data\logging_dataset_unique_functions.csv --output_csv data\logging_dataset_sampled_snippets.csv
```

13) Run LLM logging smell analysis (uses module `data_collection.llm_logging_smell_analysis`)

```powershell
python main.py llm_logging_smell_analysis
```

This command currently delegates to the `cli_llm_logging_smell_analysis` function; check `data_collection/llm_logging_smell_analysis.py` for configuration and model usage details.

---

## Configuration & paths

Defaults for data and other paths are defined in `config/constant.py`. If you want to change where data or logs are stored, update that file or pass explicit CLI arguments to the commands.

Logging output (both console and file) is managed with `util.log.setup_logging`; logs are written to `logs/app.log` by default.

---

## Troubleshooting

- Cloning failures: public repositories should clone via HTTPS. If some repos require credentials, configure Git authentication (SSH keys or a credential helper / PAT) and/or modify the `clone_repos` implementation to include credentials.

- GitHub API rate limits: the `collect` command may query GitHub and could hit rate limits. Consider using authentication or run the collection in batches.

- Missing packages: install the packages listed in the Requirements section.

- Large datasets: some operations iterate over many repos/files — run them on a subset first to validate the pipeline.

---

## Development & Contribution

- Code is organized under `data_collection/` (domain logic) and `util/` (helpers).
- Add small unit tests for core helpers (AST helpers, dataset filters) and run them before submitting PRs.

If you'd like, I can also:
- add a `requirements.txt` or `pyproject.toml` for reproducible installs
- add example small datasets and a quick smoke-test script
- add more detailed docs for `data_collection/llm_logging_smell_analysis`

---

## License & contact

This repository does not include a license file; add an appropriate `LICENSE` file if you plan to share the project.

For questions or help, open an issue or contact the maintainer.

