"""SQLAlchemy 2.0 declarative base shared by all models."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
