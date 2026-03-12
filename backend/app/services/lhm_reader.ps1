<#
.SYNOPSIS
    LibreHardwareMonitor background sensor reader.
    Loads LibreHardwareMonitorLib.dll and writes sensor data as JSON to a temp file
    every $IntervalMs milliseconds. Used by the HardwareMonitor Python backend on
    Windows as a replacement for the WMI approach (removed in LHM 0.9.x).

.PARAMETER DllPath
    Full path to LibreHardwareMonitorLib.dll.

.PARAMETER OutputFile
    Path to the output JSON file that the Python backend reads.

.PARAMETER IntervalMs
    Polling interval in milliseconds (default: 2000).
#>
param(
    [Parameter(Mandatory)][string]$DllPath,
    [Parameter(Mandatory)][string]$OutputFile,
    [int]$IntervalMs = 2000
)

Set-StrictMode -Off
$ErrorActionPreference = 'SilentlyContinue'

# ── Load LHM library ─────────────────────────────────────────────────────────
try {
    Add-Type -Path $DllPath
} catch {
    @{ error = "Failed to load DLL: $_"; timestamp = 0 } | ConvertTo-Json | Set-Content $OutputFile -Encoding UTF8
    exit 1
}

# ── Build Computer object (enable all sensors except storage to save time) ───
$computer = New-Object LibreHardwareMonitor.Hardware.Computer
$computer.IsCpuEnabled         = $true
$computer.IsGpuEnabled         = $true
$computer.IsMotherboardEnabled = $true
$computer.IsMemoryEnabled      = $true
$computer.IsBatteryEnabled     = $true
$computer.IsStorageEnabled     = $false
$computer.IsNetworkEnabled     = $false
$computer.IsControllerEnabled  = $false

try {
    $computer.Open()
} catch {
    @{ error = "Computer.Open() failed: $_"; timestamp = 0 } | ConvertTo-Json | Set-Content $OutputFile -Encoding UTF8
    exit 2
}

# ── Update visitor (triggers hardware data refresh) ─────────────────────────
$visitorSrc = @"
using LibreHardwareMonitor.Hardware;
public class UpdateVisitor : IVisitor {
    public void VisitComputer(IComputer computer) { computer.Traverse(this); }
    public void VisitHardware(IHardware hardware) {
        hardware.Update();
        foreach (var sub in hardware.SubHardware) sub.Accept(this);
    }
    public void VisitSensor(ISensor sensor) {}
    public void VisitParameter(IParameter parameter) {}
}
"@
try {
    Add-Type -TypeDefinition $visitorSrc -ReferencedAssemblies $DllPath
    $visitor = New-Object UpdateVisitor
} catch {
    # Fallback: update manually without visitor
    $visitor = $null
}

# ── Helper: recursively collect sensors from hardware + subhardware ──────────
function Get-Sensors {
    param([LibreHardwareMonitor.Hardware.IHardware]$hw)
    $result = @()
    foreach ($s in $hw.Sensors) {
        if ($null -ne $s.Value) {
            $result += [PSCustomObject]@{
                hardware     = $hw.Name
                hardwareType = $hw.HardwareType.ToString()
                name         = $s.Name
                type         = $s.SensorType.ToString()
                value        = [math]::Round([float]$s.Value, 2)
                identifier   = $s.Identifier.ToString()
            }
        }
    }
    foreach ($sub in $hw.SubHardware) {
        $sub.Update()
        $result += Get-Sensors $sub
    }
    return $result
}

# ── Main polling loop ────────────────────────────────────────────────────────
while ($true) {
    try {
        if ($visitor) {
            $computer.Accept($visitor)
        } else {
            foreach ($hw in $computer.Hardware) { $hw.Update() }
        }

        $sensors = @()
        foreach ($hw in $computer.Hardware) {
            $sensors += Get-Sensors $hw
        }

        $payload = [PSCustomObject]@{
            timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
            sensors   = $sensors
        } | ConvertTo-Json -Depth 4 -Compress

        # Atomic write: write to .tmp then rename to avoid partial-read races
        $tmp = "$OutputFile.tmp"
        [System.IO.File]::WriteAllText($tmp, $payload, [System.Text.Encoding]::UTF8)
        Move-Item -LiteralPath $tmp -Destination $OutputFile -Force

    } catch {
        # Keep running; log error in output so Python can surface it
        @{ error = $_.ToString(); timestamp = 0 } | ConvertTo-Json -Compress |
            Set-Content $OutputFile -Encoding UTF8
    }

    Start-Sleep -Milliseconds $IntervalMs
}

$computer.Close()
