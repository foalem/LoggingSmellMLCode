import os
import json
import pandas as pd
from typing import List, Dict
from langchain_openai import ChatOpenAI
from config.constant import OPENAI_API_KEY
import logging
os.environ.setdefault("OPENAI_API_KEY", OPENAI_API_KEY)
PROMPT = '''You are a senior software engineer and researcher specializing in Machine Learning (ML) observability and software quality. Your task is to analyze a **single Python function** that is part of an ML codebase and determine whether it exhibits **exactly one logging-related code smell**, if any.

🔍 **Scope of Analysis**:
- Focus **only on the function body**—analyze the code logic and any **in-function logging statements**.
- **Ignore all logging configuration**, imports, and global setup (even if present within the file).
- Identify **at most one trivial or clearly observable logging smell** per function. If more than one is possible, choose the most relevant or impactful one.

🔧 **Logging Context in ML Systems**:
ML developers use a mix of logging libraries.
The following two lists are the logging libraries found in ML systems, related to general or ML-specific logging:
- **General-purpose logging libraries**: `logging`, `warnings`
- **ML-specific logging libraries**: `wandb`, `mlflow`, `dowel`, `neptune`, `tensorboard`, `comet_ml`, `ml_logger`, `tensorflow`, `sacred`, `whylogs`

You should **prioritize the use of ML-specific logging libraries** for capturing critical ML lifecycle activities such as:
- Training and evaluation progress
- Experiment tracking
- Metric logging and visualization
- Model versioning

Using general-purpose logging (e.g., `logging.info`) for tasks better suited to ML-specific tools may indicate a logging smell.

🛡️ **Trustworthiness and MLOps Concerns**:
Logging practices that **undermine the traceability, debuggability, or auditability** of ML behavior should also be considered smells. This includes:
- Failing to log important model outputs or metrics
- Logging ambiguous or unstructured data
- Logging in a way that reduces reproducibility or interpretability

🧠 **Output Format**:
If you detect a logging smell, return **one** entry in the following format (this is just an example, use appropriate values for the function you are analyzing; do not copy these values as ground truth):

```
[
  {{
    "smell": "<smell_type>",
    "rationale": "<brief explanation of the detected smell>",
    "confidence": "<High|Medium|Low>"
  }}
]
```

If no logging smell is found, return:

```
[
  {{
    "smell": "NO_SMELL",
    "rationale": "<brief explanation of the detected smell>",
    "confidence": "<High|Medium|Low>"
  }}
]
```

✅ Be evidence-based and concise:
Avoid speculative reasoning. Return a single, clearly justified smell or nothing at all. Confidence level should reflect how clear and impactful the issue is (High, Medium, Low).

Now analyze the following Python function:

{function}
'''

# New prompt: classify into explicit categories and allow proposing a new one
PROMPT_WITH_CATEGORIES = '''You are a senior software engineer and researcher focused on ML observability and software quality. Analyze a **single Python function** (provided below) and determine whether it exhibits **exactly one logging-related code smell**. Focus only on the function body and any in-function logging statements. Ignore imports, global logging configuration, and unrelated code.

The goal is to classify the function into one of the following smell categories (choose the best match) or propose a new category if none apply.

Categories (use these exact labels when applicable) and their descriptions:
- Ambiguous Logging: Logs lack clear semantic meaning or contextual description, making it difficult to understand what the recorded values represent or how they should be interpreted.
- Heavy Logging: Logging routines perform computationally expensive operations (for example, large tensor reductions, model computations, or costly serialization) that slow down execution and may adversely affect training or inference performance.
- Misconfigured Logging: Logging configuration (levels, handlers, formatters) is defined or modified inside application/business logic rather than centrally, causing inconsistent log behavior, unpredictable levels, or accidental overrides.
- Misrouted Metric Logging: Quantitative ML metrics (losses, accuracies, step-wise metrics) are emitted using general-purpose logging (e.g., `logging.info`) instead of a dedicated tracking tool (e.g., `wandb`, `mlflow`), preventing proper ingestion into experiment dashboards and run histories.
- Metric Overwrite: The same metric key is logged repeatedly without an associated step, epoch, or timestamp, causing earlier metric values to be silently overwritten and destroying historical information.
- Log Without Context: Values or events are logged without descriptive messages, labels, or surrounding context (e.g., logging a raw number), making it unclear what the log entry refers to and reducing usefulness for debugging.
- Missing Hyperparameter Logging: Important configuration or hyperparameters that affect experiment reproducibility are never recorded, recorded inconsistently, or only logged conditionally, hindering reproducibility and comparison across runs.
- Print-Based Metrics: Performance metrics or important experiment signals are emitted using `print()` rather than a structured tracking tool, producing unstructured output that is not persisted or associated with experiment metadata.
- Print Logging: Using `print()` for program information, warnings, or errors instead of a structured logging framework, resulting in unformatted, unlevelled, and non-configurable output.
- Logging Sensitive Data: Logs accidentally include confidential or security-sensitive information (API keys, tokens, personal data), introducing security and compliance risks.
- Incorrect Log Level: Events are logged at a severity that doesn't match their importance (e.g., critical errors logged as INFO), leading to missed alerts or misinterpretation of system health.
- Misleading Logging: occurs when log messages communicate information that is factually incorrect, incomplete, or not guaranteed to reflect the program’s actual behavior.

Note: the list above is provided as the set of known categories for this task. If the observed smell does not fit any of these exactly, provide a short proposed category name.

🔧 **Guidance**:
- If multiple issues are present pick the single most relevant/impactful smell and classify to that category.
- Be concise and evidence-based: Avoid speculative reasoning. Return a single, clearly justified smell or nothing at all. Confidence level should reflect how clear and impactful the issue is (High, Medium, Low).


🧠 **Output Format**:
If you detect a logging smell, return **one** entry in the following format (this is just an example, use appropriate values for the function you are analyzing; do not copy these values as ground truth):

```
[
  {{
    "smell": "<smell_type>",
    "rationale": "<brief explanation of the detected smell>",
    "confidence": "<High|Medium|Low>"
  }}
]
```

- `smell` should be either one of the categories listed above or a short proposed new smell string when none of the categories apply.

If no logging smell is found, return:

```
[
  {{
    "smell": "NO_SMELL",
    "rationale": "<brief explanation of why there is no smell>",
    "confidence": "<High|Medium|Low>"
  }}
]
```

🧾 **Strict Output Requirements**:
- The output must be valid JSON. Do not include additional explanatory text.


Now analyze the following Python function:

{function}
'''

# New prompt: classify into explicit categories
PROMPT_WITH_CATEGORIES_ONLY = '''You are a senior software engineer and researcher focused on ML observability and software quality. Analyze a **single Python function** (provided below) and determine whether it exhibits **exactly one logging-related code smell**. Focus only on the function body and any in-function logging statements. Ignore imports, global logging configuration, and unrelated code.

The goal is to classify the function into one of the following smell categories (choose the best match).

Categories (use these exact labels) and their descriptions:
- Ambiguous Logging: Logs lack clear semantic meaning or contextual description, making it difficult to understand what the recorded values represent or how they should be interpreted.
- Heavy Logging: Logging routines perform computationally expensive operations (for example, large tensor reductions, model computations, or costly serialization) that slow down execution and may adversely affect training or inference performance.
- Misconfigured Logging: Logging configuration (levels, handlers, formatters) is defined or modified inside application/business logic rather than centrally, causing inconsistent log behavior, unpredictable levels, or accidental overrides.
- Misrouted Metric Logging: Quantitative ML metrics (losses, accuracies, step-wise metrics) are emitted using general-purpose logging (e.g., `logging.info`) instead of a dedicated tracking tool (e.g., `wandb`, `mlflow`), preventing proper ingestion into experiment dashboards and run histories.
- Metric Overwrite: The same metric key is logged repeatedly without an associated step, epoch, or timestamp, causing earlier metric values to be silently overwritten and destroying historical information.
- Log Without Context: Values or events are logged without descriptive messages, labels, or surrounding context (e.g., logging a raw number), making it unclear what the log entry refers to and reducing usefulness for debugging.
- Missing Hyperparameter Logging: Important configuration or hyperparameters that affect experiment reproducibility are never recorded, recorded inconsistently, or only logged conditionally, hindering reproducibility and comparison across runs.
- Print-Based Metrics: Performance metrics or important experiment signals are emitted using `print()` rather than a structured tracking tool, producing unstructured output that is not persisted or associated with experiment metadata.
- Print Logging: Using `print()` for program information, warnings, or errors instead of a structured logging framework, resulting in unformatted, unlevelled, and non-configurable output.
- Logging Sensitive Data: Logs accidentally include confidential or security-sensitive information (API keys, tokens, personal data), introducing security and compliance risks.
- Incorrect Log Level: Events are logged at a severity that doesn't match their importance (e.g., critical errors logged as INFO), leading to missed alerts or misinterpretation of system health.
- Misleading Logging: occurs when log messages communicate information that is factually incorrect, incomplete, or not guaranteed to reflect the program’s actual behavior.

Note: the list above is provided as the only acceptable set of known categories for this task.

🔧 **Guidance**:
- If multiple issues are present pick the single most relevant/impactful smell and classify to that category.
- Be concise and evidence-based: Avoid speculative reasoning. Return a single, clearly justified smell or nothing at all. Confidence level should reflect how clear and impactful the issue is (High, Medium, Low).


🧠 **Output Format**:
If you detect a logging smell, return **one** entry in the following format (this is just an example, use appropriate values for the function you are analyzing; do not copy these values as ground truth):

```
[
  {{
    "smell": "<smell_type>",
    "rationale": "<brief explanation of the detected smell>",
    "confidence": "<High|Medium|Low>"
  }}
]
```

- `smell` should be one of the categories listed above.

If no logging smell is found, return:

```
[
  {{
    "smell": "NO_SMELL",
    "rationale": "<brief explanation of why there is no smell>",
    "confidence": "<High|Medium|Low>"
  }}
]
```

🧾 **Strict Output Requirements**:
- The output must be valid JSON. Do not include additional explanatory text.


Now analyze the following Python function:

{function}
'''

# 1. Add 'selected' column and sample 245 snippet_ids from different libraries
def mark_selected_snippets(csv_path: str, output_path: str, sample_size: int = 1410, random_state: int = 42) -> List[str]:
    df = pd.read_csv(csv_path)
    if 'selected' not in df.columns:
        df['selected'] = 'no'
    # Only consider snippet_ids that have not been selected before
    df_unselected = df[df['selected'] == 'no']
    # Try to maximize library diversity
    libraries = df_unselected['library'].unique().tolist()
    selected_ids = set()
    per_lib = max(1, sample_size // len(libraries))
    for lib in libraries:
        lib_df = df_unselected[df_unselected['library'] == lib]
        n = min(per_lib, len(lib_df))
        if n > 0:
            sampled = lib_df.sample(n, random_state=random_state)
            selected_ids.update(sampled['snippet_id'].tolist())
    # If not enough, fill up with randoms from remaining
    if len(selected_ids) < sample_size:
        remaining = df_unselected[~df_unselected['snippet_id'].isin(selected_ids)]
        if len(remaining) > 0:
            extra = remaining.sample(min(sample_size - len(selected_ids), len(remaining)), random_state=random_state)
            selected_ids.update(extra['snippet_id'].tolist())
    df.loc[df['snippet_id'].isin(selected_ids), 'selected'] = 'yes'
    df.to_csv(output_path, index=False)
    return list(selected_ids)

# 2. Extract functions for selected snippet_ids
def extract_functions(json_path: str, selected_ids: List[str]) -> Dict[str, str]:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    id_to_func = {}
    for entry in data:
        for snip in entry.get('snippets', []):
            snip_id = snip.get('snippet_id')
            if snip_id in selected_ids:
                func = snip.get('context', {}).get('function')
                if func:
                    id_to_func[snip_id] = func
    return id_to_func

# 3. Analyze with LLM
def analyze_with_llm(id_to_func: Dict[str, str], output_json: str):
    llm = ChatOpenAI(model="gpt-5-mini", temperature=0.2)
    results = {}
    for snip_id, func in id_to_func.items():
        prompt = PROMPT_WITH_CATEGORIES_ONLY.format(function=func)
        logging.info(f"Querying LLM for snippet_id={snip_id}")
        try:
            response = llm.invoke(prompt)
            print(f"LLM response for snippet_id={snip_id}: {str(response)[:200]}")
            logging.info(f"LLM response for snippet_id={snip_id}: {str(response)[:200]}")
            results[snip_id] = {
                'function': func,
                'llm_output': response.content if hasattr(response, 'content') else str(response)
            }
        except Exception as e:
            logging.error(f"LLM error for snippet_id={snip_id}: {e}")
            results[snip_id] = {
                'function': func,
                'llm_output': f'LLM error: {e}'
            }
    with open(output_json, 'w', encoding='utf-8') as f:
        f.write(json.dumps(results, indent=2))

# 4. Save results to CSV
def save_results_to_csv(results_json: str, output_csv: str):
    with open(results_json, 'r', encoding='utf-8') as f:
        results = json.load(f)
    rows = []
    for snip_id, v in results.items():
        function = v.get('function', '')
        llm_output = v.get('llm_output', '')
        # Try to parse the LLM output as JSON, else fallback
        smell = rationale = confidence = ''
        try:
            parsed = json.loads(llm_output)
            if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                smell = parsed[0].get('smell', '')
                rationale = parsed[0].get('rationale', '')
                confidence = parsed[0].get('confidence', '')
        except Exception:
            pass
        rows.append({
            'snippet_id': snip_id,
            'function': function,
            'smell': smell,
            'rationale': rationale,
            'confidence': confidence
        })
    pd.DataFrame(rows).to_csv(output_csv, index=False, sep=';')

# 5. Save results to Excel
def save_results_to_excel(results_json: str, output_excel: str):
    with open(results_json, 'r', encoding='utf-8') as f:
        results = json.load(f)
    rows = []
    for snip_id, v in results.items():
        function = v.get('function', '')
        llm_output = v.get('llm_output', '')
        smell = rationale = confidence = ''
        try:
            parsed = json.loads(llm_output)
            if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                smell = parsed[0].get('smell', '')
                rationale = parsed[0].get('rationale', '')
                confidence = parsed[0].get('confidence', '')
        except Exception:
            pass
        rows.append({
            'snippet_id': snip_id,
            'function': function,
            'smell': smell,
            'rationale': rationale,
            'confidence': confidence
        })
    pd.DataFrame(rows).to_excel(output_excel, index=False)

# CLI entry point
def cli_llm_logging_smell_analysis(args=None):
    csv_in = os.path.join(os.path.dirname(__file__), "..", "data", "logging_dataset_sampled_snippets_selected_352.csv")
    csv_out = os.path.join(os.path.dirname(__file__), "..", "data", "logging_dataset_sampled_snippets_selected_1410.csv")
    json_in = os.path.join(os.path.dirname(__file__), "..", "data", "logging_dataset_filtered_function.json")
    llm_json = os.path.join(os.path.dirname(__file__), "..", "data", "llm_logging_smell_results.json")
    final_excel = os.path.join(os.path.dirname(__file__), "..", "data", "llm_logging_smell_results.xlsx")
    selected_ids = mark_selected_snippets(csv_in, csv_out)
    id_to_func = extract_functions(json_in, selected_ids)
    analyze_with_llm(id_to_func, llm_json)
    save_results_to_excel(llm_json, final_excel)
    print(f"Done. Results saved to {final_excel}")
