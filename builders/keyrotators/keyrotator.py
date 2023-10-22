import logging

from keyrotators.providers import terraform

logger = logging.getLogger(__name__)


def main():
    logger.info('Initiating Terraform key rotation.')
    successes = terraform.rotatekeys()

    def success_string_printer(
        success): return 'successful' if success else 'failed'

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
