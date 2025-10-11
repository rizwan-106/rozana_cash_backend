from pydantic import BaseModel,Field, ConfigDict, field_validator
from bson import ObjectId
from datetime import datetime,timezone
from enum import Enum
from models.user_model import PyObjectId
from typing import Optional


class TransactionType(str, Enum):
    WALLET_TOPUP = "wallet_topup"
    GAME_FEE = "game_fee"
    WINNING = "winning"
    WITHDRAWAL = "withdrawal"
    
class TransactionCreate(BaseModel):
    """Schema for creating a new transaction (request body)"""
    amount: float
    type: TransactionType
    reference_id: Optional[str] = None
    
    @field_validator('amount')
    @classmethod
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "amount": 199.0,
                "type": "wallet_topup",
                "reference_id": "txn_12345",
            }
        }
    )

class TransactionResponse(BaseModel):
    """Schema for transaction response"""
    transaction_id: str
    amount: float
    type: TransactionType
    reference_id: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "transaction_id": "507f1f77bcf86cd799439011",
                "amount": 199.0,
                "type": "wallet_topup",
                "reference_id": "txn_12345",
                "created_at": "2025-10-06T12:00:00"
            }
        }
    )

class UserTransaction(BaseModel):
    """Complete transaction model for database operations"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias='_id')
    user_id: PyObjectId
    amount: float
    type: TransactionType
    reference_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "amount": 199.0,
                "type": "wallet_topup",
                "reference_id": "txn_12345",
                "created_at": "2025-10-06T12:00:00"
            }
        }
    )