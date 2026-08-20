# AntiPatternLoggingML

A toolkit to collect, extract, and analyze logging usage and logging-related code snippets from GitHub repositories, with a focus on logging anti-patterns in machine learning code.

The repository provides a CLI in `main.py` to:
- download and filter repository datasets from Hugging Face
- scan repositories with GitHub code search for framework imports
- collect repository metadata such as archived/accessibility status
- merge collected metadata files
- clone repositories
- convert Jupyter notebooks to Python
- extract Python files that contain logging or library calls
- clean leading comments before import statements
- build a JSON dataset of logging snippets
- analyze and summarize logging datasets
- sample unique functions and snippets by library and log level
- run an LLM-based logging smell analysis

This README documents the current workflow and the commands implemented in `main.py`.

---

## Requirements

- Python 3.10 or newer
- Recommended: use a virtual environment or conda environment

Install project dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If you install packages manually, the project commonly relies on:
- `pandas`
- `gitpython`
- `nbconvert`
- `nbformat`
- `openpyxl`
- `datasets` / parquet support for Hugging Face dataset access
- `requests`

Some commands also rely on third-party APIs:
- GitHub API tokens for repository/code search workflows
- OpenAI API access for `llm_logging_smell_analysis`

---

## Project layout

- `main.py` - CLI entrypoint
- `data/` - default data folder configured in `config/constant.py`
- `data_collection/` - dataset download, repository scanning, extraction, analysis, and sampling modules
- `util/` - logging and helper utilities
- `logs/` - default log file location (`logs/app.log`)

---

## Quick usage

```powershell
python main.py -h
python main.py collect -h
```

Most commands write outputs into `data/` and logs into `logs/app.log` by default.

---

## Recommended workflow

### 1) Download the Hugging Face repository dataset

Downloads the `hao-li/AIDev` `all_repository` parquet file, saves the raw dataset, and creates a filtered CSV with Python repositories over a star threshold.

```powershell
python main.py download_hf_aidev_dataset
```

Example with a custom threshold:

```powershell
python main.py download_hf_aidev_dataset --min_stars 30
```

Default outputs:
- `data\all_repository_raw.csv`
- `data\all_repository_python_gt_30_stars.csv`

### 2) Scan repositories for target framework imports

Scans repositories in batches using GitHub code search and saves matches incrementally so the run can be resumed safely.

```powershell
python main.py scan_framework_imports
```

Example with custom files:

```powershell
python main.py scan_framework_imports --input_file .\data\all_repository_python_gt_10_stars.csv --output_file .\data\repositories_with_target_frameworks1.csv --state_file .\data\repositories_with_target_frameworks1_state.json --batch_size 500
```

Default files:
- input: `data\all_repository_python_gt_10_stars.csv`
- output: `data\repositories_with_target_frameworks.csv`
- state: `data\repositories_with_target_frameworks_state.json`

Notes:
- Results are saved each time a repository matches.
- The state file stores where the scan stopped.
- This command requires valid GitHub API tokens in `config/constant.py`.

### 3) Clone repositories from a CSV

Example for cloning repositories discovered by the framework scan:

```powershell
python main.py clone_repos --input_file .\data\repositories_with_target_frameworks1_matches.csv --output_dir .\data\cloned_repos_frameworks1
```

The input CSV must contain `repository_full_name`.

If the CSV also has `accessible` or `archived` columns, only repositories with `accessible == True` and `archived == False` are cloned.

### 4) Convert Jupyter notebooks to Python files

```powershell
python main.py convert_notebooks --root_dir .\data\cloned_repos_frameworks1
```

This walks the directory tree and creates `.py` files next to each `.ipynb` file.

### 5) Extract Python files that contain logging or library calls

```powershell
python main.py extract_logging_files --root_dir .\data\cloned_repos_frameworks1 --output_dir .\data\logging_files
```

### 6) Clean comments before import statements

```powershell
python main.py clean_comments --root_dir .\data\logging_files
```

### 7) Create the logging JSON dataset

Current defaults are Agent-oriented:

```powershell
python main.py create_logging_json_dataset
```

Default output:
- `data\logging_dataset_Agent.json`

### 8) Analyze the logging dataset

```powershell
python main.py analyze_logging_dataset
```

Default input/output:
- input: `data\logging_dataset_Agent.json`
- output: `data\logging_dataset_metrics.csv`

### 9) Filter the logging dataset

```powershell
python main.py filter_logging_dataset
```

Default output:
- `data\logging_dataset_filtered_function_Agent.json`

### 10) Summarize the filtered dataset

```powershell
python main.py summarize_logging_dataset
```

Default output:
- `data\logging_dataset_summary_Agent.csv`

### 11) Summarize unique functions

```powershell
python main.py summarize_unique_functions
```

Default output:
- `data\logging_dataset_unique_functions_Agent.csv`

### 12) Sample snippets

```powershell
python main.py sample_snippets
```

Default output:
- `data\logging_dataset_sampled_snippets_Agent.csv`

### 13) Run LLM logging smell analysis

```powershell
python main.py llm_logging_smell_analysis
```

Current default files used by `data_collection/llm_logging_smell_analysis.py`:
- `data\logging_dataset_sampled_snippets_Agent.csv`
- `data\logging_dataset_filtered_function_Agent.json`
- `data\llm_logging_smell_results_Agent.json`
- `data\llm_logging_smell_results_Agent.xlsx`

---

## Other available commands

### Collect GitHub repository metadata

```powershell
python main.py collect --data_folder data --log_file logs/app.log
```

Writes per-file outputs suffixed with `_with_archived.csv`.

### Merge archived results

```powershell
python main.py merge_archived --data_folder data --output_file merged_archived_dataset.csv
```

### Compute Cohen's kappa between annotation files

```powershell
python main.py compute_kappa
```

---

## Configuration

Defaults are defined in `config/constant.py`, including:
- `PATH_FILE['data']`
- GitHub tokens and paging configuration
- library/logging configuration lists
- OpenAI API key placeholder

Logging output is configured through `util.log.setup_logging` and is written to `logs/app.log` by default.

---

## Troubleshooting

- **GitHub API rate limits**: `scan_framework_imports` uses GitHub code search, which is heavily rate limited. Keep batch sizes reasonable and configure valid tokens.
- **Interrupted framework scan**: rerun the same command with the same `--state_file` to resume.
- **Clone failures**: configure Git authentication if HTTPS cloning fails for some repositories.
- **Large dataset runs**: run commands on a subset first to validate the workflow.
- **LLM command dependency issues**: `llm_logging_smell_analysis` depends on external model packages and API access. If imports fail in the environment, reinstall the required packages from `requirements.txt` and verify your OpenAI configuration before retrying.
- **OpenAI key setup**: set the API key before running the LLM step if needed.

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
python main.py llm_logging_smell_analysis
```

---

## Notes

- Some filenames in the current workflow use the `Agent` suffix because the pipeline has been configured around those outputs.
- The framework scan command behavior depends on the `FRAMEWORK_IMPORTS` mapping defined in `data_collection/scan_framework_imports.py`.
- The input file used by `scan_framework_imports` can be changed explicitly with `--input_file`.

---

## License

This repository does not currently include a license file.
