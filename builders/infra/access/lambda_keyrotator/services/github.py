from base64 import b64encode
from json import dumps
from os import environ as os_environ

import requests
from nacl import encoding, public


def _get_github_api_headers(github_pat):
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f'Bearer {github_pat}',
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get_repo_id(repo_owner, repo_name, github_pat):
    headers = _get_github_api_headers(github_pat)
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}'
    response = requests.get(
        url=url,
        headers=headers
    )
    if response.ok:
        return response.json()['id']
    exc_json = response.json()
    exc_json['status_code'] = response.status_code
    exc = RuntimeError(dumps(exc_json))
    raise exc


def _get_repo_public_key(repo_owner, repo_name, github_pat):
    headers = _get_github_api_headers(github_pat)
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/actions/secrets/public-key'
    response = requests.get(
        url=url,
        headers=headers
    )
    if response.ok:
        return [
            response.json()['key_id'],
            response.json()['key'],
        ]
    exc_json = response.json()
    exc_json['status_code'] = response.status_code
    exc = RuntimeError(dumps(exc_json))
    raise exc


def _get_env_public_key(repo_owner, repo_name, environment_name, github_pat):
    headers = _get_github_api_headers(github_pat)
    repository_id = _get_repo_id(repo_owner, repo_name, github_pat)
    url = f'https://api.github.com/repositories/{repository_id}/environments/{environment_name}/secrets/public-key'
    response = requests.get(
        url=url,
        headers=headers
    )
    if response.ok:
        return [
            response.json()['key_id'],
            response.json()['key'],
        ]
    exc_json = response.json()
    exc_json['status_code'] = response.status_code
    exc = RuntimeError(dumps(exc_json))
    raise exc


def _encrypt(public_key: str, secret_value: str) -> str:
    """Encrypt a Unicode string using the public key."""
    public_key = public.PublicKey(
        public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")


def _set_repo_secret_helper(repo_owner, repo_name, secret_name, secret_value):
    # May raise KeyError
    github_pat = os_environ['GITHUB_PERSONAL_ACCESS_TOKEN']
    gh_public_key_id, gh_public_key = _get_repo_public_key(
        repo_owner, repo_name, github_pat)  # May raise RuntimeError
    encrypted_secret = _encrypt(gh_public_key, secret_value)
    headers = _get_github_api_headers(github_pat)
    payload = {
        "encrypted_value": encrypted_secret,
        "key_id": gh_public_key_id,
    }
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/actions/secrets/{secret_name}'
    response = requests.put(
        url=url,
        headers=headers,
        data=dumps(payload)
    )
    return response.status_code


def _set_environment_secret_helper(repo_owner, repo_name, environment_name, secret_name, secret_value):
    # May raise KeyError
    github_pat = os_environ['GITHUB_PERSONAL_ACCESS_TOKEN']
    gh_public_key_id, gh_public_key = _get_env_public_key(
        repo_owner, repo_name, environment_name, github_pat)  # May raise RuntimeError
    repository_id = _get_repo_id(
        repo_owner, repo_name, github_pat)  # May raise RuntimeError
    encrypted_secret = _encrypt(gh_public_key, secret_value)
    headers = _get_github_api_headers(github_pat)
    payload = {
        "encrypted_value": encrypted_secret,
        "key_id": gh_public_key_id,
    }
    url = f'https://api.github.com/repositories/{repository_id}/environments/{environment_name}/secrets/{secret_name}'
    response = requests.put(
        url=url,
        headers=headers,
        data=dumps(payload)
    )
    return response.status_code


def set_repo_secret(secret_name, secret_value):
    repo_owner = 'advaithhl'
    repo_name = 'effective-fishstick'
    return _set_repo_secret_helper(
        repo_owner,
        repo_name,
        secret_name,
        secret_value
    ) in (201, 204)


def set_environment_secret(environment_name, secret_name, secret_value):
    repo_owner = 'advaithhl'
    repo_name = 'effective-fishstick'
    return _set_environment_secret_helper(
        repo_owner,
        repo_name,
        environment_name,
        secret_name,
        secret_value,
    ) in (201, 204)
