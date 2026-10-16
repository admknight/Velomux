# Stage a specifically reviewed FFmpeg ZIP for a *draft* Windows release build.
# This script requires a source-controlled manifest with exact archive/binary hashes.
# It does not decide whether licenses have been complied with.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = Split-Path -Parent $PSScriptRoot
$vendor = Join-Path $root 'vendor\ffmpeg'
$manifestFile = Join-Path $vendor 'BINARY_MANIFEST.json'
if (-not (Test-Path -LiteralPath $manifestFile -PathType Leaf)) {
    throw 'Reviewed FFmpeg binary manifest missing. Public/draft release packaging is blocked.'
}
$manifest = Get-Content -LiteralPath $manifestFile -Raw | ConvertFrom-Json
foreach ($field in @('binary_source_url','archive_sha256','ffmpeg_sha256','ffprobe_sha256',
                     'license_variant','source_revision')) {
    if ([string]::IsNullOrWhiteSpace([string]$manifest.$field)) { throw "Missing FFmpeg manifest field: $field" }
}
foreach ($field in @('archive_sha256','ffmpeg_sha256','ffprobe_sha256')) {
    if ([string]$manifest.$field -notmatch '^[0-9a-fA-F]{64}$') { throw "Invalid SHA-256 field: $field" }
}
$url = [uri]$manifest.binary_source_url
if ($url.Scheme -ne 'https' -or -not $url.AbsolutePath.EndsWith('.zip', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Only an explicitly reviewed HTTPS FFmpeg ZIP release is supported.'
}
$work = Join-Path $env:TEMP ('VelomuxFFmpegStage-' + [guid]::NewGuid().ToString('N'))
New-Item -Path $work -ItemType Directory -Force | Out-Null
try {
    $archive = Join-Path $work 'reviewed-ffmpeg.zip'
    Invoke-WebRequest -Uri $url -OutFile $archive
    $actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash
    if ($actual -ne $manifest.archive_sha256) { throw 'Reviewed FFmpeg archive SHA-256 mismatch.' }
    $extracted = Join-Path $work 'extracted'
    Expand-Archive -LiteralPath $archive -DestinationPath $extracted
    $matches = @(
        Get-ChildItem -LiteralPath $extracted -Recurse -File -Filter ffmpeg.exe |
            Where-Object { Test-Path -LiteralPath (Join-Path $_.DirectoryName 'ffprobe.exe') -PathType Leaf } |
            ForEach-Object { $_.DirectoryName } | Select-Object -Unique
    )
    if ($matches.Count -ne 1) { throw 'The reviewed archive must contain exactly one FFmpeg/ffprobe executable pair.' }
    $dest = Join-Path $vendor 'bin'
    New-Item -Path $dest -ItemType Directory -Force | Out-Null
    foreach ($pair in @(@('ffmpeg.exe','ffmpeg_sha256'), @('ffprobe.exe','ffprobe_sha256'))) {
        $src = Join-Path $matches[0] $pair[0]
        $hash = (Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash
        if ($hash -ne $manifest.($pair[1])) { throw "FFmpeg binary SHA-256 mismatch for $($pair[0])" }
        Copy-Item -LiteralPath $src -Destination (Join-Path $dest $pair[0]) -Force
    }
    Write-Host 'Reviewed binary hashes passed. Complete legal/security review is still required.' -ForegroundColor Green
}
finally {
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}
