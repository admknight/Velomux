"""Regression tests: scrolling the settings panel must not mutate controls."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QLabel,
                               QScrollArea, QSpinBox, QVBoxLayout, QWidget)

from modern_app import (
    MainWindow, WheelSafeComboBox, WheelSafeDoubleSpinBox, WheelSafeSpinBox,
)


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["velomux-wheel-regression"])
    yield app


def send_wheel(widget, degrees: int):
    pos = QPoint(8, 8)
    event = QWheelEvent(
        QPointF(pos),
        QPointF(widget.mapToGlobal(pos)),
        QPoint(0, 0),
        QPoint(0, degrees),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False,
    )
    QApplication.sendEvent(widget, event)
    return event


def test_wheel_never_changes_integer_float_or_dropdown_values(qt_app):
    controls = [
        (WheelSafeSpinBox(), 64),
        (WheelSafeDoubleSpinBox(), 2.5),
        (WheelSafeComboBox(), 1),
    ]
    try:
        controls[0][0].setRange(0, 512)
        controls[0][0].setValue(64)
        controls[1][0].setRange(-40, 40)
        controls[1][0].setValue(2.5)
        controls[2][0].addItems(["Source", "Mono", "Stereo"])
        controls[2][0].setCurrentIndex(1)

        for control, original in controls:
            for degrees in (120, -120, 240, -240):
                control.setFocus()
                send_wheel(control, degrees)
                actual = control.currentIndex() if isinstance(control, QComboBox) else control.value()
                assert actual == original, f"{type(control).__name__} changed due to wheel input"
    finally:
        for control, _ in controls:
            control.close()


def test_explicit_setting_changes_still_work(qt_app):
    integer = WheelSafeSpinBox()
    integer.setRange(0, 512)
    integer.setValue(128)
    integer.stepUp()
    assert integer.value() == 129

    decimal = WheelSafeDoubleSpinBox()
    decimal.setRange(-40, 40)
    decimal.setValue(0.0)
    decimal.stepDown()
    assert decimal.value() != 0

    combo = WheelSafeComboBox()
    combo.addItems(["Mono", "Stereo"])
    combo.setCurrentIndex(1)
    assert combo.currentText() == "Stereo"
    for widget in (integer, decimal, combo):
        widget.close()


def test_every_numeric_and_combobox_setting_uses_wheel_safety(qt_app):
    window = MainWindow()
    try:
        integers = window.findChildren(QSpinBox)
        decimals = window.findChildren(QDoubleSpinBox)
        dropdowns = window.findChildren(QComboBox)
        assert len(integers) >= 5, "Integer conversion controls were not found"
        assert len(decimals) >= 3, "Precision conversion controls were not found"
        assert len(dropdowns) >= 6, "Format/settings dropdowns were not found"
        for widget in integers:
            assert isinstance(widget, WheelSafeSpinBox), f"Unprotected setting: {widget!r}"
        for widget in decimals:
            assert isinstance(widget, WheelSafeDoubleSpinBox), f"Unprotected setting: {widget!r}"
        for widget in dropdowns:
            assert isinstance(widget, WheelSafeComboBox), f"Unprotected setting: {widget!r}"
        for widget in [window.gain, window.audio_bitrate, window.sample_rate,
                       window.channels, window.collision, window.encoder_speed,
                       window.preset, window.mode]:
            before = widget.currentIndex() if isinstance(widget, QComboBox) else widget.value()
            send_wheel(widget, 120)
            after = widget.currentIndex() if isinstance(widget, QComboBox) else widget.value()
            assert before == after, f"Settings changed while scrolling: {widget!r}"
    finally:
        window.close()


def test_mouse_wheel_scrolls_container_instead_of_changing_gain(qt_app):
    scroll = QScrollArea()
    scroll.resize(280, 150)
    scroll.setWidgetResizable(True)
    inner = QWidget()
    layout = QVBoxLayout(inner)
    gain = WheelSafeDoubleSpinBox()
    gain.setRange(-40, 40)
    gain.setValue(2.5)
    layout.addWidget(QLabel("GAIN · dB"))
    layout.addWidget(gain)
    for n in range(15):
        layout.addWidget(QLabel(f"Additional settings row {n}"))
    scroll.setWidget(inner)
    scroll.show()
    qt_app.processEvents()
    bar = scroll.verticalScrollBar()
    assert bar.maximum() > 0, "Test settings page must be scrollable"
    bar.setValue(0)
    send_wheel(gain, -120)
    qt_app.processEvents()
    assert gain.value() == 2.5, "Scrolling should not change gain"
    assert bar.value() > 0, "The wheel should scroll the parent settings page"
    scroll.close()
