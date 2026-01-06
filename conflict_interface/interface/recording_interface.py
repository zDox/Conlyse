from typing import Optional

from cloudscraper25 import CloudScraper

from conflict_interface.data_types.authentication import AuthDetails
from conflict_interface.interface.online_interface import OnlineInterface


class RecordingInterface(OnlineInterface):
    """
    Thin wrapper around OnlineInterface to support recording-centric sessions.
    """

    def __init__(
        self,
        game_id: int,
        session: CloudScraper,
        auth_details: AuthDetails,
        guest: bool = False,
        proxy: Optional[dict] = None,
        replay_filepath: Optional[str] = None,
    ):
        super().__init__(
            game_id=game_id,
            session=session,
            auth_details=auth_details,
            guest=guest,
            proxy=proxy,
            replay_filepath=replay_filepath,
        )
