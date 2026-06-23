param(
    [string]$SkillRoot,
    [switch]$Installed,
    [switch]$ListPorts,
    [switch]$Board,
    [ValidateSet("none", "smoke", "sensor", "otsu", "resources", "rect-target", "circle-target", "yolo", "uart-loopback", "all-core")]
    [string]$Vision = "none",
    [string]$Port,
    [double]$Timeout = 45,
    [switch]$SkipValidate
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    Write-Host ""
    Write-Host "==> $Label"
    $global:LASTEXITCODE = 0
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

function Invoke-RawReplScript {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,
        [Parameter(Mandatory = $true)]
        [string]$Label,
        [string]$AssessmentKind = ""
    )

    if (-not (Test-Path -LiteralPath $ScriptPath)) {
        throw "Missing board test script: $ScriptPath"
    }

    $cmdArgs = @($rawRepl)
    if ($Port) {
        $cmdArgs += @("--port", $Port)
    }
    if ($Timeout -gt 0) {
        $cmdArgs += @("--timeout", [string]$Timeout)
    }
    $cmdArgs += $ScriptPath

    Write-Host ""
    Write-Host "==> $Label"
    $global:LASTEXITCODE = 0
    $oldErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & python @cmdArgs 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldErrorActionPreference
    }
    foreach ($line in $output) {
        Write-Host $line
    }
    if ($exitCode -ne 0) {
        throw "$Label failed with exit code $exitCode"
    }

    if ($AssessmentKind) {
        if (-not (Test-Path -LiteralPath $assessProbe)) {
            throw "Missing probe assessment helper: $assessProbe"
        }
        $logPath = Join-Path ([System.IO.Path]::GetTempPath()) ("jlc-k230-{0}-{1}.log" -f $AssessmentKind, [System.Guid]::NewGuid().ToString("N"))
        $output | ForEach-Object { [string]$_ } | Set-Content -Encoding UTF8 -LiteralPath $logPath
        try {
            Invoke-Checked { python $assessProbe --kind $AssessmentKind $logPath } "assess probe result: $AssessmentKind"
        } finally {
            Remove-Item -LiteralPath $logPath -ErrorAction SilentlyContinue
        }
    }
}

function Invoke-ListPorts {
    $cmdArgs = @($rawRepl, "--list-ports")
    Invoke-Checked { python @cmdArgs } "list K230 serial ports"
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

if (-not $SkillRoot) {
    if ($Installed) {
        $codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
        $SkillRoot = Join-Path $codexHome "skills\jlc-k230-lushan-pi"
    } else {
        $SkillRoot = Join-Path $repoRoot "jlc-k230-lushan-pi"
    }
}

$skillRootResolved = (Resolve-Path -LiteralPath $SkillRoot).Path
$rawRepl = Join-Path $skillRootResolved "scripts\run_canmv_raw_repl.py"
$assessProbe = Join-Path $skillRootResolved "scripts\evaluate_probe_log.py"
$validateScript = Join-Path $repoRoot "tools\validate.ps1"

if (-not (Test-Path -LiteralPath $rawRepl)) {
    throw "Missing raw REPL helper: $rawRepl"
}

if (-not $SkipValidate) {
    if ($Installed) {
        Invoke-Checked { & $validateScript -Installed } "offline skill validation"
    } else {
        Invoke-Checked { & $validateScript $skillRootResolved } "offline skill validation"
    }
} else {
    Write-Warning "Skipping offline skill validation because -SkipValidate was set."
}

if ($Board -and $Vision -eq "none") {
    $Vision = "smoke"
}

$needsBoard = $Board -or $ListPorts -or ($Vision -ne "none")
if ($needsBoard) {
    Write-Host ""
    Write-Host "Board mode uses raw REPL from RAM only. It does not write /sdcard/main.py."
    Invoke-ListPorts
}

if ($Vision -ne "none" -and -not $Board) {
    $Board = $true
}

switch ($Vision) {
    "none" {
        # 只列串口或只做离线验证。
    }
    "smoke" {
        Invoke-RawReplScript -ScriptPath (Join-Path $skillRootResolved "scripts\smoke_camera_lcd.py") -Label "board smoke: camera + 3.1-inch LCD"
    }
    "sensor" {
        Invoke-RawReplScript -ScriptPath (Join-Path $skillRootResolved "scripts\probe_k230_sensor_init.py") -Label "board probe: K230 Sensor init modes"
    }
    "otsu" {
        Invoke-RawReplScript -ScriptPath (Join-Path $skillRootResolved "scripts\probe_otsu_threshold.py") -Label "board probe: Otsu threshold chain"
    }
    "resources" {
        Invoke-RawReplScript -ScriptPath (Join-Path $skillRootResolved "scripts\probe_board_resources.py") -Label "board probe: model and example resources" -AssessmentKind "resources"
    }
    "rect-target" {
        Invoke-RawReplScript -ScriptPath (Join-Path $skillRootResolved "scripts\probe_cvlite_rectangle_target.py") -Label "board target probe: cv_lite rectangle" -AssessmentKind "rect"
    }
    "circle-target" {
        Invoke-RawReplScript -ScriptPath (Join-Path $skillRootResolved "scripts\probe_circle_target.py") -Label "board target probe: circle" -AssessmentKind "circle"
    }
    "yolo" {
        Invoke-RawReplScript -ScriptPath (Join-Path $skillRootResolved "scripts\probe_yolo_runtime.py") -Label "board probe: YOLO runtime and resources" -AssessmentKind "yolo"
    }
    "uart-loopback" {
        Invoke-RawReplScript -ScriptPath (Join-Path $skillRootResolved "scripts\probe_uart2_loopback.py") -Label "board probe: UART2 loopback and TX sweep" -AssessmentKind "uart"
    }
    "all-core" {
        Invoke-RawReplScript -ScriptPath (Join-Path $skillRootResolved "scripts\smoke_camera_lcd.py") -Label "board smoke: camera + 3.1-inch LCD"
        Invoke-RawReplScript -ScriptPath (Join-Path $skillRootResolved "scripts\probe_k230_sensor_init.py") -Label "board probe: K230 Sensor init modes"
        Invoke-RawReplScript -ScriptPath (Join-Path $skillRootResolved "scripts\probe_otsu_threshold.py") -Label "board probe: Otsu threshold chain"
    }
    default {
        throw "Unsupported vision test: $Vision"
    }
}

Write-Host ""
Write-Host "TEST_OK skill=$skillRootResolved vision=$Vision board=$Board installed=$Installed"
