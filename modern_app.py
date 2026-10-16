"""Modern Qt 6 desktop GUI for Velomux.

The existing, tested conversion engine is deliberately kept separate from the GUI.
This module requires PySide6. No external stylesheets, CDNs or online services
are required to run the converter itself.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
import threading
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json

from PySide6.QtCore import Qt, QSettings, QThread, Signal, QUrl, QSize, QPointF
from PySide6.QtGui import QColor, QDesktopServices, QFont, QKeySequence, QShortcut, QIcon, QPainter, QBrush, QPixmap, QPen, QWheelEvent
from PySide6.QtWidgets import (
    QAbstractScrollArea, QApplication, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSpinBox, QSplitter,
    QStackedWidget, QStyle, QTabWidget, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget, QHeaderView, QAbstractItemView,
)

from engine import (
    Options, PRESETS, PRESET_MAP, SUPPORTED_SUFFIXES, classify,
    compatibility, convert, describe, validate_options, which_tools,
)
from toolchain import tools_origin
from velomux_flows import (FLOWS, FLOWS_BY_ID, PROFILE_BY_ID, recommended_preset,
                           destination_for, media_paths_from_arguments)
from version import APP_NAME, APP_VERSION, GITHUB_REPOSITORY

BG = '#090E19'
SURFACE = '#11192A'
SURFACE_2 = '#172237'
TEXT = '#F0F4FA'
MUTED = '#96A6BC'
BORDER = '#243047'
PURPLE = '#8980FF'
MINT = '#40D9B2'
AMBER = '#E9B871'
DANGER = '#FF7E9A'

STYLE = '''
QWidget { background: #090E19; color: #F0F4FA; font-family: "Segoe UI", "Inter", Arial; font-size: 10pt; }
QLabel { background: transparent; border: none; }
QWidget#SettingsInner { background: #11192A; }
QWidget#MainArea { background: #090E19; }
QFrame#SideBar { background: #0F1727; border-right: 1px solid #243047; }
QFrame#Panel, QFrame#Card, QFrame#MiniCard { background: #11192A; border: 1px solid #2B3A52; border-radius: 16px; }
QFrame#MiniCard { border-radius: 13px; }
QFrame#DropZone { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #22254D,stop:1 #10343D); border: 1px dashed #686FBF; border-radius: 14px; }
QLabel#Title { font-size: 22pt; font-weight: 750; color: #F5F8FF; }
QLabel#SubTitle { font-size: 9pt; color: #96A6BC; }
QLabel#Section { font-size: 13pt; font-weight: 720; }
QLabel#Caption { font-size: 9pt; color: #96A6BC; }
QLabel#Logo { background: transparent; border: none; }
QLabel#MetricValue { font-size: 19pt; font-weight: 800; }
QLabel#MetricLabel { font-size: 9pt; color: #96A6BC; }
QPushButton { color: #E8ECF7; background: #1A263A; border: 1px solid #283850; border-radius: 10px; padding: 9px 14px; font-weight: 600; min-height: 20px; }
QPushButton:hover { background: #263752; border-color: #455B7D; }
QPushButton:focus { border: 2px solid #8980FF; }
QPushButton:pressed { background: #303C69; }
QPushButton:disabled { color: #71819A; background: #141E2D; border-color: #1D2A3B; }
QPushButton#Primary { background: #8980FF; color: #111128; border-color: #8980FF; font-weight: 800; }
QPushButton#Primary:hover { background: #AAA3FF; }
QPushButton#Ghost { background: transparent; border-color: transparent; color: #AFC0D7; }
QPushButton#Ghost:hover { background: #1E2A40; color: #F6F8FF; }
QPushButton#Nav { background: transparent; border: none; border-radius: 12px; text-align: left; padding: 13px 16px; color: #9DB0CA; font-weight: 600; }
QPushButton#Nav:hover { background: #18263B; color: #F7F9FD; }
QPushButton#Nav[active="true"] { background: #27264D; color: #E6E1FF; border-left: 3px solid #8980FF; }
QPushButton#FlowCard { background: #19263B; color: #E3EAF7; border: 1px solid #32445D; border-radius: 12px; padding: 9px 10px; text-align: left; font-size: 10pt; font-weight: 700; }
QPushButton#FlowCard:hover { background: #24375A; border: 1px solid #8980FF; }
QPushButton#FlowCard:checked { background: #353266; border: 2px solid #A69CFF; color: #FFFFFF; }

QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox { background: #182338; border: 1px solid #2D3C54; border-radius: 9px; padding: 8px 11px; selection-background-color: #635DCF; min-height: 20px; }
QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #8980FF; }
QComboBox QAbstractItemView { background: #182338; color: #F0F4FA; selection-background-color: #3C427C; border: 1px solid #34445E; }
QComboBox::drop-down, QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { border: 0px; width: 22px; }
QCheckBox { background: transparent; color: #C8D2E2; spacing: 8px; padding: 4px 0; }
QCheckBox::indicator { width: 17px; height: 17px; border-radius: 5px; border: 1px solid #5E708B; background: #152036; }
QCheckBox::indicator:checked { background: #8980FF; border: 1px solid #AAA3FF; image: none; }
QTabWidget::pane { border: 1px solid #273550; border-radius: 10px; background: #11192A; top: -1px; }
QTabBar::tab { color: #92A6C1; background: #11192A; border: 0px; padding: 10px 13px; margin-right: 2px; }
QTabBar::tab:selected { color: #E9E6FF; border-bottom: 2px solid #8980FF; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #10192A; width: 9px; margin: 1px; }
QScrollBar::handle:vertical { background: #394B68; border-radius: 4px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QTableWidget { background: #11192A; alternate-background-color: #141F32; gridline-color: transparent; border: none; selection-background-color: #28395D; selection-color: #F5F7FF; outline: none; }
QTableWidget::item { padding-left: 7px; border-bottom: 1px solid #1C2A40; }
QTableWidget::item:selected { background: #28395D; }
QListWidget#PresetLibrary { background: #121F32; border: 1px solid #2D405B; border-radius: 10px; font-size: 10pt; outline: none; }
QListWidget#PresetLibrary::item { padding: 10px 9px; border-bottom: 1px solid #26354B; }
QListWidget#PresetLibrary::item:selected { background: #393A72; color: #FFFFFF; border-left: 3px solid #958CFF; }
QListWidget#PresetLibrary::item:hover:!selected { background: #202F47; }
QLabel#ErrorBanner { background: #3A2130; border: 1px solid #855060; border-radius: 10px; color: #FFD2DC; padding: 10px 12px; font-size: 10pt; }
QFrame#ToolBadge { background: #16312E; border: none; border-radius: 10px; }
QHeaderView::section { background: #172237; color: #99ACC6; font-size: 9pt; font-weight: 700; padding: 12px 8px; border: none; border-bottom: 1px solid #293750; }
QProgressBar { background: #243147; color: #F8FAFD; border-radius: 5px; border: none; text-align: center; min-height: 9px; }
QProgressBar::chunk { background: #8980FF; border-radius: 5px; }
QTextEdit { background: #0D1627; color: #C2D0E2; border: 1px solid #26364F; border-radius: 11px; padding: 10px; font-family: "Cascadia Code", Consolas; font-size: 9pt; }
QSplitter::handle { background: transparent; width: 10px; }
'''


def _scroll_settings_wheel(widget: QWidget, event: QWheelEvent) -> None:
    """Send wheel input to a scroll area, never to a settings value editor.

    A generic event.ignore() protects the setting but is insufficient for some
    Qt delivery paths: hovering a focused spin box can stop page scrolling.
    Forward the original wheel delta to the scroll-area viewport. A nested tab
    scrolls first; if it is already at the requested limit, its outer settings
    pane can scroll instead. Preserve high-resolution trackpad wheel deltas.
    """
    delta = event.angleDelta().y() or event.pixelDelta().y()
    parent = widget.parentWidget()
    while parent is not None:
        if isinstance(parent, QAbstractScrollArea):
            bar = parent.verticalScrollBar()
            if bar.maximum() > bar.minimum():
                at_limit = (
                    (delta > 0 and bar.value() <= bar.minimum()) or
                    (delta < 0 and bar.value() >= bar.maximum())
                )
                if not at_limit:
                    viewport = parent.viewport()
                    local = viewport.mapFromGlobal(event.globalPosition().toPoint())
                    forwarded = QWheelEvent(
                        QPointF(local), event.globalPosition(),
                        event.pixelDelta(), event.angleDelta(),
                        event.buttons(), event.modifiers(),
                        event.phase(), event.inverted()
                    )
                    previous = bar.value()
                    QApplication.sendEvent(viewport, forwarded)
                    if forwarded.isAccepted() or bar.value() != previous:
                        event.accept()
                        return
        parent = parent.parentWidget()
    event.ignore()


class WheelSafeSpinBox(QSpinBox):
    """Keep numeric settings fixed when using the wheel to scroll."""

    def wheelEvent(self, event):
        _scroll_settings_wheel(self, event)


class WheelSafeDoubleSpinBox(QDoubleSpinBox):
    """Keep precision settings fixed when using the wheel to scroll."""

    def wheelEvent(self, event):
        _scroll_settings_wheel(self, event)


class WheelSafeComboBox(QComboBox):
    """Prevent wheel-driven selection changes, but retain popup navigation."""

    def wheelEvent(self, event):
        _scroll_settings_wheel(self, event)


def label(text: str, object_name: str = 'Caption') -> QLabel:
    obj = QLabel(text)
    obj.setObjectName(object_name)
    obj.setWordWrap(object_name not in ('Title', 'Section', 'MetricValue', 'MetricLabel'))
    return obj


def button(text: str, slot, identity: str | None = None) -> QPushButton:
    obj = QPushButton(text)
    if identity:
        obj.setObjectName(identity)
    obj.clicked.connect(slot)
    return obj


def card(layout: QVBoxLayout | QHBoxLayout, identity: str = 'Panel', padding: int = 17) -> QFrame:
    f = QFrame()
    f.setObjectName(identity)
    if isinstance(layout, QVBoxLayout):
        layout.setContentsMargins(padding, padding, padding, padding)
    else:
        layout.setContentsMargins(padding, padding, padding, padding)
    f.setLayout(layout)
    return f


def vbox(spacing: int = 12) -> QVBoxLayout:
    obj = QVBoxLayout()
    obj.setSpacing(spacing)
    return obj


def hbox(spacing: int = 10) -> QHBoxLayout:
    obj = QHBoxLayout()
    obj.setSpacing(spacing)
    return obj


@dataclass
class QueueEntry:
    source: Path
    preset: str
    import_root: Path | None = None
    state: str = 'Waiting'
    percent: float = 0.0
    output: str = ''
    note: str = ''


class DropZone(QFrame):
    dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setObjectName('DropZone')
        self.setAcceptDrops(True)
        self.setMinimumHeight(118)
        l = vbox(4)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        intro = label('↓    Drop media here to convert', 'Section')
        intro.setAlignment(Qt.AlignmentFlag.AlignCenter)
        details = label('Video  ·  Audio  ·  Images     |     Original files stay untouched', 'Caption')
        details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(intro)
        l.addWidget(details)
        self.setLayout(l)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.dropped.emit(paths)
            event.acceptProposedAction()


class Worker(QThread):
    started_item = Signal(int)
    progress_item = Signal(int, float, str)
    result_item = Signal(int, str, str, str)
    batch_done = Signal()

    def __init__(self, jobs: list[tuple[int, Path, Path, str, str]], options: Options):
        super().__init__()
        self.jobs = jobs
        self.options = options
        self.cancel_event = threading.Event()

    def run(self):
        try:
            for idx, src, dest, preset_name, output_stem in self.jobs:
                if self.cancel_event.is_set():
                    self.result_item.emit(idx, 'Cancelled', '', 'Not started')
                    continue
                self.started_item.emit(idx)
                def on_progress(n, detail, ix=idx):
                    self.progress_item.emit(ix, float(n), str(detail))
                result = convert(src, dest, preset_name, self.options, on_progress,
                                 self.cancel_event, output_stem=output_stem)
                self.result_item.emit(idx, result.status.title(),
                                      str(result.output or ''), result.detail)
        finally:
            self.batch_done.emit()


class UpdateWorker(QThread):
    result_ready = Signal(str)

    def run(self):
        if not GITHUB_REPOSITORY:
            self.result_ready.emit('Public release repository is not configured. Update checks activate after the GitHub repository is approved and created.')
            return
        url = f'https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest'
        try:
            request = Request(url, headers={'Accept':'application/vnd.github+json', 'User-Agent':'Velomux'})
            with urlopen(request, timeout=8) as reply:
                response = json.load(reply)
            tag = str(response.get('tag_name','')).strip()
            page = str(response.get('html_url','')).strip()
            if not tag or not page.startswith('https://github.com/'):
                raise ValueError('Unexpected release API response.')
            self.result_ready.emit(f'Latest published release: {tag}\nYour installed version: {APP_VERSION}\nReview the verified release and download it at:\n{page}')
        except HTTPError as exc:
            if exc.code == 404:
                self.result_ready.emit('No public Velomux release is available yet. This is a private development preview; new builds are currently shared as GitHub Actions test artifacts.')
            else:
                self.result_ready.emit(f'Update service returned HTTP {exc.code}. Your installed converter remains available offline.')
        except (OSError, ValueError, URLError):
            self.result_ready.emit('Unable to check for updates right now. Local conversion is unaffected; try again when connected.')


def nav_icon(kind: str) -> QIcon:
    """Simple vector icons; no platform-dependent Unicode symbol font."""
    px=QPixmap(36,36)
    px.fill(Qt.GlobalColor.transparent)
    painter=QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor('#ABB7D0'),2.5))
    if kind=='convert':
        for x in (5,20):
            for y in (5,20): painter.drawRoundedRect(x,y,11,11,2.5,2.5)
    elif kind=='activity':
        for y in (8,17,26):
            painter.drawEllipse(5,y,2,2)
            painter.drawLine(12,y+1,31,y+1)
    elif kind=='updates':
        painter.drawArc(5,5,26,26,35*16,290*16)
        painter.drawLine(27,4,32,10)
        painter.drawLine(32,10,25,12)
    elif kind=='about':
        painter.drawEllipse(5,5,26,26)
        painter.drawLine(18,15,18,26)
        painter.drawEllipse(17,9,2,2)
    painter.end()
    return QIcon(px)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f'{APP_NAME}  ·  {APP_VERSION}')
        self.setMinimumSize(1120, 730)
        self.resize(1510, 935)
        self.setStyleSheet(STYLE)
        self.settings = QSettings('Velomux Community', 'Velomux')
        self.entries: list[QueueEntry] = []
        self.seen: set[str] = set()
        self.worker: Worker | None = None
        self.update_worker: UpdateWorker | None = None
        self.exit_when_finished = False
        self.nav: list[QPushButton] = []
        self._build_ui()
        self._restore_settings()
        self._show_tools()
        self._metrics()
        self._add_log('Ready. Drop media or select files to begin. Files are never modified.')
        QShortcut(QKeySequence('Ctrl+O'), self, activated=self.add_files)
        QShortcut(QKeySequence('Ctrl+Shift+O'), self, activated=self.add_folder)
        QShortcut(QKeySequence('Delete'), self, activated=self.remove_selected)

    def _build_ui(self):
        root = QWidget()
        base = hbox(0)
        base.setContentsMargins(0, 0, 0, 0)
        root.setLayout(base)
        self.setCentralWidget(root)
        side = QFrame()
        side.setObjectName('SideBar')
        side.setFixedWidth(230)
        nav_layout = vbox(9)
        nav_layout.setContentsMargins(18, 27, 18, 18)
        side.setLayout(nav_layout)
        brand = hbox(11)
        logo = label('', 'Logo')
        logo.setPixmap(brand_pixmap(45))
        logo.setFixedSize(45, 45)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.addWidget(logo)
        brand_names = vbox(1)
        name = label('VELOMUX', 'Section')
        name.setStyleSheet('font-size:14pt;font-weight:850;color:#D3CAFF;letter-spacing:1px')
        subtitle = label('MEDIA CONVERTER', 'Caption')
        subtitle.setStyleSheet('font-size:9pt;color:#9EADC5;letter-spacing:0.7px')
        brand_names.addWidget(name)
        brand_names.addWidget(subtitle)
        brand.addLayout(brand_names)
        nav_layout.addLayout(brand)
        nav_layout.addSpacing(34)
        nav_layout.addWidget(label('WORKSPACE', 'Caption'))
        for idx, (kind, text) in enumerate((('convert','Converter'),('activity','Activity'),('updates','Update Center'),('about','About'))):
            b = button(text, lambda checked=False, i=idx: self._change_page(i), 'Nav')
            b.setIcon(nav_icon(kind))
            b.setIconSize(QSize(20,20))
            b.setMinimumHeight(46)
            self.nav.append(b)
            nav_layout.addWidget(b)
        nav_layout.addStretch(1)
        nav_layout.addWidget(label('BUILT FOR EVERYONE', 'Caption'))
        nav_layout.addWidget(label('An offline-first media workstation. Open-source release planned.', 'Caption'))
        nav_layout.addSpacing(12)
        nav_layout.addWidget(label(f'PREVIEW BUILD  ·  {APP_VERSION}', 'Caption'))
        base.addWidget(side)

        content = QWidget()
        content.setObjectName('MainArea')
        root_column = vbox(0)
        root_column.setContentsMargins(28, 23, 28, 18)
        content.setLayout(root_column)
        base.addWidget(content, 1)
        head = hbox(16)
        titles = vbox(5)
        titles.addWidget(label('Your media. Your format.', 'Title'))
        titles.addWidget(label('Powerful conversion, simple controls, fully local.', 'SubTitle'))
        head.addLayout(titles)
        head.addStretch()
        self.engine_tag = label('Checking FFmpeg...', 'Caption')
        self.engine_tag.setStyleSheet('background:#162A2D;color:#67E4C2;padding:9px 13px;border-radius:10px;')
        head.addWidget(self.engine_tag)
        root_column.addLayout(head)
        root_column.addSpacing(23)
        self.pages = QStackedWidget()
        self.pages.addWidget(self._converter_page())
        self.pages.addWidget(self._activity_page())
        self.pages.addWidget(self._updates_page())
        self.pages.addWidget(self._about_page())
        root_column.addWidget(self.pages, 1)
        footer = hbox(10)
        self.status = label('Ready.', 'Caption')
        footer.addWidget(self.status, 1)
        footer.addWidget(label('PRIVATE BY DEFAULT  ·  PROCESS LOCALLY', 'Caption'))
        root_column.addSpacing(12)
        root_column.addLayout(footer)
        self._change_page(0)

    def _change_page(self, index: int):
        self.pages.setCurrentIndex(index)
        for i, item in enumerate(self.nav):
            item.setProperty('active', 'true' if i == index else 'false')
            item.style().unpolish(item)
            item.style().polish(item)

    def _converter_page(self) -> QWidget:
        page = QWidget()
        layout = vbox(16)
        layout.setContentsMargins(0, 0, 0, 0)
        page.setLayout(layout)
        metrics = hbox(13)
        self.metric_data = {}
        for title, attr, color in [('MEDIA IN QUEUE','queue','#8980FF'), ('COMPLETED','complete','#40D9B2'), ('READY TO CONVERT','ready','#E9B871')]:
            ml = vbox(6)
            caption = label(title, 'MetricLabel')
            number = label('0', 'MetricValue')
            number.setStyleSheet(f'color:{color};')
            ml.addWidget(caption)
            ml.addWidget(number)
            metrics.addWidget(card(ml, 'MiniCard', 18), 1)
            self.metric_data[attr] = number
        layout.addLayout(metrics)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(14)
        split.addWidget(self._queue_panel())
        split.addWidget(self._settings_panel())
        split.setSizes([790, 430])
        layout.addWidget(split, 1)
        return page

    def _queue_panel(self) -> QWidget:
        column = vbox(14)
        column.addWidget(label('Conversion workspace', 'Section'))
        self.drop = DropZone()
        self.drop.dropped.connect(self.import_paths)
        column.addWidget(self.drop)
        toolbar = hbox(8)
        self.add_button = button('+  Add files', self.add_files, 'Primary')
        self.folder_button = button('Add folder', self.add_folder)
        self.remove_button = button('Remove selected', self.remove_selected)
        self.clear_button = button('Clear', self.clear_queue, 'Ghost')
        for b in [self.add_button, self.folder_button, self.remove_button, self.clear_button]:
            toolbar.addWidget(b)
        toolbar.addStretch()
        column.addLayout(toolbar)
        self.queue_search = QLineEdit()
        self.queue_search.setPlaceholderText('Search files in queue...')
        self.queue_search.textChanged.connect(self._filter_queue)
        column.addWidget(self.queue_search)
        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(['FILE', 'TYPE', 'SIZE', 'TARGET', 'STATUS', 'PROGRESS'])
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(47)
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i, width in [(1,65),(2,77),(3,170),(4,98),(5,100)]:
            table.setColumnWidth(i, width)
        table.itemSelectionChanged.connect(self.show_selected_info)
        table.cellDoubleClicked.connect(self.open_file_result)
        table.setMinimumHeight(170)
        self.table = table
        column.addWidget(table, 1)
        error_row = hbox(10)
        self.failure_banner = label('', 'ErrorBanner')
        self.failure_banner.setWordWrap(True)
        self.failure_banner.hide()
        error_row.addWidget(self.failure_banner, 1)
        self.error_log_button = button('View errors', lambda: self._change_page(1))
        self.error_log_button.hide()
        error_row.addWidget(self.error_log_button)
        column.addLayout(error_row)
        totals = hbox(9)
        totals.addWidget(label('BATCH PROGRESS', 'Caption'))
        self.percent_label = label('0%', 'Caption')
        totals.addStretch()
        totals.addWidget(self.percent_label)
        column.addLayout(totals)
        self.total_progress = QProgressBar()
        self.total_progress.setTextVisible(False)
        self.total_progress.setValue(0)
        self.total_progress.setFixedHeight(10)
        column.addWidget(self.total_progress)
        actions = hbox(10)
        self.start_button = button('Start conversion', self.start_conversion, 'Primary')
        self.cancel_button = button('Cancel batch', self.cancel_conversion)
        self.cancel_button.setEnabled(False)
        actions.addWidget(self.start_button)
        actions.addWidget(self.cancel_button)
        actions.addStretch()
        actions.addWidget(button('Open destination', self.open_destination))
        column.addLayout(actions)
        pane = card(column)
        return pane

    def _settings_panel(self) -> QWidget:
        column = vbox(12)
        column.addWidget(label('VeloFlow conversion', 'Section'))
        column.addWidget(label('Start with what you want to do. Fine-tune only when needed.'))

        self.mode = WheelSafeComboBox()
        self.mode.addItems(['Quick mode', 'Advanced mode'])
        self._group_input(column, 'WORKSPACE MODE', self.mode)
        self.mode.currentIndexChanged.connect(self._toggle_mode)

        # Quick mode has its own visible task-first workflow, not a hidden
        # advanced dropdown that defaults all incoming MP4s to M4A.
        self.quick_panel = self._quick_flow_panel()
        column.addWidget(self.quick_panel)

        # Keep every original advanced option intact and discoverable.
        self.advanced_formats = QWidget()
        advanced = vbox(9)
        advanced.setContentsMargins(0, 0, 0, 0)
        advanced.addWidget(label('Advanced format library', 'Section'))
        self.family = WheelSafeComboBox()
        self.family.addItems(['Video', 'Audio', 'Image'])
        self.family.currentTextChanged.connect(self._update_presets)
        self._group_input(advanced, 'MEDIA CATEGORY', self.family)
        self.preset_search = QLineEdit()
        self.preset_search.setPlaceholderText('Search codecs, formats and bitrates...')
        self.preset_search.setClearButtonEnabled(True)
        self.preset_search.textChanged.connect(self._filter_preset_library)
        advanced.addWidget(self.preset_search)
        self.library_count = label('Loading formats...')
        advanced.addWidget(self.library_count)
        self.preset_list = QListWidget()
        self.preset_list.setObjectName('PresetLibrary')
        self.preset_list.setMinimumHeight(178)
        self.preset_list.setMaximumHeight(205)
        self.preset_list.currentItemChanged.connect(self._choose_list_preset)
        advanced.addWidget(self.preset_list)
        self.preset = WheelSafeComboBox()
        self.preset.setEditable(True)
        self.preset.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.preset.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.preset.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.preset.currentTextChanged.connect(self._sync_preset_list)
        self._group_input(advanced, 'SELECTED OUTPUT FORMAT', self.preset)
        self.apply_button = button('Apply format to selected files', self.apply_preset, 'Primary')
        advanced.addWidget(self.apply_button)
        self.advanced_formats.setLayout(advanced)
        column.addWidget(self.advanced_formats)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._general_tab(), 'General')
        self.tabs.addTab(self._video_tab(), 'Video')
        self.tabs.addTab(self._audio_tab(), 'Audio')
        self.tabs.addTab(self._image_tab(), 'Images')
        self.tabs.addTab(self._trim_tab(), 'Trim')
        self.tabs.setDocumentMode(True)
        self.tabs.setMinimumHeight(270)
        column.addWidget(self.tabs)

        # Quick-trim inputs share the exact advanced trim state and safe
        # mouse-wheel behavior; a stream-copy cut is keyframe-limited.
        self.quick_trim_start.valueChanged.connect(self.trim_start.setValue)
        self.quick_trim_end.valueChanged.connect(self.trim_end.setValue)
        self.trim_start.valueChanged.connect(self.quick_trim_start.setValue)
        self.trim_end.valueChanged.connect(self.quick_trim_end.setValue)

        self.inspector_dialog = QDialog(self)
        self.inspector_dialog.setWindowTitle('Velomux · Media inspector')
        self.inspector_dialog.resize(620, 340)
        dialog_layout = vbox(12)
        self.inspector = QTextEdit()
        self.inspector.setReadOnly(True)
        self.inspector.setPlainText('Select media to see its codecs, tracks and conversion result.')
        dialog_layout.addWidget(self.inspector, 1)
        dialog_layout.addWidget(button('Close inspector', self.inspector_dialog.close))
        self.inspector_dialog.setLayout(dialog_layout)
        column.addWidget(button('Inspect selected file and streams ↗', self._show_inspector))
        column.addStretch()

        inner = card(column, 'Panel', 17)
        scroller = QScrollArea()
        scroller.setWidgetResizable(True)
        scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroller.setWidget(inner)
        scroller.setMinimumWidth(360)
        self._update_presets('Video')
        self._toggle_mode()
        return scroller

    def _quick_flow_panel(self) -> QWidget:
        self._quick_task_id = None
        layout = vbox(11)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label('CHOOSE AN ACTION', 'Caption'))
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        self.flow_buttons = {}
        for index, task in enumerate(FLOWS):
            b = QPushButton(task.title)
            b.setObjectName('FlowCard')
            b.setCheckable(True)
            b.setMinimumHeight(54)
            b.setToolTip(task.tagline)
            b.clicked.connect(lambda checked=False, ident=task.id: self._select_quick_task(ident))
            self.flow_buttons[task.id] = b
            grid.addWidget(b, index // 2, index % 2)
        layout.addLayout(grid)
        self.quick_task_help = label(
            'Choose Video, Audio, Images, Extract audio, Compress, Rewrap or Trim. '
            'New imports are assigned a compatible suggestion; nothing converts until you press Start.'
        )
        layout.addWidget(self.quick_task_help)
        self.quick_profiles = WheelSafeComboBox()
        self.quick_profiles.setEnabled(False)
        self.quick_profiles.addItem('Select an action above...', None)
        self.quick_profiles.currentIndexChanged.connect(self._quick_profile_changed)
        self._group_input(layout, 'OUTPUT PROFILE', self.quick_profiles)
        self.quick_profile_detail = label('Purpose-based profiles keep the technical settings underneath.')
        layout.addWidget(self.quick_profile_detail)

        self.quick_trim_box = QWidget()
        trim_layout = vbox(5)
        trim_layout.setContentsMargins(0, 0, 0, 0)
        self.quick_trim_start = self._float_spin(0, 360000, 0, 0.5)
        self.quick_trim_end = self._float_spin(0, 360000, 0, 0.5, 'End of file')
        self._group_input(trim_layout, 'START · SECONDS', self.quick_trim_start)
        self._group_input(trim_layout, 'END · SECONDS', self.quick_trim_end)
        trim_layout.addWidget(label(
            'Fast stream-copy cuts align with video keyframes and are not frame-accurate.'
        ))
        self.quick_trim_box.setLayout(trim_layout)
        self.quick_trim_box.setVisible(False)
        layout.addWidget(self.quick_trim_box)

        self.quick_apply_button = button(
            'Apply this profile to selected queue files', self.apply_preset, 'Primary'
        )
        self.quick_apply_button.setEnabled(False)
        layout.addWidget(self.quick_apply_button)
        layout.addWidget(label(
            'New compatible files get this profile automatically. '
            'Existing queue choices change only when you apply them.'
        ))
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def _select_quick_task(self, task_id: str) -> None:
        task = FLOWS_BY_ID.get(task_id)
        if task is None:
            return
        self._quick_task_id = task_id
        for ident, b in self.flow_buttons.items():
            b.setChecked(ident == task_id)
        help_text = task.tagline
        if task.warning:
            help_text += ' · ' + task.warning
        self.quick_task_help.setText(help_text)
        self.quick_profiles.blockSignals(True)
        self.quick_profiles.clear()
        for preset in task.profiles:
            self.quick_profiles.addItem(preset.label, preset.id)
            self.quick_profiles.setItemData(self.quick_profiles.count()-1,
                                            preset.detail, Qt.ItemDataRole.ToolTipRole)
        self.quick_profiles.blockSignals(False)
        self.quick_profiles.setEnabled(True)
        self.quick_profiles.setCurrentIndex(0)
        self.quick_apply_button.setEnabled(True)
        self.quick_trim_box.setVisible(task_id == 'trim')
        self._quick_profile_changed()

    def _quick_profile_changed(self, index: int = -1) -> None:
        if not self.quick_profiles.isEnabled() or not self._quick_task_id:
            return
        ident = self.quick_profiles.currentData()
        chosen = PROFILE_BY_ID.get(str(ident))
        if chosen is None:
            return
        self.quick_profile_detail.setText(chosen.detail)
        engine_preset = PRESET_MAP[chosen.preset]
        self.family.setCurrentText(engine_preset.group.title())
        self.preset.setCurrentText(chosen.preset)
        self._sync_preset_list(chosen.preset)

    def _show_inspector(self):
        self.show_selected_info()
        self.inspector_dialog.show()
        self.inspector_dialog.raise_()
        self.inspector_dialog.activateWindow()

    def _choose_list_preset(self, item, previous):
        if item is None:
            return
        chosen = str(item.data(Qt.ItemDataRole.UserRole))
        if chosen and self.preset.currentText() != chosen:
            self.preset.setCurrentText(chosen)

    def _sync_preset_list(self, name: str):
        if not hasattr(self, 'preset_list'):
            return
        for index in range(self.preset_list.count()):
            item = self.preset_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == name:
                if self.preset_list.currentItem() is not item:
                    self.preset_list.blockSignals(True)
                    self.preset_list.setCurrentItem(item)
                    self.preset_list.blockSignals(False)
                return

    def _filter_preset_library(self, query: str):
        if not hasattr(self, 'preset_list'):
            return
        group = self.family.currentText().lower()
        selected = self.preset.currentText()
        candidates = [p for p in PRESETS if p.group == group]
        term = query.casefold().strip()
        self.preset_list.blockSignals(True)
        self.preset_list.clear()
        for preset in candidates:
            if term and term not in preset.name.casefold():
                continue
            item = QListWidgetItem(preset.name)
            item.setData(Qt.ItemDataRole.UserRole, preset.name)
            item.setToolTip(
                f'Output: {preset.ext.upper()}   ·   Video: {preset.vcodec or "none"}   ·   Audio: {preset.acodec or "none"}'
            )
            self.preset_list.addItem(item)
            if preset.name == selected:
                self.preset_list.setCurrentItem(item)
        self.preset_list.blockSignals(False)
        count = self.preset_list.count()
        self.library_count.setText(
            f'{count} visible {group} presets  ·  {len(candidates)} in category  ·  {len(PRESETS)} total'
        )

    def _tab_shell(self) -> tuple[QWidget,QVBoxLayout]:
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner_layout = vbox(9)
        inner_layout.setContentsMargins(13, 15, 13, 14)
        inner.setLayout(inner_layout)
        scroll.setWidget(inner)
        page_layout = vbox(0)
        page_layout.setContentsMargins(0,0,0,0)
        page_layout.addWidget(scroll)
        page.setLayout(page_layout)
        return page, inner_layout

    def _group_input(self, layout: QVBoxLayout, text: str, input_widget):
        layout.addWidget(label(text))
        layout.addWidget(input_widget)
        return input_widget

    def _spin(self, minimum=0, maximum=32768, value=0, special=None):
        obj = WheelSafeSpinBox()
        obj.setRange(minimum, maximum)
        obj.setValue(value)
        if special: obj.setSpecialValueText(special)
        return obj

    def _float_spin(self, minimum=0, maximum=36000, value=0, step=0.5, special=None):
        obj = WheelSafeDoubleSpinBox()
        obj.setRange(minimum,maximum)
        obj.setDecimals(2)
        obj.setSingleStep(step)
        obj.setValue(value)
        if special: obj.setSpecialValueText(special)
        return obj

    def _general_tab(self) -> QWidget:
        w,l = self._tab_shell()
        self.beside_source = QCheckBox('Use a Converted folder beside each input')
        self.beside_source.setChecked(True)
        l.addWidget(self.beside_source)
        self.output = QLineEdit(str(Path.home()/'Downloads'/'Converted'))
        line = hbox(6)
        line.addWidget(self.output, 1)
        line.addWidget(button('Browse', self.browse_destination))
        l.addWidget(label('CUSTOM OUTPUT DIRECTORY'))
        l.addLayout(line)
        self.collision = WheelSafeComboBox()
        self.collision.addItem('Repair incomplete; skip verified', 'repair')
        self.collision.addItem('Always replace output', 'overwrite')
        self.collision.addItem('Skip existing files', 'skip')
        self.collision.addItem('Create numbered copies', 'rename')
        self._group_input(l, 'EXISTING FILE HANDLING', self.collision)
        self.recursive = QCheckBox('Include subfolders when importing folders')
        self.recursive.setChecked(True)
        self.preserve_tree = QCheckBox('Preserve imported folder structure in custom output')
        self.preserve_tree.setChecked(True)
        self.keep_metadata = QCheckBox('Preserve metadata where supported')
        self.keep_metadata.setChecked(True)
        self.full_verify = QCheckBox('Full output stream validation (slower)')
        l.addWidget(self.recursive)
        l.addWidget(self.preserve_tree)
        l.addWidget(self.keep_metadata)
        l.addWidget(self.full_verify)
        l.addWidget(label('Safeguard: new files are staged, validated, then moved into place. Originals are never overwritten.'))
        l.addStretch()
        return w

    def _video_tab(self) -> QWidget:
        w,l = self._tab_shell()
        self.crf = self._group_input(l,'VIDEO CRF · QUALITY', self._spin(0,51,23))
        self.encoder_speed = WheelSafeComboBox()
        self.encoder_speed.addItems(['ultrafast','superfast','veryfast','faster','fast','medium','slow','slower','veryslow'])
        self.encoder_speed.setCurrentText('medium')
        self._group_input(l,'ENCODER SPEED',self.encoder_speed)
        self.video_width = self._group_input(l,'MAX WIDTH (PIXELS)', self._spin(0,8192,0,'Original'))
        self.video_height = self._group_input(l,'MAX HEIGHT (PIXELS)', self._spin(0,8192,0,'Original'))
        self.video_fps = self._group_input(l,'OUTPUT FPS', self._float_spin(0,240,0,1,'Source FPS'))
        self.video_rotate = WheelSafeComboBox()
        self.video_rotate.addItems(['0','90','180','270'])
        self._group_input(l,'ROTATION CLOCKWISE',self.video_rotate)
        self.deinterlace = QCheckBox('Deinterlace video (YADIF)')
        self.mute = QCheckBox('Remove audio track')
        l.addWidget(self.deinterlace)
        l.addWidget(self.mute)
        l.addWidget(label('Note: codec availability depends on the FFmpeg build included in the release.'))
        l.addStretch()
        return w

    def _audio_tab(self) -> QWidget:
        w,l = self._tab_shell()
        self.audio_bitrate = self._group_input(l,'BITRATE · KBPS',self._spin(0,512,0,'Preset default'))
        self.sample_rate = self._group_input(l,'SAMPLE RATE · HZ',self._spin(0,192000,0,'Source'))
        self.channels = WheelSafeComboBox()
        for text,val in [('Source',0),('Mono',1),('Stereo',2),('5.1',6),('7.1',8)]:
            self.channels.addItem(text,val)
        self._group_input(l,'CHANNELS',self.channels)
        self.normalize = QCheckBox('Loudness normalization · -16 LUFS')
        self.gain = self._group_input(l,'GAIN · dB', self._float_spin(-40,40,0,1))
        l.addWidget(self.normalize)
        l.addWidget(label('AAC in MP4 can be copied directly into M4A without quality loss when no audio processing is requested.'))
        l.addStretch()
        return w

    def _image_tab(self) -> QWidget:
        w,l = self._tab_shell()
        self.image_width = self._group_input(l,'MAX WIDTH · PX',self._spin(0,32768,0,'Source'))
        self.image_height = self._group_input(l,'MAX HEIGHT · PX',self._spin(0,32768,0,'Source'))
        self.image_quality = self._group_input(l,'IMAGE QUALITY · PRESET OR 1–100',self._spin(0,100,0,'Preset default'))
        self.image_rotate = WheelSafeComboBox()
        self.image_rotate.addItems(['0','90','180','270'])
        self._group_input(l,'ROTATE CLOCKWISE',self.image_rotate)
        self.image_flip = WheelSafeComboBox()
        self.image_flip.addItems(['none','horizontal','vertical'])
        self._group_input(l,'FLIP',self.image_flip)
        self.grayscale = QCheckBox('Convert to grayscale')
        l.addWidget(self.grayscale)
        l.addWidget(label('Aspect ratio is preserved. Supported multi-frame images can retain animation.'))
        l.addStretch()
        return w

    def _trim_tab(self) -> QWidget:
        w,l = self._tab_shell()
        self.trim_start = self._group_input(l,'START AT · SECONDS',self._float_spin(0,360000,0))
        self.trim_end = self._group_input(l,'STOP AT · SECONDS',self._float_spin(0,360000,0,1,'End of file'))
        self.playback_speed = self._group_input(l,'PLAYBACK SPEED',self._float_spin(0.5,2,1,0.05))
        l.addWidget(label('Times refer to positions in the original file. The final output is validated against the expected trimmed duration.'))
        l.addWidget(label('Trimming, filters, resizing and speed changes may require re-encoding.'))
        l.addStretch()
        return w

    def _activity_page(self) -> QWidget:
        page = QWidget()
        l = vbox(16)
        l.setContentsMargins(0,0,0,0)
        l.addWidget(label('Activity & diagnostics', 'Title'))
        l.addWidget(label('Track conversions and investigate any errors without losing the original files.'))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        l.addWidget(self.log,1)
        actions = hbox(12)
        actions.addWidget(button('Copy activity log', lambda: QApplication.clipboard().setText(self.log.toPlainText())))
        actions.addWidget(button('Clear log', self.log.clear, 'Ghost'))
        actions.addStretch()
        l.addLayout(actions)
        page.setLayout(l)
        return page

    def _updates_page(self) -> QWidget:
        page = QWidget()
        l = vbox(17)
        l.setContentsMargins(0,0,0,0)
        l.addWidget(label('Update Center', 'Title'))
        l.addWidget(label('The app and its FFmpeg engine have separate version records. Nothing is silently downloaded or installed.'))
        app_column = vbox(12)
        app_column.addWidget(label('APPLICATION', 'Caption'))
        app_column.addWidget(label(f'Velomux · {APP_VERSION}', 'Section'))
        app_column.addWidget(label('Stable updates are distributed through reviewed GitHub Releases.'))
        btnline=hbox(10)
        btnline.addWidget(button('Check published releases', self.check_updates, 'Primary'))
        btnline.addStretch()
        app_column.addLayout(btnline)
        self.update_notice = QTextEdit()
        self.update_notice.setReadOnly(True)
        self.update_notice.setFixedHeight(105)
        self.update_notice.setPlainText('Update channel is not configured yet. This preview does not self-update.')
        app_column.addWidget(self.update_notice)
        l.addWidget(card(app_column))
        ffcolumn = vbox(12)
        ffcolumn.addWidget(label('FFMPEG / FFPROBE', 'Caption'))
        self.ffmpeg_version = label('Checking installed engine...', 'Section')
        ffcolumn.addWidget(self.ffmpeg_version)
        ffcolumn.addWidget(label('Bundled tools take priority over PATH. Bundled FFmpeg is updated through reviewed releases with provenance, checksums and licensing evidence.'))
        engine_buttons = hbox(10)
        engine_buttons.addWidget(button('Official FFmpeg project ↗',lambda: QDesktopServices.openUrl(QUrl('https://ffmpeg.org/'))))
        engine_buttons.addStretch()
        ffcolumn.addLayout(engine_buttons)
        l.addWidget(card(ffcolumn))
        l.addStretch()
        page.setLayout(l)
        return page

    def _about_page(self) -> QWidget:
        page = QWidget()
        layout = vbox(17)
        layout.setContentsMargins(0, 0, 0, 0)

        brand_line = hbox(15)
        logo = label('', 'Logo')
        logo.setPixmap(brand_pixmap(72))
        logo.setFixedSize(72, 72)
        brand_line.addWidget(logo)
        product_line = vbox(3)
        product_line.addWidget(label('Velomux', 'Title'))
        product_line.addWidget(label('Convert your media, your way.', 'SubTitle'))
        product_line.addWidget(label(f'Version {APP_VERSION} · Development preview'))
        brand_line.addLayout(product_line)
        brand_line.addStretch(1)
        layout.addLayout(brand_line)

        overview = vbox(10)
        overview.addWidget(label('ABOUT THE PROJECT', 'Caption'))
        overview.addWidget(label(
            'Velomux is an independent, offline-first video, audio and image '
            'workstation. VeloFlow provides task-first conversions while Advanced '
            'Mode exposes codec and processing controls.'
        ))
        layout.addWidget(card(overview, 'Panel', 18))

        people = vbox(9)
        people.addWidget(label('PROJECT MAINTENANCE', 'Caption'))
        people.addWidget(label('Maintained by Adam Knight (@admknight)', 'Section'))
        people.addWidget(label(
            'Source, issue tracking and development builds are managed through '
            'the official Velomux GitHub repository.'
        ))
        links = hbox(9)
        links.addWidget(button(
            'GitHub repository ↗',
            lambda: QDesktopServices.openUrl(
                QUrl('https://github.com/admknight/Velomux')
            )
        ))
        links.addWidget(button(
            'Report a problem ↗',
            lambda: QDesktopServices.openUrl(
                QUrl('https://github.com/admknight/Velomux/issues')
            )
        ))
        links.addStretch(1)
        people.addLayout(links)
        layout.addWidget(card(people, 'Panel', 18))

        licenses = vbox(10)
        licenses.addWidget(label('TECHNOLOGY & CREDITS', 'Caption'))
        licenses.addWidget(label(
            'Media processing: FFmpeg / ffprobe. Interface: Qt 6 for Python '
            '(PySide6). Images: Pillow. Thanks to their contributors and maintainers.'
        ))
        licenses.addWidget(label(
            'The application license and full third-party redistribution package '
            'are pending approval for a public open-source release. '
            'This preview must not be presented as a cleared public release.'
        ))
        licenses.addWidget(label(
            'Your media is processed locally. An optional update check contacts '
            'GitHub only after you request it.'
        ))
        layout.addWidget(card(licenses, 'Panel', 18))
        layout.addStretch(1)
        page.setLayout(layout)
        return page

    def _toggle_mode(self):
        advanced = self.mode.currentIndex() == 1
        self.advanced_formats.setVisible(advanced)
        self.quick_panel.setVisible(not advanced)
        for index in range(1, self.tabs.count()):
            self.tabs.setTabVisible(index, advanced)

    def _filter_queue(self, text: str):
        needle=text.casefold().strip()
        for index, item in enumerate(self.entries):
            self.table.setRowHidden(index, bool(needle and needle not in item.source.name.casefold() and needle not in item.preset.casefold()))

    def _restore_settings(self):
        self.output.setText(str(self.settings.value('output_directory',str(Path.home()/'Downloads'/'Converted'))))
        self.beside_source.setChecked(str(self.settings.value('beside_source','true')).lower() == 'true')
        self.recursive.setChecked(str(self.settings.value('recursive','true')).lower() == 'true')
        self.preserve_tree.setChecked(str(self.settings.value('preserve_tree','true')).lower() == 'true')
        self.keep_metadata.setChecked(str(self.settings.value('metadata','true')).lower() == 'true')
        index=self.collision.findData(str(self.settings.value('collision','repair')))
        if index >= 0: self.collision.setCurrentIndex(index)
        self.mode.setCurrentIndex(int(self.settings.value('mode',0)))
        flow_id = str(self.settings.value('flow_task', '') or '')
        if flow_id in FLOWS_BY_ID:
            self._select_quick_task(flow_id)
            profile_id = str(self.settings.value('flow_profile', '') or '')
            index = self.quick_profiles.findData(profile_id)
            if index >= 0:
                self.quick_profiles.setCurrentIndex(index)
        geometry=self.settings.value('geometry')
        if geometry is not None: self.restoreGeometry(geometry)

    def _save_settings(self):
        self.settings.setValue('output_directory',self.output.text())
        self.settings.setValue('beside_source',self.beside_source.isChecked())
        self.settings.setValue('recursive',self.recursive.isChecked())
        self.settings.setValue('preserve_tree',self.preserve_tree.isChecked())
        self.settings.setValue('flow_task',self._quick_task_id or '')
        self.settings.setValue('flow_profile',self.quick_profiles.currentData() or '')
        self.settings.setValue('metadata',self.keep_metadata.isChecked())
        self.settings.setValue('collision',self.collision.currentData())
        self.settings.setValue('geometry',self.saveGeometry())
        self.settings.setValue('mode',self.mode.currentIndex())

    def _update_presets(self, family: str):
        values = [p.name for p in PRESETS if p.group == family.lower()]
        self.preset.blockSignals(True)
        self.preset.clear()
        self.preset.addItems(values)
        self.preset.blockSignals(False)
        if hasattr(self, 'preset_search'):
            self.preset_search.clear()
        self._filter_preset_library('')


    def _show_tools(self):
        a, b = which_tools()
        if a and b:
            text = tools_origin()
            self.engine_tag.setText('●  ' + text)
            self.engine_tag.setStyleSheet('background:#152D2B;color:#64E2BF;padding:9px 13px;border-radius:10px;')
            try:
                version = subprocess.run([a,'-version'],stdin=subprocess.DEVNULL,text=True,
                                         stdout=subprocess.PIPE,stderr=subprocess.DEVNULL, timeout=5)
                first = version.stdout.splitlines()[0].strip() if version.stdout else 'Version unavailable'
                self.ffmpeg_version.setText(first[:115])
                self.ffmpeg_version.setToolTip(first)
            except (OSError, subprocess.TimeoutExpired):
                self.ffmpeg_version.setText('FFmpeg detected; version unavailable')
        else:
            self.engine_tag.setText('●  FFmpeg unavailable')
            self.engine_tag.setStyleSheet('background:#38202F;color:#FF99AE;padding:9px 13px;border-radius:10px;')
            self.ffmpeg_version.setText('FFmpeg / ffprobe not found')

    def _metrics(self):
        self.metric_data['queue'].setText(str(len(self.entries)))
        self.metric_data['complete'].setText(str(sum(e.state in ('Done','Skipped') for e in self.entries)))
        self.metric_data['ready'].setText(str(sum(e.state == 'Waiting' for e in self.entries)))

    def _add_log(self, text: str):
        self.log.append(text)

    def _path_key(self, path: Path) -> str:
        return os.path.normcase(os.path.abspath(str(path)))

    def import_paths(self, paths: list[Path]):
        if self.worker and self.worker.isRunning():
            return
        selected = PRESET_MAP.get(self.preset.currentText())
        is_quick = self.mode.currentIndex() == 0
        task_id = self._quick_task_id if is_quick else None
        profile_id = self.quick_profiles.currentData() if task_id else None
        found: list[tuple[Path, Path | None]] = []
        for path in paths:
            if path.is_file():
                found.append((path, None))
            elif path.is_dir():
                walk = path.rglob('*') if self.recursive.isChecked() else path.iterdir()
                try:
                    for sub in walk:
                        if not sub.is_file():
                            continue
                        if self.recursive.isChecked() and any(
                            part.lower() == 'converted'
                            for part in sub.relative_to(path).parts[:-1]
                        ):
                            continue
                        found.append((sub, path))
                except (OSError, PermissionError) as exc:
                    self._add_log(f'[WARNING] Could not scan all files in {path}: {exc}')
        count = 0
        incompatible = 0
        for file, folder_root in found:
            if file.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            key = self._path_key(file)
            if key in self.seen:
                continue
            kind = classify(file)
            if task_id:
                name = recommended_preset(kind, task_id, str(profile_id))
                if not name:
                    incompatible += 1
                    self._add_log(
                        f'[NOT QUEUED] {file.name}: unsupported input for '
                        f'{FLOWS_BY_ID[task_id].title}.'
                    )
                    continue
            elif not is_quick and selected and compatibility(file, selected):
                name = selected.name
            else:
                # The default MUST NEVER convert imported videos to M4A
                # without an explicit Extract Audio task selection.
                name = recommended_preset(kind)
            if not name:
                incompatible += 1
                continue
            self.seen.add(key)
            self.entries.append(QueueEntry(
                file.resolve(), name,
                folder_root.resolve() if folder_root else None
            ))
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._render_row(row)
            count += 1
        self._metrics()
        self._filter_queue(self.queue_search.text())
        message = f'{len(self.entries)} in queue · {count} added'
        if incompatible:
            message += f' · {incompatible} incompatible'
        self.status.setText(message)
        self._add_log(
            f'Added {count} compatible media file(s). '
            + (f'Skipped {incompatible} incompatible input(s).' if incompatible else '')
        )

    def add_files(self):
        patterns=' '.join('*'+suffix for suffix in sorted(SUPPORTED_SUFFIXES))
        paths, _ = QFileDialog.getOpenFileNames(self,'Add video, audio or image files', '', f'Media files ({patterns});;All files (*)')
        if paths: self.import_paths([Path(p) for p in paths])

    def add_folder(self):
        name = QFileDialog.getExistingDirectory(self,'Select media folder')
        if name: self.import_paths([Path(name)])

    def _render_row(self, index: int):
        e = self.entries[index]
        try: size=e.source.stat().st_size/1048576
        except OSError: size=0
        values=[e.source.name,classify(e.source).upper(),f'{size:,.1f} MB',PRESET_MAP[e.preset].ext.upper().lstrip('.'),e.state]
        for c,value in enumerate(values):
            item=QTableWidgetItem(value)
            note = (e.note or '').strip()
            item.setToolTip(f'{e.source}\n{note}' if note else str(e.source))
            if c == 4:
                item.setForeground(QBrush(QColor(MINT if e.state in ('Done','Skipped') else DANGER if e.state=='Failed' else AMBER if e.state=='Running' else MUTED)))
            self.table.setItem(index,c,item)
        bar = self.table.cellWidget(index,5)
        if not isinstance(bar,QProgressBar):
            bar=QProgressBar()
            bar.setRange(0,100)
            bar.setFormat('%p%')
            bar.setFixedHeight(14)
            self.table.setCellWidget(index,5,bar)
        bar.setValue(int(e.percent))

    def remove_selected(self):
        if self.worker and self.worker.isRunning(): return
        selected=sorted({idx.row() for idx in self.table.selectionModel().selectedRows()},reverse=True)
        for index in selected:
            e=self.entries.pop(index)
            self.seen.discard(self._path_key(e.source))
            self.table.removeRow(index)
        self._metrics()
        self._filter_queue(self.queue_search.text())

    def clear_queue(self):
        if self.worker and self.worker.isRunning(): return
        self.entries.clear();self.seen.clear()
        self.table.setRowCount(0)
        self.total_progress.setValue(0)
        self.percent_label.setText('0%')
        self._metrics()
        self.failure_banner.hide()
        self.error_log_button.hide()
        self.inspector.setPlainText('Select a file to see its codec, resolution, duration and tracks.')

    def show_selected_info(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:return
        e=self.entries[selected[0].row()]
        try: info=describe(e.source)
        except Exception as exc: info=f'Unable to inspect media: {exc}'
        if e.output: info += '\nOutput: '+e.output
        if e.note: info += '\n\nCONVERSION RESULT: ' + e.state.upper() + '\n' + e.note
        self.inspector.setPlainText(info)

    def apply_preset(self):
        name=self.preset.currentText()
        preset=PRESET_MAP.get(name)
        if not preset:
            QMessageBox.warning(self,'Invalid preset','Choose an available format preset from the list.')
            return
        selected=sorted({s.row() for s in self.table.selectionModel().selectedRows()})
        if not selected:
            QMessageBox.information(self,'No files selected','Select one or more files in the conversion queue first.')
            return
        count=0
        for row in selected:
            entry=self.entries[row]
            if not compatibility(entry.source,preset):
                self._add_log(f'[IGNORED] {entry.source.name}: not compatible with {preset.group} preset.')
                continue
            if self.mode.currentIndex() == 0 and self._quick_task_id:
                if classify(entry.source) not in FLOWS_BY_ID[self._quick_task_id].input_kinds:
                    self._add_log(f'[IGNORED] {entry.source.name}: incompatible with selected VeloFlow.')
                    continue
            entry.preset=name
            entry.state='Waiting'
            entry.percent=0.0
            entry.output=''
            self._render_row(row)
            count+=1
        self._metrics()
        self.status.setText(f'Applied {name} to {count} files.')

    def browse_destination(self):
        name = QFileDialog.getExistingDirectory(self, 'Select output directory',self.output.text())
        if name:
            self.output.setText(name)
            self.beside_source.setChecked(False)

    def _options(self) -> Options:
        opt = Options(
            collision=str(self.collision.currentData()),keep_metadata=self.keep_metadata.isChecked(),
            decode_check=self.full_verify.isChecked(), quality=self.crf.value(),
            video_speed=self.encoder_speed.currentText(), video_width=self.video_width.value(),
            video_height=self.video_height.value(), fps=self.video_fps.value(),
            rotate_video=int(self.video_rotate.currentText()),
            deinterlace=self.deinterlace.isChecked(), mute_video=self.mute.isChecked(),
            trim_start=self.trim_start.value(), trim_end=self.trim_end.value(),
            media_speed=self.playback_speed.value(), audio_bitrate=self.audio_bitrate.value(),
            audio_sample_rate=self.sample_rate.value(), audio_channels=int(self.channels.currentData()),
            audio_normalize=self.normalize.isChecked(),audio_gain_db=self.gain.value(),
            image_width=self.image_width.value(),image_height=self.image_height.value(),
            image_quality=self.image_quality.value(),rotate_image=int(self.image_rotate.currentText()),
            flip_image=self.image_flip.currentText(),grayscale=self.grayscale.isChecked(),
        )
        validate_options(opt)
        return opt

    def _set_processing(self, processing: bool):
        for widget in (self.add_button,self.folder_button,self.remove_button,self.clear_button,
                       self.apply_button,self.preset,self.family,self.tabs,self.collision,
                       self.beside_source,self.output,self.recursive,self.preserve_tree,
                       self.quick_panel,self.mode):
            widget.setEnabled(not processing)
        self.start_button.setEnabled(not processing)
        self.cancel_button.setEnabled(processing)

    def start_conversion(self):
        if self.worker and self.worker.isRunning(): return
        if not self.entries:
            QMessageBox.information(self,'Empty queue','Add files or a folder to convert first.')
            return
        if self.mode.currentIndex() == 0 and self._quick_task_id == 'trim':
            if self.trim_start.value() == 0 and self.trim_end.value() == 0:
                QMessageBox.warning(self, 'Trim range required',
                                    'Set a start or end time for the Trim workflow.')
                return
        try:
            opt=self._options()
            custom=self.output.text().strip()
            if not self.beside_source.isChecked() and not custom: raise ValueError('Choose a destination folder.')
            target_dir=Path(custom).expanduser() if custom else Path.home()/'Downloads'/'Converted'
        except (ValueError, TypeError) as exc:
            QMessageBox.warning(self,'Invalid settings',str(exc))
            return
        if any(PRESET_MAP[e.preset].group != 'image' for e in self.entries) and not all(which_tools()):
            QMessageBox.critical(self,'FFmpeg not found','This build needs bundled FFmpeg and ffprobe, or an installed development FFmpeg. See Update Center.')
            return
        invalid=[e.preset for e in self.entries if e.preset not in PRESET_MAP]
        if invalid:
            QMessageBox.warning(self,'Invalid preset','One or more queued files have an unsupported preset.')
            return
        jobs=[]
        planned=set()
        for i,e in enumerate(self.entries):
            directory = (e.source.parent/'Converted' if self.beside_source.isChecked()
                         else destination_for(e.source, target_dir, e.import_root,
                                              self.preserve_tree.isChecked()))
            stem=e.source.stem
            ext=PRESET_MAP[e.preset].ext
            pathkey=self._path_key(directory/(stem+ext))
            if pathkey in planned:
                stem=f'{stem} [{e.source.suffix.lstrip(".")}]'
                pathkey=self._path_key(directory/(stem+ext))
                n=2
                while pathkey in planned:
                    stem=f'{e.source.stem} [{e.source.suffix.lstrip(".")}] {n}'
                    pathkey=self._path_key(directory/(stem+ext))
                    n+=1
            planned.add(pathkey)
            e.state='Waiting'; e.percent=0.0; e.note=''; e.output=''
            self._render_row(i)
            jobs.append((i,e.source,directory,e.preset,stem))
        self.total_progress.setValue(0)
        self.total_progress.setStyleSheet('')
        self.percent_label.setText('0%')
        self.failure_banner.hide()
        self.error_log_button.hide()
        self._set_processing(True)
        self._metrics()
        self.worker=Worker(jobs,opt)
        self.worker.started_item.connect(self._worker_started)
        self.worker.progress_item.connect(self._worker_progress)
        self.worker.result_item.connect(self._worker_result)
        self.worker.batch_done.connect(self._worker_done)
        self.worker.finished.connect(self._thread_finished)
        self.worker.start()
        self._add_log(f'Started {len(jobs)} conversion(s). Existing-file policy: {opt.collision}.')

    def _worker_started(self, index: int):
        entry=self.entries[index]
        entry.state='Running'
        self._render_row(index)
        self._metrics()
        self.status.setText(f'Converting {index+1}/{len(self.entries)}: {entry.source.name}')

    def _worker_progress(self, index: int, value: float, detail: str):
        self.entries[index].percent = min(99.0,max(0.0,value))
        self._render_row(index)
        overall=(index+value/100)/max(1,len(self.entries))*100
        self.total_progress.setValue(int(overall))
        self.percent_label.setText(f'{overall:.0f}%')
        self.status.setText(f'{self.entries[index].source.name} · {detail}')

    def _worker_result(self, index: int, state: str, output: str, detail: str):
        e=self.entries[index]
        e.state=state
        e.percent=100 if state in ('Done','Skipped') else 0
        e.output=output
        e.note=detail
        self._render_row(index)
        self._metrics()
        prefix = 'OK' if state == 'Done' else state.upper()
        self._add_log(f'[{prefix}] {e.source.name}: {detail}')
        if state == 'Failed':
            self.failure_banner.setText(
                f'{sum(row.state == "Failed" for row in self.entries)} conversion(s) failed. '
                'Select a failed row for its error, or open Activity for full diagnostics.'
            )
            self.failure_banner.show()
            self.error_log_button.show()
        elif self.inspector_dialog.isVisible():
            self.show_selected_info()
        count=sum(row.state in ('Done','Skipped','Failed','Cancelled') for row in self.entries)
        value=100*count/max(1,len(self.entries))
        self.total_progress.setValue(int(value))
        self.percent_label.setText(f'{value:.0f}%')

    def _worker_done(self):
        self._set_processing(False)
        counts={name:sum(e.state==name for e in self.entries) for name in ('Done','Skipped','Failed','Cancelled')}
        summary=' · '.join(f'{name} {value}' for name,value in counts.items() if value)
        self.status.setText('Batch finished. '+summary)
        failed = counts['Failed']
        if failed:
            self.total_progress.setStyleSheet(
                'QProgressBar {background:#283047;border-radius:5px;border:none;}'
                'QProgressBar::chunk {background:#FF7E9A;border-radius:5px;}'
            )
            self.failure_banner.setText(
                f'{failed} conversion(s) failed. No original file was modified. '
                'Open Activity for the exact error messages before trying again.'
            )
            self.failure_banner.show()
            self.error_log_button.show()
            self._change_page(0)
        else:
            self.total_progress.setStyleSheet('')
        self._add_log('Batch finished. '+summary)

    def _thread_finished(self):
        if self.exit_when_finished:
            self.close()

    def cancel_conversion(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel_event.set()
            self.cancel_button.setEnabled(False)
            self.status.setText('Cancelling safely…')
            self._add_log('Cancellation requested. Original files and verified existing outputs are preserved.')

    def open_file_result(self, row: int, col: int):
        if row < len(self.entries):
            output=self.entries[row].output
            if output and Path(output).is_file():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(output).resolve())))

    def open_destination(self):
        if self.table.selectionModel().selectedRows():
            e=self.entries[self.table.selectionModel().selectedRows()[0].row()]
            dest=Path(e.output).parent if e.output else e.source.parent/'Converted' if self.beside_source.isChecked() else Path(self.output.text())
        elif self.beside_source.isChecked() and self.entries:
            dest=self.entries[0].source.parent/'Converted'
        else:
            dest=Path(self.output.text())
        try:
            dest.mkdir(parents=True,exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(dest.resolve())))
        except OSError as exc:
            QMessageBox.warning(self,'Cannot open destination',str(exc))

    def check_updates(self):
        if self.update_worker and self.update_worker.isRunning(): return
        self.update_notice.setPlainText('Checking published GitHub releases…')
        self.update_worker=UpdateWorker()
        self.update_worker.result_ready.connect(self.update_notice.setPlainText)
        self.update_worker.start()

    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            ask=QMessageBox.question(self,'Conversion in progress',
                'Cancel the active conversion and exit after the worker stops?\n\nExisting outputs will be preserved until a new output is validated.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ask==QMessageBox.StandardButton.Yes:
                self.exit_when_finished=True
                self.cancel_conversion()
            event.ignore()
            return
        if self.update_worker and self.update_worker.isRunning():
            self.update_worker.requestInterruption()
            # Update check has an 8s network timeout, but do not destroy active QThreads.
            self.update_worker.wait(10000)
        self._save_settings()
        event.accept()


def bundled_asset(filename: str) -> Path:
    """Locate runtime resources inside both source and PyInstaller onedir builds."""
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    return base / 'assets' / filename


def brand_pixmap(size: int) -> QPixmap:
    pix = QPixmap(str(bundled_asset('velomux.png')))
    if not pix.isNull():
        return pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
    # The source tree includes this asset; fall back gracefully if omitted.
    pix = QPixmap(size, size)
    pix.fill(QColor(PURPLE))
    return pix


def build_app_icon() -> QIcon:
    path = bundled_asset('velomux.png')
    if path.is_file():
        return QIcon(str(path))
    return QIcon(brand_pixmap(128))


def main():
    app=QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName('Velomux Community')
    app.setStyle('Fusion')
    app.setWindowIcon(build_app_icon())
    app.setFont(QFont('Segoe UI',10))
    ui=MainWindow()
    ui.show()
    # Windows Explorer's optional right-click entry passes a quoted filename.
    # Never start encoding on launch; just queue supported local files.
    incoming = media_paths_from_arguments(sys.argv[1:])
    if incoming:
        ui.import_paths(incoming)
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
