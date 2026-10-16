"""Real Qt UI regression tests for the VeloFlow task-first conversion workspace."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from modern_app import MainWindow
from velomux_flows import FLOWS


@pytest.fixture(scope="module")
def app():
    existing = QApplication.instance()
    return existing if existing is not None else QApplication(["velomux-ui-regression"])


@pytest.fixture
def window(app):
    ui = MainWindow()
    ui.settings.clear()
    ui.mode.setCurrentIndex(0)
    yield ui
    ui.close()


def test_all_curated_actions_really_appear_in_quick_mode(window):
    assert not window._quick_task_id
    assert not window.quick_panel.isHidden(), 'Quick Mode must expose VeloFlow task buttons'
    assert window.advanced_formats.isHidden(), 'Advanced-only controls must stay out of Quick Mode'
    assert len(window.flow_buttons) == len(FLOWS) == 7
    assert all(b.isCheckable() and b.isEnabled() for b in window.flow_buttons.values())
    assert not window.quick_profiles.isEnabled()
    assert window.preset.currentText() != 'M4A - AAC (smart copy)'


def test_explicit_extract_mode_is_required_for_mp4_to_m4a(window, tmp_path):
    video = tmp_path / "Jhankar music.mp4"
    video.write_bytes(b"pending conversion")
    window.import_paths([video])
    assert len(window.entries) == 1
    assert window.entries[0].preset == 'MP4 - H.264 + AAC'
    window.clear_queue()
    window._select_quick_task('extract')
    assert window.quick_profiles.isEnabled()
    assert window.quick_profiles.count() >= 3
    window.import_paths([video])
    assert len(window.entries) == 1
    assert window.entries[0].preset == 'M4A - AAC (smart copy)'


def test_quick_mode_does_not_silently_accept_incompatible_files(window, tmp_path):
    video = tmp_path / "movie.mp4"
    audio = tmp_path / "song.wav"
    image = tmp_path / "photo.png"
    for path in (video, audio, image):
        path.write_bytes(b"test intake only")
    window._select_quick_task('images')
    window.import_paths([video, audio, image])
    assert len(window.entries) == 1
    assert window.entries[0].source == image.resolve()
    assert window.entries[0].preset == 'JPEG - High quality (95)'
    assert "incompatible" in window.status.text().lower()


def test_selected_profile_maps_to_actual_engine_and_quick_trim_widgets(window):
    window._select_quick_task('trim')
    assert not window.quick_trim_box.isHidden()
    assert window.quick_profiles.count() == 2
    window.quick_profiles.setCurrentIndex(1)
    assert window.preset.currentText() == 'MP4 - H.264 + AAC'
    window.quick_trim_start.setValue(12.5)
    window.quick_trim_end.setValue(36.25)
    assert window.trim_start.value() == 12.5
    assert window.trim_end.value() == 36.25
    window._select_quick_task('video')
    assert window.quick_trim_box.isHidden()


def test_imported_folder_root_tracked_for_preserve_hierarchy(window, tmp_path):
    library = tmp_path/'Albums'
    media = library/'1990s'/'Songs'/'Track.flac'
    media.parent.mkdir(parents=True)
    media.write_bytes(b"test intake only")
    window._select_quick_task('audio')
    window.import_paths([library])
    assert len(window.entries) == 1
    assert window.entries[0].import_root == library.resolve()
    assert window.preserve_tree.isChecked()


def test_maintainer_and_third_party_credits_really_displayed(window):
    about_page = window.pages.widget(3)
    messages = ' '.join(w.text() for w in about_page.findChildren(QLabel))
    assert 'Project Creator & Lead Maintainer' in messages
    assert 'Adam Knight' in messages
    assert '@admknight' in messages
    assert 'FFmpeg' in messages
    assert 'PySide6' in messages
