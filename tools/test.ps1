param(
    [string]$SkillRoot,
    [switch]$Installed,
    [switch]$ListPorts,
    [switch]$Board,
    [ValidateSet("none", "smoke", "sensor", "otsu", "resources", "rect-target", "circle-target", "yolo", "uart-loopback", "all-core")]
    [string]$Vision = "none",
    [string]$Port,
    [double]$Timeout = 45,
    [switch]$SkipValidate,
    [switch]$SkipUnitTests
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
$boardProbe = Join-Path $skillRootResolved "scripts\run_board_probe.py"
$validateScript = Join-Path $repoRoot "tools\validate.ps1"

if (-not $SkipValidate) {
    if ($Installed) {
        Invoke-Checked { & $validateScript -Installed } "offline skill validation"
    } else {
        Invoke-Checked { & $validateScript $skillRootResolved } "offline skill validation"
    }
} else {
    Write-Warning "Skipping offline skill validation because -SkipValidate was set."
}

if (-not $SkipUnitTests) {
    Invoke-Checked { python -m unittest discover -s (Join-Path $repoRoot "tests") } "host unit tests"
} else {
    Write-Warning "Skipping host unit tests because -SkipUnitTests was set."
}

if (-not (Test-Path -LiteralPath $boardProbe)) {
    throw "Missing installed board probe entrypoint: $boardProbe"
}

if ($Board -and $Vision -eq "none") {
    $Vision = "smoke"
}
if ($Vision -ne "none") {
    $Board = $true
}

if ($ListPorts) {
    Invoke-Checked { python $boardProbe --list-ports } "list K230 serial ports"
}

if ($Board) {
    Write-Host ""
    Write-Host "Board probes run from RAM only and do not write /sdcard/main.py."
    $probeArgs = @($boardProbe, "--vision", $Vision, "--timeout", [string]$Timeout)
    if ($Port) {
        $probeArgs += @("--port", $Port)
    }
    Invoke-Checked { python @probeArgs } "board probe: $Vision"
}

Write-Host ""
Write-Host "TEST_OK skill=$skillRootResolved vision=$Vision board=$Board installed=$Installed"
