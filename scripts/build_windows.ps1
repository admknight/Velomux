# Velomux - Windows x64 application and Inno Setup 7 installer builder.
# Build-time dependencies only: Python and Inno Setup 7. Users of the setup EXE
# do NOT need Python, Inno Setup or a separately installed FFmpeg.
[CmdletBinding()]
param(
    [switch]$UseSystemFFmpeg,
    [switch]$Installer,
    [switch]$ForDistribution,
    [string]$InnoSetupCompilerPath,
    [string]$FFmpegBinDirectory
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

function Fail([string]$message) { throw $message }

function Find-InnoSetup7 {
    param([string]$PreferredPath)

    $places = @()
    # Explicit override for custom Inno Setup 7 installations.
    foreach ($specified in @($PreferredPath, $env:VELOMUX_ISCC_PATH)) {
        if (-not [string]::IsNullOrWhiteSpace($specified)) {
            $specified = $specified.Trim('"')
            if (Test-Path -LiteralPath $specified -PathType Container) {
                $places += (Join-Path $specified 'ISCC.exe')
            }
            else { $places += $specified }
        }
    }

    # Inno Setup 7 can install per-user rather than in Program Files.
    # Example: C:\Users\<user>\AppData\Local\Programs\Inno Setup 7\ISCC.exe
    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        $places += (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 7\ISCC.exe')
    }
    foreach ($envPath in @(${env:ProgramFiles(x86)}, $env:ProgramFiles)) {
        if (-not [string]::IsNullOrWhiteSpace($envPath)) {
            $places += (Join-Path $envPath 'Inno Setup 7\ISCC.exe')
        }
    }
    foreach ($key in @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 7_is1',
        'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 7_is1',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 7_is1'
    )) {
        $record = Get-ItemProperty -Path $key -ErrorAction SilentlyContinue
        if ($record -and $record.InstallLocation) {
            $places += (Join-Path $record.InstallLocation 'ISCC.exe')
        }
    }
    $command = Get-Command 'ISCC.exe' -CommandType Application -ErrorAction SilentlyContinue
    if ($command) { $places += $command.Source }

    foreach ($candidate in ($places | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }

        # ISCC.exe can report FileMajorPart=0 even for a valid Inno Setup 7
        # installation, so Windows executable metadata is not a version check.
        # All Inno Setup 7 releases support the '/?' compiler help banner;
        # newer 7.x builds also support '--version', but 7.0.x does not.
        try {
            $helpText = (& $candidate '/?' 2>&1 | Out-String)
        }
        catch {
            Write-Warning "Unable to inspect compiler: $candidate ($($_.Exception.Message))"
            continue
        }
        if (($helpText -match '(?i)\bInno Setup\s+7(?:\.\d+){0,3}\b') -and
            ($helpText -match '(?i)\bCommand[- ]Line Compiler\b')) {
            Write-Host "Verified Inno Setup 7 compiler: $candidate" -ForegroundColor Green
            return $candidate
        }
        Write-Warning "Compiler did not identify itself as Inno Setup 7: $candidate"
    }
    Fail 'Inno Setup 7 compiler was not detected or verified. Check %LOCALAPPDATA%\Programs\Inno Setup 7\ISCC.exe or set VELOMUX_ISCC_PATH to the ISCC.exe path.'
}
Write-Host 'Velomux: checking build prerequisites...' -ForegroundColor Cyan
if (-not [Environment]::Is64BitOperatingSystem) { Fail 'This build targets 64-bit Windows.' }
$iscc = $null
if ($ForDistribution -and $UseSystemFFmpeg) { Fail 'Public distribution builds cannot use unverified system FFmpeg.' }
if ($Installer) {
    $iscc = Find-InnoSetup7 -PreferredPath $InnoSetupCompilerPath
    Write-Host "Inno Setup compiler: $iscc"
}
$pythonExe = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    # Prefer setup-python's selected interpreter on GitHub Actions. The generic
    # py -3 launcher can silently pick a different installed Python release.
    if ($python -and $python.Source -notmatch '(?i)[\/]WindowsApps[\/]') {
        & $python.Source -m venv (Join-Path $root '.venv')
    }
    elseif ($launcher) {
        & $launcher.Source -3 -m venv (Join-Path $root '.venv')
    }
    else { Fail 'Python 3.11+ is required ONLY to BUILD the installer. Use the GitHub Windows build workflow if you do not want Python on this PC.' }
    if ($LASTEXITCODE -ne 0) { Fail 'Could not create build environment.' }
}

$bin = Join-Path $root 'vendor\ffmpeg\bin'
New-Item -ItemType Directory -Force -Path $bin | Out-Null
$ffmpeg = Join-Path $bin 'ffmpeg.exe'
$ffprobe = Join-Path $bin 'ffprobe.exe'
if (-not ((Test-Path -LiteralPath $ffmpeg -PathType Leaf) -and (Test-Path -LiteralPath $ffprobe -PathType Leaf))) {
    if (-not $UseSystemFFmpeg) {
        Fail 'Place a reviewed ffmpeg.exe and ffprobe.exe in vendor\ffmpeg\bin, or use -UseSystemFFmpeg for a PRIVATE test build.'
    }
    # Resolve actual executables, NEVER Chocolatey shims from Chocolatey\bin.
    # Those shims may work on the build machine but fail on end-user PCs.
    if (-not [string]::IsNullOrWhiteSpace($FFmpegBinDirectory)) {
        $sourceDir = $FFmpegBinDirectory
    }
    else {
        $tool1 = Get-Command ffmpeg.exe -CommandType Application -ErrorAction Stop
        $tool2 = Get-Command ffprobe.exe -CommandType Application -ErrorAction Stop
        if ((Split-Path -Parent $tool1.Source) -ne (Split-Path -Parent $tool2.Source)) {
            Fail 'FFmpeg and ffprobe must come from the same tool distribution.'
        }
        $sourceDir = Split-Path -Parent $tool1.Source
        if ($sourceDir -match '(?i)[\\/]chocolatey[\\/]bin$') {
            $sourceDir = $null
            $chocoHome = if ($env:ChocolateyInstall) { $env:ChocolateyInstall } else { 'C:\ProgramData\chocolatey' }
            $toolsRoot = Join-Path $chocoHome 'lib\ffmpeg\tools'
            if (Test-Path -LiteralPath $toolsRoot -PathType Container) {
                foreach ($real in (Get-ChildItem -LiteralPath $toolsRoot -Recurse -File -Filter 'ffmpeg.exe' -ErrorAction Stop)) {
                    $peer = Join-Path $real.DirectoryName 'ffprobe.exe'
                    if (Test-Path -LiteralPath $peer -PathType Leaf) {
                        $sourceDir = $real.DirectoryName
                        break
                    }
                }
            }
            if (-not $sourceDir) {
                Fail 'Chocolatey shims were found, but real ffmpeg.exe and ffprobe.exe could not be located. Supply -FFmpegBinDirectory.'
            }
        }
    }
    foreach ($name in @('ffmpeg.exe','ffprobe.exe')) {
        if (-not (Test-Path -LiteralPath (Join-Path $sourceDir $name) -PathType Leaf)) {
            Fail "Missing real executable $name in $sourceDir"
        }
    }
    if (([IO.Path]::GetFullPath($sourceDir)).TrimEnd('\') -eq ([IO.Path]::GetFullPath($bin)).TrimEnd('\')) {
        Fail 'Cannot copy FFmpeg source over itself.'
    }
    Copy-Item -LiteralPath (Join-Path $sourceDir 'ffmpeg.exe') -Destination $ffmpeg -Force
    Copy-Item -LiteralPath (Join-Path $sourceDir 'ffprobe.exe') -Destination $ffprobe -Force
    Write-Warning 'Private TEST build: actual FFmpeg binaries copied from the build machine; NOT cleared for public redistribution.'
}
foreach ($tool in @($ffmpeg,$ffprobe)) {
    $toolInfo = Get-Item -LiteralPath $tool
    Write-Host "Validating bundled executable: $tool ($($toolInfo.Length) bytes)"
    $toolOutput = & $tool '-version' 2>&1 | Out-String
    $toolExit = $LASTEXITCODE
    if ($toolExit -ne 0) {
        Write-Warning "Bundled executable exit code: $toolExit"
        Write-Warning "Executable output: $toolOutput"
        Fail "Cannot execute bundled tool: $tool (exit $toolExit)"
    }
    Write-Host ($toolOutput.Trim() -split "\\r?\\n" | Select-Object -First 1)
}

if ($ForDistribution) {
    foreach ($required in @('LICENSE', 'vendor\ffmpeg\PROVENANCE.md',
                           'vendor\ffmpeg\SOURCE_OFFER.md', 'vendor\ffmpeg\BINARY_MANIFEST.json')) {
        if (-not (Test-Path -LiteralPath (Join-Path $root $required))) {
            Fail "Public distribution gate failed: missing $required"
        }
    }
    $manifest = Get-Content -LiteralPath (Join-Path $root 'vendor\ffmpeg\BINARY_MANIFEST.json') -Raw | ConvertFrom-Json
    foreach ($pair in @(@('ffmpeg.exe','ffmpeg_sha256'), @('ffprobe.exe','ffprobe_sha256'))) {
        $binary = Join-Path $bin $pair[0]
        $expected = [string]$manifest.($pair[1])
        if ($expected -notmatch '^[a-fA-F0-9]{64}$') { Fail "Missing/invalid SHA-256 for $($pair[0])" }
        if ((Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash -ne $expected) {
            Fail "SHA-256 mismatch for $($pair[0])"
        }
    }
    foreach ($field in @('binary_source_url','source_revision','license_variant')) {
        if ([string]::IsNullOrWhiteSpace([string]$manifest.$field)) { Fail "Manifest missing $field" }
    }
    if ($manifest.binary_source_url -notmatch '^https://') { Fail 'Binary source must use HTTPS.' }
    Write-Host 'Preliminary FFmpeg manifest checks passed. Formal licensing review remains required.'
}

Write-Host 'Installing build dependencies...' -ForegroundColor Cyan
& $pythonExe -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { Fail 'Failed to install Python build dependencies.' }
& $pythonExe -m pytest -q tests
if ($LASTEXITCODE -ne 0) { Fail 'Converter engine tests failed.' }
& $pythonExe -m py_compile engine.py modern_app.py app.py run.py cli.py toolchain.py
if ($LASTEXITCODE -ne 0) { Fail 'Source code failed syntax check.' }

Write-Host 'Running source Qt GUI smoke test...' -ForegroundColor Cyan
$priorQpa = $env:QT_QPA_PLATFORM
$priorScreenshot = $env:VELOMUX_GUI_SCREENSHOT
New-Item -ItemType Directory -Force -Path (Join-Path $root 'dist') | Out-Null
$env:QT_QPA_PLATFORM = 'offscreen'
$env:VELOMUX_GUI_SCREENSHOT = Join-Path $root 'dist\qt-gui-source.png'
$guiLog = Join-Path $env:TEMP 'Velomux-GUI-Smoke-Test.log'
if (Test-Path -LiteralPath $guiLog) { Remove-Item -LiteralPath $guiLog -Force }
try {
    & $pythonExe run.py --gui-smoke-test
    if ($LASTEXITCODE -ne 0) {
        $log = Join-Path $env:TEMP 'Velomux-GUI-Smoke-Test.log'
        if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log }
        Fail 'Source Qt GUI smoke test failed.'
    }
}
finally {
    $env:QT_QPA_PLATFORM = $priorQpa
    $env:VELOMUX_GUI_SCREENSHOT = $priorScreenshot
}

Write-Host 'Creating a standalone Windows application...' -ForegroundColor Cyan
& $pythonExe -m PyInstaller --noconfirm --clean --onedir --windowed `
    --name Velomux `
    --icon 'assets\velomux.ico' `
    --version-file 'scripts\windows_version.txt' `
    --add-binary "${ffmpeg};vendor/ffmpeg/bin" `
    --add-binary "${ffprobe};vendor/ffmpeg/bin" `
    --add-data 'assets\velomux.png;assets' `
    --collect-all PIL `
    run.py
if ($LASTEXITCODE -ne 0) { Fail 'PyInstaller did not build Velomux.exe.' }

$bundle = Join-Path $root 'dist\Velomux'
$application = Join-Path $bundle 'Velomux.exe'
$internalFFmpeg = Join-Path $bundle '_internal\vendor\ffmpeg\bin\ffmpeg.exe'
$internalFFprobe = Join-Path $bundle '_internal\vendor\ffmpeg\bin\ffprobe.exe'
foreach ($file in @($application, $internalFFmpeg, $internalFFprobe)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { Fail "Bundled executable missing: $file" }
}
Copy-Item -LiteralPath (Join-Path $root 'README.md') -Destination $bundle -Force
Copy-Item -LiteralPath (Join-Path $root 'THIRD_PARTY_NOTICES.md') -Destination $bundle -Force
if ($ForDistribution) {
    foreach ($name in @('LICENSE','vendor\ffmpeg\PROVENANCE.md',
                        'vendor\ffmpeg\SOURCE_OFFER.md', 'vendor\ffmpeg\BINARY_MANIFEST.json')) {
        $targetName = Split-Path $name -Leaf
        Copy-Item -LiteralPath (Join-Path $root $name) -Destination (Join-Path $bundle $targetName) -Force
    }
}

Write-Host 'Running frozen application self-test...' -ForegroundColor Cyan
$process = Start-Process -FilePath $application -ArgumentList '--self-test' -PassThru -Wait
if ($process.ExitCode -ne 0) { Fail "Packaged application self-test failed (exit $($process.ExitCode))." }
Write-Host 'Running FROZEN Qt GUI smoke test...' -ForegroundColor Cyan
$priorQpa = $env:QT_QPA_PLATFORM
$priorScreenshot = $env:VELOMUX_GUI_SCREENSHOT
$env:QT_QPA_PLATFORM = 'offscreen'
$env:VELOMUX_GUI_SCREENSHOT = Join-Path $root 'dist\qt-gui-frozen.png'
$guiLog = Join-Path $env:TEMP 'Velomux-GUI-Smoke-Test.log'
if (Test-Path -LiteralPath $guiLog) { Remove-Item -LiteralPath $guiLog -Force }
try {
    $guiResult = Start-Process -FilePath $application -ArgumentList '--gui-smoke-test' -PassThru -Wait
    if ($guiResult.ExitCode -ne 0) {
        $log = Join-Path $env:TEMP 'Velomux-GUI-Smoke-Test.log'
        if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log }
        Fail "Packaged Qt GUI smoke test failed (exit $($guiResult.ExitCode))."
    }
}
finally {
    $env:QT_QPA_PLATFORM = $priorQpa
    $env:VELOMUX_GUI_SCREENSHOT = $priorScreenshot
}
Write-Host 'Running REAL media conversions in the frozen application...' -ForegroundColor Cyan
$integration = Start-Process -FilePath $application -ArgumentList '--media-integration-test' -PassThru -Wait
if ($integration.ExitCode -ne 0) {
    $log = Join-Path $env:TEMP 'Velomux-Media-Integration-Test.log'
    if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log }
    Fail "Frozen application media integration test failed (exit $($integration.ExitCode))."
}
Write-Host 'Frozen GUI and actual MP4/M4A/MP3/image conversions passed.' -ForegroundColor Green

$portable = Join-Path $root 'dist\Velomux-Windows-Portable-x64.zip'
if (Test-Path -LiteralPath $portable) { Remove-Item -LiteralPath $portable -Force }
Compress-Archive -LiteralPath $bundle -DestinationPath $portable -CompressionLevel Optimal
Write-Host "Portable app created: $portable"

if ($Installer) {
    Write-Host 'Compiling Inno Setup 7 installer...' -ForegroundColor Cyan
    & $iscc (Join-Path $root 'installer\Velomux.iss')
    if ($LASTEXITCODE -ne 0) { Fail 'Inno Setup 7 compiler failed.' }
    $setup = Join-Path $root 'dist\installer\Velomux-Setup-0.3.0-preview-Win-x64.exe'
    if (-not (Test-Path -LiteralPath $setup -PathType Leaf)) { Fail 'Installer EXE was not created.' }
    Write-Host "TEST INSTALLER: $setup" -ForegroundColor Green
    Get-FileHash -LiteralPath $setup -Algorithm SHA256 | Format-List
}
Write-Host 'DONE. These are development/test artifacts and are not publicly release-cleared.' -ForegroundColor Green
