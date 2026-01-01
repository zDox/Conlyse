"""
Conflict of Nations authentication service.
Verifies user credentials against the CoN game servers.
"""
import requests
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

CON_BASE_URL = "https://www.conflictnations.com/"
CON_LOGIN_URL = "https://www.conflictnations.com/index.php?id=2&L=0"


class ConAuthService:
    """
    Service to authenticate users against Conflict of Nations.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

    def verify_credentials(self, username: str, password: str) -> dict:
        """
        Verify CoN credentials by attempting to log in.

        Returns:
            dict with keys:
                - success: bool
                - player_id: int (if successful)
                - site_user_id: int (if successful)
                - error: str (if failed)
        """
        try:
            # First, get the login page to obtain any CSRF tokens
            login_page = self.session.get(CON_BASE_URL, timeout=30)
            login_page.raise_for_status()

            # Attempt login via the game's AJAX login endpoint
            login_data = {
                'login': username,
                'password': password,
                'remember': '1',
            }

            # CoN uses an AJAX login endpoint
            login_response = self.session.post(
                'https://www.conflictnations.com/index.php?eID=api&key=userHandler&action=doLogin',
                data=login_data,
                timeout=30
            )

            if login_response.status_code != 200:
                return {
                    'success': False,
                    'error': 'Login request failed'
                }

            try:
                result = login_response.json()
            except ValueError:
                # Not JSON, check if we got redirected to game hub
                return self._check_login_success(username)

            # Check the response for success indicators
            if result.get('result', {}).get('success') or result.get('success'):
                user_data = result.get('result', {}).get('user', {})
                return {
                    'success': True,
                    'player_id': user_data.get('playerID'),
                    'site_user_id': user_data.get('siteUserID'),
                    'username': username,
                }
            else:
                error_msg = result.get('result', {}).get('error', 'Invalid credentials')
                return {
                    'success': False,
                    'error': error_msg
                }

        except requests.exceptions.Timeout:
            logger.error("Timeout connecting to CoN servers")
            return {
                'success': False,
                'error': 'Connection timeout - CoN servers may be slow'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error during CoN auth: {e}")
            return {
                'success': False,
                'error': 'Could not connect to CoN servers'
            }
        except Exception as e:
            logger.exception(f"Unexpected error during CoN auth: {e}")
            return {
                'success': False,
                'error': 'Authentication service error'
            }

    def _check_login_success(self, username: str) -> dict:
        """
        Check if login was successful by accessing a protected page.
        """
        try:
            # Try to access the game hub which requires authentication
            hub_response = self.session.get(
                'https://www.conflictnations.com/index.php?eID=api&key=uberCon&action=getPlayerInfo',
                timeout=30
            )

            if hub_response.status_code == 200:
                try:
                    data = hub_response.json()
                    if data.get('result', {}).get('playerID'):
                        return {
                            'success': True,
                            'player_id': data['result']['playerID'],
                            'site_user_id': data['result'].get('siteUserID'),
                            'username': username,
                        }
                except ValueError:
                    pass

            return {
                'success': False,
                'error': 'Could not verify login'
            }
        except Exception as e:
            logger.error(f"Error checking login success: {e}")
            return {
                'success': False,
                'error': 'Could not verify login'
            }

    def close(self):
        """Close the session."""
        self.session.close()


def verify_con_credentials(username: str, password: str) -> dict:
    """
    Convenience function to verify CoN credentials.
    """
    service = ConAuthService()
    try:
        return service.verify_credentials(username, password)
    finally:
        service.close()
