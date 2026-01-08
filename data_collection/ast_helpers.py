import ast
import os
import hashlib
from config.constant import LIBRARY_CONFIG

general_libs = {'logging', 'warnnings'}
ml_libs = set(LIBRARY_CONFIG['import']) - general_libs

def get_library_type(libs):
    libs = set(libs)
    if libs & general_libs and libs & ml_libs:
        return 'hybrid'
    elif libs & general_libs:
        return 'general-purpose'
    elif libs & ml_libs:
        return 'ML-specific'
    return None

def extract_logging_info(py_file_path, project_name=None):
    with open(py_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    tree = ast.parse(content, filename=py_file_path)
    # Map alias/imported name to library
    imported = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in LIBRARY_CONFIG['import']:
                    imported[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module in LIBRARY_CONFIG['import']:
                for alias in node.names:
                    imported[alias.asname or alias.name] = node.module
    # Find all logging calls
    snippets = []
    lines = content.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            lib_used = None
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                if func.value.id in imported:
                    lib_used = imported[func.value.id]
            elif isinstance(func, ast.Name):
                if func.id in imported:
                    lib_used = imported[func.id]
            if lib_used:
                lineno = getattr(node, 'lineno', None)
                end_lineno = getattr(node, 'end_lineno', None)
                # Extract the full source segment for the call (multi-line safe)
                try:
                    snippet_line = ast.get_source_segment(content, node)
                except Exception:
                    snippet_line = None
                if not snippet_line and lineno:
                    # Fallback: join lines from lineno to end_lineno
                    if end_lineno and end_lineno > lineno:
                        snippet_line = '\n'.join(lines[lineno-1:end_lineno])
                    else:
                        snippet_line = lines[lineno-1] if 0 < lineno <= len(lines) else ''
                # Find class/function context
                class_ctx, func_ctx, func_code = None, None, None
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.FunctionDef) and parent.lineno <= lineno <= getattr(parent, 'end_lineno', parent.lineno):
                        func_ctx = parent.name
                        # Extract the full function code
                        func_start = parent.lineno
                        func_end = getattr(parent, 'end_lineno', func_start)
                        func_code = '\n'.join(lines[func_start-1:func_end])
                    if isinstance(parent, ast.ClassDef) and parent.lineno <= lineno <= getattr(parent, 'end_lineno', parent.lineno):
                        class_ctx = parent.name
                # Lines before/after
                before = lines[lineno-2] if lineno and lineno > 1 else None
                after = lines[end_lineno] if end_lineno and end_lineno < len(lines) else (lines[lineno] if lineno and lineno < len(lines) else None)
                snippet_id = 'snip_' + hashlib.md5(f'{py_file_path}_{lineno}_{snippet_line}'.encode()).hexdigest()[:8]
                snippets.append({
                    'snippet_id': snippet_id,
                    'snippet': snippet_line.strip() if snippet_line else '',
                    'context': {
                        'class': class_ctx,
                        'function_name': func_ctx,
                        'function': func_code,
                        'lines_before': before.strip() if before else None,
                        'lines_after': after.strip() if after else None
                    },
                    'line_number': lineno
                })
    # Determine main library and type
    used_libs = set(s['snippet'].split('(')[0].split('.')[0] for s in snippets)
    used_libs = [imported.get(lib, lib) for lib in used_libs if lib in imported]
    main_lib = used_libs[0] if used_libs else None
    lib_type = get_library_type(used_libs)
    # Build JSON
    file_id = 'file_' + hashlib.md5(py_file_path.encode()).hexdigest()[:8]
    return {
        'id': file_id,
        'project_name': project_name or os.path.basename(os.path.dirname(py_file_path)),
        'file_path': os.path.relpath(py_file_path, start=os.path.join('data', 'logging_files')),
        'library': main_lib,
        'library_type': lib_type,
        'python_file_content': content,
        'snippets': snippets
    }

def extract_all_logging_files(logging_files_root):
    dataset = []
    for dirpath, _, filenames in os.walk(logging_files_root):
        for filename in filenames:
            if filename.endswith('.py'):
                py_path = os.path.join(dirpath, filename)
                # Project name = first folder under logging_files
                rel = os.path.relpath(py_path, logging_files_root)
                project = rel.split(os.sep)[0] if os.sep in rel else None
                data = extract_logging_info(py_path, project_name=project)
                if data['snippets']:
                    dataset.append(data)
    return dataset

def has_library_call(py_file_path):
    """
    Returns True if the python file contains at least one function call from any library in LIBRARY_CONFIG['import'].
    Handles: import library, import library as alias, from library import func, from library import func as alias.
    """
    try:
        with open(py_file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=py_file_path)
    except Exception:
        return False
    library_names = set(LIBRARY_CONFIG.get('import', []))
    # Map: alias or imported name -> library
    imported = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in library_names:
                    imported[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module in library_names:
                for alias in node.names:
                    imported[alias.asname or alias.name] = node.module
    # Now check all function calls
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # Case: alias.function() or library.function()
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                if func.value.id in imported:
                    return True
            # Case: direct function call (from ... import func or from ... import func as alias)
            if isinstance(func, ast.Name):
                if func.id in imported:
                    return True
    return False
