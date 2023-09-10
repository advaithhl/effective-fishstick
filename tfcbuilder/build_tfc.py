# This code creates an organization in the Terraform cloud and multiple
# workspaces as defined by corresponding environment variables. The environment
# variables required for this script are as follows:
#
# `TF_API_TOKEN`: A user token which has access to create organizations.
# `TF_CLOUD_ORGANIZATION`: Desired name of your organization.
# `TF_EMAIL`: Desired email to be assigned to your organization.
# `TF_WORKSPACE_environment`: Desired name of your workspace for each
# environment. There must be a corresponding `TF_WORKSPACE_environment` for
# each item in the `environments` list defined in code. For example, if
# `environments` = ['DEV', 'TEST', 'PROD'], the following variables are required:
# `TF_WORKSPACE_DEV`, `TF_WORKSPACE_TEST`, and `TF_WORKSPACE_PROD`.
#
# Sample usage:
# $ python3 build_tfc.py
# Organization named 'testing-organization' created.
# Workspace named 'workspace_dev' created.
# Workspace named 'workspace_test' created.
# Workspace named 'workspace_prod' created.

import os

from terrasnek.api import TFC
from terrasnek.exceptions import TFCHTTPUnclassified, TFCHTTPUnprocessableEntity

# Define the environments here.
environments = [
    'DEV',
    'TEST',
    'PROD',
]

# Dynamically populated `dict` containing workspaces and their IDs.
workspace_ids = {}

if __name__ == '__main__':
    # Try to fetch the required environment variables.
    try:
        tf_token = os.environ['TF_API_TOKEN']
        tf_organization_name = os.environ['TF_CLOUD_ORGANIZATION']
        tf_email = os.environ['TF_EMAIL']
    except KeyError as ke:
        # Log the missing environment variable and exit.
        print(f'Unable to find required environment variable: {ke}')
        exit(1)

    # Initialize the API with the user token.
    api = TFC(tf_token)

    # Payload for making API call to create an organization.
    create_org_payload = {
        "data": {
            "type": "organizations",
            "attributes": {
                "name": tf_organization_name,
                "email": tf_email
            }
        }
    }

    # Try to create the organization.
    try:
        api.orgs.create(create_org_payload)
    except TFCHTTPUnclassified as invalid_token_error:
        # Log the error and say that organization couldn't be created.
        print('Failed to create organization.')
        print(invalid_token_error)
        exit(2)
    except TFCHTTPUnprocessableEntity as name_exists_error:
        # Log the error and say that organization couldn't be created.
        print('Failed to create organization.')
        print(name_exists_error)
        exit(2)
    else:
        # Log that the organization was created.
        print(f"Organization named '{tf_organization_name}' created.")
        # The following call configures the API to use the newly created
        # workspace for future calls (like creating workspaces).
        api.set_org(tf_organization_name)

    # Dynamically populated `dict` containing workspaces and their IDs.
    # Used for creating workspace-specific environment variables.
    workspace_ids = {}

    # Loop for each environment.
    for environment in environments:
        # Try to fetch the name of the environment-specific workspace.
        try:
            tf_workspace_name = os.getenv(f'TF_WORKSPACE_{environment}')
        except KeyError as ke:
            # Log the missing environment variable and exit.
            print(f'Unable to find required environment variable: {ke}')
            exit(3)
        else:
            # Payload for making API call to create a workspace.
            create_workspace_payload = {
                "data": {
                    "attributes": {
                        "name": tf_workspace_name,
                        "description": f"Automatically created workspace for {environment} environment."
                    },
                    "type": "workspaces"
                }
            }

            # Try to create a workspace specific to the environment.
            try:
                response = api.workspaces.create(create_workspace_payload)
            except TFCHTTPUnclassified as invalid_token_error:
                # Log the error and say that workspace couldn't be created.
                print(
                    f"Failed to create workspace named '{tf_workspace_name}'.")
                print(invalid_token_error)
                exit(4)
            except TFCHTTPUnprocessableEntity as name_exists_error:
                # Log the error and say that workspace couldn't be created.
                print(
                    f"Failed to create workspace named '{tf_workspace_name}'.")
                print(name_exists_error)
                exit(4)
            else:
                # Get the workspace ID and save to `workspace_ids` dict.
                workspace_id = response['data']['id']
                workspace_ids[environment] = workspace_id

                # Log that the workspace was created.
                print(
                    f"Workspace named '{tf_workspace_name}' with ID '{workspace_id}' created.")
