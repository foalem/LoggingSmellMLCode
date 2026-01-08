import ijson
import csv
import os
from collections import defaultdict
from config.constant import LOGGING_CONFIG

def summarize_unique_functions(json_path, csv_path):
    """
    Summarize unique functions per logging library and for 'logging' per log level.
    Output CSV columns:
      - library
      - log_level (if applicable)
      - unique_function_count
    """
    # Prepare data structures
    lib_func_to_snippets = defaultdict(lambda: {'funcs': set(), 'snippet_ids': set()})  # {lib: {'funcs': set(function_code), 'snippet_ids': set(snippet_id)}}
    logging_level_func_to_snippets = defaultdict(lambda: {'funcs': set(), 'snippet_ids': set()})  # {level: {'funcs': set(function_code), 'snippet_ids': set(snippet_id)}}

    def extract_log_level(snippet):
        import re
        m = re.match(r"logging\.(info|debug|warning|warn|error|critical|fatal|exception|log)\s*\(", snippet.strip())
        if m:
            return m.group(1).lower()
        return None

    with open(json_path, 'r', encoding='utf-8') as f:
        for entry in ijson.items(f, 'item'):
            lib = entry.get('library')
            for snip in entry.get('snippets', []):
                ctx = snip.get('context', {})
                func_code = ctx.get('function', None)
                snippet_id = snip.get('snippet_id') or snip.get('id') or snip.get('id_snippet')
                snippet_str = snip.get('snippet', '')
                if not func_code or not snippet_id:
                    continue
                func_code_str = func_code.strip()
                if lib == 'logging':
                    level = extract_log_level(snippet_str)
                    if not level:
                        level = 'unknown'
                    logging_level_func_to_snippets[level]['funcs'].add(func_code_str)
                    logging_level_func_to_snippets[level]['snippet_ids'].add(snippet_id)
                else:
                    lib_func_to_snippets[lib]['funcs'].add(func_code_str)
                    lib_func_to_snippets[lib]['snippet_ids'].add(snippet_id)

    # Write results to CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['library', 'log_level', 'unique_function_count', 'snippet_ids']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        # Write for non-logging libraries
        for lib, data in lib_func_to_snippets.items():
            if lib == 'logging':
                continue
            writer.writerow({
                'library': lib,
                'log_level': '',
                'unique_function_count': len(data['funcs']),
                'snippet_ids': ';'.join(sorted(data['snippet_ids']))
            })
        # Write for logging library by level
        for level, data in logging_level_func_to_snippets.items():
            writer.writerow({
                'library': 'logging',
                'log_level': level,
                'unique_function_count': len(data['funcs']),
                'snippet_ids': ';'.join(sorted(data['snippet_ids']))
            })

def cli_summarize_unique_functions(args):
    summarize_unique_functions(args.json_path, args.csv_path)
    print(f"Unique function summary written to {args.csv_path}")
