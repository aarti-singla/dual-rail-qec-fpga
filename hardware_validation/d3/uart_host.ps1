# uart_host.ps1: PowerShell version of uart_host.py (no installation needed on Windows).
# Usage: .\uart_host.ps1 -Port COM5 -VectorsFile vectors\syndrome_stim_40000.csv
# If scripts are blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

param(
    [Parameter(Mandatory=$true)][string]$Port,
    [Parameter(Mandatory=$true)][string]$VectorsFile,
    [string]$LogFile = "uart_results.csv",
    [int]$TimeoutMs = 500
)

# ---- Reference decoder: same d=3 bit-flip mapping as the paper ----
# 00 -> no error, 10 -> q0, 11 -> q1, 01 -> q2
function Get-ReferenceDecode {
    param([int]$s_zz01, [int]$s_zz12)
    $syn = ($s_zz01 -shl 1) -bor $s_zz12
    switch ($syn) {
        0b00 { return @{Correction = 0b000; ErrIdx = 3} }  # no error
        0b10 { return @{Correction = 0b001; ErrIdx = 0} }  # q0
        0b11 { return @{Correction = 0b010; ErrIdx = 1} }  # q1
        0b01 { return @{Correction = 0b100; ErrIdx = 2} }  # q2
    }
}

# ---- Load vectors from CSV ----
if (-not (Test-Path $VectorsFile)) {
    Write-Error "Vector file not found: $VectorsFile"
    exit 1
}
$vectors = Import-Csv $VectorsFile
Write-Host "Loaded $($vectors.Count) syndrome vectors from $VectorsFile"

# ---- Open the serial port ----
$serialPort = New-Object System.IO.Ports.SerialPort $Port, 115200, ([System.IO.Ports.Parity]::None), 8, ([System.IO.Ports.StopBits]::One)
$serialPort.ReadTimeout = $TimeoutMs
$serialPort.WriteTimeout = $TimeoutMs

try {
    $serialPort.Open()
} catch {
    Write-Error "Could not open $Port : $_"
    exit 1
}

Start-Sleep -Seconds 2   # let the board's USB-UART bridge settle

$results = New-Object System.Collections.Generic.List[Object]
$mismatches = 0
$timeouts = 0
$i = 0
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

foreach ($v in $vectors) {
    $i++
    $s_zz01 = [int]$v.s_zz01
    $s_zz12 = [int]$v.s_zz12

    $txByte = ($s_zz01 -band 0x1) -bor (($s_zz12 -band 0x1) -shl 1)
    $serialPort.Write(@([byte]$txByte), 0, 1)

    $status = "OK"
    $hwCorrection = $null
    $hwErrIdx = $null
    $hwLatency = $null

    try {
        $byte0 = $serialPort.ReadByte()
        $byte1 = $serialPort.ReadByte()

        $hwCorrection = $byte0 -band 0x7
        $hwErrIdx = ($byte0 -shr 3) -band 0x3
        $hwValid = ($byte0 -shr 5) -band 0x1
        $hwLatency = $byte1

        $ref = Get-ReferenceDecode -s_zz01 $s_zz01 -s_zz12 $s_zz12
        if ($hwCorrection -ne $ref.Correction -or $hwErrIdx -ne $ref.ErrIdx -or $hwValid -ne 1) {
            $status = "MISMATCH"
            $mismatches++
        }
    } catch {
        $status = "TIMEOUT"
        $timeouts++
    }

    $results.Add([PSCustomObject]@{
        s_zz01 = $s_zz01
        s_zz12 = $s_zz12
        hw_correction = $hwCorrection
        hw_err_idx = $hwErrIdx
        hw_latency_cycles = $hwLatency
        status = $status
    })

    if ($i % 1000 -eq 0) {
        $elapsed = $stopwatch.Elapsed.TotalSeconds
        Write-Host ("  {0}/{1} vectors sent ({2} mismatches, {3} timeouts, {4:N1}s elapsed)" -f $i, $vectors.Count, $mismatches, $timeouts, $elapsed)
    }
}

$stopwatch.Stop()
$serialPort.Close()

$results | Export-Csv -Path $LogFile -NoTypeInformation

Write-Host ""
Write-Host ("=" * 60)
Write-Host " Total vectors     : $($vectors.Count)"
Write-Host " Mismatches        : $mismatches"
Write-Host " Timeouts          : $timeouts"
Write-Host " Matched reference : $($vectors.Count - $mismatches - $timeouts) / $($vectors.Count)"
Write-Host (" Wall-clock time   : {0:N1} s" -f $stopwatch.Elapsed.TotalSeconds)

$validCycles = $results | Where-Object { $_.hw_latency_cycles -ne $null } | Select-Object -ExpandProperty hw_latency_cycles
if ($validCycles.Count -gt 0) {
    $minC = ($validCycles | Measure-Object -Minimum).Minimum
    $maxC = ($validCycles | Measure-Object -Maximum).Maximum
    $mode = ($validCycles | Group-Object | Sort-Object Count -Descending | Select-Object -First 1).Name
    Write-Host " Measured latency  : $minC-$maxC cycles (mode: $mode)"
}
Write-Host " Full log written to: $LogFile"
Write-Host ("=" * 60)

if ($mismatches -eq 0 -and $timeouts -eq 0) {
    Write-Host "All hardware responses matched the independent reference decoder."
} else {
    Write-Host "WARNING: some responses did not match or timed out -- see log for details."
}
