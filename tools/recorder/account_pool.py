import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import reduce
from collections import defaultdict
from pathlib import Path

from tools.recorder.account import Account
from tools.recorder.proxy import Proxy
from tools.recorder.proxy import get_proxies
from tools.recorder.recorder_logger import get_logger

logger = get_logger()

@dataclass
class AccountPoolStatus:
    accounts: int
    proxies: int
    assigned_games: int
    open_game_slots: int

class AccountPool:
    def __init__(self, path: str, webshare_token: str | None = None):
        self.accounts: list[Account] = []
        self.proxies: dict[str, Proxy] = {}
        self.web_share_token = webshare_token
        self.pool_path: Path = Path(path)
        self.free_account_pointer = 0
        self.guest_account_pointer = 0
        self.guest_join_counts: dict[str, int] = {}

        if self.web_share_token is None:
            self.load_token()
        self.load_proxies()
        self.load_accounts()

    def save_to_json(self, path: str = None) -> None:
        if path is None:
            path = self.pool_path
        try:
            with open(path, 'w') as f:
                json.dump({
                    "WEBSHARE_API_TOKEN": self.web_share_token,
                    "accounts": [account.to_dict() for account in self.accounts]
                }, f, indent=4)
        except IOError as e:
            logger.error(f"Error writing to account_pool.json: {e}")

    def load_token(self) -> None:
        if not self.pool_path.exists():
            raise FileNotFoundError(f"File {self.pool_path} does not exist")

        with open(self.pool_path, 'r') as f:
            credentials = json.load(f)
        self.web_share_token = credentials['WEBSHARE_API_TOKEN']


    def load_proxies(self) -> None:
        if self.web_share_token is None:
            raise Exception("WebShare token not set")
        self.proxies = get_proxies(self.web_share_token)


    def load_accounts(self, path = None) -> None:
        if path is None:
            path = self.pool_path
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    accounts_file = json.load(f)
                    json_accounts = accounts_file.get("accounts", [])
                    for json_account in json_accounts:
                        self.accounts.append(Account.from_dict(json_account))
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Warning: Error reading account_pool.json: {e}. Starting fresh.")

        """
        After loading the accounts from file we need to check if all proxies are still valid.
        If not we need to reassign the unassigned proxies to the accounts.
        """
        assigned_proxy_ids = set()
        unassigned_proxy_ids = set(self.proxies.keys())
        accounts_missing_proxies = []

        for account in self.accounts:
            proxy = self.proxies.get(account.proxy_id)
            if proxy is None:
                logger.warning(
                    f"Warning: Account {account.username} has a proxy ID {account.proxy_id} that does not exist")
                accounts_missing_proxies.append(account)
            elif proxy.id in assigned_proxy_ids:
                accounts_missing_proxies.append(account)
            else:
                assigned_proxy_ids.add(account.proxy_id)
                unassigned_proxy_ids.remove(account.proxy_id)

        if len(accounts_missing_proxies) > len(unassigned_proxy_ids):
            logger.warning("Not enough unassigned proxies to assign proxies to accounts")

        for account in accounts_missing_proxies:
            if len(unassigned_proxy_ids) == 0:
                # Remove accounts that cannot be assigned a proxy
                logger.warning(f"Removing account {account.username} due to lack of available proxies")
                self.accounts.remove(account)
                continue
            proxy_id = unassigned_proxy_ids.pop()
            proxy = self.proxies[proxy_id]
            account.set_proxy(proxy)

    def is_proxy_in_use(self, proxy_id: str) -> bool:
        for account in self.accounts:
            if account.proxy_id == proxy_id:
                return True
        return False

    def get_free_proxy(self) -> Proxy | None:
        for proxy in self.proxies.values():
            if not self.is_proxy_in_use(proxy.id):
                return proxy

    def has_account(self, username: str) -> bool:
        for account in self.accounts:
            if account.username == username:
                return True
        return False

    def get_account(self, username: str) -> Account | None:
        for account in self.accounts:
            if account.username == username:
                return account

    def extend(self, account: Account) -> bool:
        """
        Extends the accounts pool by adding a new account if it is not already present, and
        associates it with a free proxy if available.


        :param account: The account to be added to the `accounts` pool.
        :type account: Account
        :return: A boolean value indicating whether the account was successfully added to
            the accounts pool (`True`) or not (`False`).
        :rtype: bool
        """
        if self.has_account(account.username):
            return False

        proxy = self.get_free_proxy()
        if proxy is None:
            return False
        else:
            account.set_proxy(proxy)
            self.accounts.append(account)
            return True


    def extend_by_accounts(self, accounts: list[Account]) -> bool:
        """
        Extends the account pool by a list of accounts.

        :param accounts: A list of Account instances to extend the account pool with.
        :type accounts: list[Account]
        :return: A boolean value indicating whether all accounts were
            successfully extended. Returns True if all operations were
            successful, otherwise False.
        :rtype: bool
        """
        return all(self.extend(account) for account in accounts)

    def get_free_accounts(self, number_of_accounts) -> list[Account]:
        """
        Retrieves a list of available accounts that each at least have one free game.

        :param number_of_accounts: The number of free accounts to return. This represents how many
            accounts the caller wants to retrieve from the free pool.
        :type number_of_accounts: int
        :return: A list containing up to `number_of_accounts` free accounts that are eligible.
        :rtype: list[Account]
        """
        free_accounts = []
        for index in range(self.free_account_pointer, self.free_account_pointer + number_of_accounts):
            if index >= len(self.accounts):
                return free_accounts
            if not self.accounts[index].has_maximum_games():
                free_accounts.append(self.accounts[index])
            else:
                self.free_account_pointer += 1
        return free_accounts

    def next_free_account(self) -> Account | None:
        """
        Finds the next free account that has at least one free game.

        :return: The next free account instance or None if no free account is available.
        :rtype: Account | None
        """
        if self.free_account_pointer >= len(self.accounts):
            return None

        while self.accounts[self.free_account_pointer].has_maximum_games():
            self.free_account_pointer += 1
            if self.free_account_pointer >= len(self.accounts):
                return None

        return self.accounts[self.free_account_pointer]

    def skip_free_account(self) -> None:
        """
        Skips the current free account by incrementing the free account pointer.
        This is useful when the current free account is not suitable for use.
        """
        self.free_account_pointer += 1

    def get_any_account(self) -> Account | None:
        if len(self.accounts) == 0:
            return None
        return self.accounts[0]

    def next_guest_account(self, max_guest_games_per_account: int | None) -> Account | None:
        """
        Returns the next account eligible for joining as guest respecting the cap.
        """
        if len(self.accounts) == 0:
            return None
        total = len(self.accounts)
        checked = 0
        while checked < total:
            account = self.accounts[self.guest_account_pointer % total]
            self.guest_account_pointer += 1
            checked += 1
            current = self.guest_join_counts.get(account.username, 0)
            if max_guest_games_per_account is None or current < max_guest_games_per_account:
                return account
        return None

    def increment_guest_join(self, account: Account):
        if not account:
            return
        self.guest_join_counts[account.username] = self.guest_join_counts.get(account.username, 0) + 1

    def decrement_guest_join(self, account: Account):
        if not account:
            return
        if account.username in self.guest_join_counts:
            self.guest_join_counts[account.username] = max(0, self.guest_join_counts[account.username] - 1)

    def status(self) -> AccountPoolStatus:
        accounts = len(self.accounts)
        proxies = len(self.proxies)

        def account_stats(account):
            return len(account.get_my_games()), account.open_game_slots()

        # Parallelize the computation across accounts using threads
        with ThreadPoolExecutor(max_workers=10) as executor:  # Adjust max_workers as needed
            results = list(executor.map(account_stats, self.accounts))

        # Aggregate results
        assigned_games, open_game_slots = reduce(
            lambda acc, curr: (acc[0] + curr[0], acc[1] + curr[1]),
            results,
            (0, 0)
        )

        return AccountPoolStatus(accounts, proxies, assigned_games, open_game_slots)
