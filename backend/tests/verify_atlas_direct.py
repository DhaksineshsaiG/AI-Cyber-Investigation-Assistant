import asyncio
import certifi
import uuid
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

async def verify_atlas():
    print("=" * 60)
    print("DIRECT MONGODB ATLAS CONNECTION VERIFICATION (NO FALLBACK)")
    print("=" * 60)

    uri = settings.MONGODB_URI
    db_name = settings.effective_db_name
    print(f"Target Database: {db_name}")

    if not uri or uri.startswith("mongodb://localhost"):
        print("ERROR: Live MongoDB Atlas URI is not configured.")
        return False

    # Direct connection strictly to Atlas with TLS and certifi
    client = AsyncIOMotorClient(
        uri,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000
    )

    try:
        # 1. Ping Atlas
        print("\n[Step 1] Pinging MongoDB Atlas...")
        ping_res = await client.admin.command("ping")
        print(f"  [OK] Atlas ping response: {ping_res}")

        # 2. Confirm genuine Atlas ReplicaSet cluster
        print("\n[Step 2] Confirming Genuine Atlas Cluster Topology...")
        hello_res = await client.admin.command("hello")
        primary_host = hello_res.get("primary", "")
        set_name = hello_res.get("setName", "Unknown")
        hosts = hello_res.get("hosts", [])
        is_atlas = "mongodb.net" in primary_host or any("mongodb.net" in h for h in hosts)
        
        print(f"  [OK] Replica Set Name: {set_name}")
        print(f"  [OK] Primary Node Hostname: {primary_host.split(':')[0]}")
        print(f"  [OK] Cluster Nodes Count: {len(hosts)}")
        print(f"  [OK] Confirmed Genuine Atlas Cloud Cluster: {is_atlas}")

        # 3. Access cyber_investigation database
        print(f"\n[Step 3] Accessing Database '{db_name}'...")
        db = client[db_name]
        col = db["_connectivity_test"]

        # 4. Perform temporary test write & read
        test_id = str(uuid.uuid4())
        test_payload = {
            "test_id": test_id,
            "purpose": "Direct Atlas connectivity verification",
            "verified_at": "2026-09-23"
        }
        print("\n[Step 4] Performing Temporary Write & Read Test...")
        insert_res = await col.insert_one(test_payload)
        print(f"  [OK] Inserted test document into Atlas (ID: {insert_res.inserted_id})")

        doc = await col.find_one({"test_id": test_id})
        assert doc is not None, "Read operation failed: Document not found in Atlas!"
        assert doc["test_id"] == test_id, "Read operation failed: Content mismatch!"
        print("  [OK] Read test document back from Atlas successfully. Data integrity verified.")

        # 5. Cleanup temporary test document & collection
        print("\n[Step 5] Cleaning Up Temporary Test Data...")
        del_res = await col.delete_one({"test_id": test_id})
        await db.drop_collection("_connectivity_test")
        print(f"  [OK] Deleted test document ({del_res.deleted_count} removed) and dropped temporary collection.")

        print("\n" + "=" * 60)
        print("ALL DIRECT ATLAS VERIFICATION CHECKS PASSED SUCCESSFULLY!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n[FAILED] Atlas connection error: {type(e).__name__}: {e}")
        return False
    finally:
        client.close()

if __name__ == "__main__":
    success = asyncio.run(verify_atlas())
    sys.exit(0 if success else 1)
