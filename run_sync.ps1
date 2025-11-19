# Google Sheets to sbdb Auto Sync Script
# PowerShell version

# Set UTF-8 encoding for PowerShell output
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Use script's directory automatically (handles Korean path correctly)
$WorkDir = $PSScriptRoot
if (-not $WorkDir) {
    $WorkDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}

$LogDir = Join-Path $WorkDir "logs"
$ScriptPath = Join-Path $WorkDir "sync_google_sheet_incremental.py"

Write-Host "Working Directory: $WorkDir" -ForegroundColor Cyan
Write-Host "Log Directory: $LogDir" -ForegroundColor Cyan

# Create log directory if not exists
if (-not (Test-Path $LogDir)) {
    try {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
        Write-Host "Created log directory" -ForegroundColor Green
    } catch {
        Write-Host "Failed to create log directory: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

# Generate log filename
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path $LogDir "sync_$Timestamp.log"

Write-Host "Log file: $LogFile" -ForegroundColor Cyan

# Log header
$Header = @"
==================================================
Google Sheets Auto Sync
Start Time: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Working Directory: $WorkDir
==================================================
"@

try {
    $Header | Out-File -FilePath $LogFile -Encoding UTF8
} catch {
    Write-Host "Failed to write log header: $($_.Exception.Message)" -ForegroundColor Red
}

# Change to working directory
Set-Location $WorkDir

# Run Python script
Write-Host ""
Write-Host "Starting sync..." -ForegroundColor Yellow
Write-Host ""

try {
    $Process = Start-Process -FilePath "python" `
        -ArgumentList $ScriptPath `
        -Wait `
        -NoNewWindow `
        -PassThru `
        -RedirectStandardOutput (Join-Path $LogDir "temp_stdout.txt") `
        -RedirectStandardError (Join-Path $LogDir "temp_stderr.txt")

    # Read output
    $StdOut = Get-Content (Join-Path $LogDir "temp_stdout.txt") -Raw -ErrorAction SilentlyContinue
    $StdErr = Get-Content (Join-Path $LogDir "temp_stderr.txt") -Raw -ErrorAction SilentlyContinue

    # Display output
    if ($StdOut) { Write-Host $StdOut }
    if ($StdErr) { Write-Host $StdErr -ForegroundColor Red }

    # Append to log
    if ($StdOut) { $StdOut | Out-File -FilePath $LogFile -Append -Encoding UTF8 }
    if ($StdErr) { $StdErr | Out-File -FilePath $LogFile -Append -Encoding UTF8 }

    # Clean up temp files
    Remove-Item (Join-Path $LogDir "temp_stdout.txt") -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $LogDir "temp_stderr.txt") -ErrorAction SilentlyContinue

    if ($Process.ExitCode -eq 0) {
        $Success = @"

[SUCCESS] Sync completed successfully
Exit Code: 0
"@
        $Success | Out-File -FilePath $LogFile -Append -Encoding UTF8
        Write-Host ""
        Write-Host "[SUCCESS] Sync completed" -ForegroundColor Green
    } else {
        $Error = @"

[ERROR] Sync failed with exit code: $($Process.ExitCode)
"@
        $Error | Out-File -FilePath $LogFile -Append -Encoding UTF8
        Write-Host ""
        Write-Host "[ERROR] Sync failed (Exit Code: $($Process.ExitCode))" -ForegroundColor Red
    }

} catch {
    $ErrorMsg = @"

[ERROR] Exception occurred: $($_.Exception.Message)
Stack Trace: $($_.Exception.StackTrace)
"@
    $ErrorMsg | Out-File -FilePath $LogFile -Append -Encoding UTF8
    Write-Host ""
    Write-Host "[ERROR] Exception: $($_.Exception.Message)" -ForegroundColor Red
}

# Log footer
$Footer = @"
==================================================
End Time: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
==================================================
"@

try {
    $Footer | Out-File -FilePath $LogFile -Append -Encoding UTF8
} catch {
    Write-Host "Failed to write log footer" -ForegroundColor Red
}

Write-Host ""
Write-Host "Log saved to: $LogFile" -ForegroundColor Cyan
