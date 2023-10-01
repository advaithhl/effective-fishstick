from services import terraform


def lambda_handler(event, context):
    terraform.rotatekeys()
