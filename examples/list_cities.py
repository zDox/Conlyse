import logging


from pprint import pprint

import matplotlib.pyplot as plt
from PIL import Image

from conflict_interface.data_types.army_state.unit import Unit
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger
from examples.helper_functions import load_credentials
from PIL import Image
from io import BytesIO

if __name__ == "__main__":
    setup_library_logger(logging.DEBUG)

    interface = HubInterface()
    username, password = "IpXOoCknBFbBKI", "qsubmliInVbgyF"
    interface.login(username, password)

    game = interface.join_game(9900696)
    # Load image from bytes
    for army in game.get_armies().values():
        path = army.get_image()
        print(f"path: {path}")
        image = Image.open(BytesIO(game.game_api.get_image(path)))
        plt.figure(figsize=(5, 5))
        plt.imshow(image)
        plt.axis("off")
        plt.title(f"{army.id}_{army.army_number}")
        plt.show()
