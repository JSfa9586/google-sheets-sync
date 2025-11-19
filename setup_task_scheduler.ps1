# Windows Task Scheduler Auto Registration Script
# Google Sheets Auto Sync Task

# Use script's directory automatically (handles Korean path correctly)
$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}

$TaskName = "GoogleSheets-to-sbdb-AutoSync"
$TaskDescription = "3시간마다 구글 시트를 sbdb에 자동 동기화합니다."
$SyncScriptPath = Join-Path $ScriptDir "run_sync.ps1"

Write-Host "Script Directory: $ScriptDir" -ForegroundColor Cyan
Write-Host "Sync Script: $SyncScriptPath" -ForegroundColor Cyan
Write-Host ""

# Check if sync script exists
if (-not (Test-Path $SyncScriptPath)) {
    Write-Host "ERROR: Sync script not found: $SyncScriptPath" -ForegroundColor Red
    exit 1
}

# Get current user properly
$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
Write-Host "Current User: $CurrentUser" -ForegroundColor Cyan
Write-Host ""

# Check if task exists and remove
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create trigger (repeat every 3 hours, indefinitely)
# Note: Omitting RepetitionDuration makes it repeat indefinitely
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Hours 3)

# Create action (run PowerShell script)
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$SyncScriptPath`""

# Task settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# Register task (simplified - use current user automatically)
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Description $TaskDescription `
        -Trigger $Trigger `
        -Action $Action `
        -Settings $Settings `
        -User $CurrentUser `
        -Force | Out-Null

    Write-Host ""
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "Task Scheduler Registration Completed!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "Task Name: $TaskName"
    Write-Host "User: $CurrentUser"
    Write-Host "Schedule: Every 3 hours (indefinitely)"
    Write-Host "Script: $SyncScriptPath"
    Write-Host ""
    Write-Host "Task Management:" -ForegroundColor Cyan
    Write-Host "  - View: taskschd.msc (Open Task Scheduler)"
    Write-Host "  - Run now: Start-ScheduledTask -TaskName '$TaskName'"
    Write-Host "  - Status: Get-ScheduledTaskInfo -TaskName '$TaskName'"
    Write-Host "  - Remove: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
    Write-Host ""
    Write-Host "Logs: $(Join-Path $ScriptDir 'logs')" -ForegroundColor Yellow
    Write-Host "================================================" -ForegroundColor Green

    # Verify task was created
    $CreatedTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($CreatedTask) {
        Write-Host ""
        Write-Host "Task verification: SUCCESS" -ForegroundColor Green

        # Ask for test run
        Write-Host ""
        $TestRun = Read-Host "Do you want to test run now? (Y/N)"
        if ($TestRun -eq "Y" -or $TestRun -eq "y") {
            Write-Host ""
            Write-Host "Starting test run..." -ForegroundColor Cyan
            Start-ScheduledTask -TaskName $TaskName

            Write-Host "Waiting for task to complete..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5

            $TaskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
            Write-Host ""
            Write-Host "Task Info:" -ForegroundColor Cyan
            Write-Host "  Last run: $($TaskInfo.LastRunTime)"
            Write-Host "  Last result: $($TaskInfo.LastTaskResult) (0 = Success)"
            Write-Host "  Next run: $($TaskInfo.NextRunTime)"

            # Show recent log
            $LogDir = Join-Path $ScriptDir "logs"
            if (Test-Path $LogDir) {
                Start-Sleep -Seconds 2
                $LatestLog = Get-ChildItem $LogDir -Filter "sync_*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
                if ($LatestLog) {
                    Write-Host ""
                    Write-Host "Latest log file: $($LatestLog.FullName)" -ForegroundColor Yellow
                    Write-Host "Log size: $([math]::Round($LatestLog.Length / 1KB, 2)) KB" -ForegroundColor Yellow
                }
            }
        }
    } else {
        Write-Host ""
        Write-Host "WARNING: Task created but verification failed" -ForegroundColor Yellow
    }

} catch {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Red
    Write-Host "ERROR: Failed to register task" -ForegroundColor Red
    Write-Host "================================================" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possible solutions:" -ForegroundColor Yellow
    Write-Host "  1. Run PowerShell as Administrator"
    Write-Host "  2. Check if Task Scheduler service is running:"
    Write-Host "     Get-Service -Name 'Schedule'"
    Write-Host "  3. Try manual registration using Task Scheduler GUI"
    Write-Host "     - Press Win+R, type: taskschd.msc"
    Write-Host "================================================" -ForegroundColor Red
}
