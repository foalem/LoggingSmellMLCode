import ast
import json
import csv
import os

def analyze_logging_dataset(json_path, csv_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    num_files = len(data)
    num_general = sum(1 for d in data if d.get('library_type') == 'general-purpose')
    num_ml = sum(1 for d in data if d.get('library_type') == 'ML-specific')
    num_hybrid = sum(1 for d in data if d.get('library_type') == 'hybrid')
    num_functions = 0
    num_classes = 0
    num_loggings = 0
    for d in data:
        # Count functions and classes in the file content
        content = d.get('python_file_content', '')
        try:
            tree = ast.parse(content)
            num_functions += sum(isinstance(n, ast.FunctionDef) for n in ast.walk(tree))
            num_classes += sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
        except Exception:
            pass
        # Count logging statements (snippets)
        num_loggings += len(d.get('snippets', []))
    # Write to CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'number_of_python_files',
            'number_of_general_purpose',
            'number_of_ml_specific',
            'number_of_hybrid',
            'number_of_functions',
            'number_of_classes',
            'number_of_logging_statements'
        ])
        writer.writerow([
            num_files,
            num_general,
            num_ml,
            num_hybrid,
            num_functions,
            num_classes,
            num_loggings
        ])
