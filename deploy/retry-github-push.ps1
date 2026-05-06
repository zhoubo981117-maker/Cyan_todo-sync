param(
    [string]$Repo = "zhoubo981117-maker/Cyan_todo-sync",
    [string]$Branch = "main",
    [string]$LogPath = "deploy_retry.log"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Log {
    param([string]$Message)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message"
    Write-Output $line
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
}

function Invoke-GhJson {
    param(
        [string[]]$ApiArgs,
        [object]$Body = $null
    )
    $gh = "gh"
    if (Test-Path "C:\Users\huawei\AppData\Local\Programs\GitHub CLI\bin\gh.exe") {
        $gh = "C:\Users\huawei\AppData\Local\Programs\GitHub CLI\bin\gh.exe"
    }

    if ($null -eq $Body) {
        return (& $gh api @ApiArgs | ConvertFrom-Json)
    }

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $tmp = [System.IO.Path]::GetTempFileName()
    [System.IO.File]::WriteAllText($tmp, ($Body | ConvertTo-Json -Depth 100 -Compress), $utf8NoBom)
    try {
        return (& $gh api @ApiArgs --input $tmp | ConvertFrom-Json)
    }
    finally {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    }
}

function New-GitHubBlob {
    param([string]$Path)
    $bytes = [System.IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $Path))
    return Invoke-GhJson -ApiArgs @("repos/$Repo/git/blobs", "--method", "POST") -Body @{
        content = [Convert]::ToBase64String($bytes)
        encoding = "base64"
    }
}

Set-Location (Split-Path -Parent $PSScriptRoot)

$localHead = (git rev-parse HEAD).Trim()
$localTree = (git rev-parse "HEAD^{tree}").Trim()
$message = (git log -1 --pretty=%s).Trim()
$remoteRef = Invoke-GhJson -ApiArgs @("repos/$Repo/git/ref/heads/$Branch")
$remoteSha = $remoteRef.object.sha
$remoteCommit = Invoke-GhJson -ApiArgs @("repos/$Repo/git/commits/$remoteSha")
$remoteTree = $remoteCommit.tree.sha

Write-Log "Local HEAD: $localHead"
Write-Log "Remote HEAD: $remoteSha"

if ($remoteSha -eq $localHead -or $remoteTree -eq $localTree) {
    Write-Log "Already published. No retry needed."
    exit 0
}

Write-Log "Trying normal git push..."
$oldErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
git -c http.version=HTTP/1.1 push origin $Branch 2>&1 | ForEach-Object { Write-Log $_ }
$pushExitCode = $LASTEXITCODE
$ErrorActionPreference = $oldErrorActionPreference
if ($pushExitCode -eq 0) {
    Write-Log "git push succeeded."
    exit 0
}

Write-Log "git push failed. Publishing current HEAD tree through GitHub API..."
$entries = @()
git ls-tree -r HEAD | ForEach-Object {
    if (-not $_) { return }
    $parts = $_ -split "`t", 2
    if ($parts.Count -ne 2) { return }
    $meta = $parts[0] -split " "
    $path = $parts[1]
    $blob = New-GitHubBlob -Path $path
    $entries += @{
        path = $path
        mode = $meta[0]
        type = "blob"
        sha = $blob.sha
    }
}

$tree = Invoke-GhJson -ApiArgs @("repos/$Repo/git/trees", "--method", "POST") -Body @{ tree = $entries }
$commit = Invoke-GhJson -ApiArgs @("repos/$Repo/git/commits", "--method", "POST") -Body @{
    message = $message
    tree = $tree.sha
    parents = @($remoteSha)
}
Invoke-GhJson -ApiArgs @("repos/$Repo/git/refs/heads/$Branch", "--method", "PATCH") -Body @{
    sha = $commit.sha
    force = $false
} | Out-Null

Write-Log "GitHub API publish succeeded: $($commit.sha)"
