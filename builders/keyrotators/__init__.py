# Configure logging for the keyrotaters.
# The logger captures all logs and has 3 handlers: console, log, and error.
#
# The console handler has a DEBUG level set, so it logs everything. This can be
# referred when checking the workflow logs of Github Actions.
#
# The log handler has an INFO level set, so it logs the normal activities of the
# key rotator to a file called 'keyrotation.log'. This can be exported as an
# artifact during the workflow run.
#
# The error handler has an ERROR level set, so it logs the errors/exceptions
# which occurs during key rotation to a file called 'keyrotation-error.log'.
# Like the 'keyrotation.log' file, this can also be exported as an artifact
# during workflow run.
import logging

# Initialize the logger.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Set logger format.
formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')
consoleFormatter = logging.Formatter(
    '%(asctime)s:%(name)s.%(funcName)s:%(levelname)s:%(message)s')

# Define console handler for printing debug logs to stdout.
consolePrintHandler = logging.StreamHandler()
consolePrintHandler.setLevel(logging.DEBUG)
consolePrintHandler.setFormatter(consoleFormatter)
logger.addHandler(consolePrintHandler)

# Define log handler for writing info logs to file.
logFileHandler = logging.FileHandler('keyrotation.log')
logFileHandler.setLevel(logging.INFO)
logFileHandler.setFormatter(formatter)
logger.addHandler(logFileHandler)

# Define error handler for writing error logs to file.
errorFileHandler = logging.FileHandler('keyrotation-error.log')
errorFileHandler.setLevel(logging.ERROR)
errorFileHandler.setFormatter(formatter)
logger.addHandler(errorFileHandler)
