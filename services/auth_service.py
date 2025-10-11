from fastapi import HTTPException
from database.db import user_db
from schemas.auth_schema import CreateUser, User
from utils.auth_util import hash_password
from database.db import user_db

async def get_user_by_email(email:str):
    user=await user_db.find_one({'email':email})
    return user

# async def create_user(user:CreateUser):
#     user_obj=User(**user.model_dump())
#     user_dict=user_obj.model_dump(by_alias=True)
#     user_dict['password']=hash_password(user_dict['password'])
#     await user_db.insert_one(user_dict)
#     return User(**user_dict)

async def create_user(user:CreateUser):
    user_obj=User(**user.model_dump())
    user_dict=user_obj.model_dump(by_alias=True)
    user_dict['password']=hash_password(user_dict['password'])
    result = await user_db.insert_one(user_dict)
    created_user = await user_db.find_one({"_id": result.inserted_id})
    return created_user  # ✅ This returns dict from MongoDB

