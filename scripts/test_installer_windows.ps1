# GitHub/Windows CI gate: install, smoke test the *installed* app, uninstall.
# No system-wide configuration is changed; Inno Setup installer is per-user.
[CmdletBinding()]
param(
    [string]$SetupPath = (Join-Path (Split-Path -Parent $PSScriptRoot) 'dist\installer\Velomux-Setup-0.2.3-preview-Win-x64.exe'),
    [string]$InstallDir = (Join-Path $env:TEMP 'VelomuxInstallerSmoke')
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not (Test-Path -LiteralPath $SetupPath -PathType Leaf)) {
    throw "Velomux setup does not exist: $SetupPath"
}
$exe = Join-Path $InstallDir 'Velomux.exe'
$uninstaller = Join-Path $InstallDir 'unins000.exe'
$contextVerb = 'Registry::HKEY_CURRENT_USER\Software\Classes\*\shell\Velomux'
$contextCommand = "$contextVerb\command"
if (Test-Path -LiteralPath $InstallDir) {
    throw "Refusing to overwrite an existing test installation folder: $InstallDir"
}
$installed = $false
$priorQpa = $env:QT_QPA_PLATFORM
try {
    Write-Host 'Installing Velomux in a temporary test folder...' -ForegroundColor Cyan
    $proc = Start-Process -FilePath $SetupPath -ArgumentList @(
        '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/TASKS=explorercontext', "/DIR=`"$InstallDir`""
    ) -PassThru -Wait
    if ($proc.ExitCode -ne 0) { throw "Inno installer exited with $($proc.ExitCode)" }
    $installed = $true
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
        throw 'Velomux.exe was not found after installation.'
    }
    if (-not (Test-Path -LiteralPath $contextCommand)) {
        throw 'Optional Explorer context command was not installed.'
    }
    $verbText = (Get-Item -LiteralPath $contextCommand).GetValue('')
    if (-not $verbText.Contains('Velomux.exe') -or -not $verbText.Contains('%1')) {
        throw "Invalid installed Explorer context command: $verbText"
    }
    $env:QT_QPA_PLATFORM = 'offscreen'
    foreach ($mode in @('--self-test', '--gui-smoke-test', '--media-integration-test')) {
        Write-Host "Testing installed executable: $mode"
        $probe = Start-Process -FilePath $exe -ArgumentList $mode -PassThru -Wait
        if ($probe.ExitCode -ne 0) {
            $log = Join-Path $env:TEMP 'Velomux-GUI-Smoke-Test.log'
            if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log }
            throw "Installed Velomux $mode failed with exit code $($probe.ExitCode)"
        }
    }
    Write-Host 'Installed executable passed both release smoke tests.' -ForegroundColor Green
}
finally {
    $env:QT_QPA_PLATFORM = $priorQpa
    if ($installed) {
        if (-not (Test-Path -LiteralPath $uninstaller -PathType Leaf)) {
            throw "Inno uninstaller not found: $uninstaller"
        }
        Write-Host 'Uninstalling temporary test installation...' -ForegroundColor Cyan
        $removal = Start-Process -FilePath $uninstaller -ArgumentList @(
            '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'
        ) -PassThru -Wait
        if ($removal.ExitCode -ne 0) { throw "Uninstaller exited with $($removal.ExitCode)" }
        if (Test-Path -LiteralPath $exe -PathType Leaf) {
            throw 'Velomux.exe still exists after uninstall.'
        }
        if (Test-Path -LiteralPath $contextVerb) {
            throw 'Optional Explorer context verb remains after uninstall.'
        }
    }
}
Write-Host 'PASS: Windows silent install / frozen tests / uninstall.' -ForegroundColor Green
