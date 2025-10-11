"""Migration script for normalizing user_transactions collection

- Ensures `type` is a string (wallet_topup, game_fee, winning, withdrawal)
- Converts user_id strings to ObjectId where applicable

Usage (PowerShell):
    python .\scripts\migrate_user_transactions.py --dry-run
    python .\scripts\migrate_user_transactions.py --apply

This script uses motor and reads MONGODB_URL and DATABASE from env.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import asyncio
import os
import argparse
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DATABASE")

client = AsyncIOMotorClient(DB_URL)
db = client[DB_NAME]
user_txn = db.get_collection("user_transactions")

VALID_TYPES = {"wallet_topup", "game_fee", "winning", "withdrawal"}

async def dry_run():
    print("Running dry-run: scanning documents")
    cursor = user_txn.find({})
    issues = 0
    async for doc in cursor:
        doc_id = doc.get("_id")
        user_id = doc.get("user_id")
        ttype = doc.get("type")
        fixes = []
        # Check user_id
        if isinstance(user_id, str):
            if ObjectId.is_valid(user_id):
                fixes.append(f"user_id string -> ObjectId valid: {user_id}")
            else:
                fixes.append(f"user_id string but invalid ObjectId: {user_id}")
        # Check type
        if not isinstance(ttype, str):
            fixes.append(f"type not string: {ttype}")
        else:
            if ttype not in VALID_TYPES:
                fixes.append(f"type invalid value: {ttype}")
        if fixes:
            issues += 1
            print(f"_id={doc_id}: {fixes}")
    print(f"Scan complete. Documents with issues: {issues}")

async def apply_changes():
    print("Applying changes: normalizing documents")
    cursor = user_txn.find({})
    updated = 0
    async for doc in cursor:
        doc_id = doc.get("_id")
        user_id = doc.get("user_id")
        ttype = doc.get("type")
        update_ops = {}
        # Convert user_id str -> ObjectId
        if isinstance(user_id, str) and ObjectId.is_valid(user_id):
            update_ops["user_id"] = ObjectId(user_id)
        # Convert type to string (if enum-like) or validate
        if not isinstance(ttype, str):
            try:
                # attempt to stringify
                update_ops["type"] = str(ttype)
            except Exception:
                pass
        else:
            # optionally normalize case
            if ttype not in VALID_TYPES:
                # lower and replace spaces/underscores
                normalized = ttype.lower().strip()
                if normalized in VALID_TYPES:
                    update_ops["type"] = normalized
        if update_ops:
            await user_txn.update_one({"_id": doc_id}, {"$set": update_ops})
            updated += 1
            print(f"Updated {doc_id}: {update_ops}")
    print(f"Migration complete. Documents updated: {updated}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply fixes")
    parser.add_argument("--dry-run", action="store_true", help="Show potential fixes, don't apply")
    args = parser.parse_args()
    if not args.apply and not args.dry_run:
        parser.print_help()
    else:
        loop = asyncio.get_event_loop()
        if args.dry_run:
            loop.run_until_complete(dry_run())
        if args.apply:
            loop.run_until_complete(apply_changes())
