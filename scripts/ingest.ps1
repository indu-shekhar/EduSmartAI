# PowerShell script to refresh the document index
# Usage: .\scripts\ingest.ps1 [-Rebuild] [-Verbose]

param(
    [switch]$Rebuild,
    [switch]$Verbose,
    [switch]$Help,
    [string]$BooksPath = "",
    [string]$StoragePath = ""
)

if ($Help) {
    Write-Host "EduSmartAI Document Ingestion Script" -ForegroundColor Green
    Write-Host "Usage: .\scripts\ingest.ps1 [-Rebuild] [-Verbose] [-BooksPath <path>] [-StoragePath <path>] [-Help]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Parameters:" -ForegroundColor Cyan
    Write-Host "  -Rebuild         Completely rebuild the index (default: refresh)" -ForegroundColor White
    Write-Host "  -Verbose         Enable verbose output" -ForegroundColor White
    Write-Host "  -BooksPath       Custom path to books directory" -ForegroundColor White
    Write-Host "  -StoragePath     Custom path to storage directory" -ForegroundColor White
    Write-Host "  -Help            Show this help message" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Cyan
    Write-Host "  .\scripts\ingest.ps1                     # Refresh index" -ForegroundColor White
    Write-Host "  .\scripts\ingest.ps1 -Rebuild            # Rebuild index" -ForegroundColor White
    Write-Host "  .\scripts\ingest.ps1 -Verbose            # Verbose output" -ForegroundColor White
    exit 0
}

Write-Host "📚 EduSmartAI Document Ingestion" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

# Change to project directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectPath = Split-Path -Parent $scriptPath
Set-Location $projectPath

Write-Host "📁 Project directory: $projectPath" -ForegroundColor Cyan

# Check if virtual environment exists
if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please create it first with: py -m venv .venv" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Activate virtual environment
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Yellow
& ".\.venv\Scripts\Activate.ps1"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to activate virtual environment" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if .env file exists and load it
if (Test-Path ".env") {
    Write-Host "⚙️  Loading environment configuration..." -ForegroundColor Yellow
    
    # Basic check for GEMINI_API_KEY
    $envContent = Get-Content ".env" -Raw
    if (-not ($envContent -match "GEMINI_API_KEY\s*=\s*[^\s]+")) {
        Write-Host "⚠️  Warning: GEMINI_API_KEY not found or empty in .env file" -ForegroundColor Yellow
        Write-Host "Please set your Gemini API key in the .env file" -ForegroundColor Cyan
        Read-Host "Press Enter to continue anyway (this will likely fail)"
    }
} else {
    Write-Host "❌ .env file not found!" -ForegroundColor Red
    Write-Host "Please copy .env.example to .env and configure your settings" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Build command arguments
$args = @()

if ($Rebuild) {
    $args += "--rebuild"
    Write-Host "🔄 Mode: Complete rebuild" -ForegroundColor Yellow
} else {
    $args += "--refresh"
    Write-Host "🔄 Mode: Refresh index" -ForegroundColor Yellow
}

if ($Verbose) {
    $args += "--verbose"
}

if ($BooksPath) {
    $args += "--books"
    $args += $BooksPath
    Write-Host "📚 Books directory: $BooksPath" -ForegroundColor Cyan
}

if ($StoragePath) {
    $args += "--storage"
    $args += $StoragePath
    Write-Host "💾 Storage directory: $StoragePath" -ForegroundColor Cyan
}

# Check books directory
$booksDir = if ($BooksPath) { $BooksPath } else { "books" }
if (Test-Path $booksDir) {
    $pdfCount = (Get-ChildItem "$booksDir\*.pdf" -ErrorAction SilentlyContinue).Count
    if ($pdfCount -eq 0) {
        Write-Host "⚠️  Warning: No PDF files found in $booksDir" -ForegroundColor Yellow
        $response = Read-Host "Continue anyway? (y/N)"
        if ($response -ne "y" -and $response -ne "Y") {
            exit 0
        }
    } else {
        Write-Host "📄 Found $pdfCount PDF files to process" -ForegroundColor Green
    }
} else {
    Write-Host "❌ Books directory not found: $booksDir" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "🚀 Starting document ingestion..." -ForegroundColor Green
Write-Host "Arguments: $($args -join ' ')" -ForegroundColor Gray

# Run the ingestion script
try {
    $startTime = Get-Date
    python ingest.py @args
    $endTime = Get-Date
    $duration = $endTime - $startTime
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Ingestion completed successfully!" -ForegroundColor Green
        Write-Host "⏱️  Total time: $($duration.ToString('mm\:ss'))" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "🎯 Your documents are now indexed and ready for queries!" -ForegroundColor Green
        Write-Host "Start the application with: .\scripts\run_dev.ps1" -ForegroundColor Cyan
    } else {
        Write-Host ""
        Write-Host "❌ Ingestion failed!" -ForegroundColor Red
        Write-Host "Check the output above and ingest.log for details" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Error running ingestion script" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

if ($args -contains "--verbose") {
    Write-Host ""
    Write-Host "📋 Log file location: ingest.log" -ForegroundColor Gray
}

Write-Host ""
Read-Host "Press Enter to exit"
