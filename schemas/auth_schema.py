from pydantic import BaseModel, EmailStr, Field, ConfigDict
from enum import Enum
from models.user_model import PyObjectId
from datetime import datetime
class UserRole(str, Enum):
    ADMIN='admin'
    USER='user'
    
class CreateUser(BaseModel):
    name:str=Field(min_length=2, max_length=100)
    email:EmailStr
    password:str=Field(min_length=8)
    role:UserRole=UserRole.USER  # ← Add default value here
    model_config=ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Rahul Kumar",
                "email": "rahul@gmail.com",
                "password": "Password123",
                # "role": "user"
            }
        }
    )
    
class User(BaseModel):#it will use in DB
    id: PyObjectId = Field(default_factory=PyObjectId, alias='_id')
    name: str
    email: EmailStr
    password: str  # Hashed password
    role: UserRole=UserRole.USER  # ← Add default value here
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,  # 'id' aur '_id' dono kaam karenge
        arbitrary_types_allowed=True,  # PyObjectId allow karne ke liye
        from_attributes=True,  # Dict se object banana easy
    )

    
class LoginUser(BaseModel):
    email:EmailStr
    password:str
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "rahul@gmail.com",
                "password": "Password123"
            }
        }
    )
    

class UserResponse(BaseModel):
    """
    GET /users/, GET /users/{id} mein use hoga
    Password NAHI bhejenge client ko!
    """
    id: str = Field(alias='_id')
    name: str
    email: EmailStr
    role: str  # Enum value as string
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "name": "Rahul Kumar",
                "email": "rahul@gmail.com",
                # "role": "user",
                "is_active": True,
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-15T10:30:00"
            }
        }
    )
    
    
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse  # ← User ki details bhi add karo (better UX)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "_id": "507f1f77bcf86cd799439011",
                    "name": "Rahul Kumar",
                    "email": "rahul@gmail.com",
                    # "role": "user",
                    "is_active": True,
                    "created_at": "2024-01-15T10:30:00",
                    "updated_at": "2024-01-15T10:30:00"
                }
            }
        }
    )