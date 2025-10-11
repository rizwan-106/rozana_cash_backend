# Development Startup Script
# This ensures consistent environment settings

Write-Host "🚀 Starting Khazana Khelo in Development Mode" -ForegroundColor Green

# Clear any existing ENVIRONMENT variable
Remove-Item Env:\ENVIRONMENT -ErrorAction SilentlyContinue

# Set development environment explicitly
$env:ENVIRONMENT = "development"

# Verify .env file exists
if (!(Test-Path ".env")) {
    Write-Host "⚠️  .env file not found! Creating one..." -ForegroundColor Yellow
    "ENVIRONMENT=development" | Out-File -FilePath ".env" -Encoding UTF8
}

# Show current settings
Write-Host "📋 Current Settings:" -ForegroundColor Cyan
Write-Host "   Environment: $env:ENVIRONMENT" -ForegroundColor White
Write-Host "   Working Dir: $(Get-Location)" -ForegroundColor White
Write-Host "   .env exists: $(Test-Path '.env')" -ForegroundColor White

# Kill any existing processes
Write-Host "🔄 Stopping existing processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process uvicorn -ErrorAction SilentlyContinue | Stop-Process -Force

# Start the application
Write-Host "▶️  Starting application..." -ForegroundColor Green
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000