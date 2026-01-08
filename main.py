import argparse
import os
import glob
import pandas as pd
from util.log import setup_logging
from util.util import read_csv_file, get_repo_names_from_csv, save_csv_file
from data_collection.get_repo_infos import collect_repos_info
from config.constant import PATH_FILE
from git import Repo
import shutil
import nbconvert
import nbformat
from data_collection.ast_helpers import has_library_call, extract_all_logging_files
import json
from data_collection.analyze_logging_dataset import analyze_logging_dataset
from data_collection.filter_logging_dataset import filter_logging_dataset
from data_collection.summarize_logging_dataset import summarize_logging_dataset
from data_collection.summarize_unique_functions import cli_summarize_unique_functions
from data_collection.sample_snippets_by_library import cli_sample_snippets

def collect_command(args):
    logger = setup_logging(args.log_file)
    data_folder = args.data_folder
    csv_files = glob.glob(os.path.join(data_folder, '*.csv'))

    for csv_file in csv_files:
        logger.info(f'Processing file: {csv_file}')
        df = read_csv_file(csv_file)
        repo_names = get_repo_names_from_csv(df)
        repo_infos = collect_repos_info(repo_names)
        # Merge results with original DataFrame
        info_df = df.merge(
            right=pd.DataFrame(repo_infos),
            on='repository_full_name',
            how='left'
        )
        out_file = csv_file.replace('.csv', '_with_archived.csv')
        save_csv_file(info_df, out_file)
        logger.info(f'Saved results to: {out_file}')

def merge_archived_command(args):
    logger = setup_logging(args.log_file)
    data_folder = args.data_folder
    archived_files = glob.glob(os.path.join(data_folder, '*_with_archived.csv'))

    if not archived_files:
        logger.warning('No *_with_archived.csv files found in the data folder.')
        return

    df_list = [pd.read_csv(f) for f in archived_files]
    merged_df = pd.concat(df_list, ignore_index=True)
    merged_df = merged_df.drop_duplicates()
    output_path = os.path.join(data_folder, args.output_file)
    merged_df.to_csv(output_path, index=False)
    logger.info(f'Merged file saved to: {output_path}')

def clone_repos_command(args):
    logger = setup_logging(args.log_file)
    merged_csv = args.input_file
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(merged_csv)
    # Filter only accessible and not archived repos if columns exist
    if 'accessible' in df.columns:
        df = df[df['accessible'] == True]
    if 'archived' in df.columns:
        df = df[df['archived'] == False]
    repo_names = df['repository_full_name'].dropna().unique()
    for repo_full_name in repo_names:
        owner, repo = repo_full_name.split('/')
        dest_path = os.path.join(output_dir, owner, repo)
        if os.path.exists(dest_path):
            logger.info(f"Repo already cloned: {repo_full_name}")
            continue
        repo_url = f"https://github.com/{repo_full_name}.git"
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        try:
            logger.info(f"Cloning {repo_url} to {dest_path}")
            Repo.clone_from(repo_url, dest_path)
        except Exception as e:
            logger.error(f"Failed to clone {repo_full_name}: {e}")
            # Clean up partial clone
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path)

def convert_notebooks_command(args):
    logger = setup_logging(args.log_file)
    root_dir = args.root_dir
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.ipynb'):
                notebook_path = os.path.join(dirpath, filename)
                py_path = os.path.splitext(notebook_path)[0] + '.py'
                try:
                    logger.info(f"Converting {notebook_path} to {py_path}")
                    with open(notebook_path, 'r', encoding='utf-8') as f:
                        nb = nbformat.read(f, as_version=4)
                    exporter = nbconvert.PythonExporter()
                    source, _ = exporter.from_notebook_node(nb)
                    with open(py_path, 'w', encoding='utf-8') as f:
                        f.write(source)
                except Exception as e:
                    logger.error(f"Failed to convert {notebook_path}: {e}")

def extract_logging_files_command(args):
    logger = setup_logging(args.log_file)
    root_dir = args.root_dir
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.py'):
                py_path = os.path.join(dirpath, filename)
                if has_library_call(py_path):
                    # Find repo path relative to root_dir
                    rel_path = os.path.relpath(py_path, root_dir)
                    # username/reponame/....py
                    repo_folder = os.path.join(output_dir, os.path.dirname(rel_path))
                    os.makedirs(repo_folder, exist_ok=True)
                    dest_path = os.path.join(repo_folder, filename)
                    shutil.copy2(py_path, dest_path)
                    logger.info(f"Copied {py_path} to {dest_path}")

def clean_comments_command(args):
    logger = setup_logging(args.log_file)
    root_dir = args.root_dir
    def remove_comments_before_import(py_file_path):
        with open(py_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        new_lines = []
        found_import = False
        for line in lines:
            stripped = line.strip()
            if not found_import:
                if stripped.startswith('import') or stripped.startswith('from'):
                    found_import = True
                    new_lines.append(line)
                elif not stripped.startswith('#') and stripped != '':
                    new_lines.append(line)
                # else: skip comment lines before import
            else:
                new_lines.append(line)
        with open(py_file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        logger.info(f"Cleaned comments before import in: {py_file_path}")
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.py'):
                remove_comments_before_import(os.path.join(dirpath, filename))

def create_logging_json_dataset_command(args):
    logger = setup_logging(args.log_file)
    root_dir = args.root_dir
    output_file = args.output_file
    logger.info(f"Extracting logging dataset from {root_dir}")
    dataset = extract_all_logging_files(root_dir)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved logging dataset to {output_file}")

def analyze_logging_dataset_command(args):
    analyze_logging_dataset(args.json_path, args.csv_path)
    print(f"Metrics written to {args.csv_path}")

def filter_logging_dataset_command(args):
    filter_logging_dataset(args.input_json, args.output_json)
    print(f"Filtered dataset written to {args.output_json}")

def summarize_logging_dataset_command(args):
    summarize_logging_dataset(args.json_path, args.csv_path)
    print(f"Summary statistics written to {args.csv_path}")

def main():
    parser = argparse.ArgumentParser(description='GitHub repository info CLI')
    subparsers = parser.add_subparsers(dest='command', required=True)

    collect_parser = subparsers.add_parser('collect', help='Collect GitHub repository archived status')
    collect_parser.add_argument('--data_folder', type=str, default=PATH_FILE['data'], help='Path to data folder with CSV files')
    collect_parser.add_argument('--log_file', type=str, default='logs/app.log', help='Path to log file')
    collect_parser.set_defaults(func=collect_command)

    merge_parser = subparsers.add_parser('merge_archived', help='Merge all *_with_archived.csv files, remove duplicates, and save as one file')
    merge_parser.add_argument('--data_folder', type=str, default=PATH_FILE['data'], help='Path to data folder with archived CSV files')
    merge_parser.add_argument('--output_file', type=str, default='merged_archived_dataset.csv', help='Output file name')
    merge_parser.add_argument('--log_file', type=str, default='logs/app.log', help='Path to log file')
    merge_parser.set_defaults(func=merge_archived_command)

    clone_parser = subparsers.add_parser('clone_repos', help='Clone all repositories from merged CSV file')
    clone_parser.add_argument('--input_file', type=str, default=os.path.join(PATH_FILE['data'], 'merged_archived_dataset.csv'), help='Merged CSV file with repository names')
    clone_parser.add_argument('--output_dir', type=str, default=os.path.join(PATH_FILE['data'], 'cloned_repos'), help='Directory to clone repositories into')
    clone_parser.add_argument('--log_file', type=str, default='logs/app.log', help='Path to log file')
    clone_parser.set_defaults(func=clone_repos_command)

    convert_parser = subparsers.add_parser('convert_notebooks', help='Convert all Jupyter notebooks in cloned_repos to Python files')
    convert_parser.add_argument('--root_dir', type=str, default=os.path.join(PATH_FILE['data'], 'cloned_repos'), help='Root directory to search for notebooks')
    convert_parser.add_argument('--log_file', type=str, default='logs/app.log', help='Path to log file')
    convert_parser.set_defaults(func=convert_notebooks_command)

    extract_parser = subparsers.add_parser('extract_logging_files', help='Extract all Python files with logging calls')
    extract_parser.add_argument('--root_dir', type=str, default=os.path.join(PATH_FILE['data'], 'cloned_repos'), help='Root directory to search for Python files')
    extract_parser.add_argument('--output_dir', type=str, default=os.path.join(PATH_FILE['data'], 'logging_files'), help='Directory to save extracted Python files')
    extract_parser.add_argument('--log_file', type=str, default='logs/app.log', help='Path to log file')
    extract_parser.set_defaults(func=extract_logging_files_command)

    clean_parser = subparsers.add_parser('clean_comments', help='Remove comments before import statements in all Python files in a directory')
    clean_parser.add_argument('--root_dir', type=str, default=os.path.join(PATH_FILE['data'], 'logging_files'), help='Root directory to clean Python files')
    clean_parser.add_argument('--log_file', type=str, default='logs/app.log', help='Path to log file')
    clean_parser.set_defaults(func=clean_comments_command)

    dataset_parser = subparsers.add_parser('create_logging_json_dataset', help='Create a JSON dataset from logging Python files')
    dataset_parser.add_argument('--root_dir', type=str, default=os.path.join(PATH_FILE['data'], 'logging_files'), help='Root directory to search for logging Python files')
    dataset_parser.add_argument('--output_file', type=str, default=os.path.join(PATH_FILE['data'], 'logging_dataset.json'), help='Output JSON file path')
    dataset_parser.add_argument('--log_file', type=str, default='logs/app.log', help='Path to log file')
    dataset_parser.set_defaults(func=create_logging_json_dataset_command)

    analyze_parser = subparsers.add_parser('analyze_logging_dataset', help='Analyze logging_dataset.json and output metrics as CSV')
    analyze_parser.add_argument('--json_path', type=str, default=os.path.join(PATH_FILE['data'], 'logging_dataset.json'), help='Path to logging_dataset.json')
    analyze_parser.add_argument('--csv_path', type=str, default=os.path.join(PATH_FILE['data'], 'logging_dataset_metrics.csv'), help='Path to output CSV file')
    analyze_parser.set_defaults(func=analyze_logging_dataset_command)

    filter_parser = subparsers.add_parser('filter_logging_dataset', help='Filter logging_dataset.json to retain only relevant snippets and fields')
    filter_parser.add_argument('--input_json', type=str, default=os.path.join(PATH_FILE['data'], 'logging_dataset.json'), help='Input JSON file path')
    filter_parser.add_argument('--output_json', type=str, default=os.path.join(PATH_FILE['data'], 'logging_dataset_filtered_function.json'), help='Output filtered JSON file path')
    filter_parser.set_defaults(func=filter_logging_dataset_command)

    summarize_parser = subparsers.add_parser('summarize_logging_dataset', help='Summarize logging_dataset_filtered_function.json and output statistics as CSV')
    summarize_parser.add_argument('--json_path', type=str, default=os.path.join(PATH_FILE['data'], 'logging_dataset_filtered_function.json'), help='Path to filtered logging dataset JSON')
    summarize_parser.add_argument('--csv_path', type=str, default=os.path.join(PATH_FILE['data'], 'logging_dataset_summary.csv'), help='Path to output CSV file')
    summarize_parser.set_defaults(func=summarize_logging_dataset_command)

    # New CLI command for unique function summary
    summarize_unique_parser = subparsers.add_parser('summarize_unique_functions', help='Summarize unique functions per logging library and log level')
    summarize_unique_parser.add_argument('--json_path', type=str, default=os.path.join(PATH_FILE['data'], 'logging_dataset_filtered_function.json'), help='Path to filtered logging dataset JSON')
    summarize_unique_parser.add_argument('--csv_path', type=str, default=os.path.join(PATH_FILE['data'], 'logging_dataset_unique_functions.csv'), help='Path to output CSV file')
    summarize_unique_parser.set_defaults(func=cli_summarize_unique_functions)

    sample_snippets_parser = subparsers.add_parser('sample_snippets', help='Sample code snippets by library and log level')
    sample_snippets_parser.add_argument('--input_csv', type=str, default=os.path.join(PATH_FILE['data'], 'logging_dataset_unique_functions.csv'), help='Input CSV file with unique functions')
    sample_snippets_parser.add_argument('--output_csv', type=str, default=os.path.join(PATH_FILE['data'], 'logging_dataset_sampled_snippets.csv'), help='Output CSV file for sampled snippets')
    sample_snippets_parser.add_argument('--random_state', type=int, default=42, help='Random state for reproducibility')
    sample_snippets_parser.set_defaults(func=cli_sample_snippets)

    llm_smell_parser = subparsers.add_parser('llm_logging_smell_analysis', help='Analyze logging smells in sampled snippets using GPT-5-mini')
    llm_smell_parser.set_defaults(func=lambda args: __import__('data_collection.llm_logging_smell_analysis', fromlist=['cli_llm_logging_smell_analysis']).cli_llm_logging_smell_analysis(args))

    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
