from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import certifi
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables ONCE at the top
load_dotenv()

# Get environment variables
db_url = os.getenv("MONGODB_URL")
database_name = os.getenv("DATABASE", "khazana_khelo")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Validate critical environment variables
if not db_url:
    logger.error("❌ MONGODB_URL environment variable not set")
    raise ValueError("MONGODB_URL environment variable is required")

if not database_name:
    logger.error("❌ DATABASE environment variable not set")
    raise ValueError("DATABASE environment variable is required")

# MongoDB Client Configuration
try:
    if "mongodb+srv://" in db_url:
        logger.info(f"🔄 Connecting to MongoDB ({ENVIRONMENT} environment)...")
        
        client_config = {
            "maxPoolSize": 50,
            "minPoolSize": 10,
            "maxIdleTimeMS": 45000,
            "serverSelectionTimeoutMS": 5000,
            "connectTimeoutMS": 10000,
            "socketTimeoutMS": 60000,
            "retryWrites": True,
        }
        
        # 👉🏻 MAIN CHANGE: Different SSL for development vs production
        if ENVIRONMENT == "production":
            # Production: Strict SSL
            client_config.update({
                "tls": True,
                "tlsCAFile": certifi.where(),
            })
            logger.info("✅ Production: Using strict SSL")
        else:
            # 👉🏻 Development: Relaxed SSL (fixes Windows SSL error)
            client_config.update({
                "tls": True,
                "tlsAllowInvalidCertificates": True,
            })
            logger.info("✅ Development: Using relaxed SSL")
        
        client = AsyncIOMotorClient(db_url, **client_config)
        db = client[database_name]
        
        logger.info(f"✅ Database '{database_name}' connected")
        
    else:
        # Local MongoDB
        client = AsyncIOMotorClient(db_url)
        db = client[database_name]
        logger.info("✅ Local MongoDB connected")
        
except Exception as e:
    logger.error(f"❌ Connection failed: {str(e)}")
    raise

# Collections
user_db = db.get_collection("users")
user_transaction_db = db.get_collection("user_transactions")
admin_db = db.get_collection("admin_db")

# 👉🏻 ADDED: Connection test
async def test_connection():
    try:
        await client.admin.command("ping")
        logger.info("✅ MongoDB ping successful")
        return True
    except Exception as e:
        logger.error(f"❌ MongoDB ping failed: {str(e)}")
        return False

# 👉🏻 ADDED: Close connection
async def close_connection():
    try:
        client.close()
        logger.info("🔌 Connection closed")
    except Exception as e:
        logger.error(f"❌ Error closing: {str(e)}")