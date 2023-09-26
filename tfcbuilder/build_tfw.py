# This code creates a workspace in an existing organization. The created
# workspace maybe related to one environment (like dev, test, or prod).
# Additionally, a variable set is created for the workspace and an AWS key is
# added to the variable set. The environment variables needed for this script
# are as follows:
#
# `TF_API_TOKEN`: A user token which has access to create organizations.
# `TF_CLOUD_ORGANIZATION`: Name of your existing organization.
# `ENVIRONMENT_NAME`: Name of the environment this workspace corresponds to.
# `TF_WORKSPACE`: Desired name of your workspace.
#
# `AWS_ACCESS_KEY_ID`: An access key to AWS.
# `AWS_SECRET_ACCESS_KEY`: The "password" to the access key.
# Sample usage:
# $ python3 build_tfw.py
# Workspace named 'workspace_dev' with ID 'ws-123456789abcdea' created.
# Variable set named 'variables_dev' created under workspace 'workspace_dev'.

import os

from terrasnek.api import TFC
from terrasnek.exceptions import (TFCHTTPNotFound, TFCHTTPUnclassified,
                                  TFCHTTPUnprocessableEntity)

if __name__ == '__main__':
    try:
        tf_token = os.environ['TF_API_TOKEN']
        tf_organization_name = os.environ['TF_CLOUD_ORGANIZATION']
        environment = os.environ['ENVIRONMENT_NAME']

        aws_key = os.environ['AWS_ACCESS_KEY_ID']
        aws_secret_key = os.environ['AWS_SECRET_ACCESS_KEY']
    except KeyError as ke:
        # Log the missing environment variable and exit.
        print(f'Unable to find required environment variable: {ke}')
        exit(1)

    # Initialize the API with the user token.
    api = TFC(tf_token)
    # The following call configures the API to use the newly created
    # workspace for future calls (like creating workspaces).
    # Note that this DOES NOT check if the organization exists or not.
    api.set_org(tf_organization_name)

    try:
        tf_workspace_name = os.environ['TF_WORKSPACE']
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
    except TFCHTTPNotFound as no_organization_error:
        # Log the error and say that workspace couldn't be created.
        print(
            f"Failed to create workspace named '{tf_workspace_name}'.")
        print(no_organization_error)
        exit(4)
    else:
        # Get the workspace ID.
        workspace_id = response['data']['id']

        # Log that the workspace was created.
        print(
            f"Workspace named '{tf_workspace_name}' with ID '{workspace_id}' created.")

    # Create variable set for the workspace.
    varset_name = f"variables_{environment.lower()}"
    varset_desc = f"Automatically created variable set for {environment} environment."

    # Payload for making API call to create a workspace.
    create_varset_payload = {
        "data": {
            "type": "varsets",
            "attributes": {
                "name": varset_name,
                "description": varset_desc,
                "global": False,
            },
            "relationships": {
                "workspaces": {
                    "data": [
                        {
                            "id": workspace_id,
                            "type": "workspaces"
                        }
                    ]
                },
                "vars": {
                    "data": [
                        {
                            "type": "vars",
                            "attributes": {
                                "key": 'AWS_ACCESS_KEY_ID',
                                "value": aws_key,
                                "category": "env",
                                "sensitive": True
                            }
                        },
                        {
                            "type": "vars",
                            "attributes": {
                                "key": 'AWS_SECRET_ACCESS_KEY',
                                "value": aws_secret_key,
                                "category": "env",
                                "sensitive": True
                            }
                        },
                    ]
                },
            }
        }
    }

    # Try to create a variable set.
    try:
        api.var_sets.create(create_varset_payload)
    except TFCHTTPUnclassified as invalid_token_error:
        # Log the error and say that variable set couldn't be created.
        print(
            f"Failed to create variable set named '{varset_name}'.")
        print(invalid_token_error)
        exit(5)
    except TFCHTTPUnprocessableEntity as name_exists_error:
        # Log the error and say that variable set couldn't be created.
        print(
            f"Failed to create variable set named '{varset_name}'.")
        print(name_exists_error)
        exit(5)
    else:
        print(
            f"Variable set named '{varset_name}' created under workspace '{tf_workspace_name}'.")
