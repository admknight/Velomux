"""Velomux launcher and independently invoked frozen Windows release gates."""
from __future__ import annotations
import sys


def self_test() -> int:
    """Verify the private/frozen binary includes matching, executable FFmpeg tools."""
    from pathlib import Path
    import subprocess
    from PIL import Image
    from toolchain import find_tools, tools_origin
    ffmpeg, ffprobe = find_tools()
    if not ffmpeg or not ffprobe or tools_origin() != 'Bundled FFmpeg':
        return 21
    for executable in (ffmpeg, ffprobe):
        if not Path(executable).is_file():
            return 22
        result = subprocess.run([executable, '-version'], stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=12)
        if result.returncode != 0:
            return 23
    if Image.new('RGB', (2, 2)).size != (2, 2):
        return 24
    from PySide6.QtWidgets import QApplication
    _ = QApplication.instance()
    return 0


def gui_smoke_test() -> int:
    """Construct, display and close the REAL Qt main window (offscreen in CI).

    This deliberately exercises actual widget construction, navigation, Quick/Advanced
    controls and the bundled FFmpeg version indicator. No media is converted and
    no network/update request is initiated.
    """
    import os
    import tempfile
    import traceback
    from pathlib import Path
    report = Path(tempfile.gettempdir()) / 'Velomux-GUI-Smoke-Test.log'
    try:
        from PySide6.QtWidgets import QApplication
        from modern_app import MainWindow
        from version import APP_NAME
        app = QApplication.instance() or QApplication(['Velomux', '--gui-smoke-test'])
        app.setApplicationName(APP_NAME)
        window = MainWindow()
        assert window.centralWidget() is not None
        assert window.pages.count() == 4, 'Expected four main application pages.'
        assert window.table.columnCount() >= 4, 'Conversion queue columns are missing.'
        assert window.tabs.count() >= 4, 'Advanced conversion tabs are missing.'
        for idx in range(window.pages.count()):
            window._change_page(idx)
            assert window.pages.currentIndex() == idx, f'Navigation failed: page {idx}'
        window.mode.setCurrentIndex(1)
        assert window.tabs.isTabVisible(1), 'Advanced mode did not show video controls.'
        window.mode.setCurrentIndex(0)
        assert not window.tabs.isTabVisible(1), 'Quick mode did not hide advanced controls.'
        window.show()
        app.processEvents()
        assert window.isVisible(), 'Qt could not show the main application window.'
        screenshot = os.environ.get('VELOMUX_GUI_SCREENSHOT', '').strip()
        if screenshot:
            image = window.grab()
            if image.isNull() or not image.save(screenshot, 'PNG'):
                raise RuntimeError(f'Could not capture the actual Qt window: {screenshot}')
        window.close()
        app.processEvents()
        report.write_text('PASS: Velomux main window, pages, settings, and mode switching.\n', encoding='utf-8')
        return 0
    except Exception:
        report.write_text('FAIL: Velomux GUI smoke test.\n' + traceback.format_exc(), encoding='utf-8')
        return 31


def main() -> int:
    if '--self-test' in sys.argv:
        try:
            return self_test()
        except Exception:
            return 25
    if '--gui-smoke-test' in sys.argv:
        return gui_smoke_test()
    try:
        from modern_app import main as qt_main
    except ImportError as exc:
        if exc.name not in ('PySide6', 'shiboken6') and not str(exc.name or '').startswith('PySide6.'):
            raise
        print('Velomux needs PySide6 for its modern interface.', file=sys.stderr)
        return 2
    return qt_main()


if __name__ == '__main__':
    sys.exit(main())
