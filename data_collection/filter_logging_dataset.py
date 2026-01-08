import ijson
import json
import re
from config.constant import LOGGING_CONFIG

def is_logging_config_snippet(snippet, library):
    """Return True if the snippet is a logging config call for the given library."""
    if not snippet or not library:
        return False
    snippet_stripped = snippet.strip()
    config_calls = LOGGING_CONFIG.get(library, [])
    for config_call in config_calls:
        if snippet_stripped.startswith(config_call):
            return True
    return False

def is_tensorflow_summary_snippet(snippet):
    """Return True if the snippet is a tf.summary call."""
    if not snippet:
        return False
    return snippet.strip().startswith('tf.summary')

def is_tensorflow_logging_snippet(snippet):
    """
    Return True if the snippet is a tf.summary call or tf.compat.v1.logging.<level>(...) call.
    Only these are considered logging for TensorFlow, all other tf.* calls are excluded.
    """
    if not snippet:
        return False
    s = snippet.strip()
    # Only allow tf.summary.* calls (not any tf.*)
    if s.startswith('tf.summary'):
        return True
    # Only allow tf.compat.v1.logging.<level>(...) calls
    tf_logging_levels = [
        'debug', 'error', 'fatal', 'flush', 'info', 'log', 'log_every_n',
        'log_first_n', 'log_if', 'vlog', 'warn', 'warning'
    ]
    pattern = r"^tf\.compat\.v1\.logging\.({})\s*\(".format('|'.join(tf_logging_levels))
    if re.match(pattern, s):
        return True
    return False

def filter_logging_dataset(input_json, output_json):
    with open(input_json, 'r', encoding='utf-8') as f, open(output_json, 'w', encoding='utf-8') as out:
        out.write('[')
        first = True
        for entry in ijson.items(f, 'item'):
            lib = entry.get('library')
            lib_type = entry.get('library_type')
            filtered_snippets = []
            for snip in entry.get('snippets', []):
                ctx = snip.get('context', {})
                func_name = ctx.get('function_name')
                func_code = ctx.get('function')
                snippet_str = snip.get('snippet', '')
                if func_name and func_code:
                    # Only keep tf.summary or tf.compat.v1.logging.<level>(...) calls for any snippet
                    if is_tensorflow_logging_snippet(snippet_str):
                        filtered_snippets.append(snip)
                        continue
                    # Exclude any tf.* or tf_* or tf_module.* or keras.* calls that are not tf.summary or tf.compat.v1.logging.<level>
                    s = snippet_str.strip()
                    if s.startswith('tf.') or s.startswith('tf_') or s.startswith('tf_module.') or s.startswith('keras.') or s.startswith('tensorflow.'):
                        continue
                    # Otherwise, check for logging config for all libraries in LOGGING_CONFIG
                    is_config = False
                    for lib_key, config_calls in LOGGING_CONFIG.items():
                        for config_call in config_calls:
                            if s.startswith(config_call):
                                is_config = True
                                break
                        if is_config:
                            break
                    if not is_config:
                        filtered_snippets.append(snip)
            if filtered_snippets:
                filtered_entry = {
                    'library': lib,
                    'library_type': lib_type,
                    'snippets': filtered_snippets
                }
                if not first:
                    out.write(',\n')
                out.write(json.dumps(filtered_entry, ensure_ascii=False, indent=2))
                first = False
        out.write(']')
