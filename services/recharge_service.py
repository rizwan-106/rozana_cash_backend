from schemas.recharge_schema import RechargePackCreate, RechargePackUpdate
from datetime import datetime
from database.db import recharge_pack_db
from typing import List

async def create_pack(pack: RechargePackCreate) -> dict:
        """Create a new recharge pack"""
        # Check if pack_id already exists
        existing = await recharge_pack_db.find_one({"pack_id": pack.pack_id})
        if existing:
            raise ValueError(f"Pack with pack_id '{pack.pack_id}' already exists")
        pack_dict = pack.dict()
        pack_dict["is_active"] = True
        pack_dict["created_at"] = datetime.utcnow()
        pack_dict["updated_at"] = datetime.utcnow()
        result = await recharge_pack_db.insert_one(pack_dict)
        pack_dict["_id"] = str(result.inserted_id)
        
        return pack_dict

async def get_all_packs(active_only: bool = False) -> List[dict]:
        """Get all recharge packs"""
        query = {"is_active": True} if active_only else {}
        cursor = recharge_pack_db.find(query).sort("display_order", 1)
        
        packs = []
        async for document in cursor:
            document["_id"] = str(document["_id"])
            packs.append(document)
        return packs
    
async def get_pack_by_id(pack_id: str) -> dict:
        """Get a specific pack by pack_id"""        
        pack = await recharge_pack_db.find_one({"pack_id": pack_id})
        if pack:
            pack["_id"] = str(pack["_id"])
            return pack
        return None
    
async def update_pack(pack_id: str, pack_update: RechargePackUpdate) -> dict:
        """Update a recharge pack"""
        # Get current pack
        existing_pack = await recharge_pack_db.find_one({"pack_id": pack_id})
        if not existing_pack:
            raise ValueError(f"Pack with pack_id '{pack_id}' not found")
        
        # Update only provided fields
        update_data = {k: v for k, v in pack_update.dict().items() if v is not None}
        update_data["updated_at"] = datetime.utcnow()
        
        await recharge_pack_db.update_one(
            {"pack_id": pack_id},
            {"$set": update_data}
        )
        
        # Return updated pack
        updated_pack = await recharge_pack_db.find_one({"pack_id": pack_id})
        updated_pack["_id"] = str(updated_pack["_id"])
        
        return updated_pack
    
async def delete_pack(pack_id: str) -> bool:
        """Soft delete a pack (set is_active to False)"""
        result = await recharge_pack_db.update_one(
            {"pack_id": pack_id},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
    

async def hard_delete_pack(pack_id: str) -> bool:
        """Permanently delete a pack"""
        result = await recharge_pack_db.delete_one({"pack_id": pack_id})
        return result.deleted_count > 0