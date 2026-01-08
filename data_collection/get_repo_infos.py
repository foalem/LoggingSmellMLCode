import requests
import random
from config.constant import GitHub_CONFIG
from util.requests_time import delay_request
import logging

def check_repo_status(repo_full_name):
    tokens = GitHub_CONFIG['token']
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'token {random.choice(tokens)}'
    }
    url = f'https://api.github.com/repos/{repo_full_name}'
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return {'repository_full_name': repo_full_name, 'archived': data.get('archived', False), 'accessible': True}
        else:
            logging.warning(f"Repo {repo_full_name} not accessible. Status: {response.status_code}")
            return {'repository_full_name': repo_full_name, 'archived': None, 'accessible': False}
    except Exception as e:
        logging.error(f"Error checking repo {repo_full_name}: {e}")
        return {'repository_full_name': repo_full_name, 'archived': None, 'accessible': False}
    finally:
        delay_request(1)

def collect_repos_info(repo_names):
    results = []
    for repo in repo_names:
        results.append(check_repo_status(repo))
    return results

