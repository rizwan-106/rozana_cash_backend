from fastapi import APIRouter, HTTPException,Request
from fastapi.responses import RedirectResponse, JSONResponse
from schemas.auth_schema import LoginUser, LoginResponse, CreateUser, UserResponse
import os
import jwt

from services.auth_service import get_user_by_email, create_user
from utils.auth_util import verify_password, create_token
from config.google_oauth2 import oauth

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
    
    # token = create_token({
    #     'user_id': str(existing_user['_id']),
    #     'email': existing_user['email'],
    #     # 'role': existing_user['role']
    # })
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
    """
    Step 1: Redirect user to Google login page
    """
    # redirect_uri = os.getenv(
    #     "GOOGLE_REDIRECT_URI",
    #     "http://127.0.0.1:8000/api/v1/auth/google/callback"
    # )
    # Get redirect URI from request host dynamically
    redirect_uri = f"{request.url.scheme}://{request.url.netloc}/api/v1/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def auth_google_callback(request: Request):
    """
    Step 2: Handle Google OAuth callback
    """
    try:
        # Exchange code for access token
        token = await oauth.google.authorize_access_token(request)
        
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

        # return JSONResponse({
        #     "msg": "Google login successful",
        #     "user": {
        #         "id": str(user["_id"]),
        #         "email": user["email"],
        #         "name": user.get("name"),
        #         "is_active": user.get("is_active", True),
        #         "created_at": user.get("created_at").isoformat() if user.get("created_at") else None
        #     },
        #     "token": jwt_token
        # })
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        redirect_url = f"{frontend_url}/auth/callback?token={jwt_token}"
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        print(f"Error during Google OAuth callback: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Authentication with Google failed.")