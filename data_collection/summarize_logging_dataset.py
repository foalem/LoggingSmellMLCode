import json
import csv
import re
from collections import Counter
from config.constant import LOGGING_CONFIG

def summarize_logging_dataset(json_path, csv_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    lib_counter = Counter()
    logging_stmt_count = 0
    function_set = set()
    loglevel_counter = Counter()
    loglevel_pattern = re.compile(r"logging\.(info|debug|warning|warn|error|critical|fatal|exception|log)\s*\(")
    # Build regex patterns for all libraries in LOGGING_CONFIG
    lib_patterns = {}
    for lib, calls in LOGGING_CONFIG.items():
        # Use the library name as a pattern (e.g., 'mlflow')
        lib_patterns[lib] = re.compile(rf"\\b{re.escape(lib)}\\.")
    for entry in data:
        lib = entry.get('library')
        libtype = entry.get('library_type')
        for snip in entry.get('snippets', []):
            snippet_str = snip.get('snippet', '')
            actual_lib = lib
            # If hybrid and logging, try to reassign library by regex
            if lib == 'logging' and libtype == 'hybrid' and snippet_str:
                for lib_key, pattern in lib_patterns.items():
                    if pattern.search(snippet_str):
                        actual_lib = lib_key
                        break
            lib_counter[actual_lib] += 1
            logging_stmt_count += 1
            ctx = snip.get('context', {})
            func_code = ctx.get('function')
            if func_code:
                function_set.add(func_code)
            # log level statistic for logging library only
            if actual_lib == 'logging' and snippet_str:
                m = loglevel_pattern.match(snippet_str.strip())
                if m:
                    loglevel_counter[m.group(1).lower()] += 1
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['library', 'count'])
        for lib, count in lib_counter.items():
            writer.writerow([lib, count])
        writer.writerow([])
        writer.writerow(['number_of_logging_statements', logging_stmt_count])
        writer.writerow(['number_of_functions', len(function_set)])
        writer.writerow([])
        writer.writerow(['log_level', 'count'])
        for level, count in loglevel_counter.items():
            writer.writerow([level, count])
