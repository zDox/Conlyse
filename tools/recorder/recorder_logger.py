import logging

LOGGER_NAME = "rec"
def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)
