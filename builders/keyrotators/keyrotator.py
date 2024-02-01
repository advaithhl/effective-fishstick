import logging

from keyrotators.providers import aws, terraform

logger = logging.getLogger(__name__)


def terraform_rotator():
    logger.info('Initiating Terraform key rotation.')
    successes = terraform.rotatekeys()

    logger.debug(
        'Terraform keyrotation result - New token creation:'
        f' {success_string_printer(successes["creation"])}')
    logger.debug(
        'Terraform keyrotation result - New token testing:'
        f' {success_string_printer(successes["testing"])}')
    logger.debug(
        'Terraform keyrotation result - Current token invalidation:'
        f' {success_string_printer(successes["destruction"])}')
    logger.debug(
        'Terraform keyrotation result - Setting Github secret:'
        f' {success_string_printer(successes["github"])}')


def aws_rotator():
    logger.info('Initiating AWS key rotation.')
    successes = aws.rotatekeys()

    logger.debug(
        'AWS keyrotation result - Number of deactivated tokens deleted:'
        f' {successes["deletion"]}')
    logger.debug(
        'AWS keyrotation result - New token creation:'
        f' {success_string_printer(successes["creation"])}')
    logger.debug(
        'AWS keyrotation result - New token testing:'
        f' {success_string_printer(successes["testing"])}')
    logger.debug(
        'AWS keyrotation result - Current token invalidation:'
        f' {success_string_printer(successes["deactivation"])}')
    logger.debug(
        'AWS keyrotation result - Setting Github secret:'
        f' {success_string_printer(successes["github"])}')
    logger.debug(
        'AWS keyrotation result - Setting Terraform secret:'
        f' {success_string_printer(successes["terraform"])}')


def no_rotation():
    logger.error('No provider was requested to be rotated! '
                 'Please pass any provider name as --PROVIDER for performing keyrotation.')


def success_string_printer(success):
    return 'successful' if success else 'failed'
