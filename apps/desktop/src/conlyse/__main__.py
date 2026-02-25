import logging

from conlyse.app import App
from conlyse.logger import setup_logger

if __name__ == "__main__":
    setup_logger(logging.DEBUG)
    app = App()
    app.start()