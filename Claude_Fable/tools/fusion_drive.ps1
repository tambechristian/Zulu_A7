Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class U32 {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
}
"@
function Shot($name) {
  $s = [System.Windows.Forms.Screen]::AllScreens | Where-Object { $_.DeviceName -eq '\\.\DISPLAY5' }
  $bmp = New-Object System.Drawing.Bitmap $s.Bounds.Width, $s.Bounds.Height
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($s.Bounds.Location, [System.Drawing.Point]::Empty, $s.Bounds.Size)
  $out = Join-Path $env:SP ($name + '.png'); $bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $bmp.Dispose(); Write-Output "shot $out"
}
function Activate() {
  $p = Get-Process Fusion360 -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
  [void][U32]::SetForegroundWindow($p.MainWindowHandle); Start-Sleep -Milliseconds 600
  $ws = New-Object -ComObject WScript.Shell; [void]$ws.AppActivate($p.Id); Start-Sleep -Milliseconds 400
  Write-Output ("activated {0} '{1}'" -f $p.Id, $p.MainWindowTitle)
}
function Click($x, $y) {
  [void][U32]::SetCursorPos($x, $y); Start-Sleep -Milliseconds 150
  [U32]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 80; [U32]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 300
}
function TypeText($t) { $ws = New-Object -ComObject WScript.Shell; $ws.SendKeys($t); Start-Sleep -Milliseconds 300 }
