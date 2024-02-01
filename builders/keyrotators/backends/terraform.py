import logging
from os import environ as os_environ

from terrasnek.api import TFC

logger = logging.getLogger(__name__)


def _get_api():
    logger.debug('Trying to get Terraform Cloud API client.')
    try:
        tf_token = os_environ['TF_API_TOKEN']
    except KeyError:
        logger.exception("No environment variable named 'TF_API_TOKEN'."
                         "This is required as no token was given in method arguments.")
        return None
    try:
        tf_organization_name = os_environ['TF_CLOUD_ORGANIZATION']
    except KeyError:
        logger.exception("No environment variable named 'TF_CLOUD_ORGANIZATION'."
                         "This is required as no token was given in method arguments.")
        return None

    api = TFC(tf_token)
    api.set_org(tf_organization_name)
    logger.debug('Terraform Cloud API client created.')
    return api


def _get_workspace_id(api, workspace_name):
    logger.debug(f'Trying to get workspace ID for workspace {workspace_name}')
    search_param = {
        'search': workspace_name
    }
    workspaces = api.workspaces.list(search=search_param)
    logger.debug(
        f'Fetched workspace ID {workspaces["data"][0]["id"]} for {workspace_name}')
    return workspaces['data'][0]['id']


def _get_varset_vars_id(api, workspace_id):
    logger.debug(f'Fetching variable set for workspace {workspace_id}')
    var_sets = api.var_sets.list_for_workspace(workspace_id)
    logger.debug('Fetched variable set')
    # Only one variable set is assocated to one workspace.
    var_set = var_sets['data'][0]
    ret_value = [var_set['id']]

    var_ids = [var['id'] for var in var_set['relationships']['vars']['data']]
    ret_value.append(var_ids)
    logger.debug(
        f'Fetched variable IDs {var_ids} for workspace {workspace_id}')
    return ret_value


def _get_update_var_in_varset_payload(
        key, value, description, sensitivity):
    return {
        "data": {
            "type": "vars",
            "attributes": {
                "key": key,
                "value": value,
                "description": description,
                "sensitive": sensitivity,
                "category": "terraform",
                "hcl": False
            }
        }
    }


def _update_variable(
        api, var_set_id, var_id,
        payload_key, payload_value,
        payload_description, payload_sensitivity):
    logger.debug(f'Creating payload to update variable {payload_key}')
    payload = _get_update_var_in_varset_payload(
        payload_key,
        payload_value,
        payload_description,
        payload_sensitivity
    )

    logger.debug(f'Calling API to update variable {payload_key}')
    api.var_sets.update_var_in_varset(var_set_id, var_id, payload)
    logger.info(f'Updated variable {payload_key}')


def _update_aws_keys(workspace_name, aws_access_key_id, aws_secret_access_key):
    logger.info(f'Trying to update AWS keys for {workspace_name}')
    api = _get_api()
    workspace_id = _get_workspace_id(api, workspace_name)
    var_set_id, var_ids = _get_varset_vars_id(api, workspace_id)
    descriptions = [
        'Autorotated AWS access key for effective-fishstick',
        'Autorotated AWS secret key for effective-fishstick'
    ]
    logger.debug('Trying to update access key.')
    _update_variable(
        api, var_set_id, var_ids[0],
        'AWS_ACCESS_KEY_ID', aws_access_key_id,
        descriptions[0], True
    )
    logger.debug('Trying to update secret key.')
    _update_variable(
        api, var_set_id, var_ids[1],
        'AWS_SECRET_ACCESS_KEY', aws_secret_access_key,
        descriptions[1], True
    )


def update_aws_keys(workspace_name, aws_access_key_id, aws_secret_access_key):
    logger.info(f"Trying to update AWS keys for {workspace_name}")
    try:
        _update_aws_keys(workspace_name, aws_access_key_id,
                         aws_secret_access_key)
    except Exception:
        logger.exception('An error occurred when updating AWS keys.')
        return False
    logger.info(
        f"Successfully updated AWS keys in workspace '{workspace_name}'.")
    return True
