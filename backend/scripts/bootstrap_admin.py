import sys
import os
import getpass
import asyncio
from pathlib import Path
from datetime import datetime, timezone

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import db_manager
from app.utils.security import hash_password

async def bootstrap():
    print("=" * 60)
    print("ONE-TIME ADMINISTRATOR BOOTSTRAP UTILITY")
    print("=" * 60)

    await db_manager.connect()
    db = db_manager.db
    if db is None:
        print("[ERROR] Could not connect to database.")
        return

    users_col = db["users"]
    admin_count = await users_col.count_documents({"role": "admin"})

    if admin_count > 0:
        print(f"\n[NOTICE] System is already initialized. {admin_count} admin account(s) exist.")
        print("To create additional users, log in as an administrator via the application.")
        await db_manager.close()
        return

    # Check env vars first, fallback to secure prompt
    env_user = os.environ.get("BOOTSTRAP_ADMIN_USER_ID", "").strip()
    env_pass = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "").strip()
    env_name = os.environ.get("BOOTSTRAP_ADMIN_DISPLAY_NAME", "").strip()

    if env_user and env_pass:
        user_id = env_user.lower()
        password = env_pass
        display_name = env_name or "System Administrator"
        print(f"\n[INFO] Read credentials from environment for user '{user_id}'.")
    else:
        print("\nEnter credentials for the initial primary administrator account:")
        try:
            raw_id = input("Admin User ID (e.g. admin): ").strip()
            user_id = raw_id.lower()
            if not user_id:
                print("[ERROR] User ID cannot be empty.")
                await db_manager.close()
                return

            display_name = input("Display Name (e.g. Lead Administrator): ").strip() or "System Administrator"
            password = getpass.getpass("Password (min 8 chars): ")
            confirm = getpass.getpass("Confirm Password: ")

            if password != confirm:
                print("[ERROR] Passwords do not match.")
                await db_manager.close()
                return

            if len(password) < 8:
                print("[ERROR] Password must be at least 8 characters.")
                await db_manager.close()
                return
        except (KeyboardInterrupt, EOFError):
            print("\n[CANCELLED] Bootstrap aborted.")
            await db_manager.close()
            return

    now_iso = datetime.now(timezone.utc).isoformat()
    password_hash = hash_password(password)

    user_doc = {
        "user_id": user_id,
        "display_name": display_name,
        "password_hash": password_hash,
        "role": "admin",
        "is_active": True,
        "created_at": now_iso,
        "updated_at": now_iso,
        "last_login_at": None,
        "created_by": "cli_bootstrap"
    }

    await users_col.insert_one(user_doc)
    print(f"\n[OK] Administrator '{user_id}' ({display_name}) created successfully.")
    print("You can now log in using these credentials in the web application.")
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(bootstrap())
