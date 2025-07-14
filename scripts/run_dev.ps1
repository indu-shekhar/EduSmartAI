# PowerShell script to run EduSmartAI in development mode
# Usage: .\scripts\run_dev.ps1 [-RefreshIndex]

param(
    [switch]$RefreshIndex,
    [switch]$Help,
    [int]$Port = 8000
)

if ($Help) {
    Write-Host "EduSmartAI Development Server" -ForegroundColor Green
    Write-Host "Usage: .\scripts\run_dev.ps1 [-RefreshIndex] [-Port <port>] [-Help]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Parameters:" -ForegroundColor Cyan
    Write-Host "  -RefreshIndex    Refresh the document index before starting" -ForegroundColor White
    Write-Host "  -Port <number>   Specify the port number (default: 8000)" -ForegroundColor White
    Write-Host "  -Help            Show this help message" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Cyan
    Write-Host "  .\scripts\run_dev.ps1                    # Start development server" -ForegroundColor White
    Write-Host "  .\scripts\run_dev.ps1 -RefreshIndex      # Refresh index and start" -ForegroundColor White
    Write-Host "  .\scripts\run_dev.ps1 -Port 5000         # Start on port 5000" -ForegroundColor White
    exit 0
}

Write-Host "EduSmartAI Development Server" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

# Change to project directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectPath = Split-Path -Parent $scriptPath
Set-Location $projectPath

Write-Host "Project directory: $projectPath" -ForegroundColor Cyan

# Check if virtual environment exists
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please create it first with: py -m venv venv" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
try {
    & ".\venv\Scripts\Activate.ps1"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to activate virtual environment"
    }
} catch {
    Write-Host "Failed to activate virtual environment" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "Warning: .env file not found!" -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Write-Host "Found .env.example file. Please copy it to .env and configure your settings." -ForegroundColor Cyan
        $response = Read-Host "Would you like me to copy .env.example to .env now? (y/N)"
        if ($response -eq "y" -or $response -eq "Y") {
            Copy-Item ".env.example" ".env"
            Write-Host "Copied .env.example to .env" -ForegroundColor Green
            Write-Host "Please edit .env file and add your GEMINI_API_KEY" -ForegroundColor Yellow
            Write-Host "Press Enter when ready to continue..."
            Read-Host
        }
    }
}

# Set environment variables for Flask
$env:FLASK_APP = "app"
$env:FLASK_DEBUG = "1"
$env:FLASK_ENV = "development"

Write-Host "Environment configured for development" -ForegroundColor Green

# Check if dependencies are installed
Write-Host "Checking dependencies..." -ForegroundColor Yellow
try {
    python -c "import flask; import llama_index.core; import chromadb" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Dependencies not found"
    }
    Write-Host "Dependencies are installed" -ForegroundColor Green
} catch {
    Write-Host "Some dependencies might be missing" -ForegroundColor Yellow
    $response = Read-Host "Would you like to install dependencies now? (y/N)"
    if ($response -eq "y" -or $response -eq "Y") {
        Write-Host "Installing dependencies..." -ForegroundColor Yellow
        pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to install dependencies" -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }
        Write-Host "Dependencies installed successfully" -ForegroundColor Green
    }
}

# Refresh index if requested
if ($RefreshIndex) {
    Write-Host "Refreshing document index..." -ForegroundColor Yellow
    python ingest.py --refresh
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to refresh index" -ForegroundColor Red
        $response = Read-Host "Continue anyway? (y/N)"
        if ($response -ne "y" -and $response -ne "Y") {
            exit 1
        }
    } else {
        Write-Host "Index refreshed successfully" -ForegroundColor Green
    }
}

# Check if books directory has content
if (Test-Path "books") {
    $pdfCount = (Get-ChildItem "books\*.pdf" -ErrorAction SilentlyContinue).Count
    if ($pdfCount -eq 0) {
        Write-Host "Warning: No PDF files found in books directory" -ForegroundColor Yellow
        Write-Host "Add some PDF files to books\ directory for full functionality" -ForegroundColor Cyan
    } else {
        Write-Host "Found $pdfCount PDF files in books directory" -ForegroundColor Green
    }
} else {
    Write-Host "Creating books directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "books" -Force | Out-Null
    Write-Host "Books directory created. Add PDF files for indexing." -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Starting Flask development server on port $Port..." -ForegroundColor Green
Write-Host "Open your browser and navigate to: http://localhost:$Port" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start Flask development server
try {
    flask run --host=127.0.0.1 --port=$Port --reload
} catch {
    Write-Host "Failed to start Flask server" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Development server stopped" -ForegroundColor Yellow
