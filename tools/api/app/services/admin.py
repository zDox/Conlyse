from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.device import Device
from app.models.user import User, UserRole


async def list_users(db: AsyncSession, page: int = 1, page_size: int = 20) -> tuple[list[User], int]:
    """Return a paginated list of users and the total count."""
    total_result = await db.execute(select(func.count()).select_from(User))
    total = total_result.scalar_one()
    offset = (page - 1) * page_size
    result = await db.execute(
        select(User).order_by(User.id).offset(offset).limit(page_size)
    )
    return list(result.scalars().all()), total


async def get_user(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user: User | None = result.scalars().first()
    if not user:
        raise LookupError(f"User {user_id} not found")
    return user


async def update_user_role(db: AsyncSession, user_id: int, role: UserRole) -> User:
    user = await get_user(db, user_id)
    user.role = role
    await db.commit()
    await db.refresh(user)
    return user


async def ban_user(db: AsyncSession, user_id: int) -> User:
    user = await get_user(db, user_id)
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user


async def reset_user_password(db: AsyncSession, user_id: int, new_password: str) -> None:
    user = await get_user(db, user_id)
    user.hashed_password = hash_password(new_password)
    await db.commit()


async def revoke_user_device(db: AsyncSession, user_id: int, device_id: int) -> None:
    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.user_id == user_id)
    )
    device: Device | None = result.scalars().first()
    if not device:
        raise LookupError(f"Device {device_id} not found for user {user_id}")
    await db.delete(device)
    await db.commit()
