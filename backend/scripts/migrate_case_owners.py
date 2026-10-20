import sys
import os
import argparse
import asyncio
from pathlib import Path
from datetime import datetime, timezone

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import db_manager

async def run_migration(assign_to: str = None, dry_run: bool = False, rollback: bool = False):
    print("=" * 60)
    print("FORENSIC CASE OWNERSHIP MIGRATION UTILITY")
    print("=" * 60)

    await db_manager.connect()
    db = db_manager.db
    if db is None:
        print("[ERROR] Could not connect to database.")
        return

    cases_col = db["cases"]
    users_col = db["users"]

    if rollback:
        print("\n[ACTION] Rolling back previous case owner migration...")
        migrated_cases = await cases_col.find({"legacy_unmigrated": True}).to_list(500)
        print(f"  Found {len(migrated_cases)} migrated case(s) to rollback.")
        if migrated_cases:
            res = await cases_col.update_many(
                {"legacy_unmigrated": True},
                {"$unset": {"owner_user_id": "", "legacy_unmigrated": ""}}
            )
            print(f"  [OK] Successfully rolled back {res.modified_count} case(s).")
        await db_manager.close()
        return

    # Find unassigned cases
    unassigned_filter = {"$or": [{"owner_user_id": {"$exists": False}}, {"owner_user_id": None}]}
    unassigned_cases = await cases_col.find(unassigned_filter).to_list(500)
    total_unassigned = len(unassigned_cases)

    print(f"\n[SCAN] Found {total_unassigned} legacy case(s) without an owner.")
    for c in unassigned_cases[:10]:
        print(f"  - [{c.get('case_id')}] '{c.get('title')}' (Investigator field: {c.get('investigator')})")
    if total_unassigned > 10:
        print(f"  ... and {total_unassigned - 10} more cases.")

    if total_unassigned == 0:
        print("\n[OK] All cases in database already have an assigned owner_user_id.")
        await db_manager.close()
        return

    if dry_run or not assign_to:
        print("\n[DRY RUN] No changes were made to the database.")
        print("To assign these cases to a user, run with: --assign-to <user_id>")
        await db_manager.close()
        return

    # Verify target user exists
    target_id = assign_to.strip().lower()
    target_user = await users_col.find_one({"user_id": target_id})
    if not target_user:
        print(f"\n[ERROR] Target user '{target_id}' does not exist in the database.")
        print("Please create the user first before assigning cases.")
        await db_manager.close()
        return

    print(f"\n[MIGRATE] Assigning {total_unassigned} legacy case(s) to user '{target_id}' ({target_user.get('display_name')})...")
    now_iso = datetime.now(timezone.utc).isoformat()

    res = await cases_col.update_many(
        unassigned_filter,
        {"$set": {
            "owner_user_id": target_id,
            "legacy_unmigrated": True,
            "updated_at": now_iso
        }}
    )

    print(f"  [OK] Successfully assigned {res.modified_count} case(s) to '{target_id}'.")
    print("  [NOTE] These cases are marked with 'legacy_unmigrated: true' and can be rolled back using --rollback.")
    await db_manager.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate legacy case ownership")
    parser.add_argument("--assign-to", type=str, help="Target user ID to assign unowned cases to")
    parser.add_argument("--dry-run", action="store_true", help="Inspect without modifying")
    parser.add_argument("--rollback", action="store_true", help="Rollback previously migrated legacy cases")
    args = parser.parse_args()

    asyncio.run(run_migration(assign_to=args.assign_to, dry_run=args.dry_run, rollback=args.rollback))
