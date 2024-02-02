import logging
from base64 import b64encode
from json import dumps
from os import environ as os_environ

import requests
from nacl import encoding, public

logger = logging.getLogger(__name__)


# A dictionary which maps possible values of `ENVIRONMENT_NAME` repo variable
# name to Github environment names.
environment_mapping = {
    'PROD': 'production',
    'TEST': 'test',
    'DEV': 'development',
}

def _get_github_api_headers(github_pat):
    logger.debug(
        'Getting Github API headers. This is usually for further API calls.')
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f'Bearer {github_pat}',
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get_repo_id(repo_owner, repo_name, github_pat):
    headers = _get_github_api_headers(github_pat)
    logger.debug('Making GET call to get repo ID: '
                 f"Repo owner: '{repo_owner}', Repo name: '{repo_name}'.")
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}'
    response = requests.get(
        url=url,
        headers=headers
    )
    logger.debug(f"Reponse status: {response.status_code}.")
    if response.ok:
        return response.json()['id']
    exc_json = response.json()
    exc_json['status_code'] = response.status_code
    exc = RuntimeError(dumps(exc_json))
    raise exc


def _get_repo_public_key(repo_owner, repo_name, github_pat):
    logger.debug('Fetching headers for getting repo public key.')
    headers = _get_github_api_headers(github_pat)

    logger.debug('Making GET call to get repo public key: '
                 f"Repo owner: '{repo_owner}', Repo name: '{repo_name}'.")
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/actions/secrets/public-key'
    response = requests.get(
        url=url,
        headers=headers
    )
    logger.debug(f"Reponse status: {response.status_code}.")
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
    logger.debug('Fetching headers for getting environment public key.')
    headers = _get_github_api_headers(github_pat)

    logger.debug('Trying to get repo ID for getting public key.')
    try:
        repository_id = _get_repo_id(repo_owner, repo_name, github_pat)
    except RuntimeError:
        logger.exception(
            'An error occurred when fetching repository ID.')
        return None
    else:
        logger.debug('Repo ID fetched successfully.')

    logger.debug('Making GET call to get environment public key: '
                 f"Repo ID: '{repository_id}', Environment: '{environment_name}'.")
    url = f'https://api.github.com/repositories/{repository_id}/environments/{environment_name}/secrets/public-key'
    response = requests.get(
        url=url,
        headers=headers
    )
    logger.debug(f"Reponse status: {response.status_code}.")
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
    ret_value = b64encode(encrypted).decode("utf-8")
    logger.debug('Encryption was successful.')
    return ret_value


def _set_repo_secret_helper(repo_owner, repo_name, secret_name, secret_value):
    try:
        github_pat = os_environ['GITHUB_PERSONAL_ACCESS_TOKEN']
    except KeyError:
        logger.exception('Github PAT was not found in environment variables.')
        return None
    else:
        logger.debug(
            'Github PAT successfully fetched from environment variable.')

    logger.debug('Trying to get repository public key.')
    try:
        gh_public_key_id, gh_public_key = _get_repo_public_key(
            repo_owner, repo_name, github_pat)
    except RuntimeError:
        logger.exception(
            'An error occurred when fetching repository public key.')
        return None
    else:
        logger.debug(
            f"Github repository public key with ID '{gh_public_key_id}' fetched successfully.")

    logger.debug(
        f"Encrypting secret value with Github repository public key '{gh_public_key_id}'.")
    encrypted_secret = _encrypt(gh_public_key, secret_value)

    logger.debug('Fetching headers for setting repo secret.')
    headers = _get_github_api_headers(github_pat)

    logger.debug('Making PUT call to create/update repo secret: '
                 f"Repo owner: '{repo_owner}', Repo name: '{repo_name}', "
                 f"Secret name: '{secret_name}'")
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
    logger.debug(f"Reponse status: {response.status_code}.")
    return response.status_code


def _set_environment_secret_helper(repo_owner, repo_name, environment_name, secret_name, secret_value):
    try:
        github_pat = os_environ['GITHUB_PERSONAL_ACCESS_TOKEN']
    except KeyError:
        logger.exception('Github PAT was not found in environment variables.')
        return None
    else:
        logger.debug(
            'Github PAT successfully fetched from environment variable.')

    logger.debug('Trying to get environment public key.')
    try:
        gh_public_key_id, gh_public_key = _get_env_public_key(
            repo_owner, repo_name, environment_name, github_pat)
    except RuntimeError:
        logger.exception(
            'An error occurred when fetching environment public key.')
        return None
    else:
        logger.debug(
            f"Github environment '{environment_name}' public key with ID '{gh_public_key_id}' fetched successfully.")

    logger.debug(
        'Trying to get repo ID for setting/updating environment secret.')
    try:
        repository_id = _get_repo_id(
            repo_owner, repo_name, github_pat)
    except RuntimeError:
        logger.exception(
            'An error occurred when fetching repository ID.')
        return None
    else:
        logger.debug('Repo ID fetched successfully.')

    logger.debug(
        f"Encrypting secret value with Github environment public key '{gh_public_key_id}'.")
    encrypted_secret = _encrypt(gh_public_key, secret_value)

    logger.debug('Fetching headers for setting environment secret.')
    headers = _get_github_api_headers(github_pat)

    logger.debug('Making PUT call to create/update repo secret: '
                 f"Repository ID: '{repository_id}', Environment name: '{environment_name}', "
                 f"Secret name: '{secret_name}'.")
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
    logger.debug(f"Reponse status: {response.status_code}.")
    return response.status_code


def set_repo_secret(secret_name, secret_value):
    repo_owner = 'advaithhl'
    repo_name = 'effective-fishstick'
    logger.debug(f"Repository owner name: '{repo_owner}'.")
    logger.debug(f"Repository name: '{repo_name}'.")
    logger.debug(f"Repository secret name: '{secret_name}'.")
    response_code = _set_repo_secret_helper(
        repo_owner,
        repo_name,
        secret_name,
        secret_value
    )

    if response_code == 201:
        actioned = 'created'
    elif response_code == 204:
        actioned = 'updated'
    else:
        logger.error(
            f"An error occured when creating/updating repository secret '{secret_name}'.")
        return False

    logger.info(
        f"Repository secret named '{secret_name}' has been {actioned} in '{repo_name}' "
        f"owned by '{repo_owner}'.")
    return True


def set_environment_secret(environment_name, secret_name, secret_value):
    repo_owner = 'advaithhl'
    repo_name = 'effective-fishstick'
    logger.debug(f"Repository owner name: '{repo_owner}'.")
    logger.debug(f"Repository name: '{repo_name}'.")
    logger.debug(f"Environment name: '{environment_name}'.")
    logger.debug(f"Environment secret name: '{secret_name}'.")

    response_code = _set_environment_secret_helper(
        repo_owner,
        repo_name,
        environment_name,
        secret_name,
        secret_value,
    )

    if response_code == 201:
        actioned = 'created'
    elif response_code == 204:
        actioned = 'updated'
    else:
        logger.error(
            f"An error occured when creating/updating environment secret '{secret_name}'.")
        return False

    logger.info(
        f"Environment secret named '{secret_name}' has been {actioned} in '{repo_name}' "
        f"owned by '{repo_owner}' under the environment '{environment_name}'.")
    return True
