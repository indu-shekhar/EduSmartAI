# PowerShell Script Troubleshooting Guide

## Issues Fixed

### 1. PowerShell Execution Policy Error
**Problem**: Scripts cannot run due to execution policy restrictions.

**Solution**: Run this command in PowerShell as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2. Unicode Character Encoding Issues
**Problem**: Emojis and special characters causing parser errors.

**Solution**: Removed all Unicode characters from PowerShell scripts to ensure compatibility across different PowerShell versions and encoding settings.

### 3. Line Ending Issues
**Problem**: Mixed line endings causing parsing errors.

**Solution**: Ensured all PowerShell scripts use Windows CRLF line endings.

### 4. Ampersand Operator Issues
**Problem**: Improper use of & operator causing syntax errors.

**Solution**: Wrapped commands in try-catch blocks and used proper PowerShell syntax.

## How to Test the Fix

1. **Check Execution Policy**:
   ```powershell
   Get-ExecutionPolicy -Scope CurrentUser
   ```
   Should return "RemoteSigned" or "Unrestricted"

2. **Test Script Syntax**:
   ```powershell
   Get-Command .\scripts\run_dev.ps1
   ```
   Should not show any syntax errors.

3. **Run with Verbose**:
   ```powershell
   .\scripts\run_dev.ps1 -Verbose
   ```

## Alternative Solutions

If you still encounter issues, you can:

1. **Use the batch files instead**:
   ```cmd
   .\scripts\activate_venv.bat
   python ingest.py --refresh
   flask run --host=127.0.0.1 --port=8000
   ```

2. **Run commands manually**:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   $env:FLASK_APP = "app"
   $env:FLASK_DEBUG = "1"
   flask run --port=8000
   ```

3. **Use PowerShell ISE or VS Code** instead of regular PowerShell console for better Unicode support.

## Common PowerShell Issues and Solutions

### Issue: "Execution of scripts is disabled on this system"
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
```

### Issue: "Cannot load module" errors
```powershell
Import-Module -Name Microsoft.PowerShell.Management -Force
```

### Issue: Unicode display problems
Set PowerShell to use UTF-8:
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```
