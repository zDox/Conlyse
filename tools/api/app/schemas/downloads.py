from __future__ import annotations

from pydantic import BaseModel


class PresignedURLResponse(BaseModel):
    url: str
    expires_in: int


class VersionedPresignedURLResponse(PresignedURLResponse):
    version: str


class BinaryVersionsResponse(BaseModel):
    platform: str
    versions: list[str]
