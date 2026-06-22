param(
    [string]$SkillRoot,
    [switch]$Installed,
    [switch]$ListPorts,
    [switch]$Board,
    [ValidateSet("none", "smoke", "sensor", "otsu", "resources", "rect-target", "circle-target", "all-core")]
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
        [string]$Label
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

    Invoke-Checked { python @cmdArgs } $Label
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
        Invoke-RawReplScript -ScriptPath (Join-Path $skillRootResolved "scripts\probe_board_resources.py") -Label "board probe: model and example resources"
    }
    "rect-target" {
        Invoke-RawReplScript -ScriptPath (Join-Path $skillRootResolved "scripts\probe_cvlite_rectangle_target.py") -Label "board target probe: cv_lite rectangle"
    }
    "circle-target" {
        Invoke-RawReplScript -ScriptPath (Join-Path $skillRootResolved "scripts\probe_circle_target.py") -Label "board target probe: circle"
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
