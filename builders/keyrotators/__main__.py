import argparse

from keyrotators import keyrotator

# Flag to track if any argument was provided.
no_arguments_provided = True

# Initialise parser.
parser = argparse.ArgumentParser(
    prog='Keyrotator',
    description='Rotates variables, keys, and secrets in various locations.',
)

# Argument for Terraform key rotation.
parser.add_argument(
    '--terraform',
    action='store_true',
    help='Rotate Terraform Cloud token and update Github secret.'
)

# Aargument for AWS key rotation.
parser.add_argument(
    '--aws',
    action='store_true',
    help='Rotate AWS IAM access and secret keys and update Github secret '
         'and Terraform variable set.'
)

# Parse the arguments.
args = parser.parse_args()

# Check if Terraform key is to be rotated.
if args.terraform:
    no_arguments_provided = False
    keyrotator.terraform_rotator()

# Check if AWS keys are to be rotated.
if args.aws:
    no_arguments_provided = False
    keyrotator.aws_rotator()

# Check if no arguments were provided.
if no_arguments_provided:
    keyrotator.no_rotation()
