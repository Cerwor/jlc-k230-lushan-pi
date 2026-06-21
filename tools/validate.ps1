param(
    [string]$SkillRoot,
    [switch]$Installed
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    Write-Host ""
    Write-Host "==> $Label"
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
$localValidator = Join-Path $skillRootResolved "scripts\validate_skill.py"
$codexHomeForValidator = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$quickValidator = Join-Path $codexHomeForValidator "skills\.system\skill-creator\scripts\quick_validate.py"

if (-not (Test-Path -LiteralPath $localValidator)) {
    throw "Missing local validator: $localValidator"
}

Invoke-Checked { python $localValidator $skillRootResolved } "skill local preflight"

if (Test-Path -LiteralPath $quickValidator) {
    Invoke-Checked { python $quickValidator $skillRootResolved } "skill-creator quick_validate"
} else {
    Write-Warning "quick_validate.py not found: $quickValidator"
}

Write-Host ""
Write-Host "VALIDATE_REPO_OK skill=$skillRootResolved"
