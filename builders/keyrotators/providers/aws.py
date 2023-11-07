import logging
from os import environ as os_environ

import backoff
import boto3
import boto3.session
from botocore.exceptions import ClientError
from keyrotators.backends.github import \
    set_environment_secret as github_set_environment_secret
from keyrotators.backends.terraform import \
    update_aws_keys as terraform_update_aws_keys

logger = logging.getLogger(__name__)
AWS_ACCESS_KEY_DESCRIPTION = 'Autorotated key for effective-fishstick'


def _get_session(aws_access_key_id=None, aws_secret_access_key=None, aws_region='ap-south-1'):
    if not aws_access_key_id:
        logger.debug(
            "'aws_access_key_id' not provided. Falling back to environment variable.")
        try:
            aws_access_key_id = os_environ['AWS_ACCESS_KEY_ID']
        except KeyError:
            logger.exception("No environment variable named 'AWS_ACCESS_KEY_ID'."
                             "This is required as no token was given in method arguments.")
            return None
    if not aws_secret_access_key:
        logger.debug(
            "'aws_secret_access_key' not provided. Falling back to environment variable.")
        try:
            aws_secret_access_key = os_environ['AWS_SECRET_ACCESS_KEY']
        except KeyError:
            logger.exception("No environment variable named 'AWS_SECRET_ACCESS_KEY'."
                             "This is required as no token was given in method arguments.")
            return None

    session = boto3.session.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region
    )

    try:
        session.client('sts').get_caller_identity()
    except ClientError:
        logger.exception('Session validation has failed. See exception below.')
        return None
    return session


def _delete_deactivated_keys(iam_client):
    all_access_keys = iam_client.list_access_keys()
    count = 0

    for access_key in all_access_keys['AccessKeyMetadata']:
        if access_key['Status'] == 'Inactive':
            access_key_id = access_key['AccessKeyId']
            logger.debug(f"Deleting inactive key: '{access_key_id}'.")
            iam_client.delete_access_key(
                AccessKeyId=access_key_id)
            count += 1

    return count


@backoff.on_exception(backoff.expo, ClientError, max_time=30)
def _get_username(iam_client):
    logger.debug(
        'Gathering username from client object. '
        'This operation will be retried upon error for some time.')
    response = iam_client.get_user()
    return response['User']['UserName']


def _get_current_key_id(session):
    logger.debug('Getting frozen credentials for session.')
    return session.get_credentials().get_frozen_credentials().access_key


def _generate_new_key(iam_client, description):
    logger.debug('Generating new access keys.')
    response = iam_client.create_access_key()
    logger.debug('Access keys generated.')
    access_key_id = response['AccessKey']['AccessKeyId']
    access_key_secret = response['AccessKey']['SecretAccessKey']

    logger.debug('Getting username to add access key description as tag.')
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

    logger.debug('Gathering username using current keys.')
    username = _get_username(iam_client)
    logger.debug(f"Username obtained using current keys: '{username}'.")
    try:
        logger.debug('Gathering username using new keys.')
        test_username = _get_username(new_iam_client)
        logger.debug(f"Username obtained using new keys: '{test_username}'.")
    except ClientError:
        logger.exception('Unable to gather username using new keys.')
        return False

    if test_username == username:
        logger.debug('Usernames fetched using current and new keys match.')
        return True
        # new_key_last_used_tzaware = iam_client.get_access_key_last_used(
        #     AccessKeyId=new_access_key_id
        # )['AccessKeyLastUsed']['LastUsedDate']
        # new_key_last_used = new_key_last_used_tzaware.replace(tzinfo=None)

        # if new_key_last_used > time_before_key_usage:
        #     pass


def _deactivate_key(iam_client, access_key_id):
    logger.debug('An access key is being disabled.')
    response = iam_client.update_access_key(
        AccessKeyId=access_key_id,
        Status='Inactive'
    )
    return response['ResponseMetadata']['HTTPStatusCode'] == 200


def _rotate_key_on_github(access_key_id, access_key_secret):
    r1 = github_set_environment_secret(
        'development', 'AWS_ACCESS_KEY_ID', access_key_id)
    r2 = github_set_environment_secret(
        'development', 'AWS_SECRET_ACCESS_KEY', access_key_secret)
    return r1 and r2


def _rotate_key_on_terraform(access_key_id, access_key_secret):
    r = terraform_update_aws_keys(
        'workspace_dev', access_key_id, access_key_secret)
    return r


def rotatekeys():
    logger.info('AWS access keys are being rotated.')
    successes = {
        'deletion': 0,
        'creation': False,
        'testing': False,
        'deactivation': False,
        'github': False,
        'terraform': False,
    }
    logger.debug('Creating an AWS session with current credentials.')
    session = _get_session()
    if not session:
        logger.critical(
            'AWS session could not be created.'
            'See accompanying logs for more information.')
        return successes
    logger.debug('Creating IAM client with session.')
    iam_client = session.client('iam')
    logger.debug('Obtaining current access key from session.')
    current_access_key_id = _get_current_key_id(session)
    logger.debug('Deleting deactivated keys, if any.')
    _deactivated_keys_count = _delete_deactivated_keys(iam_client)
    if _deactivated_keys_count:
        logger.info(f"{_deactivated_keys_count} key(s) found and deleted.")
        successes['deletion'] = _deactivated_keys_count
    logger.debug('Generating new keys.')
    new_access_key_id, new_access_key_secret = _generate_new_key(
        iam_client, AWS_ACCESS_KEY_DESCRIPTION)
    logger.info('New access key generated.')
    successes['creation'] = True
    logger.debug('Creating a new session with new key.')
    new_session = _get_session(new_access_key_id, new_access_key_secret)
    logger.debug('Creating IAM client with new session.')
    new_iam_client = new_session.client('iam')
    logger.debug('Testing new access keys.')
    new_key_working = _test_new_key(
        iam_client, new_iam_client)
    if new_key_working:
        logger.info('Newly generated access keys passed the test.')
        successes['testing'] = True
        logger.debug('Deactivating current key.')
        _deactivation_result = _deactivate_key(
            iam_client, current_access_key_id)
        if _deactivation_result:
            logger.info('Deactivation of current key is successful.')
            successes['deactivation'] = True
        else:
            logger.warning('Deactivation of current key has failed.')
        logger.info('Updating keys on Github.')
        github_keyrotation_result = _rotate_key_on_github(
            new_access_key_id, new_access_key_secret)
        successes['github'] = github_keyrotation_result
        terraform_keyrotation_result = _rotate_key_on_terraform(
            new_access_key_id, new_access_key_secret)
        successes['terraform'] = terraform_keyrotation_result
    else:
        logger.error('Newly generated keys failed the test.')
        _deactivation_result = _deactivate_key(iam_client, new_access_key_id)
        if _deactivation_result:
            logger.info('Deactivation of new key is successful.')
        else:
            logger.error('Deactivation of new key has failed.')
        successes['github'] = False
        successes['terraform'] = False
    return successes
