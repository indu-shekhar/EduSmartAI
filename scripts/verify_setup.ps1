# PowerShell script to verify EduSmartAI installation
# Usage: .\scripts\verify_setup.ps1

Write-Host "🔍 EduSmartAI Setup Verification" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

$errors = @()
$warnings = @()

# Change to project directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectPath = Split-Path -Parent $scriptPath
Set-Location $projectPath

Write-Host "📁 Project directory: $projectPath" -ForegroundColor Cyan

# Check Python installation
Write-Host "`n🐍 Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
        
        # Check Python version
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
                $errors += "Python 3.10+ required, found $pythonVersion"
            }
        }
    } else {
        $errors += "Python not found in PATH"
    }
} catch {
    $errors += "Python not found or not accessible"
}

# Check virtual environment
Write-Host "`n🔧 Checking virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "✅ Virtual environment found" -ForegroundColor Green
    
    # Try to activate and check packages
    try {
        & ".\.venv\Scripts\Activate.ps1"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Virtual environment can be activated" -ForegroundColor Green
            
            # Check key packages
            $packages = @("flask", "llama_index", "chromadb", "python-dotenv")
            foreach ($package in $packages) {
                try {
                    python -c "import $($package.replace('-', '_'))" 2>$null
                    if ($LASTEXITCODE -eq 0) {
                        Write-Host "✅ Package $package is installed" -ForegroundColor Green
                    } else {
                        $errors += "Package $package not found"
                    }
                } catch {
                    $errors += "Failed to check package $package"
                }
            }
        } else {
            $errors += "Failed to activate virtual environment"
        }
    } catch {
        $errors += "Error activating virtual environment"
    }
} else {
    $errors += "Virtual environment not found at .venv\"
}

# Check configuration files
Write-Host "`n⚙️  Checking configuration files..." -ForegroundColor Yellow

# Check .env file
if (Test-Path ".env") {
    Write-Host "✅ .env file found" -ForegroundColor Green
    
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "GEMINI_API_KEY\s*=\s*[^\s]+") {
        Write-Host "✅ GEMINI_API_KEY configured" -ForegroundColor Green
    } else {
        $warnings += "GEMINI_API_KEY not configured in .env"
    }
} else {
    if (Test-Path ".env.example") {
        Write-Host "⚠️  .env file not found, but .env.example exists" -ForegroundColor Yellow
        $warnings += ".env file needs to be created from .env.example"
    } else {
        $errors += ".env.example file not found"
    }
}

# Check requirements.txt
if (Test-Path "requirements.txt") {
    Write-Host "✅ requirements.txt found" -ForegroundColor Green
} else {
    $errors += "requirements.txt not found"
}

# Check directory structure
Write-Host "`n📂 Checking directory structure..." -ForegroundColor Yellow

$requiredDirs = @("app", "app\blueprints", "app\services", "app\models", "app\templates", "app\static", "scripts", "tests")
foreach ($dir in $requiredDirs) {
    if (Test-Path $dir) {
        Write-Host "✅ Directory $dir exists" -ForegroundColor Green
    } else {
        $errors += "Directory $dir not found"
    }
}

# Check books and storage directories
if (Test-Path "books") {
    $pdfCount = (Get-ChildItem "books\*.pdf" -ErrorAction SilentlyContinue).Count
    Write-Host "✅ Books directory exists ($pdfCount PDF files)" -ForegroundColor Green
    if ($pdfCount -eq 0) {
        $warnings += "No PDF files found in books directory"
    }
} else {
    Write-Host "⚠️  Books directory will be created automatically" -ForegroundColor Yellow
}

if (Test-Path "storage") {
    Write-Host "✅ Storage directory exists" -ForegroundColor Green
} else {
    Write-Host "⚠️  Storage directory will be created automatically" -ForegroundColor Yellow
}

# Check key application files
Write-Host "`n📄 Checking application files..." -ForegroundColor Yellow

$keyFiles = @(
    "app\__init__.py",
    "app\config.py",
    "app\blueprints\chat.py",
    "app\services\llama_index_service.py",
    "app\templates\base.html",
    "app\templates\chat.html",
    "app\static\css\custom.css",
    "app\static\js\app.js",
    "ingest.py"
)

foreach ($file in $keyFiles) {
    if (Test-Path $file) {
        Write-Host "✅ $file exists" -ForegroundColor Green
    } else {
        $errors += "Key file $file not found"
    }
}

# Check Windows scripts
Write-Host "`n🔧 Checking Windows scripts..." -ForegroundColor Yellow

$scripts = @(
    "scripts\activate_venv.bat",
    "scripts\run_dev.ps1",
    "scripts\ingest.ps1"
)

foreach ($script in $scripts) {
    if (Test-Path $script) {
        Write-Host "✅ $script exists" -ForegroundColor Green
    } else {
        $errors += "Script $script not found"
    }
}

# Test import of main modules
Write-Host "`n🧪 Testing module imports..." -ForegroundColor Yellow
if (Test-Path ".venv\Scripts\Activate.ps1") {
    & ".\.venv\Scripts\Activate.ps1"
    
    try {
        python -c "from app import create_app; print('✅ App creation works')" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Flask app can be imported" -ForegroundColor Green
        } else {
            $errors += "Failed to import Flask app"
        }
    } catch {
        $errors += "Error testing Flask app import"
    }
}

# Summary
Write-Host "`n📊 Verification Summary" -ForegroundColor Green
Write-Host "======================" -ForegroundColor Green

if ($errors.Count -eq 0) {
    Write-Host "🎉 All checks passed!" -ForegroundColor Green
    
    if ($warnings.Count -gt 0) {
        Write-Host "`n⚠️  Warnings:" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host "   • $warning" -ForegroundColor Yellow
        }
    }
    
    Write-Host "`n🚀 You're ready to start EduSmartAI!" -ForegroundColor Green
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Add PDF files to the books\ directory" -ForegroundColor White
    Write-Host "2. Run: .\scripts\ingest.ps1" -ForegroundColor White
    Write-Host "3. Run: .\scripts\run_dev.ps1" -ForegroundColor White
    Write-Host "4. Open http://localhost:8000 in your browser" -ForegroundColor White
    
} else {
    Write-Host "❌ Setup verification failed!" -ForegroundColor Red
    Write-Host "`nErrors found:" -ForegroundColor Red
    foreach ($error in $errors) {
        Write-Host "   • $error" -ForegroundColor Red
    }
    
    if ($warnings.Count -gt 0) {
        Write-Host "`nWarnings:" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host "   • $warning" -ForegroundColor Yellow
        }
    }
    
    Write-Host "`n🔧 Please fix the errors above and run this script again." -ForegroundColor Yellow
}

Write-Host "`n📚 For help, see README.md or create an issue on GitHub." -ForegroundColor Cyan
Read-Host "`nPress Enter to exit"
