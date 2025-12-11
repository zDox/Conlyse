import logging

LOGGER_NAME = "rec_conv"


def setup_converter_logger(level=logging.WARNING):
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

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
    logger.addHandler(console_handler)

def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)
