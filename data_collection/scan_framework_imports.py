import json
import os
import random
import time
from typing import Any

import pandas as pd
import requests

from config.constant import GitHub_CONFIG, PATH_FILE
from util.log import setup_logging

FRAMEWORK_IMPORTS = {
    'comet_ml': ['comet_ml'],
    'whylogs': ['whylogs'],
    'wandb': ['wandb'],
    'tensorboard': ['tensorboard', 'tensorboardX'],
    'mlflow': ['mlflow'],
    # 'tensorflow': ['tensorflow', 'tf'],
    'neptune': ['neptune', 'neptune.new'],
    'dowel': ['dowel'],
    'sacred': ['sacred'],
    'ml_logger': ['ml_logger'],
    'logging': ['logging'],
    'warnings': ['warnings']
}



FRAMEWORK_IMPORTS1 = {
    # 'langchain': ['langchain'],
    # 'autogen': ['autogen'],
    # 'crewai': ['crewai'],
    # 'semantic_kernel': ['semantic_kernel', 'semantic kernel'],
    # 'llamaindex': ['llama_index', 'llamaindex'],
    # 'haystack': ['haystack'],
    # 'litellm': ['litellm'],
    # 'vllm': ['vllm'],
    'ollama': ['ollama'],
    'instructor': ['instructor']
}
GITHUB_SEARCH_CODE_URL = 'https://api.github.com/search/code'
DEFAULT_INPUT_FILE = os.path.join(PATH_FILE['data'], 'all_repository_python_gt_10_stars.csv')
DEFAULT_OUTPUT_FILE = os.path.join(PATH_FILE['data'], 'repositories_with_target_frameworks.csv')
DEFAULT_STATE_FILE = os.path.join(PATH_FILE['data'], 'repositories_with_target_frameworks_state.json')
DEFAULT_BATCH_SIZE = 20
REQUEST_SLEEP_SECONDS = 65


def _delay_next_request() -> None:
    """Sleep between GitHub code search requests to respect API rate limits."""
    time.sleep(REQUEST_SLEEP_SECONDS)



def _build_headers() -> dict[str, str]:
    """Build authenticated GitHub API headers using one configured token."""
    token = random.choice(GitHub_CONFIG['token'])
    return {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    }



def _load_state(state_file: str) -> dict[str, Any]:
    """Load the persisted scan state or return a fresh default state."""
    if not os.path.exists(state_file):
        return {
            'next_start_index': 0,
            'processed_repositories': 0,
            'matched_repositories': 0,
            'last_repository': None,
            'completed': False,
        }

    with open(state_file, 'r', encoding='utf-8') as file:
        return json.load(file)



def _save_state(state_file: str, state: dict[str, Any]) -> None:
    """Persist the current scan state to disk for resume support."""
    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    with open(state_file, 'w', encoding='utf-8') as file:
        json.dump(state, file, indent=2)



def _load_existing_results(output_file: str) -> pd.DataFrame:
    """Load existing matched repositories if the output file already exists."""
    if os.path.exists(output_file):
        return pd.read_csv(output_file)
    return pd.DataFrame()



def _save_results(output_file: str, results_df: pd.DataFrame) -> None:
    """Save matched repositories to CSV, removing duplicates when present."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    if not results_df.empty:
        results_df = results_df.drop_duplicates(subset=['repository_full_name'])
    results_df.to_csv(output_file, index=False)



def _append_match_to_results(output_file: str, match: dict[str, Any]) -> None:
    """Append one matched repository to the CSV immediately and keep repository_full_name unique."""
    existing_results_df = _load_existing_results(output_file)
    match_df = pd.DataFrame([match])
    combined_df = pd.concat([existing_results_df, match_df], ignore_index=True) if not existing_results_df.empty else match_df
    _save_results(output_file, combined_df)



def _build_code_search_query(repository_full_name: str, import_term: str) -> str:
    """Build a repository-scoped GitHub code search query for Python files containing an import term."""
    escaped_term = import_term.replace(' ', '" "') if ' ' in import_term else import_term
    return f'{escaped_term} in:file language:python repo:{repository_full_name}'



def _search_repository_for_import(repository_full_name: str, import_term: str, logger) -> dict[str, Any] | None:
    """Search one repository for one import term and return the first matching code search item, if any."""
    params = {
        'q': _build_code_search_query(repository_full_name, import_term),
        'per_page': 1,
        'page': 1,
    }

    try:
        response = requests.get(GITHUB_SEARCH_CODE_URL, headers=_build_headers(), params=params, timeout=60)
        if response.status_code == 200:
            payload = response.json()
            items = payload.get('items', [])
            if items:
                return items[0]
            return None

        logger.warning(f'GitHub code search failed for {repository_full_name} and term {import_term}. Status: {response.status_code}')
        return None
    except requests.RequestException as exc:
        logger.error(f'GitHub code search request error for {repository_full_name} and term {import_term}: {exc}')
        return None
    finally:
        _delay_next_request()



def _find_framework_match(repository_full_name: str, logger) -> dict[str, Any] | None:
    """Search a repository for any target framework import and return match metadata when found."""
    for framework_name, import_terms in FRAMEWORK_IMPORTS.items():
        for import_term in import_terms:
            logger.info(f'Searching {repository_full_name} for import term: {import_term}')
            match_item = _search_repository_for_import(repository_full_name, import_term, logger)
            if match_item:
                return {
                    'repository_full_name': repository_full_name,
                    'matched_framework': framework_name,
                    'matched_term': import_term,
                    'matched_file_name': match_item.get('name'),
                    'matched_file_path': match_item.get('path'),
                    'matched_html_url': match_item.get('html_url'),
                    'score': match_item.get('score'),
                }
    return None



def scan_repositories_for_framework_imports(
    input_file: str = DEFAULT_INPUT_FILE,
    output_file: str = DEFAULT_OUTPUT_FILE,
    state_file: str = DEFAULT_STATE_FILE,
    batch_size: int = DEFAULT_BATCH_SIZE,
    log_file: str = 'logs/app.log',
) -> dict[str, Any]:
    """Scan repositories in batches for target Python framework imports and resume from saved state if needed."""
    logger = setup_logging(log_file)
    logger.info(f'Loading repositories from: {input_file}')

    df = pd.read_csv(input_file)
    if 'repository_full_name' not in df.columns:
        raise ValueError("The input CSV must contain a 'repository_full_name' column.")

    repository_names = df['repository_full_name'].dropna().astype(str).drop_duplicates().tolist()
    state = _load_state(state_file)
    existing_results_df = _load_existing_results(output_file)
    existing_repo_names = set(existing_results_df['repository_full_name'].tolist()) if not existing_results_df.empty else set()

    if existing_results_df.empty:
        _save_results(output_file, pd.DataFrame(columns=[
            'repository_full_name',
            'matched_framework',
            'matched_term',
            'matched_file_name',
            'matched_file_path',
            'matched_html_url',
            'score',
        ]))

    start_index = int(state.get('next_start_index', 0))
    end_index = min(start_index + batch_size, len(repository_names))
    batch_repository_names = repository_names[start_index:end_index]

    logger.info(f'Processing repositories from index {start_index} to {end_index - 1}')

    processed_count = int(state.get('processed_repositories', 0))
    matched_count = int(state.get('matched_repositories', 0))

    for repository_full_name in batch_repository_names:
        logger.info(f'Processing repository: {repository_full_name}')
        state['last_repository'] = repository_full_name

        if repository_full_name in existing_repo_names:
            logger.info(f'Repository already present in output file: {repository_full_name}')
            processed_count += 1
            state['processed_repositories'] = processed_count
            _save_state(state_file, state)
            continue

        match = _find_framework_match(repository_full_name, logger)
        if match:
            _append_match_to_results(output_file, match)
            existing_repo_names.add(repository_full_name)
            matched_count += 1
            state['matched_repositories'] = matched_count
            logger.info(f'Match found for repository: {repository_full_name} ({match["matched_framework"]})')
        else:
            logger.info(f'No target import found for repository: {repository_full_name}')

        processed_count += 1
        state['processed_repositories'] = processed_count
        _save_state(state_file, state)

    state['next_start_index'] = end_index
    state['completed'] = end_index >= len(repository_names)
    _save_state(state_file, state)

    logger.info(f'Batch completed. Next start index: {state["next_start_index"]}')
    return {
        'input_file': input_file,
        'output_file': output_file,
        'state_file': state_file,
        'processed_in_batch': len(batch_repository_names),
        'next_start_index': state['next_start_index'],
        'completed': state['completed'],
        'matched_repositories': state['matched_repositories'],
    }



def cli_scan_framework_imports(args) -> None:
    """Run the batch repository scan from CLI arguments and print a compact summary."""
    result = scan_repositories_for_framework_imports(
        input_file=args.input_file,
        output_file=args.output_file,
        state_file=args.state_file,
        batch_size=args.batch_size,
        log_file=args.log_file,
    )

    print(f"Input file: {result['input_file']}")
    print(f"Output file: {result['output_file']}")
    print(f"State file: {result['state_file']}")
    print(f"Processed in batch: {result['processed_in_batch']}")
    print(f"Next start index: {result['next_start_index']}")
    print(f"Matched repositories so far: {result['matched_repositories']}")
    print(f"Completed: {result['completed']}")



