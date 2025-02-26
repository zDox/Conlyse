from pprint import pprint

from conflict_interface.hub_interface import HubInterface

if __name__ == "__main__":
    hub = HubInterface()
    print(hub)
    user_name = "Juicy8533"
    password = "REMOVED_SECRET"

    hub.login(user_name, password)
    print(hub.first_join(4))