from pprint import pprint

from conflict_interface.hub_api import HubApi, AjaxRequest

if __name__ == "__main__":
    api = HubApi()
    user_name = "Juicy8533"
    password = "REMOVED_SECRET"

    api.login(user_name, password)
    pprint(api.get_my_games())