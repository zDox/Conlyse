from web_api import WebAPI
import creds
from pprint import pprint


if __name__ == "__main__":
    web_api = WebAPI()
    web_api.login(creds.username, creds.password)
    pprint(web_api.auth)
    res = web_api.get_international_games()
    pprint(res)
