"""__init__.py — re-export all models so Alembic can discover them."""

from app.models.base import Base  # noqa: F401
from app.models.device import Device  # noqa: F401
from app.models.session import Session  # noqa: F401
from app.models.user import User, UserRole  # noqa: F401
from app.models.game import Game, RecordingListEntry  # noqa: F401
