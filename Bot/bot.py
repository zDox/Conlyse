import logging
from game import Game
import logger
from time import sleep


def main():
    logger.initLogger(logging.DEBUG)
    game_1 = Game(login_data={"bot_username": "user9913153", "bot_password": "c7z#76XJ8$$!5Zdf", "game_id": "5851266"}, interval=10)
    game_1.setup()
    while True:
        game_1.long_game_scan()
        sleep(3600)


if __name__ == "__main__":
    main()
