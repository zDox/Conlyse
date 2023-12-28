import requests, lxml.html
import creds
import base64
from urllib.parse import quote, urlencode
import hashlib
import json
interesting_keys = ["userID","authHash","authTstamp","chatAuth","chatAuthTstamp","uberAuthHash","uberAuthTstamp","rights"]



class WebAPI():
    def __init__(self):
        self.session = requests.Session()

    def login(self, username, password):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.159 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Dest': 'document',
            'Referer': 'https://www.conflictnations.com/index.php?source=browser-desktop',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        params = {
            'id': '322',
            'source': 'browser-desktop',
        }

        data = {
            'user': username,
            'pass': password,
        }

        response = self.session.post(
            'https://www.conflictnations.com/index.php',
            params=params,
            headers=headers,
            data=data,
        )
        if response.status_code != 200:
            print("Error not able to login")
            return False

        response_html = lxml.html.fromstring(response.text)

        url = response_html.xpath(r'//iframe[@id="ifm"]/@src')[0]
        parameters = url.split("&")

        self.auth = {}
        for parameter in parameters[1:]:
            key, value = parameter.split("=")
            if key not in interesting_keys:
                continue
            self.auth[key] = value

    def sendApiRequest(self, params, action):
        headers = {
            'Host': 'www.conflictnations.com',
            'Sec-Ch-Ua': '"Chromium";v="119", "Not?A_Brand";v="24"',
            'Accept': '*/*',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Sec-Ch-Ua-Mobile': '?0',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.159 Safari/537.36',
            'Sec-Ch-Ua-Platform': '"Linux"',
            'Origin': 'https://www.conflictnations.com',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Accept-Language': 'en-US,en;q=0.9',
            'Priority': 'u=1, i',
        }

        keycode = "uberCon"

        if keycode != "open":
            params['authTstamp'] = self.auth["authTstamp"]
            params['authUserID'] = self.auth["userID"]
        
        encoded_params = ""
        param_list = []
        if params:
            for key, value in params.items():
                param_list.append(key + "=" + value)
            encoded_params = "&".join(param_list)
        
        encoded_params_b64 = base64.b64encode(encoded_params.encode()).decode()
        data_string = "data=" + encoded_params_b64
        
        if keycode == "open":
            hash_prepare = keycode + action + encoded_params
        else:
            hash_prepare = keycode + action + encoded_params
            hash_prepare += self.auth["uberAuthHash"]
        hash_str = hashlib.sha1(hash_prepare.encode()).hexdigest()

        params = {
            'eID': 'api',
            'key': keycode,
            'action': action,
            'hash': hash_str,
            'outputFormat': 'json',
            'apiVersion': '20141208',
        }
        return self.session.post(
            'https://www.conflictnations.com/index.php',
            params=params,
            headers=headers,
            data=data_string,
        )


if __name__ == "__main__":
    web_api = WebAPI()
    web_api.login(creds.username, creds.password)
    print(web_api.auth)
    res = web_api.sendApiRequest({"userID": web_api.auth["userID"]}, "getInternationalGames")
    print(res.text)
