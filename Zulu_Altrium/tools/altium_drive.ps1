# Drive Altium Designer from PowerShell when the desktop app's computer-use tools are not available
# (2026-09-21: they dropped out of the session mid-run and could not be re-attached).  Dot-source it:
#     . tools/altium_drive.ps1; Activate; Shot before; Click 15 32; Keys '{DOWN 3}{ENTER}'
# The process is made DPI-aware first: Shot then captures the primary screen in PHYSICAL pixels (1920 x 1200
# here) and SetCursorPos takes the same pixels, so a point read off a shot can be clicked as it is.  (Without
# this, PowerShell is DPI-unaware: CopyFromScreen returned a 1536 x 960 top-left CROP of the physical screen
# while SetCursorPos was scaled by 1.25 -- every click landed 25 % too far right and down.)  Each PowerShell tool call is a fresh process: dot-source
# in every call.  Set $env:SP to the directory Shot writes into.
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class U32 {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}
"@
[void][U32]::SetProcessDPIAware()
function Shot($name) {
  $s = [System.Windows.Forms.Screen]::PrimaryScreen
  $bmp = New-Object System.Drawing.Bitmap $s.Bounds.Width, $s.Bounds.Height
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($s.Bounds.Location, [System.Drawing.Point]::Empty, $s.Bounds.Size)
  $out = Join-Path $env:SP ($name + '.png'); $bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $bmp.Dispose()
  Write-Output "shot $out"
}
function Crop($name, $x0, $y0, $x1, $y1, $scale) {
  # a magnified crop of the primary screen, for reading small text
  $s = [System.Windows.Forms.Screen]::PrimaryScreen
  $bmp = New-Object System.Drawing.Bitmap $s.Bounds.Width, $s.Bounds.Height
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($s.Bounds.Location, [System.Drawing.Point]::Empty, $s.Bounds.Size); $g.Dispose()
  $w = $x1 - $x0; $h = $y1 - $y0
  $c = New-Object System.Drawing.Bitmap ([int]($w * $scale)), ([int]($h * $scale))
  $g2 = [System.Drawing.Graphics]::FromImage($c); $g2.InterpolationMode = 'NearestNeighbor'
  $g2.DrawImage($bmp, (New-Object System.Drawing.Rectangle 0, 0, $c.Width, $c.Height), (New-Object System.Drawing.Rectangle $x0, $y0, $w, $h), 'Pixel')
  $g2.Dispose(); $bmp.Dispose()
  $out = Join-Path $env:SP ($name + '.png'); $c.Save($out, [System.Drawing.Imaging.ImageFormat]::Png); $c.Dispose()
  Write-Output "crop $out"
}
function Activate() {
  $p = Get-Process X2 -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
  if ($null -eq $p) { throw 'Altium (X2.EXE) is not running' }
  [void][U32]::SetForegroundWindow($p.MainWindowHandle); Start-Sleep -Milliseconds 500
  $ws = New-Object -ComObject WScript.Shell; [void]$ws.AppActivate($p.Id); Start-Sleep -Milliseconds 400
  # the first click after a focus change is swallowed (2026-09-21: four times in a row): spend it on the title bar
  [void][U32]::SetCursorPos(900, 14); Start-Sleep -Milliseconds 150
  [U32]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 60; [U32]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 500
  Write-Output ("activated {0} '{1}'" -f $p.Id, $p.MainWindowTitle)
}
function Front() {
  $h = [U32]::GetForegroundWindow(); $sb = New-Object System.Text.StringBuilder 256; [void][U32]::GetWindowText($h, $sb, 256); $sb.ToString()
}
function MoveTo($x, $y) { [void][U32]::SetCursorPos($x, $y); Start-Sleep -Milliseconds 120 }
function Click($x, $y) {
  MoveTo $x $y
  [U32]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 80; [U32]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 350
}
function DblClick($x, $y) {
  MoveTo $x $y
  foreach ($i in 1..2) { [U32]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 60; [U32]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 90 }
  Start-Sleep -Milliseconds 400
}
function Keys($t) { $ws = New-Object -ComObject WScript.Shell; $ws.SendKeys($t); Start-Sleep -Milliseconds 350 }
function Pause($ms) { Start-Sleep -Milliseconds $ms }
