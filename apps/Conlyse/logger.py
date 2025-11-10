import logging

LIBRARY_LOGGER_NAME = "rpv"
logging.getLogger(LIBRARY_LOGGER_NAME).addHandler(logging.NullHandler())


def setup_library_logger(level=logging.WARNING):
    logger = logging.getLogger(LIBRARY_LOGGER_NAME)
    logger.setLevel(level)

    # Set up a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Format to include where the log comes from
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s.%(module)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Avoid duplicate handlers
    logger.handlers.clear()
    if not logger.handlers:
        logger.addHandler(console_handler)

def get_logger() -> logging.Logger:
    return logging.getLogger(LIBRARY_LOGGER_NAME)
