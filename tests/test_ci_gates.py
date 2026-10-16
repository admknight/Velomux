"""CI safety and release-process regression checks (Windows runtime must test separately)."""
import ast
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def text(relative):
    return (ROOT / relative).read_text(encoding='utf-8')


def test_gui_test_exercises_real_qt_window_instead_of_import_only():
    source = text('run.py')
    tree = ast.parse(source)
    assert any(isinstance(n, ast.FunctionDef) and n.name == 'gui_smoke_test' for n in tree.body)
    assert 'from modern_app import MainWindow' in source
    assert 'window = MainWindow()' in source
    assert 'window.show()' in source
    assert 'window.pages.count() == 4' in source
    assert 'window.mode.setCurrentIndex(1)' in source
    assert 'window.close()' in source
    assert "'--gui-smoke-test' in sys.argv" in source


def test_private_build_checks_source_frozen_and_installed_app():
    builder = text('scripts/build_windows.ps1')
    pipeline = text('.github/workflows/build-windows-installer.yml')
    installer_test = text('scripts/test_installer_windows.ps1')
    assert 'run.py --gui-smoke-test' in builder
    assert "-ArgumentList '--gui-smoke-test'" in builder
    assert 'test_installer_windows.ps1' in pipeline
    assert '--media-integration-test' in builder
    assert '--media-integration-test' in installer_test
    assert "'--self-test', '--gui-smoke-test'" in installer_test
    assert 'unins000.exe' in installer_test
    assert 'SHA256SUMS.txt' in pipeline
    assert 'BUILD_PROVENANCE.txt' in pipeline
    assert re.search(r'permissions:\s*\n\s*contents: read', pipeline)
    assert 'gh release create' not in pipeline


def test_chocolatey_wrapper_is_not_shipped_and_public_requires_vetted_binary():
    builder = text('scripts/build_windows.ps1')
    release = text('.github/workflows/draft-release.yml')
    stage = text('scripts/stage_reviewed_ffmpeg.ps1')
    assert 'Chocolatey shims' in builder
    assert 'Get-ChildItem -LiteralPath $toolsRoot -Recurse' in builder
    assert '-ForDistribution' in release
    assert 'archive_sha256' in stage
    assert 'ffmpeg_sha256' in stage and 'ffprobe_sha256' in stage
    assert 'binary_source_url' in stage
    assert "Copy-Item -LiteralPath $src" in stage
    assert 'reviewer_confirmed' in release
    assert '--verify-tag --draft --prerelease' in release
    assert '--latest=false' in release
    assert '--publish' not in release
    assert 'contents: write' in release
    assert 'version.py' in release
