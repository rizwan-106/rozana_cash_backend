from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager  # ✅ ADDED: For lifespan management
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware
import os
import sys
from pathlib import Path

# Load environment variables FIRST (before any imports that use them)
env_file = Path(__file__).parent.parent / '.env'

# Check if .env file exists
if not env_file.exists():
    print(f"⚠️ WARNING: .env file not found at {env_file}")
    print("Creating default .env file...")
    with open(env_file, 'w') as f:
        f.write("ENVIRONMENT=development\n")

# Load environment variables with explicit override
load_dotenv(dotenv_path=env_file, override=False)  # Don't override existing system vars

from routers import auth_router, user_router, admin_router
from database.db import test_connection, close_connection  # ✅ ADDED: Import connection functions

# Environment Configuration
# Load from .env file first, then check system env
load_dotenv(dotenv_path=env_file, override=True)  # Force override system vars
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
print(f"🔧 Environment Mode: {ENVIRONMENT}")
print(f"📁 Loaded from: {env_file}")
print(f"🔍 System ENV var: {os.environ.get('ENVIRONMENT', 'Not set')}")
print(f"🆔 Process ID: {os.getpid()}")
print(f"💻 Working Directory: {os.getcwd()}")
print("-" * 50)

# Required Environment Variables
REQUIRED_ENV_VARS = {
    "MONGODB_URL": "MongoDB connection string",
    "DATABASE": "Database name", 
    "SECRET_KEY": "JWT secret key",
    "ALGORITHM": "JWT algorithm",
    "ENVIRONMENT": "Environment (development/production)",
    "EXPIRE_MINUTE": "JWT token expiration in minutes",
    "GOOGLE_CLIENT_ID": "Google OAuth Client ID",
    "GOOGLE_CLIENT_SECRET": "Google OAuth Client Secret",
    "GOOGLE_REDIRECT_URI": "Google OAuth Redirect URI"
}

def validate_environment():
    """Validate all required environment variables are set"""
    missing_vars = []
    weak_configs = []
    
    for var, description in REQUIRED_ENV_VARS.items():
        value = os.getenv(var)
        if not value:
            missing_vars.append(f"❌ {var} ({description})")
        # ✅ CHANGED: Check SECRET_KEY length instead of exact value
        elif var == "SECRET_KEY" and len(value) < 32:
            weak_configs.append(f"⚠️ {var} is too short (minimum 32 characters)")
        elif var == "MONGODB_URL" and value == "mongodb://localhost:27017" and ENVIRONMENT == "production":
            weak_configs.append(f"⚠️ {var} using local database in production")
    
    if missing_vars:
        print("\n🚨 CRITICAL: Missing required environment variables:")
        for var in missing_vars:
            print(f"  {var}")
        if ENVIRONMENT == "production":
            print("\n💀 Cannot start in production with missing variables!")
            sys.exit(1)
        else:
            print("\n⚠️ Development mode: Check your .env file")
    
    # ✅ CHANGED: Exit on weak config in production
    if weak_configs and ENVIRONMENT == "production":
        print("\n⚠️ WARNING: Weak production configuration detected:")
        for config in weak_configs:
            print(f"  {config}")
        print("\n💡 Fix these before production deployment!")
        sys.exit(1)  # ✅ ADDED: Don't allow production with weak config
    
    return True

# Validate environment on startup
validate_environment()

# ✅ ADDED: Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"\n🚀 Starting Khazana Khelo API ({ENVIRONMENT} mode)")
    connection_success = await test_connection()
    if not connection_success:
        print("❌ Failed to connect to MongoDB - shutting down")
        sys.exit(1)
    print("✅ All systems ready!\n")
    
    yield
    
    # Shutdown
    print("\n🔌 Shutting down...")
    await close_connection()
    print("👋 Goodbye!\n")

# FastAPI Configuration
app_config = {
    "title": "Khazana Khelo API",
    "version": "1.0.0",
    "description": "Gaming Platform Backend API",
    "lifespan": lifespan  # ✅ ADDED: Lifespan management
}

if ENVIRONMENT == "production":
    print("🔒 Production mode: Docs disabled")
    app_config.update({
        "docs_url": None,
        "redoc_url": None,
        "openapi_url": None
    })
else:
    print(f"✅ {ENVIRONMENT} mode: Docs enabled at /docs")
    app_config.update({
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json"
    })

app = FastAPI(**app_config)

@app.get("/")
def root():
    return {"message": "FastAPI Render deploy successful!"}

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY"),
    same_site="none",  # ✅ CHANGED: "none" for cross-site
    https_only=True if ENVIRONMENT == "production" else False,  # ✅ CHANGED: True in production
    domain=None,       # Explicit domain setting
    max_age=3600       # ✅ ADDED: Set session timeout
)

# Include routers
app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(admin_router.router)

# ✅ CHANGED: Improved CORS Configuration
if ENVIRONMENT == "production":
    allowed_origins =["*"]  # Start with empty list-> Allowed All
    # Add additional origins from environment
    additional_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
    if additional_origins and additional_origins[0]:
        allowed_origins.extend([origin.strip() for origin in additional_origins])
else:
    allowed_origins = ["*"]  # Allow all origins in development

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With"
    ],
    expose_headers=["X-Total-Count"],
    max_age=600
)

# Protected routes
PROTECTED_PATHS = [  # ✅ CHANGED: Renamed from protected_path to PROTECTED_PATHS (convention)
    '/api/v1/admin/update-upi_id',
    '/api/v1/admin/upi_id',
    '/api/v1/admin/get_all_users',
    '/api/v1/admin/all_wallet_data',
    '/api/v1/admin/user/{user_id}/transactions',
    '/api/v1/admin/users_with_txn_summary',
    '/api/v1/admin/todays_earnings',
    '/api/v1/admin/monthly_earnings',
    '/api/v1/admin/last_year_earnings',
    '/api/v1/admin/last_month_earnings',
    '/api/v1/user/create_transaction'
]

# Custom OpenAPI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    schema = get_openapi(
        title="Khazana Khelo API",  # ✅ CHANGED: Fixed title
        version="1.0.0",
        description="Gaming Platform Backend API",  # ✅ CHANGED: Fixed description
        routes=app.routes
    )
    
    schema['components']['securitySchemes'] = {
        'HTTPBearer': {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT'
        }
    }
    
    for path, path_item in schema['paths'].items():
        for method_name, method in path_item.items():
            if isinstance(method, dict) and path in PROTECTED_PATHS:  # ✅ CHANGED: Use PROTECTED_PATHS
                method['security'] = [{'HTTPBearer': []}]
    
    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi