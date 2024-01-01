from web_api import WebAPI
import creds
from json import dumps

if __name__ == "__main__":
    web_api = WebAPI()
    web_api.login(creds.username, creds.password)
    print(web_api.auth)
    res = web_api.get_international_games()
    print(res)
