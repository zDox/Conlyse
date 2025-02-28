import os
TEST_KEYS = ["TEST_ACCOUNT_USERNAME", "TEST_ACCOUNT_PASSWORD", "TEST_ACCOUNT_EMAIL"]

def load_credentials() -> tuple[str, str, str]:


    if all(os.getenv(key) is not None for key in TEST_KEYS):
        # All credential details are already loaded as environment variables
        return os.getenv("TEST_ACCOUNT_USERNAME"), os.getenv("TEST_ACCOUNT_PASSWORD"), os.getenv("TEST_ACCOUNT_EMAIL")

    if not os.path.exists("credentials.json"):
        raise Exception("credentials.json file is missing")
    
    import json

    with open("credentials.json", "r") as file:
        credentials = json.load(file)

    missing_keys = [key for key in TEST_KEYS if key not in credentials]
    if missing_keys:
        raise Exception(f"Missing test keys in credentials.json: {', '.join(missing_keys)}")

    return credentials["TEST_ACCOUNT_USERNAME"], credentials["TEST_ACCOUNT_PASSWORD"], credentials["TEST_ACCOUNT_EMAIL"]