from datetime import datetime, timedelta
from os import environ as os_environ

from github import set_repo_secret as github_set_repo_secret
from terrasnek.api import TFC
from terrasnek.exceptions import TFCHTTPUnauthorized

TF_TOKEN_NAME_TEMPLATE = 'Autorotated token for effective-fishstick'


def _get_api(tf_token=None, tf_organization_name=None):
    if not tf_token:
        tf_token = os_environ['TF_API_TOKEN']
    if not tf_organization_name:
        tf_organization_name = os_environ['TF_CLOUD_ORGANIZATION']

    api = TFC(tf_token)
    api.set_org(tf_organization_name)
    return api


def _get_user_id(api):
    return api.account.show()['data']['id']


def _generate_new_token_name(version):
    return f'{TF_TOKEN_NAME_TEMPLATE} - #{version}'


def _get_current_token_details(api):
    user_id = _get_user_id(api)
    user_tokens = api.user_tokens.list(user_id)

    version = 0
    token_id = None

    for token_data in user_tokens['data']:
        token_description = token_data['attributes']['description']
        if token_description.startswith(TF_TOKEN_NAME_TEMPLATE):
            version = int(token_description.split('#')[1])
            token_id = token_data['id']
    return (version, token_id)


def _get_expiry_time():
    utcnow = datetime.utcnow()
    timedelta_days21 = timedelta(days=21)
    expirytime = utcnow + timedelta_days21
    return expirytime


def _generate_new_token(api, version):
    user_id = _get_user_id(api)
    token_name = _generate_new_token_name(version)

    expiry = _get_expiry_time()
    payload = {
        "data": {
            "type": "authentication-tokens",
            "attributes": {
                "description": token_name,
                "expired-at": expiry.isoformat()
            }
        }
    }

    response = api.user_tokens.create(user_id, payload)
    token_id, token = response['data']['id'], response['data']['attributes']['token']
    return (token_name, token_id, token)


def _test_new_token(current_api, token_id, token):
    new_api = _get_api(token)

    time_before_api_usage = datetime.utcnow()

    # Gather user ID using both tokens.
    user_id = _get_user_id(current_api)
    try:
        test_user_id = _get_user_id(new_api)
    except TFCHTTPUnauthorized:
        return False

    # Check if both APIs give same results.
    if test_user_id == user_id:
        # Use current API to fetch last used time of new API.
        new_api_last_used_str = current_api.user_tokens.show(
            token_id)['data']['attributes']['last-used-at']
        new_api_last_used_tzaware = datetime.fromisoformat(
            new_api_last_used_str)
        # Use naive datetime objects.
        new_api_last_used = new_api_last_used_tzaware.replace(tzinfo=None)

        # Check if new token was indeed used in the check.
        if new_api_last_used > time_before_api_usage:
            return True


def _destroy_token(api, token_id):
    api.user_tokens.destroy(token_id)


def _rotate_key_on_github(token):
    return github_set_repo_secret('TF_API_TOKEN', token)


def rotatekeys():
    successes = {}
    api = _get_api()
    current_version, current_token_id = _get_current_token_details(api)
    _, new_token_id, new_token = _generate_new_token(api, current_version + 1)
    new_token_working = _test_new_token(api, new_token_id, new_token)
    if new_token_working:
        if current_token_id:
            _destroy_token(api, current_token_id)
        github_keyrotation_result = _rotate_key_on_github(new_token)
        successes['github'] = github_keyrotation_result
    else:
        _destroy_token(api, new_token_id)
        successes['github'] = False
    return successes
