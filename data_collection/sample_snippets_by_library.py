import pandas as pd
import os

# Sampling plan: (library, log_level) -> sample size
SAMPLE_PLAN = [
    ("wandb", None, 237),
    ("neptune", None, 114),
    ("tensorflow", None, 26),
    ("mlflow", None, 215),
    ("comet_ml", None, 76),
    ("dowel", None, 179),
    ("ml_logger", None, 106),
    ("tensorboard", None, 141),
    ("whylogs", None, 3),
    ("sacred", None, 2),
    ("logging", "warning", 293),
    ("logging", "Warn", 293),  # treat 'Warn' as 'warning' for sampling
    ("logging", "info", 477),
    ("logging", "exception", 92),
    ("logging", "debug", 227),
    ("logging", "error", 232),
    ("logging", "fatal", 10),
    ("logging", "critical", 18),
]

INPUT_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "logging_dataset_unique_functions.csv")
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "logging_dataset_sampled_snippets.csv")

def sample_snippets(input_csv=INPUT_CSV, output_csv=OUTPUT_CSV, random_state=42):
    df = pd.read_csv(input_csv)
    # Explode the snippet_ids column
    df = df.copy()
    df["snippet_ids"] = df["snippet_ids"].astype(str)
    df = df.assign(snippet_id=df["snippet_ids"].str.split(';')).explode("snippet_id")
    df = df.drop(columns=["snippet_ids"])  # Remove the old column
    df = df.rename(columns={"snippet_id": "snippet_id"})
    df["log_level"] = df["log_level"].astype(str).str.lower().replace({"warn": "warning"})
    sampled_rows = []
    used_ids = set()
    # Special handling for logging warning/Warn: sample 293 in total, not 293 each
    logging_warning_mask = (df["library"] == "logging") & (df["log_level"] == "warning")
    logging_warning_group = df[logging_warning_mask].drop_duplicates(subset=["snippet_id"])
    if len(logging_warning_group) > 293:
        logging_warning_sample = logging_warning_group.sample(293, random_state=random_state)
    else:
        logging_warning_sample = logging_warning_group
    sampled_rows.append(logging_warning_sample)
    used_ids.update(logging_warning_sample["snippet_id"].tolist())
    # Now sample for all other (lib, log_level) pairs
    for lib, log_level, n in SAMPLE_PLAN:
        if lib == "logging" and (log_level is not None and log_level.lower() in ("warning", "warn")):
            continue  # already handled above
        if log_level is None:
            group = df[(df["library"] == lib) & (~df["snippet_id"].isin(used_ids))]
        else:
            group = df[(df["library"] == lib) & (df["log_level"] == log_level.lower()) & (~df["snippet_id"].isin(used_ids))]
        group = group.drop_duplicates(subset=["snippet_id"])
        if len(group) > n:
            sample = group.sample(n, random_state=random_state)
        else:
            sample = group
        sampled_rows.append(sample)
        used_ids.update(sample["snippet_id"].tolist())
    result = pd.concat(sampled_rows, ignore_index=True)
    # Ensure no duplicate snippet_ids in the final result
    result = result.drop_duplicates(subset=["snippet_id"])
    # Now, for each (lib, log_level), enforce the sample size strictly
    final_rows = []
    # Special case for logging warning/Warn
    warning_mask = (result["library"] == "logging") & (result["log_level"] == "warning")
    warning_group = result[warning_mask]
    if len(warning_group) > 293:
        warning_group = warning_group.sample(293, random_state=random_state)
    final_rows.append(warning_group)
    # All other groups
    for lib, log_level, n in SAMPLE_PLAN:
        if lib == "logging" and (log_level is not None and log_level.lower() in ("warning", "warn")):
            continue
        if log_level is None:
            group = result[(result["library"] == lib)]
        else:
            group = result[(result["library"] == lib) & (result["log_level"] == log_level.lower())]
        if len(group) > n:
            group = group.sample(n, random_state=random_state)
        final_rows.append(group)
    final_result = pd.concat(final_rows, ignore_index=True)
    final_result = final_result.drop_duplicates(subset=["snippet_id"])
    final_result.to_csv(output_csv, index=False)
    print(f"Sampled {len(final_result)} unique snippets saved to {output_csv}")

# CLI entry point
def cli_sample_snippets(args=None):
    if args is not None and hasattr(args, 'input_csv') and hasattr(args, 'output_csv') and hasattr(args, 'random_state'):
        sample_snippets(input_csv=args.input_csv, output_csv=args.output_csv, random_state=args.random_state)
    else:
        sample_snippets()
