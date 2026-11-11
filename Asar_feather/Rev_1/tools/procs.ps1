# list python / sh processes with command lines; -Kill <regex> stops the ones whose command line matches
param([string]$Kill = '')
$ps = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -or $_.Name -eq 'sh.exe' }
foreach ($p in $ps) {
    $cl = [string]$p.CommandLine
    $short = $cl -replace [regex]::Escape('C:\Users\tambe\AppData\Local\Temp\routing\s5'), '$D'
    $short = $short -replace [regex]::Escape('C:/Users/tambe/AppData/Local/Temp/routing/s5'), '$D'
    if ($short.Length -gt 170) { $short = $short.Substring(0, 170) }
    $mb = [int]($p.PrivatePageCount / 1MB)
    $flag = ''
    if ($Kill -ne '' -and $cl -match $Kill) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue; $flag = 'KILLED ' }
    '{0}{1,6} {2,6} MB  {3}' -f $flag, $p.ProcessId, $mb, $short
}
$o = Get-CimInstance Win32_OperatingSystem
'commit {0:N1}/{1:N1} GB, free phys {2:N1} GB' -f (($o.TotalVirtualMemorySize - $o.FreeVirtualMemory) / 1MB), ($o.TotalVirtualMemorySize / 1MB), ($o.FreePhysicalMemory / 1MB)
