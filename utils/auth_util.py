from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, status, Depends
import hashlib, base64, jwt, os
from datetime import datetime, timezone, timedelta
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from database.db import user_db

SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("EXPIRE_MINUTE", 60))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/v1/signin")

# ---------------- Password Utils ----------------
def hash_password(password: str) -> str:
    # Pre-hash with sha256 to avoid bcrypt 72-byte limit
    # sha256_digest = hashlib.sha256(password.encode("utf-8")).digest()
    # safe_password = base64.b64encode(sha256_digest).decode("ascii")
    # safe_password = safe_password[:72]
    # return pwd_context.hash(safe_password)
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # sha256_digest = hashlib.sha256(plain_password.encode("utf-8")).digest()
    # safe_password = base64.b64encode(sha256_digest).decode("ascii")
    # safe_password = safe_password[:72]  # truncate here too
    # print(f"safe pass: {safe_password}")
    # print(f"hashed pass: {hashed_password}")
    # return pwd_context.verify(safe_password, hashed_password)
    return pwd_context.verify(plain_password, hashed_password)

# ---------------- Token Utils ---------------- #
def create_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {
        # "sub": data.get("user_id"),# user identifier (email / id)
        "sub": data.get("sub"),      # user identifier (email / id)
        "email":data.get("email"),
        "role": data.get("role"),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def authenticate_user(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload=authenticate_user(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or token expired",
            headers={'WWW-Authenticate': 'Bearer'}
        )
    # return payload
    user_id = payload.get("sub")
    user = await user_db.find_one({"_id": user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user  # ✅ Returns fresh data with updated email/password

def admin_role(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user # Return the full current_user object, not just role

def user_role(current_user:dict=Depends(get_current_user)):
    if current_user.get('role')!='user':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users can perform transactions"
        )
    return current_user

#=====================#==========================#===========================#==================
def create_token_for_mobile(user:dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {
        "sub": str(user.get("_id")),      # user identifier (email / id)
        "mobile":user.get("mobile_number"),
        "role": user.get("role"),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)