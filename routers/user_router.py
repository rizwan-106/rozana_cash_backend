from fastapi import APIRouter, HTTPException, Depends
from utils.auth_util import  get_current_user
from bson.errors import InvalidId
from bson import ObjectId
from datetime import datetime
from database.db import user_transaction_db
from schemas.user_transaction_schema import TransactionCreate,TransactionResponse

router=APIRouter(prefix='/api/v1/user', tags=['User'])


@router.post('/create_transaction',response_model=TransactionResponse)
async def create_transactions(transaction:TransactionCreate, current_user:dict=Depends(get_current_user)):
    user_id=current_user['sub']
    # user_id=current_user['user_id']
    
    try:
        user_object_id = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    txn_doc={
        # "user_id":ObjectId(user_id),
        "user_id": user_object_id,
        "amount":transaction.amount,
        # "type": transaction.type,
        "type": transaction.type.value,#edited by copilot
        "reference_id": transaction.reference_id,
        "created_at": datetime.utcnow()
    }
    
    try:
        # Insert into database
        result = await user_transaction_db.insert_one(txn_doc)
        
        # Return response
        return TransactionResponse(
            transaction_id=str(result.inserted_id),
            amount=transaction.amount,
            type=transaction.type,
            reference_id=transaction.reference_id,
            created_at=txn_doc["created_at"]
        )
    except Exception as e:
        print(f"Error creating transaction: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to create transaction: {str(e)}"
        )