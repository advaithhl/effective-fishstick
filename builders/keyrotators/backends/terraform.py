from terrasnek.api import TFC

from os import environ as os_environ


def _get_api():
    tf_token = os_environ['TF_API_TOKEN']
    tf_organization_name = os_environ['TF_CLOUD_ORGANIZATION']

    api = TFC(tf_token)
    api.set_org(tf_organization_name)
    return api


def _get_workspace_id(api, workspace_name):
    workspaces = api.workspaces.list()
    for workspace in workspaces['data']:
        if workspace['attributes']['name'] == workspace_name:
            return workspace['id']


def _get_varset_vars_id(api, workspace_id):
    var_sets = api.var_sets.list_for_workspace(workspace_id)
    # Only one variable set is assocated to one workspace.
    var_set = var_sets['data'][0]
    ret_value = [var_set['id']]

    var_ids = [var['id'] for var in var_set['relationships']['vars']['data']]
    ret_value.append(var_ids)
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
    payload = _get_update_var_in_varset_payload(
        payload_key,
        payload_value,
        payload_description,
        payload_sensitivity
    )
    api.var_sets.update_var_in_varset(var_set_id, var_id, payload)


def _update_aws_keys(workspace_name, aws_access_key_id, aws_secret_access_key):
    api = _get_api()
    workspace_id = _get_workspace_id(api, workspace_name)
    var_set_id, var_ids = _get_varset_vars_id(api, workspace_id)
    descriptions = [
        'Autorotated AWS access key for effective-fishstick',
        'Autorotated AWS secret key for effective-fishstick'
    ]
    _update_variable(
        api, var_set_id, var_ids[0],
        'AWS_ACCESS_KEY_ID', aws_access_key_id,
        descriptions[0], True
    )
    _update_variable(
        api, var_set_id, var_ids[1],
        'AWS_SECRET_ACCESS_KEY', aws_secret_access_key,
        descriptions[1], True
    )


def update_aws_keys(workspace_name, aws_access_key_id, aws_secret_access_key):
    try:
        _update_aws_keys(workspace_name, aws_access_key_id, aws_secret_access_key)
    except Exception as e:
        print(e)
        return False
    return True

