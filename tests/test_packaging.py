"""Static release metadata/branding checks (not a substitute for Windows install QA)."""
from pathlib import Path
import re
from PIL import Image
from version import APP_NAME, APP_VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_product_identity_and_no_old_brand():
    assert APP_NAME == 'Velomux'
    assert APP_VERSION == '0.3.0-preview'
    for relative in ('modern_app.py','app.py','engine.py','cli.py','version.py',
                     'README.md','installer/Velomux.iss','scripts/build_windows.ps1'):
        assert ('scope' + 'wise') not in (ROOT/relative).read_text(encoding='utf-8').lower()


def test_windows_ico_contains_brand_and_multiple_sizes():
    icon = ROOT/'assets/velomux.ico'
    png = ROOT/'assets/velomux.png'
    assert icon.is_file() and png.is_file()
    with Image.open(icon) as im:
        assert im.format == 'ICO'
        assert (256, 256) in im.ico.sizes()
        assert (16, 16) in im.ico.sizes()
    with Image.open(png) as im:
        assert im.size == (512, 512)


def test_inno_setup_source_matches_app_and_build_output():
    setup = (ROOT/'installer/Velomux.iss').read_text(encoding='utf-8')
    build = (ROOT/'scripts/build_windows.ps1').read_text(encoding='utf-8')
    assert '#define ProductVersion "0.3.0"' in setup
    assert 'SetupArchitecture=x64' in setup
    assert 'PrivilegesRequired=lowest' in setup
    assert 'Source: "..\\dist\\Velomux\\*"' in setup
    assert 'Velomux.exe' in setup
    assert 'Velomux-Setup-0.3.0-preview-Win-x64.exe' in build
    assert '--add-binary "${ffmpeg};vendor/ffmpeg/bin"' in build
    assert '--add-binary "${ffprobe};vendor/ffmpeg/bin"' in build
    assert '--add-data' in build and 'velomux.png' in build
    assert '--self-test' in build
    assert 'Find-InnoSetup7' in build


def test_test_installer_workflow_cannot_publish_releases():
    workflow = (ROOT/'.github/workflows/build-windows-installer.yml').read_text(encoding='utf-8')
    assert 'workflow_dispatch:' in workflow
    assert 'contents: read' in workflow
    assert 'actions/upload-artifact@v4' in workflow
    assert 'actions/create-release' not in workflow
    assert 'softprops/action-gh-release' not in workflow
    assert re.search(r'is-7_1_0/innosetup-7.1.0-x64.exe', workflow)


def test_inno_setup_per_user_detection_and_override():
    build = (ROOT/'scripts/build_windows.ps1').read_text(encoding='utf-8')
    assert "Join-Path $env:LOCALAPPDATA 'Programs\\Inno Setup 7\\ISCC.exe'" in build
    assert '$env:VELOMUX_ISCC_PATH' in build
    assert '$InnoSetupCompilerPath' in build
    assert 'Find-InnoSetup7 -PreferredPath $InnoSetupCompilerPath' in build
    assert "FileVersionInfo]::GetVersionInfo" not in build
    assert "$candidate '/?'" in build
    assert r"Inno Setup\s+7" in build
    assert "Command[- ]Line Compiler" in build
    assert "return $candidate" in build
