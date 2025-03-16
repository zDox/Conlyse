from time import sleep


from conflict_interface.interface.hub_interface import HubInterface
from examples.helper_functions import load_credentials

if __name__ == "__main__":
    username, password, email, proxy_url = load_credentials()
    itf = HubInterface({
        "http": proxy_url,
        "https": proxy_url,
    })
    itf.login(username, password)
    game = itf.join_game(9812061, replay_filename="test.zip")
    sleep(5)
    game.update()
    print(game.client_time().timestamp())