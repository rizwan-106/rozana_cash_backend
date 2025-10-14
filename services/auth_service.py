from fastapi import HTTPException
from database.db import user_db
from schemas.auth_schema import CreateUser, User, SendOTPRequest
from utils.auth_util import hash_password
from database.db import user_db
import random
import phonenumbers
from utils.otp_store import otp_store

async def get_user_by_email(email:str):
    user=await user_db.find_one({'email':email})
    return user

async def get_user_by_mobile(mobile_number:str):
    user=await user_db.find_one({'mobile_number':mobile_number})
    return user

async def create_user(user:CreateUser):
    user_obj=User(**user.model_dump())
    user_dict=user_obj.model_dump(by_alias=True)
    user_dict['password']=hash_password(user_dict['password'])
    result = await user_db.insert_one(user_dict)
    created_user = await user_db.find_one({"_id": result.inserted_id})
    return created_user  # ✅ This returns dict from MongoDB


def validate_mobile_number(mobile_number:str):
    try:
        parsed = phonenumbers.parse(mobile_number, "IN")  # IN = India
        if not phonenumbers.is_valid_number(parsed):
            raise HTTPException(status_code=400, detail="Invalid mobile number format")
    except phonenumbers.NumberParseException:
        raise HTTPException(status_code=400, detail="Invalid mobile number format")

def generate_otp() -> str:
    """Generate a 4-digit random OTP"""
    return str(random.randint(1000, 9999))

def send_otp(user:SendOTPRequest):
    # otp_store={}
    validate_mobile_number(user.mobile_number)
    otp=generate_otp()
    otp_store[user.mobile_number] = {"otp": otp, "name": user.name}
    print(otp)
    return {
        "message": f"OTP sent to {user.mobile_number}",
        "otp": otp  # In real scenario, you won't return OTP in response
    }