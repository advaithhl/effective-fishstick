import logging
from datetime import datetime, timedelta
from os import environ as os_environ

from keyrotators.backends.github import \
    set_repo_secret as github_set_repo_secret
from terrasnek.api import TFC
from terrasnek.exceptions import (TFCException, TFCHTTPNotFound,
                                  TFCHTTPUnauthorized)

logger = logging.getLogger(__name__)
TF_TOKEN_NAME_TEMPLATE = 'Autorotated token for effective-fishstick'


def _get_api(tf_token=None, tf_organization_name=None):
    if not tf_token:
        logger.debug(
            "'tf_token' not provided. Falling back to environment variable.")
        try:
            tf_token = os_environ['TF_API_TOKEN']
        except KeyError:
            logger.exception("No environment variable named 'TF_API_TOKEN'."
                             "This is required as no token was given in method arguments.")
            return None
    if not tf_organization_name:
        logger.debug(
            "'tf_organization_name' not provided. Falling back to environment variable.")
        try:
            tf_organization_name = os_environ['TF_CLOUD_ORGANIZATION']
        except KeyError:
            logger.exception("No environment variable named 'TF_CLOUD_ORGANIZATION'."
                             "This is required as no token was given in method arguments.")
            return None

    api = TFC(tf_token)
    api.set_org(tf_organization_name)
    return api


def _get_user_id(api):
    try:
        return api.account.show()['data']['id']
    except TFCHTTPUnauthorized:
        logger.exception(
            'API object is unauthorised. Please check the token used to '
            'initialize the API.')
        return None


def _generate_new_token_name(version):
    return f'{TF_TOKEN_NAME_TEMPLATE} - #{version}'


def _get_current_token_details(api):
    user_id = _get_user_id(api)
    if not user_id:
        return None
    logger.debug(f"User ID parsed to be '{user_id}'.")
    user_tokens = api.user_tokens.list(user_id)

    version = 0
    token_id = None

    for token_data in user_tokens['data']:
        token_description = token_data['attributes']['description']
        if token_description.startswith(TF_TOKEN_NAME_TEMPLATE):
            version = int(token_description.split('#')[1])
            token_id = token_data['id']
    logger.debug(f"Current token has version #{version}.")
    logger.debug(f"Current token has ID '{token_id}'.")
    return (version, token_id)


def _get_expiry_time():
    utcnow = datetime.utcnow()
    timedelta_days21 = timedelta(days=21)
    expirytime = utcnow + timedelta_days21
    return expirytime


def _generate_new_token(api, version):
    user_id = _get_user_id(api)
    if not user_id:
        return None
    logger.debug(f"New token will be generated for '{user_id}'.")
    token_name = _generate_new_token_name(version)

    expiry = _get_expiry_time()
    logger.debug(f"New token will be set to expire at '{expiry}'.")
    payload = {
        "data": {
            "type": "authentication-tokens",
            "attributes": {
                "description": token_name,
                "expired-at": expiry.isoformat()
            }
        }
    }

    try:
        response = api.user_tokens.create(user_id, payload)
    except TFCException:
        logger.exception(
            'An error occured while trying to generate a new token.')
        return None
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
    try:
        api.user_tokens.destroy(token_id)
    except TFCHTTPNotFound:
        logger.exception(
            f"Token with ID '{token_id}' does not exist "
            "or user is unauthorised to perform deletion.")
        return False
    else:
        logger.debug(f"Token with ID {token_id} has been destroyed.")
        return True


def _rotate_key_on_github(token):
    return github_set_repo_secret('TF_API_TOKEN', token)


def rotatekeys():
    logger.info('TFC user token is being rotated.')
    successes = {
        'creation': False,
        'testing': False,
        'destruction': None,
        'github': False,
    }
    api = _get_api()
    if not api:
        logger.critical(
            'TFC API could not be initialized. See accompanying logs for more info.')
        return successes
    _current_token_details = _get_current_token_details(api)
    if not _current_token_details:
        logger.critical('TFC API initialized with invalid credentials.')
        return successes
    current_version, current_token_id = _current_token_details
    _new_token_details = _generate_new_token(api, current_version + 1)
    if not _new_token_details:
        logger.critical('New TFC token generation was unsuccessful.'
                        'See accompanying logs for more info.')
        return successes
    successes['creation'] = True
    _, new_token_id, new_token = _new_token_details
    logger.info(f'Newly generated token has version #{current_version + 1}.')
    logger.debug(f"Newly generated token has ID '{new_token_id}'.")
    new_token_working = _test_new_token(api, new_token_id, new_token)
    if new_token_working:
        successes['testing'] = True
        logger.info('Newly generated token passed the test.')
        if current_token_id:
            logger.debug(
                f"Destructing token with ID '{current_token_id}' as it had "
                "been previously autogenerated as part of key rotation.")
            token_destruction_result = _destroy_token(api, current_token_id)
            if token_destruction_result:
                successes['destruction'] = True
                logger.info('Destruction of current token is successful.')
            else:
                successes['destruction'] = False
                logger.warning('Destruction of current token has failed. '
                               'This can cause problems in future automatic '
                               'keyrotations if the problem is not fixed!')
        else:
            logger.debug(
                'No token found which was previously autogenerated as part of key rotation.')
        github_keyrotation_result = _rotate_key_on_github(new_token)
        if github_keyrotation_result:
            logger.info(
                'Newly generated token was successfully stored as Github secret.')
        else:
            logger.error('Newly generated token could not be saved.')
        successes['github'] = github_keyrotation_result
    else:
        logger.warning('Newly generated token failed the test.')
        token_destruction_result = _destroy_token(api, new_token_id)
        if token_destruction_result:
            logger.info('Newly generated destroyed as test had failed.')
        else:
            logger.warning('Newly generated token could not be destroyed.')
    return successes
