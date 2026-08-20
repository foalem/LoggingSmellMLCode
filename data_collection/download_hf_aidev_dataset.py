import os
import pandas as pd

from config.constant import PATH_FILE
from util.log import setup_logging


DATASET_NAME = 'hao-li/AIDev'
DATASET_FILE_NAME = 'all_repository.parquet'
DATASET_URL = f'hf://datasets/{DATASET_NAME}/{DATASET_FILE_NAME}'
LANGUAGE_COLUMN = 'language'
STARS_COLUMN = 'stars'
SOURCE_REPOSITORY_COLUMN = 'full_name'
TARGET_REPOSITORY_COLUMN = 'repository_full_name'


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of the DataFrame with stripped column names."""
    normalized_df = df.copy()
    normalized_df.columns = [str(column).strip() for column in normalized_df.columns]
    return normalized_df


def _standardize_repository_name_column(df: pd.DataFrame) -> pd.DataFrame:
    """Rename full_name to repository_full_name so downstream commands can reuse the CSV."""
    standardized_df = df.copy()
    if SOURCE_REPOSITORY_COLUMN in standardized_df.columns and TARGET_REPOSITORY_COLUMN not in standardized_df.columns:
        standardized_df = standardized_df.rename(columns={SOURCE_REPOSITORY_COLUMN: TARGET_REPOSITORY_COLUMN})
    return standardized_df


def _filter_python_projects(df: pd.DataFrame, min_stars: int) -> pd.DataFrame:
    """Filter rows to Python repositories whose star count is strictly greater than min_stars."""
    filtered_df = _normalize_columns(df)
    filtered_df = _standardize_repository_name_column(filtered_df)
    filtered_df[LANGUAGE_COLUMN] = filtered_df[LANGUAGE_COLUMN].astype(str)
    filtered_df[STARS_COLUMN] = pd.to_numeric(filtered_df[STARS_COLUMN], errors='coerce')

    python_mask = filtered_df[LANGUAGE_COLUMN].str.contains('python', case=False, na=False)
    stars_mask = filtered_df[STARS_COLUMN] > min_stars
    return filtered_df[python_mask & stars_mask].copy()


def _load_all_repository_dataframe() -> pd.DataFrame:
    """Load the Hugging Face all_repository parquet file into a pandas DataFrame."""
    return pd.read_parquet(DATASET_URL)


def download_and_filter_aidev_dataset(
    output_dir: str = PATH_FILE['data'],
    raw_output_file: str = 'all_repository_raw.csv',
    filtered_output_file: str = 'all_repository_python_gt_30_stars.csv',
    min_stars: int = 10,
    log_file: str = 'logs/app.log',
):
    """Download the AIDev all_repository dataset, save the raw CSV, and save the filtered Python CSV."""
    logger = setup_logging(log_file)
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f'Loading Hugging Face parquet dataset: {DATASET_URL}')
    df = _load_all_repository_dataframe()

    logger.info('Normalizing dataset columns')
    df = _normalize_columns(df)
    df = _standardize_repository_name_column(df)

    raw_output_path = os.path.join(output_dir, raw_output_file)
    filtered_output_path = os.path.join(output_dir, filtered_output_file)

    logger.info(f'Saving raw dataset to: {raw_output_path}')
    df.to_csv(raw_output_path, index=False)

    logger.info(f'Filtering Python projects with more than {min_stars} stars')
    filtered_df = _filter_python_projects(df, min_stars=min_stars)

    logger.info(f'Saving filtered dataset to: {filtered_output_path}')
    filtered_df.to_csv(filtered_output_path, index=False)

    logger.info(f'Download complete. Raw rows: {len(df)}, Filtered rows: {len(filtered_df)}')
    return {
        'raw_output_path': raw_output_path,
        'filtered_output_path': filtered_output_path,
        'raw_rows': len(df),
        'filtered_rows': len(filtered_df),
    }


def cli_download_hf_aidev_dataset(args):
    """Run the all_repository download and filtering flow from CLI arguments and print summary output."""
    result = download_and_filter_aidev_dataset(
        output_dir=args.output_dir,
        raw_output_file=args.raw_output_file,
        filtered_output_file=args.filtered_output_file,
        min_stars=args.min_stars,
        log_file=args.log_file,
    )

    print(f"Raw dataset written to {result['raw_output_path']}")
    print(f"Filtered dataset written to {result['filtered_output_path']}")
    print(f"Raw rows: {result['raw_rows']}")
    print(f"Filtered rows: {result['filtered_rows']}")
