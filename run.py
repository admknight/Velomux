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


def media_integration_test() -> int:
    """Verify real conversions using bundled FFmpeg from the frozen executable.

    A synthetic video has a deliberately shorter audio track: this used to
    make valid M4A extractions fail duration validation. Also test repairing a
    zero-byte output and converting an image without changing either source.
    """
    import tempfile
    import traceback
    import subprocess
    from pathlib import Path
    from PIL import Image
    from toolchain import find_tools
    from engine import Options, convert, probe, _duration
    report = Path(tempfile.gettempdir()) / 'Velomux-Media-Integration-Test.log'
    try:
        ffmpeg, ffprobe = find_tools()
        if not ffmpeg or not ffprobe:
            raise RuntimeError('Bundled FFmpeg/ffprobe not found.')
        with tempfile.TemporaryDirectory(prefix='Velomux integration ') as temp:
            root = Path(temp)
            media = root / ('90s Jhankar - long video and short audio ' + 'music ' * 13 + '.mp4')
            command = [
                ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                '-f', 'lavfi', '-t', '7', '-i', 'color=c=blue:s=160x120:r=12',
                '-f', 'lavfi', '-t', '2', '-i', 'sine=frequency=660:sample_rate=44100',
                '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '96k', str(media),
            ]
            result = subprocess.run(command, input=b'', capture_output=True, timeout=45)
            if result.returncode:
                raise RuntimeError('Synthetic MP4 creation failed: ' + result.stderr.decode(errors='replace')[-1500:])
            folder = root / 'Converted'
            expected = convert(media, folder, 'M4A - AAC (smart copy)', Options(decode_check=True))
            if expected.status != 'done':
                raise RuntimeError('MP4 to M4A failed: ' + expected.detail)
            if not 1.8 <= _duration(probe(expected.output)) <= 2.2:
                raise RuntimeError('Wrong extracted AAC audio duration.')
            expected.output.write_bytes(b'')
            repaired = convert(media, folder, 'M4A - AAC (smart copy)', Options(decode_check=True))
            if repaired.status != 'done':
                raise RuntimeError('Zero-byte recovery failed: ' + repaired.detail)
            lossy = convert(media, folder, 'MP3 - 192 kbps', Options(decode_check=True))
            if lossy.status != 'done':
                raise RuntimeError('MP3 encoding failed: ' + lossy.detail)
            image_source = root / 'Sample image.png'
            Image.new('RGB', (80, 50), (32, 126, 220)).save(image_source)
            img_result = convert(image_source, folder, 'WebP - Lossless')
            if img_result.status != 'done':
                raise RuntimeError('WebP encoding failed: ' + img_result.detail)
            if not media.exists() or not image_source.exists():
                raise RuntimeError('Conversion modified an input source.')
        report.write_text('PASS: Bundled media conversion: MP4→AAC, repair, MP3, WebP.\n', encoding='utf-8')
        return 0
    except Exception:
        report.write_text('FAIL: Bundled media conversion.\n' + traceback.format_exc(), encoding='utf-8')
        return 41


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
        assert window.preset_list.count() >= 15, 'Audio preset library is not visible.'
        window.family.setCurrentText('Video')
        assert window.preset_list.count() >= 10, 'Video presets are not discoverable.'
        window.family.setCurrentText('Image')
        assert window.preset_list.count() >= 10, 'Image presets are not discoverable.'
        window.family.setCurrentText('Audio')
        window.preset_search.setText('MP3')
        assert window.preset_list.count() >= 3, 'Preset library search did not find MP3 alternatives.'
        window.preset_search.clear()

        # In the frozen EXE too, scrolling over a settings field must never
        # silently change its value. The full parent-scroll test runs in pytest.
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtWidgets import QComboBox
        for field in (window.audio_bitrate, window.sample_rate, window.gain,
                      window.channels, window.collision, window.preset, window.mode,
                      window.crf, window.video_fps, window.image_quality):
            before = field.currentIndex() if isinstance(field, QComboBox) else field.value()
            origin = QPoint(8, 8)
            event = QWheelEvent(
                QPointF(origin), QPointF(field.mapToGlobal(origin)),
                QPoint(0, 0), QPoint(0, -120),
                Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                Qt.ScrollPhase.ScrollUpdate, False
            )
            QApplication.sendEvent(field, event)
            after = field.currentIndex() if isinstance(field, QComboBox) else field.value()
            assert after == before, 'Mouse wheel modified a conversion setting.'

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
    if '--media-integration-test' in sys.argv:
        return media_integration_test()
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
