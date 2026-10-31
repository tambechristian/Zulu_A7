# write the full command line of every running tools/router.py process, one per line
param([string]$Out = "$env:LOCALAPPDATA\Temp\routing\s5\running_cmds.txt")
$lines = Get-CimInstance Win32_Process |
    Where-Object { $_.Name -like 'python*' -and ([string]$_.CommandLine) -like '*router.py*' } |
    ForEach-Object { [string]$_.CommandLine }
$lines | Out-File -FilePath $Out -Encoding utf8
Write-Output ("{0} router processes" -f @($lines).Count)
