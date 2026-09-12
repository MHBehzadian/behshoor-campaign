"""Creates (or updates the password of) one admin website account. Run once
during install — see ../../install.sh.

Usage (from backend/):
    python scripts/create_admin.py --username admin --password '...' --name "ادمین"
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.db import async_session  # noqa: E402
from app.models import User, UserRole  # noqa: E402
from app.security import hash_password  # noqa: E402


async def create_or_update_admin(username: str, password: str, full_name: str) -> None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user is None:
            session.add(User(role=UserRole.ADMIN, full_name=full_name, username=username, password_hash=hash_password(password)))
            print(f"Created admin '{username}'.")
        else:
            user.password_hash = hash_password(password)
            user.role = UserRole.ADMIN
            print(f"Updated password for existing user '{username}'.")
        await session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", default="ادمین")
    args = parser.parse_args()
    asyncio.run(create_or_update_admin(args.username, args.password, args.name))
