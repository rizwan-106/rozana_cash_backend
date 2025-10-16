from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class RechargePack(BaseModel):
    pack_id:str
    name: str
    price: float
    spins: int
    discount_percentage: Optional[float] = 0
    is_active: bool = True
    display_order: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class RechargePackCreate(BaseModel):
    pack_id: str  # e.g., "starter", "value", "power", "mega"
    name: str
    price: float
    spins: int
    discount_percentage: Optional[float] = 0
    display_order: int

class RechargePackUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    spins: Optional[int] = None
    discount_percentage: Optional[float] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None