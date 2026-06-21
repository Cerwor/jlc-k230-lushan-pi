param(
    [Parameter(Mandatory = $true)]
    [string]$Message,
    [string]$Branch,
    [string[]]$Files,
    [switch]$All,
    [switch]$NoMerge,
    [string]$Body
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

function Get-CheckedOutput {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    $output = & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
    return $output
}

function New-BranchName {
    param([string]$Text)
    $slug = $Text.ToLowerInvariant() -replace "[^a-z0-9]+", "-"
    $slug = $slug.Trim("-")
    if (-not $slug) {
        $slug = "skill-update"
    }
    if ($slug.Length -gt 48) {
        $slug = $slug.Substring(0, 48).Trim("-")
    }
    return "codex/$slug"
}

function Sync-InstalledSkill {
    param([string]$RepoRoot)

    $repoSkill = (Resolve-Path -LiteralPath (Join-Path $RepoRoot "jlc-k230-lushan-pi")).Path
    $codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
    $skillsRoot = Join-Path $codexHome "skills"
    New-Item -ItemType Directory -Force -Path $skillsRoot | Out-Null

    $skillsRootResolved = (Resolve-Path -LiteralPath $skillsRoot).Path
    $target = Join-Path $skillsRootResolved "jlc-k230-lushan-pi"

    if (Test-Path -LiteralPath $target) {
        $targetResolved = (Resolve-Path -LiteralPath $target).Path
        if (-not $targetResolved.StartsWith($skillsRootResolved, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove unexpected path: $targetResolved"
        }
        Remove-Item -LiteralPath $targetResolved -Recurse -Force
    }

    Copy-Item -LiteralPath $repoSkill -Destination $skillsRootResolved -Recurse -Force
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $repoRoot

if ($All -and $Files) {
    throw "Use either -All or -Files, not both."
}

Invoke-Checked { gh --version } "check gh"
Invoke-Checked { gh auth status } "check gh auth"

$repoInfo = Get-CheckedOutput { gh repo view --json nameWithOwner,defaultBranchRef } "read GitHub repo info" | ConvertFrom-Json
$baseBranch = $repoInfo.defaultBranchRef.name
$currentBranch = (Get-CheckedOutput { git branch --show-current } "read current branch").Trim()

if (-not $Branch) {
    $Branch = New-BranchName -Text $Message
}

if ($currentBranch -eq $baseBranch -or $currentBranch -eq "main" -or $currentBranch -eq "master") {
    Invoke-Checked { git switch -c $Branch } "create branch $Branch"
} elseif ($currentBranch -ne $Branch) {
    throw "Current branch is $currentBranch. Switch to $baseBranch or pass -Branch $currentBranch to publish from it."
}

if ($All) {
    Invoke-Checked { git add -A } "stage all changes"
} elseif ($Files) {
    Invoke-Checked { git add -- $Files } "stage selected files"
}

$staged = @(Get-CheckedOutput { git diff --cached --name-only } "read staged files")
if ($staged.Count -eq 0) {
    throw "No staged files. Pass -Files, pass -All, or stage files before running publish.ps1."
}

Write-Host ""
Write-Host "Staged files:"
$staged | ForEach-Object { Write-Host "  $_" }

Invoke-Checked { & (Join-Path $repoRoot "tools\validate.ps1") } "run repository validation"

Invoke-Checked { git commit -m $Message } "commit"
Invoke-Checked { git push -u origin $Branch } "push branch"

if (-not $Body) {
    $Body = "## Summary`n- $Message`n`n## Validation`n- tools/validate.ps1"
}

$prUrl = (Get-CheckedOutput {
    gh pr create --base $baseBranch --head $Branch --title "[codex] $Message" --body $Body
} "create PR").Trim()

Write-Host ""
Write-Host "PR: $prUrl"

$prInfo = Get-CheckedOutput {
    gh pr view $prUrl --json state,isDraft,mergeStateStatus,url
} "read PR state" | ConvertFrom-Json

if ($prInfo.mergeStateStatus -ne "CLEAN") {
    throw "PR is not clean to merge: $($prInfo.mergeStateStatus). Review $($prInfo.url)"
}

if (-not $NoMerge) {
    Invoke-Checked {
        gh pr merge $prUrl --squash --delete-branch --subject $Message --body "Published via tools/publish.ps1."
    } "merge PR"

    Invoke-Checked { git switch $baseBranch } "switch back to $baseBranch"
    Invoke-Checked { git pull --ff-only origin $baseBranch } "sync $baseBranch"

    Write-Host ""
    Write-Host "==> sync installed skill"
    Sync-InstalledSkill -RepoRoot $repoRoot

    Invoke-Checked { & (Join-Path $repoRoot "tools\validate.ps1") -Installed } "validate installed skill"
}

Invoke-Checked { git status --short --branch } "final git status"

Write-Host ""
Write-Host "PUBLISH_OK pr=$prUrl"
