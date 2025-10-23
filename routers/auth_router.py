from fastapi import APIRouter, HTTPException,Request,status
import os
import jwt
from datetime import datetime, timedelta
from fastapi.responses import RedirectResponse, JSONResponse
from schemas.auth_schema import LoginUser, LoginResponse, CreateUser, UserResponse, SendOTPRequest,VerifyOTPRequest,UpdateProfileRequest
from services.auth_service import send_otp

from services.auth_service import get_user_by_email, create_user, get_user_by_mobile
from utils.auth_util import verify_password, create_token, create_token_for_mobile
from config.google_oauth2 import oauth
from utils.otp_store import otp_store, otp_lookup
from database.db import user_db
from fastapi import Depends
from services.auth_service import generate_otp

# JWT_SECRET = os.getenv("JWT_SECRET","")
JWT_SECRET = os.getenv("SECRET_KEY")

router = APIRouter(prefix='/api/v1/auth', tags=['Auth'])

@router.post('/signup')
async def signup(user: CreateUser):
    existing_user = await get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(status_code=409, detail='User already exists')
    
    # Create User in DB
    new_user = await create_user(user)
    return {
        'message': "User created successfully."
    }

@router.post('/signin')
async def signin(user: LoginUser):
    existing_user = await get_user_by_email(user.email)
    if not existing_user:
        raise HTTPException(status_code=401, detail='User not found.')
    
    isPasswordVerified = verify_password(user.password, existing_user['password'])
    
    if not isPasswordVerified:
        raise HTTPException(status_code=401, detail="Password didn't matched.")
    token = create_token({
        'sub': str(existing_user['_id']),
        'email': existing_user['email'],
        'role': existing_user['role']
    })
    
    return LoginResponse(
        access_token=token,
        token_type='bearer',
        user=UserResponse(**existing_user)
    )    
    
# -------------------- Google OAuth2 --------------------# 
@router.get("/login/google")
async def login_via_google(request: Request):
    # redirect_uri = os.getenv(
    #     "GOOGLE_REDIRECT_URI",
    #     "http://127.0.0.1:8000/api/v1/auth/google/callback"
    # )
    # Get redirect URI from request host dynamically
    redirect_uri = f"{request.url.scheme}://{request.url.netloc}/api/v1/auth/google/callback"
    print(redirect_uri)
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def auth_google_callback(request: Request):
    """
    Step 2: Handle Google OAuth callback
    """
    try:
        # Exchange code for access token
        token = await oauth.google.authorize_access_token(request)
        # print("LIne 79: ",token)
        
        # Get user info from token (or fetch manually)
        user_info = token.get("userinfo")
        if not user_info:
            resp = await oauth.google.get("userinfo", token=token)
            user_info = resp.json()
        
        email = user_info.get("email")
        name = user_info.get("name")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")

        # Check if user already exists in DB
        existing_user = await get_user_by_email(email)
        if existing_user:
            user = existing_user
        else:
            # ✅ FIXED: Pass CreateUser Pydantic model instead of dict
            new_user_data = CreateUser(
                email=email,
                name=name,
                password=os.urandom(16).hex(),  # Random secure password
                # role="user",  # ⚠️ COMMENT: Add this if your CreateUser schema has role field
                # oauth_provider="google"  # ⚠️ COMMENT: Add this if your CreateUser schema has oauth_provider field
            )
            created_user = await create_user(new_user_data)
            
            # Convert Pydantic model to dict if needed
            if hasattr(created_user, 'dict'):
                user = created_user.dict()
            elif hasattr(created_user, 'model_dump'):
                user = created_user.model_dump()
            else:
                user = created_user
                
        payload = {
            "sub": str(user["_id"]),
            "email": user["email"],
            "role": user.get("role", "user")
        }
        jwt_token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

        
        # Production में flexibility के लिए
        frontend_url = os.getenv("FRONTEND_URL")
        if frontend_url:
            # ✅ ROLE-BASED REDIRECT
            user_role = user.get("role", "user")
            
            if user_role == "admin":
                redirect_url = f"{frontend_url}/admin/dashboard?token={jwt_token}"
            else:
                redirect_url = f"{frontend_url}/dashboard?token={jwt_token}"  # User dashboard
            
            return RedirectResponse(url=redirect_url)
        else:
            return JSONResponse({
            "success": True,
            "message": "Authentication successful",
            "data": {
                "access_token": jwt_token,
                "token_type": "bearer",
                "user": {
                    "id": str(user["_id"]),
                    "email": user["email"],
                    "name": user.get("name"),
                    "role": user.get("role", "user")
                }
            }
        })
    except Exception as e:
        print(f"Error during Google OAuth callback: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Authentication with Google failed.")
    
# =========================================#===================================#
# MOBILE NUMBER SYSTEM
@router.post('/send-otp')
async def requestOTP(request: SendOTPRequest):
    # Implement OTP sending logic here (e.g., using Twilio, Nexmo, etc.)
    existing_user = await get_user_by_mobile(request.mobile_number)
    otp=generate_otp()
    otp_store[request.mobile_number] = {"otp": otp, "name": request.name}
    
    otp_lookup[otp] = request.mobile_number  # Store the mapping of OTP to mobile number
    
    if existing_user:
        return {"message": "OTP sent", "is_new_user": False, "otp": otp}
    else:
        # New user - REGISTER case
        await user_db.insert_one({
            "name": request.name,
            "mobile_number": request.mobile_number,
            "role": request.role,
            "created_at": datetime.utcnow(),
        })
        return {"message": "OTP sent", "is_new_user": True, "otp": otp}

@router.post("/verify-otp")
async def verify_otp(data: VerifyOTPRequest):

    # Step 1: Find mobile number using OTP
    mobile_number = otp_lookup.get(data.otp)
    if not mobile_number:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Step 2: Fetch OTP info using mobile number
    info = otp_store.get(mobile_number)
    if not info or info["otp"] != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Step 3: Check if user exists
    existing_user = await user_db.find_one({"mobile_number": mobile_number})
    if existing_user:
        await user_db.update_one(
            {"mobile_number": mobile_number},
            {"$set": {"is_verified": True}}
        )
        user_data = existing_user
    else:
        user_data = {
            "name": info["name"],
            "mobile_number": mobile_number,
            "role": info.get("role", "user"),
            "is_verified": True,
            "created_at": datetime.utcnow(),
        }
        await user_db.insert_one(user_data)

    # Step 4: Clear OTP after success
    otp_store.pop(mobile_number, None)
    otp_lookup.pop(data.otp, None)

    # Step 5: Generate token
    token = create_token_for_mobile(user_data)

    return {
        "message": "OTP verified successfully",
        "access_token": token,
        "user": {
            "name": user_data["name"],
            "mobile_number": mobile_number,
        },
    }
