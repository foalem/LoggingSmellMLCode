import pandas as pd
import os

def read_csv_file(filepath):
    return pd.read_csv(filepath)

def get_repo_names_from_csv(df):
    if 'repository_full_name' in df.columns:
        return df['repository_full_name'].tolist()
    raise ValueError('repository_full_name column not found')

def save_csv_file(df, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_csv(filepath, index=False)

