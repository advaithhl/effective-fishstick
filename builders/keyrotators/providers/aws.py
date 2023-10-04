from os import environ as os_environ

import backoff
import boto3
import boto3.session
from botocore.exceptions import ClientError
from keyrotators.backends.github import \
    set_environment_secret as github_set_environment_secret
from keyrotators.backends.terraform import \
    update_aws_keys as terraform_update_aws_keys

AWS_ACCESS_KEY_DESCRIPTION = 'Autorotated key for effective-fishstick'


def _get_session(aws_access_key_id=None, aws_secret_access_key=None, aws_region='ap-south-1'):
    if not aws_access_key_id:
        aws_access_key_id = os_environ['AWS_ACCESS_KEY_ID']
    if not aws_secret_access_key:
        aws_secret_access_key = os_environ['AWS_SECRET_ACCESS_KEY']

    session = boto3.session.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region
    )
    return session


def _delete_deactivated_keys(iam_client):
    all_access_keys = iam_client.list_access_keys()

    for access_key in all_access_keys['AccessKeyMetadata']:
        if access_key['Status'] == 'Inactive':
            access_key_id = access_key['AccessKeyId']
            iam_client.delete_access_key(
                AccessKeyId=access_key_id)


@backoff.on_exception(backoff.expo, ClientError, max_time=30)
def _get_username(iam_client):
    response = iam_client.get_user()
    return response['User']['UserName']


def _get_current_key_id(session):
    return session.get_credentials().get_frozen_credentials().access_key


def _generate_new_key(iam_client, description):
    response = iam_client.create_access_key()
    access_key_id = response['AccessKey']['AccessKeyId']
    access_key_secret = response['AccessKey']['SecretAccessKey']
    iam_client.tag_user(
        UserName=_get_username(iam_client),
        Tags=[{
            'Key': access_key_id,
            'Value': description,
        }]
    )
    return access_key_id, access_key_secret


def _test_new_key(iam_client, new_iam_client):
    # AWS seems to have delays in updating last_used times, so skipping.
    # time_before_key_usage = datetime.utcnow()

    username = _get_username(iam_client)
    try:
        test_username = _get_username(new_iam_client)
    except ClientError:
        return False

    if test_username == username:
        return True
        # new_key_last_used_tzaware = iam_client.get_access_key_last_used(
        #     AccessKeyId=new_access_key_id
        # )['AccessKeyLastUsed']['LastUsedDate']
        # new_key_last_used = new_key_last_used_tzaware.replace(tzinfo=None)

        # if new_key_last_used > time_before_key_usage:
        #     pass


def _deactivate_key(iam_client, access_key_id):
    iam_client.update_access_key(
        AccessKeyId=access_key_id,
        Status='Inactive'
    )


def _rotate_key_on_github(access_key_id, access_key_secret):
    r1 = github_set_environment_secret(
        'development', 'AWS_ACCESS_KEY_ID', access_key_id)
    r2 = github_set_environment_secret(
        'development', 'AWS_SECRET_ACCESS_KEY', access_key_secret)
    return r1 and r2


def _rotate_key_on_terraform(access_key_id, access_key_secret):
    r1 = terraform_update_aws_keys(
        'development', 'AWS_ACCESS_KEY_ID', access_key_id)
    r2 = terraform_update_aws_keys(
        'development', 'AWS_SECRET_ACCESS_KEY', access_key_secret)
    return r1 and r2


def rotatekeys():
    successes = {}
    session = _get_session()
    iam_client = session.client('iam')
    current_access_key_id = _get_current_key_id(session)
    _delete_deactivated_keys(iam_client)
    new_access_key_id, new_access_key_secret = _generate_new_key(
        iam_client, AWS_ACCESS_KEY_DESCRIPTION)
    new_session = _get_session(new_access_key_id, new_access_key_secret)
    new_iam_client = new_session.client('iam')
    new_key_working = _test_new_key(
        iam_client, new_iam_client)
    if new_key_working:
        _deactivate_key(iam_client, current_access_key_id)
        github_keyrotation_result = _rotate_key_on_github(
            new_access_key_id, new_access_key_secret)
        successes['github'] = github_keyrotation_result
        terraform_keyrotation_result = _rotate_key_on_terraform(
            new_access_key_id, new_access_key_secret)
        successes['terraform'] = terraform_keyrotation_result
    else:
        _deactivate_key(iam_client, new_access_key_id)
        successes['github'] = False
        successes['terraform'] = False
    return successes
