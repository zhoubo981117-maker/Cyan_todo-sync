param(
    [string]$Repo = "zhoubo981117-maker/Cyan_todo-sync",
    [string]$Branch = "main",
    [string]$LogPath = "deploy_retry.log",
    [string]$TaskName = "Cyan-Dify-Agent-System Git Push Retry"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Log {
    param([string]$Message)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message"
    Write-Output $line
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
}

function Disable-RetryTask {
    if (-not $TaskName) {
        return
    }
    try {
        schtasks /Change /TN $TaskName /Disable 2>&1 | ForEach-Object { Write-Log $_ }
    }
    catch {
        Write-Log "Failed to disable scheduled task ${TaskName}: $($_.Exception.Message)"
    }
}

function Invoke-GhJson {
    param(
        [string[]]$ApiArgs,
        [object]$Body = $null
    )
    $gh = $script:GhPath
    if (-not $gh) {
        throw "GitHub CLI is not available"
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

function Resolve-GhPath {
    if (Test-Path "C:\Users\huawei\AppData\Local\Programs\GitHub CLI\bin\gh.exe") {
        return "C:\Users\huawei\AppData\Local\Programs\GitHub CLI\bin\gh.exe"
    }

    $cmd = Get-Command gh -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    return $null
}

function Get-GitBlobBytes {
    param([string]$BlobSha)
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "git"
    $psi.Arguments = "cat-file blob $BlobSha"
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $proc = [System.Diagnostics.Process]::Start($psi)
    $memory = New-Object System.IO.MemoryStream
    $proc.StandardOutput.BaseStream.CopyTo($memory)
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()
    if ($proc.ExitCode -ne 0) {
        throw "git cat-file failed for ${BlobSha}: $stderr"
    }
    return $memory.ToArray()
}

function New-GitHubBlob {
    param([string]$BlobSha)
    $bytes = Get-GitBlobBytes -BlobSha $BlobSha
    return Invoke-GhJson -ApiArgs @("repos/$Repo/git/blobs", "--method", "POST") -Body @{
        content = [Convert]::ToBase64String($bytes)
        encoding = "base64"
    }
}

Set-Location (Split-Path -Parent $PSScriptRoot)

$localHead = (git rev-parse HEAD).Trim()
$localTree = (git rev-parse "HEAD^{tree}").Trim()
$message = (git log -1 --pretty=%s).Trim()
Write-Log "Local HEAD: $localHead"
Write-Log "Trying normal git push..."
$oldErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
git -c http.version=HTTP/1.1 push origin $Branch 2>&1 | ForEach-Object { Write-Log $_ }
$pushExitCode = $LASTEXITCODE
$ErrorActionPreference = $oldErrorActionPreference
if ($pushExitCode -eq 0) {
    Write-Log "git push succeeded."
    Disable-RetryTask
    exit 0
}

Write-Log "git push failed. Checking whether GitHub API fallback is available..."
$script:GhPath = Resolve-GhPath
if (-not $script:GhPath) {
    Write-Log "GitHub CLI is not available. Waiting for next scheduled retry."
    exit $pushExitCode
}

$remoteRef = Invoke-GhJson -ApiArgs @("repos/$Repo/git/ref/heads/$Branch")
$remoteSha = $remoteRef.object.sha
$remoteCommit = Invoke-GhJson -ApiArgs @("repos/$Repo/git/commits/$remoteSha")
$remoteTree = $remoteCommit.tree.sha

Write-Log "Remote HEAD: $remoteSha"

if ($remoteSha -eq $localHead -or $remoteTree -eq $localTree) {
    Write-Log "Already published. No retry needed."
    Disable-RetryTask
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
    $blob = New-GitHubBlob -BlobSha $meta[2]
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
Disable-RetryTask
