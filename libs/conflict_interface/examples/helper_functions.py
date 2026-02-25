import os

KEYS = ["ACCOUNT_USERNAME", "ACCOUNT_PASSWORD", "ACCOUNT_EMAIL", "PROXY_URL"]


def load_credentials() -> tuple[str, str, str, str]:
    if all(os.getenv(key) is not None for key in KEYS):
        # All credential details are already loaded as environment variables
        return (os.getenv("ACCOUNT_USERNAME"), os.getenv("ACCOUNT_PASSWORD"), os.getenv("ACCOUNT_EMAIL"),
                os.getenv("PROXY_URL"))

    if not os.path.exists("credentials.json"):
        raise Exception("credentials.json file is missing")

    import json

    with open("credentials.json", "r") as file:
        credentials = json.load(file)

    missing_keys = [key for key in KEYS if key not in credentials]
    if missing_keys:
        raise Exception(f"Missing test keys in credentials.json: {', '.join(missing_keys)}")

    return (
    credentials["ACCOUNT_USERNAME"], credentials["ACCOUNT_PASSWORD"], credentials["ACCOUNT_EMAIL"],
    credentials["PROXY_URL"])
