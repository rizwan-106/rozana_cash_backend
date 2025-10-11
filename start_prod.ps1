# Production Startup Script
# This ensures production environment settings

Write-Host "🏭 Starting Khazana Khelo in Production Mode" -ForegroundColor Red

# Set production environment explicitly
$env:ENVIRONMENT = "production"

# Verify required files
if (!(Test-Path ".env")) {
    Write-Host "❌ .env file not found! Production requires .env file." -ForegroundColor Red
    exit 1
}

# Show current settings
Write-Host "📋 Current Settings:" -ForegroundColor Cyan
Write-Host "   Environment: $env:ENVIRONMENT" -ForegroundColor White
Write-Host "   Working Dir: $(Get-Location)" -ForegroundColor White

# Validate production requirements
$envContent = Get-Content ".env" -Raw
if ($envContent -like "*your-super-secure-secret-key*") {
    Write-Host "❌ Default SECRET_KEY detected! Change it for production." -ForegroundColor Red
    exit 1
}

# Kill any existing processes
Write-Host "🔄 Stopping existing processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process uvicorn -ErrorAction SilentlyContinue | Stop-Process -Force

# Start the application (no reload in production)
Write-Host "▶️  Starting application in production mode..." -ForegroundColor Green
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4