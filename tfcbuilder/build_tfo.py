# This code creates an organization in the Terraform cloud. The environment
# variables required for this script are as follows:
#
# `TF_API_TOKEN`: A user token which has access to create organizations.
# `TF_CLOUD_ORGANIZATION`: Desired name of your organization.
# `TF_EMAIL`: Desired email to be assigned to your organization.
#
# Sample usage:
# $ python3 build_tfo.py
# Organization named 'testing-organization' created.

import os

from terrasnek.api import TFC
from terrasnek.exceptions import TFCHTTPUnclassified, TFCHTTPUnprocessableEntity


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
