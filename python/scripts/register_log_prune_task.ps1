# 注册 Windows 计划任务：每天清理 Agent 日志（Agent 未常驻时可单独使用）
# 用法（PowerShell 管理员或非管理员均可，任务会创建在当前用户下）:
#   cd G:\Projects\blog\python
#   .\scripts\register_log_prune_task.ps1
#   .\scripts\register_log_prune_task.ps1 -Time "03:30" -Unregister

param(
    [string]$Time = "03:00",
    [switch]$Unregister
)

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$TaskName = "BlogAgentLogPrune"
$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) {
    Write-Error "未找到 python，请先安装并加入 PATH"
    exit 1
}
$Script = Join-Path $Root "scripts\prune_agent_logs.py"

if ($Unregister) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "已移除计划任务: $TaskName"
    exit 0
}

$Action = New-ScheduledTaskAction -Execute $Python -Argument "`"$Script`"" -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null

Write-Host "已注册计划任务: $TaskName"
Write-Host "  每天 $Time 执行: python `"$Script`""
Write-Host "  工作目录: $Root"
Write-Host "移除任务: .\scripts\register_log_prune_task.ps1 -Unregister"
