import logging

LOGGER_NAME = "sro"
def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)
