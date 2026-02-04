import asyncio
import getpass
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.main import close_db, init_db
from src.services import UserService

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

load_dotenv(_root / ".env")


async def main() -> None:
    username = os.getenv("ADMIN_USERNAME", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "").strip()

    if not username:
        username = input("Superuser username: ").strip()
    if not password:
        password = getpass.getpass("Superuser password: ").strip()

    if not username or not password:
        print(
            "Username and password are required. "
            "Set ADMIN_USERNAME and ADMIN_PASSWORD in .env or enter interactively."
        )
        sys.exit(1)

    await init_db()
    try:
        existing_user = await UserService.get_user_by_username(username)
        if existing_user:
            if existing_user.is_superuser:
                print(f"Superuser already exists: {username}")
            else:
                existing_user.is_superuser = True
                await existing_user.save()
                print(f"User '{username}' promoted to superuser.")
        else:
            await UserService.create_user(username, password, is_superuser=True)
            print(f"Superuser created: {username}")

    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
