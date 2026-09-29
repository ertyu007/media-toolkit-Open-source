from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk

from . import __version__

from .ffmpeg import (
    CancellationToken,
    ConversionCancelled,
    FFmpegError,
    JobSpec,
    VIDEO_QUALITY_PRESETS,
    build_command,
    check_disk_space,
    cleanup_temporary_output,
    convert,
    finalize_output,
    normalize_trim,
    output_path,
    parse_trim_seconds,
    probe,
    temporary_output_path,
    tools_available,
    validate_operation,
)
from .importer import (
    ImportSpec,
    URLImportError,
    VIDEO_QUALITIES,
    check_destination_disk_space,
    cleanup_import_workspace,
    cleanup_orphaned_import_workspaces,
    import_audio_for_processing,
    import_url,
    url_summary,
    validate_url,
    ytdlp_available,
)
from .separator import (
    SELECTABLE_STEMS,
    STEM_LABELS,
    SeparatorError,
    separate_audio,
    separate_expected_outputs,
    separator_installed,
    cleanup_orphaned_workspaces,
)
from .dependencies import DependencyInstallError
from .donate import DONATE_BODY, DONATE_HEADING, DONATE_NOTE, donate_image_path
from .history import KIND_LABELS, add_entry, clear_history, load_history, remove_entry
from .preview import LinkPreview, download_thumbnail, fetch_link_preview
from .dragdrop import drop_files_supported, register_drop_files
from .legal import DISCLAIMER_TEXT
from .setup_ui import ToolSetupDialog
from .tools import missing_required_tools
from .app_update import (
    AppReleaseInfo,
    AppUpdateError,
    fetch_latest_app_release,
    get_skipped_version,
    is_app_update_available,
    load_settings,
    save_settings,
)
from .ytdlp_update import (
    YtDlpUpdateError,
    installed_ytdlp_version,
    is_newer_available,
    latest_ytdlp_version,
    update_ytdlp,
)
from .ui_components.dialogs import (
    CANCEL,
    KEEP,
    OVERWRITE,
    AppUpdateDialog,
    ErrorDialog,
    OverwriteDialog,
    sanitize_error_message,
)
from .ui_components.format import format_file_size
from .ui_components.motion import (
    Tween,
    fade_in_window,
    mix_color,
)
from .ui_components.theme import (
    ACCENT,
    ACCENT_DISABLED_BG,
    ACCENT_DISABLED_FG,
    ACCENT_GLOW,
    ACCENT_HOVER,
    ACCENT_SOFT,
    ACTION_BG,
    BG,
    BORDER,
    BORDER_LIGHT,
    CARD,
    DISABLED_BG,
    DISABLED_FG,
    ERROR,
    FIELD,
    FONT_FAMILY,
    FONT_SIZE_BASE,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    FONT_SIZE_TOP,
    MENU_ACTIVE_FG,
    MENU_BG,
    MUTED,
    PROGRESS_TROUGH,
    SECONDARY_BG,
    SECONDARY_BORDER,
    SECONDARY_HOVER,
    SECTION_ACCENT,
    SUCCESS,
    TEXT,
    THEME_NAME,
    TOAST_BG,
    TOP_BAR_BG,
    TOPBAR_BUTTON_BG,
    TOPBAR_BUTTON_HOVER,
    TOPBAR_BUTTON_FG,
    normalize_theme,
    pick_ui_font,
)
from .ui_components.widgets import (
    InlineError,
    PILL_HEIGHT,
    RainbowBar,
    RoundedButton,
    RoundedCombobox,
    RoundedEntry,
    SegmentedControl,
    Switch,
    ToastManager,
)
from .sound import play_completion_chime

AUDIO_FORMAT_LABELS = ('MP3', 'M4A', 'WAV', 'FLAC', 'OPUS')
AUDIO_FORMAT_VALUES = {'MP3': 'mp3', 'M4A': 'm4a', 'WAV': 'wav', 'FLAC': 'flac', 'OPUS': 'opus'}
VIDEO_FORMAT_LABELS = ('MP4  •  เล่นได้ทั่วไป', 'MOV  •  ProRes (After Effects)')
VIDEO_FORMAT_VALUES = {
    'MP4  •  เล่นได้ทั่วไป': 'mp4',
    'MOV  •  ProRes (After Effects)': 'mov',
}
FPS_LABELS = ('สูงสุด', '60fps', '30fps')
FPS_VALUES = {'สูงสุด': 'สูงสุด', '60fps': '60', '30fps': '30'}

# Progress phases
PROGRESS_PHASES = {
    'idle': 'พร้อมเริ่มงาน',
    'validating': 'กำลังตรวจสอบ…',
    'downloading': 'กำลังดาวน์โหลด…',
    'extracting': 'กำลังแยกเสียง…',
    'converting': 'กำลังแปลงวิดีโอ…',
    'separating': 'กำลังแยกสเต็ม…',
    'finalizing': 'กำลังบันทึกไฟล์…',
    'done': 'เสร็จสิ้น',
    'error': 'เกิดข้อผิดพลาด',
}



def destination_path(value: str) -> Path:
    text = value.strip()
    if not text:
        raise ValueError('กรุณาเลือกโฟลเดอร์บันทึกก่อนเริ่มงาน')
    return Path(text)


# Explorer-style history columns: name stretches, the rest keep pixel widths
# so the fixed header always lines up with the rows.
_HISTORY_COLUMN_MINSIZES = {1: 70, 2: 110, 3: 90}
_SELECTED_HISTORY_KEY = 'selected_history_id'


def validate_job_settings(raw: dict) -> dict:
    """Validated startup/popup settings; unknown values fall back to defaults."""
    try:
        home_downloads = str(Path.home() / 'Downloads')
    except Exception:
        home_downloads = ''
    destination = str(raw.get('destination') or '').strip() or home_downloads
    mode = str(raw.get('mode') or 'video')
    if mode not in ('audio', 'video', 'stems'):
        mode = 'video'
    audio_format = str(raw.get('audio_format') or 'MP3')
    if audio_format not in AUDIO_FORMAT_LABELS:
        audio_format = 'MP3'
    video_format = str(raw.get('video_format') or VIDEO_FORMAT_LABELS[0])
    if video_format not in VIDEO_FORMAT_LABELS:
        video_format = VIDEO_FORMAT_LABELS[0]
    fps = str(raw.get('fps') or FPS_LABELS[0])
    if fps not in FPS_LABELS:
        fps = FPS_LABELS[0]
    return {
        'destination': destination,
        'mode': mode,
        'audio_format': audio_format,
        'video_format': video_format,
        'quality': str(raw.get('quality') or 'Balanced'),
        'fps': fps,
        'theme': normalize_theme(raw.get('theme')),
        'chime_enabled': bool(raw.get('chime_enabled', True)),
        'auto_update_check': bool(raw.get('auto_update_check', True)),
    }


def load_job_defaults() -> dict:
    """Validated job-form defaults from disk; never raises."""
    try:
        raw = load_settings()
    except Exception:
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    return validate_job_settings(raw)


def find_history_index(entries: list, selected_id: str | None) -> int | None:
    """Index of the entry with *selected_id* (falls back to target path)."""
    if not selected_id:
        return None
    for index, entry in enumerate(entries):
        if getattr(entry, 'id', None) == selected_id:
            return index
    for index, entry in enumerate(entries):
        if getattr(entry, 'target', None) == selected_id:
            return index
    return None


def load_selected_history_id() -> str | None:
    """Last history entry the user picked (survives restarts); None on failure."""
    try:
        value = load_settings().get(_SELECTED_HISTORY_KEY)
    except Exception:
        return None
    return str(value) if value else None


def save_selected_history_id(entry_id: str | None) -> None:
    """Remember the picked history entry; never raises (selection is cosmetic)."""
    try:
        settings = load_settings()
        if entry_id:
            settings[_SELECTED_HISTORY_KEY] = entry_id
        else:
            settings.pop(_SELECTED_HISTORY_KEY, None)
        save_settings(settings)
    except Exception:
        pass


def format_debug_line(when: datetime, message: str) -> str:
    """Pure formatter for one debug-log line (``[HH:MM:SS] message``)."""
    return f"[{when.strftime('%H:%M:%S')}] {message}"


def find_clipora_uninstaller(app_dir: Path) -> Path | None:
    """Inno Setup uninstaller next to the frozen exe; None when absent."""
    candidate = Path(app_dir) / 'unins000.exe'
    try:
        return candidate if candidate.is_file() else None
    except OSError:
        return None


def route_dropped_paths(paths: list[str]) -> tuple[str, str] | None:
    """Route an Explorer drop: first existing file → source, else dir → destination."""
    cleaned = [(raw or '').strip().strip('"') for raw in paths]
    for path in cleaned:
        if path and os.path.isfile(path):
            return ('source', path)
    for path in cleaned:
        if path and os.path.isdir(path):
            return ('destination', path)
    return None


def fit_photo_image(image: tk.PhotoImage, max_width: int, max_height: int) -> tk.PhotoImage:
    """Scale a PhotoImage to fit inside a bounding box (stdlib only)."""
    width, height = image.width(), image.height()
    if width <= max_width and height <= max_height:
        return image
    best: tuple[int, int, int, int] | None = None
    for zoom in range(1, 9):
        for subsample in range(1, 9):
            scaled_width = width * zoom // subsample
            scaled_height = height * zoom // subsample
            if scaled_width <= max_width and scaled_height <= max_height:
                if best is None or (scaled_width * scaled_height) > (best[0] * best[1]):
                    best = (scaled_width, scaled_height, zoom, subsample)
    if best is None:
        return image.subsample(max(1, width // max_width), max(1, height // max_height))
    _scaled_width, _scaled_height, zoom, subsample = best
    if zoom > 1 and subsample > 1:
        return image.zoom(zoom).subsample(subsample)
    if zoom > 1:
        return image.zoom(zoom)
    if subsample > 1:
        return image.subsample(subsample)
    return image


def source_summary(path_value: str) -> str:
    if not path_value.strip():
        return 'ยังไม่ได้เลือกไฟล์'
    path = Path(path_value)
    try:
        if path.is_file():
            return f'{path.name}  •  {format_file_size(path.stat().st_size)}'
    except OSError:
        pass
    return 'ไม่พบไฟล์นี้ กรุณาเลือกไฟล์ใหม่'


class CliporaApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title('Clipora')
        self.geometry('760x720')
        self.minsize(700, 600)
        self.configure(bg=BG)
        self._first_run_setup = bool(missing_required_tools())
        if self._first_run_setup:
            self.withdraw()

        available_fonts = set(tkfont.families(self))
        self.ui_font = pick_ui_font(available_fonts)
        self._icon = self._create_icon()
        self.iconphoto(True, self._icon)

        self.source = tk.StringVar()
        self.input_kind = tk.StringVar(value='url')
        defaults = load_job_defaults()
        self.destination = tk.StringVar(value=defaults['destination'])
        self.mode = tk.StringVar(value=defaults['mode'])
        self.stem_vars = {
            stem: tk.BooleanVar(value=stem in ('vocals', 'instrumental'))
            for stem in SELECTABLE_STEMS
        }
        self._stems_options: ttk.Frame | None = None
        self._trim_options: ttk.Frame | None = None
        self.audio_format = tk.StringVar(value=defaults['audio_format'])
        self.video_format = tk.StringVar(value=defaults['video_format'])
        self.fps = tk.StringVar(value=defaults['fps'])
        self.quality = tk.StringVar(value=defaults['quality'])
        self.mode_desc = tk.StringVar(value='')
        self._details_expanded = False
        self._last_av_mode = 'video'
        self._hovering_start = False
        self._start_button_color = ACCENT
        self._button_tween = Tween(self.after, self.after_cancel, duration_ms=100)
        self._flash_tween = Tween(self.after, self.after_cancel, duration_ms=200)
        self.authorized = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value='พร้อมเริ่มงาน')
        self.source_detail = tk.StringVar(value=source_summary(''))
        self.source_hint = tk.StringVar(value='เลือกไฟล์ หรือลากมาวางที่นี่')
        self.source_button_text = tk.StringVar(value='เลือกไฟล์')
        self.progress_text = tk.StringVar(value='0%')
        self._cancellation: CancellationToken | None = None
        self._closing = False
        self._active_source_kind = 'file'
        self._source_values = {'file': '', 'url': ''}
        self._progress_action = 'กำลังประมวลผล'
        self._input_widgets: list[ttk.Widget] = []
        self._setup_dialog: ToolSetupDialog | None = None
        self._ytdlp_checking = False
        self._app_update_checking = False
        self._recent_destinations: list[str] = []
        self._result_targets: list[Path] = []
        self._chime_var = tk.BooleanVar(value=defaults['chime_enabled'])
        self._auto_update_var = tk.BooleanVar(value=defaults['auto_update_check'])
        self._build()
        self._toast = ToastManager(self)
        self._drop_unregister = (
            register_drop_files(self, self._on_drop_files)
            if drop_files_supported() else None
        )
        self._bind_shortcuts()
        self.source.trace_add('write', self._on_source_changed)
        self.bind_all('<Control-KeyPress>', self._on_control_keypress, add='+')
        self.bind_all('<Shift-Insert>', self._on_paste_shortcut, add='+')
        self.after_idle(self.source_entry.focus_set)
        self.after(120, self._maybe_offer_tool_setup)
        self.after(3000, self._maybe_check_ytdlp_update)
        self.after(5000, self._maybe_check_app_update)
        self.protocol('WM_DELETE_WINDOW', self._on_close)

    def _create_icon(self) -> tk.PhotoImage:
        image = tk.PhotoImage(width=40, height=40)
        image.put(BG, to=(0, 0, 40, 40))
        for y in range(4, 36):
            image.put(ACCENT, to=(4, y, 36, y + 1))
        for y in range(12, 28):
            width = min(y - 11, 27 - y)
            image.put(TEXT, to=(16, y, 16 + width, y + 1))
        image.put(ACCENT_SOFT, to=(4, 0, 5, 40))
        image.put(ACCENT_SOFT, to=(35, 0, 36, 40))
        image.put(ACCENT_SOFT, to=(0, 4, 40, 5))
        image.put(ACCENT_SOFT, to=(0, 35, 40, 36))
        return image

    def _build(self) -> None:
        style = ttk.Style(self)
        self._style = style
        style.theme_use('clam')
        self.option_add('*TCombobox*Listbox.background', FIELD)
        self.option_add('*TCombobox*Listbox.foreground', TEXT)
        self.option_add('*TCombobox*Listbox.selectBackground', ACCENT)
        self.option_add('*TCombobox*Listbox.selectForeground', TEXT)

        # ── Base frames / labels ──────────────────────────────────────────────
        style.configure('TFrame', background=BG)
        style.configure('Card.TFrame', background=CARD)
        style.configure('CardBorder.TFrame', background=CARD, borderwidth=1, relief='solid')
        style.configure('TopBar.TFrame', background=TOP_BAR_BG)
        style.configure('Action.TFrame', background=ACTION_BG, borderwidth=0, relief='flat')

        style.configure('TLabel', background=BG, foreground=TEXT, font=(self.ui_font, FONT_SIZE_BASE))
        style.configure('Card.TLabel', background=CARD, foreground=TEXT, font=(self.ui_font, FONT_SIZE_BASE))
        style.configure('Muted.TLabel', background=BG, foreground=MUTED, font=(self.ui_font, FONT_SIZE_BASE))
        style.configure('CardMuted.TLabel', background=CARD, foreground=MUTED, font=(self.ui_font, FONT_SIZE_BASE))

        # Top bar title
        style.configure(
            'TopBarTitle.TLabel',
            background=TOP_BAR_BG,
            foreground=TEXT,
            font=(self.ui_font, FONT_SIZE_TOP, 'bold'),
        )
        style.configure(
            'TopBarMuted.TLabel',
            background=TOP_BAR_BG,
            foreground=MUTED,
            font=(self.ui_font, FONT_SIZE_SMALL),
        )

        # Section headers inside cards — "01  แหล่งสื่อ" style
        style.configure(
            'CardSection.TLabel',
            background=CARD,
            foreground=SECTION_ACCENT,
            font=(self.ui_font, FONT_SIZE_BASE, 'bold'),
        )
        style.configure(
            'CardSectionNum.TLabel',
            background=ACCENT,
            foreground=MENU_ACTIVE_FG,
            font=(self.ui_font, FONT_SIZE_SMALL, 'bold'),
            padding=(7, 3),
        )
        style.configure('Section.TLabel', background=CARD, foreground=TEXT, font=(self.ui_font, FONT_SIZE_BASE, 'bold'))

        # Action bar labels
        style.configure(
            'Action.TLabel',
            background=ACTION_BG,
            foreground=TEXT,
            font=(self.ui_font, FONT_SIZE_BASE, 'bold'),
        )
        style.configure(
            'ActionMuted.TLabel',
            background=ACTION_BG,
            foreground=MUTED,
            font=(self.ui_font, FONT_SIZE_BASE),
        )
        style.configure(
            'Action.TFrame', background=ACTION_BG,
        )

        # ── Modern section chrome ────────────────────────────────────────────
        style.configure(
            'SectionTitle.TLabel',
            background=BG,
            foreground=TEXT,
            font=(self.ui_font, FONT_SIZE_BASE, 'bold'),
        )
        style.configure(
            'ModeDesc.TLabel',
            background=BG,
            foreground=MUTED,
            font=(self.ui_font, FONT_SIZE_SMALL),
        )
        style.configure(
            'ErrorOnBg.TLabel',
            background=BG,
            foreground=ERROR,
            font=(self.ui_font, FONT_SIZE_SMALL),
        )
        style.configure(
            'Ghost.TButton',
            background=BG,
            foreground=MUTED,
            bordercolor=BG,
            lightcolor=BG,
            darkcolor=BG,
            font=(self.ui_font, FONT_SIZE_SMALL),
            padding=(10, 6),
        )
        style.map(
            'Ghost.TButton',
            background=[('active', SECONDARY_BG)],
            foreground=[('active', TEXT), ('disabled', DISABLED_FG)],
        )
        style.configure(
            'GhostLarge.TButton',
            background=BG,
            foreground=MUTED,
            bordercolor=BG,
            lightcolor=BG,
            darkcolor=BG,
            font=(self.ui_font, FONT_SIZE_TOP, 'bold'),
            padding=(10, 6),
        )
        style.map(
            'GhostLarge.TButton',
            background=[('active', SECONDARY_BG)],
            foreground=[('active', TEXT), ('disabled', DISABLED_FG)],
        )
        style.configure(
            'Side.TButton',
            background=TOP_BAR_BG,
            foreground=MUTED,
            bordercolor=TOP_BAR_BG,
            lightcolor=TOP_BAR_BG,
            darkcolor=TOP_BAR_BG,
            font=(self.ui_font, FONT_SIZE_BASE, 'bold'),
            padding=(12, 9),
            anchor='w',
        )
        style.map(
            'Side.TButton',
            background=[('active', SECONDARY_BG)],
            foreground=[('active', TEXT), ('disabled', DISABLED_FG)],
        )
        style.configure(
            'SideActive.TButton',
            background=ACCENT_SOFT,
            foreground=TEXT,
            bordercolor=ACCENT_SOFT,
            lightcolor=ACCENT_SOFT,
            darkcolor=ACCENT_SOFT,
            font=(self.ui_font, FONT_SIZE_BASE, 'bold'),
            padding=(12, 9),
            anchor='w',
        )
        style.map(
            'SideActive.TButton',
            background=[('active', ACCENT_SOFT)],
            foreground=[('disabled', DISABLED_FG)],
        )

        # ── Buttons ───────────────────────────────────────────────────────────
        style.configure(
            'TopBar.TButton',
            background=TOPBAR_BUTTON_BG,
            foreground=TOPBAR_BUTTON_FG,
            bordercolor=BORDER_LIGHT,
            lightcolor=BORDER_LIGHT,
            darkcolor=BORDER_LIGHT,
            font=(self.ui_font, FONT_SIZE_SMALL, 'bold'),
            padding=(12, 7),
        )
        style.map(
            'TopBar.TButton',
            background=[('active', TOPBAR_BUTTON_HOVER)],
            foreground=[('active', TEXT)],
        )
        style.configure(
            'TopBarAccent.TButton',
            background=ACCENT,
            foreground=MENU_ACTIVE_FG,
            bordercolor=ACCENT,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            font=(self.ui_font, FONT_SIZE_SMALL, 'bold'),
            padding=(12, 7),
        )
        style.map(
            'TopBarAccent.TButton',
            background=[('active', ACCENT_HOVER)],
            bordercolor=[('active', ACCENT_HOVER)],
        )
        style.configure(
            'Secondary.TButton',
            background=SECONDARY_BG,
            foreground=TEXT,
            bordercolor=SECONDARY_BORDER,
            lightcolor=SECONDARY_BORDER,
            darkcolor=SECONDARY_BORDER,
            font=(self.ui_font, FONT_SIZE_BASE, 'bold'),
            padding=(16, 10),
        )
        style.map(
            'Secondary.TButton',
            background=[('active', SECONDARY_HOVER), ('disabled', DISABLED_BG)],
            foreground=[('disabled', DISABLED_FG)],
            bordercolor=[('focus', ACCENT), ('disabled', SECONDARY_BORDER)],
        )
        style.configure(
            'Accent.TButton',
            background=ACCENT,
            foreground=TEXT,
            bordercolor=ACCENT,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            font=(self.ui_font, FONT_SIZE_BASE + 1, 'bold'),
            padding=(20, 14),
        )
        style.map(
            'Accent.TButton',
            background=[('active', ACCENT_HOVER), ('disabled', ACCENT_DISABLED_BG)],
            bordercolor=[('active', ACCENT_HOVER), ('disabled', ACCENT_DISABLED_BG)],
            foreground=[('disabled', ACCENT_DISABLED_FG)],
        )
        # Primary dialog button (dialogs use their own accent style).
        style.configure('DialogAccent.TButton',
            background=ACCENT,
            foreground=TEXT,
            bordercolor=ACCENT,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            font=(self.ui_font, FONT_SIZE_BASE, 'bold'),
            padding=(16, 9),
        )
        style.map(
            'DialogAccent.TButton',
            background=[('active', ACCENT_HOVER), ('disabled', ACCENT_DISABLED_BG)],
            bordercolor=[('active', ACCENT_HOVER), ('disabled', ACCENT_DISABLED_BG)],
            foreground=[('disabled', ACCENT_DISABLED_FG)],
        )
        # ── Form controls ─────────────────────────────────────────────────────
        style.layout(
            'Segment.TRadiobutton',
            [
                (
                    'Radiobutton.padding',
                    {
                        'sticky': 'nswe',
                        'children': [('Radiobutton.label', {'sticky': 'nswe'})],
                    },
                )
            ],
        )
        style.configure(
            'Segment.TRadiobutton',
            background=FIELD,
            foreground=MUTED,
            font=(self.ui_font, FONT_SIZE_BASE, 'bold'),
            padding=(14, 10),
            anchor='center',
        )
        style.map(
            'Segment.TRadiobutton',
            background=[('selected', ACCENT), ('active', SECONDARY_HOVER), ('disabled', DISABLED_BG)],
            foreground=[('selected', TEXT), ('active', TEXT), ('disabled', DISABLED_FG)],
        )

        # ── Progress / separators ─────────────────────────────────────────────
        style.configure(
            'Clipora.Horizontal.TProgressbar',
            background=ACCENT,
            troughcolor=PROGRESS_TROUGH,
            bordercolor=PROGRESS_TROUGH,
            lightcolor=ACCENT_GLOW,
            darkcolor=ACCENT,
            thickness=6,
        )
        style.configure('Card.TSeparator', background=BORDER)

        # ── Misc widget styles ────────────────────────────────────────────────
        style.configure('Error.TLabel', background=CARD, foreground=ERROR, font=(self.ui_font, FONT_SIZE_SMALL))
        style.configure('Toast.TFrame', background=TOAST_BG, borderwidth=1, relief='solid', bordercolor=ACCENT)
        style.configure(
            'Heading.TLabel',
            background=BG,
            foreground=TEXT,
            font=(self.ui_font, FONT_SIZE_TITLE, 'bold'),
        )

        # ── Root layout ───────────────────────────────────────────────────────
        # Col 0 = collapsible sidebar, col 1 = top bar + content + action + footer
        # Row 0 = top bar, row 1 = scrollable content, row 2 = action bar, row 3 = footer
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=0)
        self.rowconfigure(3, weight=0)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)

        # ── Sidebar ─────────────────────────────────────────────────────────────
        self._sidebar = ttk.Frame(self, style='TopBar.TFrame', padding=(12, 12, 12, 12))
        self._sidebar.grid(row=0, column=0, rowspan=4, sticky='nsew')
        self._sidebar_visible = True
        self._view = 'job'
        self._view_buttons: dict[str, ttk.Button] = {}

        ttk.Label(self._sidebar, text='เมนู', style='TopBarMuted.TLabel').pack(
            anchor='w', pady=(0, 8)
        )
        for value, label in (('job', 'งานปัจจุบัน'), ('history', 'ประวัติ')):
            button = ttk.Button(
                self._sidebar, text=label, style='Side.TButton',
                command=lambda v=value: self._show_view(v),
            )
            button.pack(fill='x', pady=(0, 6))
            self._view_buttons[value] = button
        ttk.Separator(self._sidebar, orient='horizontal').pack(fill='x', pady=(6, 12))
        for label, command in (
            ('เครื่องมือ (Ctrl+T)', lambda: self._open_tool_setup(repair_mode=True)),
            ('อัปเดต yt-dlp (Ctrl+U)', lambda: self._check_ytdlp_update(auto=False)),
            ('ตรวจอัปเดต Clipora...', lambda: self._check_app_update(auto=False)),
        ):
            ttk.Button(
                self._sidebar, text=label, style='Ghost.TButton', command=command,
            ).pack(fill='x', anchor='w', pady=(0, 2))
        ttk.Separator(self._sidebar, orient='horizontal').pack(fill='x', pady=(12, 12))
        for label, command in (
            ('คู่มือ (F1)', lambda: webbrowser.open(
                'https://github.com/ertyu007/media-toolkit-Open-source/blob/main/docs/USER_GUIDE.md')),
            ('รายงานปัญหา', lambda: webbrowser.open(
                'https://github.com/ertyu007/media-toolkit-Open-source/issues')),
            ('สนับสนุนโครงการ', self._open_donate_dialog),
        ):
            ttk.Button(
                self._sidebar, text=label, style='Ghost.TButton', command=command,
            ).pack(fill='x', anchor='w', pady=(0, 2))
        ttk.Frame(self._sidebar, style='TopBar.TFrame').pack(fill='both', expand=True)
        ttk.Separator(self._sidebar, orient='horizontal').pack(fill='x', pady=(0, 8))
        ttk.Button(
            self._sidebar, text='⚙ ตั้งค่า', style='Ghost.TButton',
            command=self._open_settings,
        ).pack(fill='x', anchor='w')

        # ── Top bar ───────────────────────────────────────────────────────────
        topbar = ttk.Frame(self, style='TopBar.TFrame', padding=(12, 10, 16, 10))
        topbar.grid(row=0, column=1, sticky='ew')
        topbar.columnconfigure(2, weight=1)

        self._sidebar_toggle = ttk.Button(
            topbar, text='«', style='GhostLarge.TButton', width=4,
            command=self._toggle_sidebar,
        )
        self._sidebar_toggle.grid(row=0, column=0, padx=(0, 6))
        self._sync_sidebar_toggle()

        # ── Top bar ───────────────────────────────────────────────────────────
        topbar = ttk.Frame(self, style='TopBar.TFrame', padding=(20, 10, 16, 10))
        ttk.Label(topbar, image=self._icon, background=TOP_BAR_BG).grid(
            row=0, column=1, padx=(0, 10), pady=2,
        )

        brand_col = ttk.Frame(topbar, style='TopBar.TFrame')
        brand_col.grid(row=0, column=2, sticky='w')
        ttk.Label(brand_col, text='Clipora', style='TopBarTitle.TLabel').pack(side='left')
        ttk.Label(
            brand_col,
            text=f'  v{__version__}',
            style='TopBarMuted.TLabel',
        ).pack(side='left')

        # Thin separator under topbar
        tk.Frame(self, bg=BORDER, height=1).grid(row=0, column=1, sticky='sew')

        # ── Main: single-column scrollable content (mode + source-kind
        # controls in content are the single source of truth)
        main = ttk.Frame(self, style='TFrame')
        main.grid(row=1, column=1, sticky='nsew')
        self._main_view = main
        main.rowconfigure(0, weight=1)
        main.columnconfigure(0, weight=1)

        # ── Scrollable content area ───────────────────────────────────────────
        content_outer = ttk.Frame(main, style='TFrame')
        content_outer.grid(row=0, column=0, sticky='nsew')
        content_outer.rowconfigure(0, weight=1)
        content_outer.columnconfigure(0, weight=1)

        self.card_canvas = tk.Canvas(
            content_outer, bg=BG, highlightthickness=0, borderwidth=0,
        )
        self.card_scrollbar = ttk.Scrollbar(
            content_outer, orient='vertical', command=self.card_canvas.yview,
        )
        self.card_canvas.grid(row=0, column=0, sticky='nsew')
        self.card_scrollbar.grid(row=0, column=1, sticky='ns')

        # Inner content frame — holds the hero and sections
        content = ttk.Frame(self.card_canvas, style='TFrame', padding=(24, 20, 24, 20))
        content_window = self.card_canvas.create_window((0, 0), window=content, anchor='nw')
        content.columnconfigure(0, weight=1)

        def _on_card_configure(_event: tk.Event) -> None:
            self.card_canvas.configure(scrollregion=self.card_canvas.bbox('all'))

        def _on_canvas_configure(_event: tk.Event) -> None:
            self.card_canvas.itemconfigure(content_window, width=self.card_canvas.winfo_width())

        def _on_scroll_command(first: str, last: str) -> None:
            self.card_scrollbar.set(first, last)
            if float(first) <= 0.0 and float(last) >= 1.0:
                self.card_scrollbar.grid_remove()
            else:
                self.card_scrollbar.grid()

        def _on_mousewheel(event: tk.Event) -> None:
            widget = self.winfo_containing(event.x_root, event.y_root)
            if widget is not None and isinstance(widget, ttk.Combobox):
                return
            delta = int(getattr(event, 'delta', 0))
            if delta:
                self.card_canvas.yview_scroll(int(-delta / 120), 'units')

        content.bind('<Configure>', _on_card_configure)
        self.card_canvas.bind('<Configure>', _on_canvas_configure)
        self.card_canvas.configure(yscrollcommand=_on_scroll_command)
        self.card_canvas.bind('<Enter>', lambda _e: self.bind_all('<MouseWheel>', _on_mousewheel))
        self.card_canvas.bind('<Leave>', lambda _e: self.unbind_all('<MouseWheel>'))

        # ── Helper: flat section with a small title ───────────────────────────
        # (Tk has no native border-radius; a canvas-drawn rounded card
        # rendered with artifacts inside the scroll area, so sections stay
        # flat and stable.)
        def _make_section(parent: ttk.Frame, title: str, row: int) -> tuple[ttk.Frame, ttk.Frame]:
            """Create a flat section; returns (body_frame, header_frame)."""
            section = ttk.Frame(parent, style='TFrame')
            section.grid(row=row, column=0, sticky='ew', pady=(0, 18))
            section.columnconfigure(0, weight=1)
            header = ttk.Frame(section, style='TFrame')
            header.grid(row=0, column=0, sticky='ew', pady=(0, 10))
            header.columnconfigure(0, weight=1)
            ttk.Label(header, text=title, style='SectionTitle.TLabel').grid(
                row=0, column=0, sticky='w',
            )
            body = ttk.Frame(section, style='TFrame')
            body.grid(row=1, column=0, sticky='ew')
            body.columnconfigure(0, weight=1)
            return body, header

        def _divider(parent: ttk.Frame, row: int) -> None:
            tk.Frame(parent, bg=BORDER, height=1).grid(
                row=row, column=0, sticky='ew', pady=(0, 18),
            )

        # ── Mode hero ─────────────────────────────────────────────────────────
        hero = ttk.Frame(content, style='TFrame')
        hero.grid(row=0, column=0, sticky='ew', pady=(0, 18))
        hero.columnconfigure(0, weight=1)
        self._mode_control = SegmentedControl(
            hero,
            options=[
                ('audio', 'แยกเสียง'),
                ('video', 'แปลงเป็นวิดีโอ'),
                ('stems', 'แยกสเต็มเสียง'),
            ],
            variable=self.mode,
            command=self._on_mode_change,
        )
        self._mode_control.grid(row=0, column=0, sticky='ew')
        ttk.Label(
            hero, textvariable=self.mode_desc, style='ModeDesc.TLabel',
        ).grid(row=1, column=0, sticky='w', pady=(6, 0))

        # ── Section 1: Source ─────────────────────────────────────────────────
        source_body, source_hdr = _make_section(content, 'แหล่งสื่อ', row=1)

        # Source type toggle — right side of header (stems view only)
        source_kind_frame = ttk.Frame(source_hdr, style='TFrame')
        source_kind_frame.grid(row=0, column=2, sticky='e')
        self._source_kind_frame = source_kind_frame
        self.file_source_radio = ttk.Radiobutton(
            source_kind_frame, text='ไฟล์', variable=self.input_kind,
            value='file', command=self._sync_source_kind, style='Segment.TRadiobutton',
        )
        self.file_source_radio.pack(side='left')
        self.url_source_radio = ttk.Radiobutton(
            source_kind_frame, text='URL', variable=self.input_kind,
            value='url', command=self._sync_source_kind, style='Segment.TRadiobutton',
        )
        self.url_source_radio.pack(side='left', padx=(3, 0))

        # Inline error
        self._source_error = InlineError(
            source_body, frame_style='TFrame', label_style='ErrorOnBg.TLabel',
        )
        self._source_error.grid(row=0, column=0, sticky='ew', pady=(0, 6))
        self._source_error.grid_remove()

        # Input + button row
        source_row = ttk.Frame(source_body, style='TFrame')
        source_row.grid(row=1, column=0, sticky='ew')
        source_row.columnconfigure(0, weight=1)
        self.source_entry = RoundedEntry(source_row, textvariable=self.source)
        self.source_entry.grid(row=0, column=0, sticky='ew', padx=(0, 8))
        self.source_entry.bind('<FocusOut>', lambda _e: self._validate_source_or_hide())
        self.source_button = RoundedButton(
            source_row, textvariable=self.source_button_text,
            command=self._source_action, width=16,
        )
        self.source_button.grid(row=0, column=1)

        # Source detail + rights line
        ttk.Label(
            source_body, textvariable=self.source_detail, style='ModeDesc.TLabel',
        ).grid(row=2, column=0, sticky='w', pady=(8, 0))

        link_font = (self.ui_font, 9, 'underline')
        self.rights_row = ttk.Frame(source_body, style='TFrame')
        self.rights_row.grid(row=3, column=0, sticky='w', pady=(8, 0))
        self.rights_check = Switch(
            self.rights_row, text='ฉันยืนยันว่าอ่านและยอมรับ', variable=self.authorized,
        )
        self.rights_check.pack(side='left')
        self.disclaimer_link = tk.Label(
            self.rights_row, text='คำปฏิเสธด้านลิขสิทธิ์',
            bg=BG, fg=ACCENT, font=link_font, cursor='hand2',
        )
        self.disclaimer_link.pack(side='left')
        self.disclaimer_link.bind('<Button-1>', lambda _event: self._open_disclaimer())
        ttk.Label(
            self.rights_row, text='แล้ว และจะไม่ดาวน์โหลดเนื้อหาที่มีลิขสิทธิ์',
            style='ModeDesc.TLabel',
        ).pack(side='left')
        self.rights_row.grid_remove()

        # Link preview card (URL mode only, filled by a debounced worker)
        self._preview_frame = ttk.Frame(source_body, style='Card.TFrame')
        self._preview_frame.grid(row=4, column=0, sticky='ew', pady=(10, 0))
        self._preview_thumb = ttk.Label(self._preview_frame, style='Card.TLabel')
        self._preview_thumb.pack(side='left', padx=(0, 12))
        preview_text = ttk.Frame(self._preview_frame, style='Card.TFrame')
        preview_text.pack(side='left', fill='both', expand=True)
        self._preview_title = ttk.Label(
            preview_text, text='', style='Card.TLabel',
            font=(self.ui_font, FONT_SIZE_BASE, 'bold'), wraplength=430,
            justify='left',
        )
        self._preview_title.pack(anchor='w')
        self._preview_meta = ttk.Label(
            preview_text, text='', style='CardMuted.TLabel',
            font=(self.ui_font, FONT_SIZE_SMALL), wraplength=430,
            justify='left',
        )
        self._preview_meta.pack(anchor='w', pady=(2, 0))
        self._preview_frame.grid_remove()
        self._preview_gen = 0
        self._preview_after = None
        self._preview_token = None
        self._preview_url = ''
        self._preview_image = None
        self._preview_tmp: tempfile.TemporaryDirectory | None = None

        _divider(content, row=2)

        # ── Section 2: Destination ────────────────────────────────────────────
        dest_body, _ = _make_section(content, 'บันทึกที่', row=3)

        self._dest_error = InlineError(
            dest_body, frame_style='TFrame', label_style='ErrorOnBg.TLabel',
        )
        self._dest_error.grid(row=0, column=0, sticky='ew', pady=(0, 6))
        self._dest_error.grid_remove()

        dest_row = ttk.Frame(dest_body, style='TFrame')
        dest_row.grid(row=1, column=0, sticky='ew')
        dest_row.columnconfigure(0, weight=1)
        self.destination_entry = RoundedEntry(
            dest_row, textvariable=self.destination,
        )
        self.destination_entry.grid(row=0, column=0, sticky='ew', padx=(0, 8))
        self.destination_entry.bind('<FocusOut>', lambda _e: self._validate_destination_or_hide())
        self.destination_entry.bind('<Button-1>', self._show_destination_history)
        self.destination_button = RoundedButton(
            dest_row, text='เลือกโฟลเดอร์',
            command=self._choose_destination, width=14,
        )
        self.destination_button.grid(row=0, column=1)

        _divider(content, row=4)

        # ── Section 3: Format / Options ───────────────────────────────────────
        fmt_body, _ = _make_section(content, 'รูปแบบผลลัพธ์', row=5)

        # Format dropdowns
        result_options = ttk.Frame(fmt_body, style='TFrame')
        result_options.grid(row=0, column=0, sticky='ew')
        result_options.columnconfigure(1, weight=1)
        self.option_label = ttk.Label(result_options, style='ModeDesc.TLabel')
        self.option_label.grid(row=0, column=0, padx=(0, 10), sticky='e')
        self.format_box = RoundedCombobox(
            result_options, textvariable=self.audio_format, values=AUDIO_FORMAT_LABELS,
            width=12,
        )
        self.format_box.grid(row=0, column=1, sticky='w')
        self.video_format_box = RoundedCombobox(
            result_options, textvariable=self.video_format, values=VIDEO_FORMAT_LABELS,
            width=30,
        )
        self.video_format_box.grid(row=0, column=1, sticky='w')

        # Stem picker (stems mode only)
        self._stems_options = ttk.Frame(fmt_body, style='TFrame')
        self._stems_options.grid(row=1, column=0, sticky='ew', pady=(12, 0))
        self._stems_options.columnconfigure(0, weight=1)
        ttk.Label(self._stems_options, text='สเต็มที่ต้องการ', style='ModeDesc.TLabel').grid(
            row=0, column=0, sticky='w',
        )
        self._stem_check_widgets: list[Switch] = []
        stem_row = ttk.Frame(self._stems_options, style='TFrame')
        stem_row.grid(row=1, column=0, sticky='w', pady=(8, 0))
        for stem in SELECTABLE_STEMS:
            check = Switch(
                stem_row, text=STEM_LABELS[stem],
                variable=self.stem_vars[stem],
            )
            check.pack(side='left', padx=(0, 14))
            self._stem_check_widgets.append(check)
        self._stems_options.grid_remove()

        # Collapsible extra options (quality / fps / trim)
        self.details_toggle = ttk.Button(
            fmt_body, text='▸ ตัวเลือกเพิ่มเติม', style='Ghost.TButton',
            command=self._toggle_details,
        )
        self.details_toggle.grid(row=2, column=0, sticky='w', pady=(12, 0))

        self._details_box = ttk.Frame(fmt_body, style='TFrame')
        self._details_box.grid(row=3, column=0, sticky='ew', pady=(4, 0))
        self.quality_label = ttk.Label(self._details_box, text='คุณภาพ', style='ModeDesc.TLabel')
        self.quality_label.grid(row=0, column=0, padx=(0, 8), sticky='e')
        self.quality_box = RoundedCombobox(
            self._details_box, textvariable=self.quality, values=VIDEO_QUALITY_PRESETS,
            width=12,
        )
        self.quality_box.grid(row=0, column=1, sticky='w')
        self.fps_label = ttk.Label(self._details_box, text='เฟรมเรต', style='ModeDesc.TLabel')
        self.fps_label.grid(row=0, column=2, padx=(16, 8), sticky='e')
        self.fps_box = RoundedCombobox(
            self._details_box, textvariable=self.fps, values=FPS_LABELS,
            width=10,
        )
        self.fps_box.grid(row=0, column=3, sticky='w')

        # Trim row for local file jobs (audio/video modes only)
        self._trim_options = ttk.Frame(self._details_box, style='TFrame')
        self._trim_options.grid(row=1, column=0, columnspan=4, sticky='ew', pady=(12, 0))
        ttk.Label(self._trim_options, text='เริ่ม (วินาที/HH:MM:SS)', style='ModeDesc.TLabel').grid(
            row=0, column=0, padx=(0, 8), sticky='e',
        )
        self.start_time_entry = RoundedEntry(self._trim_options, width=12)
        self.start_time_entry.grid(row=0, column=1, sticky='w')
        ttk.Label(self._trim_options, text='ระยะเวลา (เว้นว่าง = ทั้งหมด)', style='ModeDesc.TLabel').grid(
            row=0, column=2, padx=(16, 8), sticky='e',
        )
        self.duration_entry = RoundedEntry(self._trim_options, width=12)
        self.duration_entry.grid(row=0, column=3, sticky='w')
        self._details_box.grid_remove()

        # ── Action dock (sticky bottom) ─────────────────────────────────────────
        action_bar = ttk.Frame(self, style='Action.TFrame', padding=(24, 12, 24, 12))
        self._action_bar = action_bar
        action_bar.grid(row=2, column=1, sticky='ew')
        action_bar.columnconfigure(0, weight=1)

        # Primary action button — full-width pill, on top for prominence.
        # Hover/press/success colors are tweened via set_fill (see Motion).
        self._start_accent = True
        self.start_button = RoundedButton(
            action_bar, text='เริ่มแยกเสียง', command=self._start,
            fill=ACCENT, hover_fill=ACCENT_GLOW, height=52, font_size=12,
            hover_internal=False,
        )
        self.start_button.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        self.start_button.bind('<Enter>', self._on_start_hover_in, add='+')
        self.start_button.bind('<Leave>', self._on_start_hover_out, add='+')
        self.start_button.bind('<ButtonPress-1>', self._on_start_press, add='+')
        self.start_button.bind('<ButtonRelease-1>', self._on_start_release, add='+')

        # Progress row
        prog_row = ttk.Frame(action_bar, style='Action.TFrame')
        prog_row.grid(row=1, column=0, sticky='ew', pady=(0, 6))
        prog_row.columnconfigure(0, weight=1)
        ttk.Label(prog_row, textvariable=self.status, style='Action.TLabel').grid(
            row=0, column=0, sticky='w',
        )
        ttk.Label(prog_row, textvariable=self.progress_text, style='ActionMuted.TLabel').grid(
            row=0, column=1, sticky='e',
        )

        self.progress = RainbowBar(action_bar, height=14)
        self.progress.grid(row=2, column=0, sticky='ew')

        # Result panel — shown after a job completes
        self.result_panel = ttk.Frame(action_bar, style='Action.TFrame')
        self.result_panel.grid(row=3, column=0, sticky='ew', pady=(10, 0))
        self.result_panel.columnconfigure(0, weight=1)
        self.result_summary = ttk.Label(
            self.result_panel, text='', style='Action.TLabel', wraplength=560,
        )
        self.result_summary.grid(row=0, column=0, sticky='w')
        self.result_size = ttk.Label(
            self.result_panel, text='', style='ActionMuted.TLabel',
        )
        self.result_size.grid(row=0, column=1, sticky='e', padx=(10, 0))
        result_actions = ttk.Frame(self.result_panel, style='Action.TFrame')
        result_actions.grid(row=1, column=0, columnspan=2, sticky='w', pady=(8, 0))
        self.open_folder_btn = RoundedButton(
            result_actions, text='เปิดโฟลเดอร์',
            command=self._open_result_folder, width=14,
        )
        self.open_folder_btn.pack(side='left', padx=(0, 8))
        self.open_file_btn = RoundedButton(
            result_actions, text='เปิดไฟล์',
            command=self._open_result_file, width=14,
        )
        self.open_file_btn.pack(side='left')
        self.result_panel.grid_remove()

        # ── History view (same cell as content + action dock) ───────────────
        self._history_view = ttk.Frame(self, style='TFrame')
        self._history_view.grid(row=1, column=1, rowspan=2, sticky='nsew')
        self._history_view.rowconfigure(0, weight=1)
        self._history_view.columnconfigure(0, weight=1)
        self._history_panel = HistoryPanel(self._history_view)
        self._history_panel.grid(row=0, column=0, sticky='nsew')
        self._history_view.grid_remove()

        # ── Footer ─────────────────────────────────────────────────────────────
        footer = ttk.Frame(self, style='TFrame', padding=(0, 6, 0, 8))
        footer.grid(row=3, column=1, sticky='ew')
        ttk.Label(
            footer,
            text='create by ertyu007',
            style='ModeDesc.TLabel',
            anchor='center',
        ).grid(row=0, column=0, sticky='ew')

        # ── Input widget list (for enable/disable during job) ──────────────────
        self._input_widgets = [
            self.file_source_radio,
            self.url_source_radio,
            self.source_entry,
            self.source_button,
            self.rights_check,
            self.destination_entry,
            self.destination_button,
            self.format_box,
            self.video_format_box,
            self.details_toggle,
            self.quality_box,
            self.fps_box,
            self.start_time_entry,
            self.duration_entry,
            *self._stem_check_widgets,
        ]
        self._sync_source_kind()
        self._sync_options()
        self._show_view('job')

    def _maybe_offer_tool_setup(self) -> None:
        if self._first_run_setup and missing_required_tools():
            self._open_tool_setup(repair_mode=False, first_run=True)
        else:
            self.deiconify()

    def _open_tool_setup(
        self,
        repair_mode: bool = False,
        first_run: bool = False,
        separator: bool = False,
    ) -> None:
        if self._cancellation is not None:
            messagebox.showwarning(
                'กำลังทำงาน',
                'รอให้งานปัจจุบันเสร็จหรือยกเลิกก่อนติดตั้งและซ่อมเครื่องมือ',
                parent=self,
            )
            return
        if self._setup_dialog is not None:
            try:
                if self._setup_dialog.winfo_exists():
                    self._setup_dialog.deiconify()
                    self._setup_dialog.lift()
                    self._setup_dialog.focus_force()
                    return
            except tk.TclError:
                pass
        self._setup_dialog = ToolSetupDialog(
            self,
            repair_mode=repair_mode,
            first_run=first_run,
            separator=separator,
            on_ready=self._tools_ready,
            on_cancelled=self._setup_cancelled if first_run else None,
        )

    def _tools_ready(self) -> None:
        self._first_run_setup = False
        self.deiconify()
        self.lift()
        self.status.set('พร้อมเริ่มงาน')
        self.after_idle(self.source_entry.focus_set)

    def _setup_cancelled(self) -> None:
        if self._first_run_setup:
            self.destroy()

    def _maybe_check_ytdlp_update(self) -> None:
        if self._auto_update_var.get():
            self._check_ytdlp_update(auto=True)

    def _check_ytdlp_update(self, auto: bool = False) -> None:
        if self._ytdlp_checking:
            return
        if self._cancellation is not None:
            if not auto:
                messagebox.showwarning(
                    'กำลังทำงาน',
                    'รอให้งานปัจจุบันเสร็จหรือยกเลิกก่อนอัปเดต yt-dlp',
                    parent=self,
                )
            return
        if self._setup_dialog is not None:
            try:
                if self._setup_dialog.winfo_exists():
                    if not auto:
                        messagebox.showinfo(
                            'เครื่องมือ',
                            'ปิดหน้าต่างติดตั้งเครื่องมือก่อนตรวจสอบอัปเดต yt-dlp',
                            parent=self,
                        )
                    return
            except tk.TclError:
                pass
        self._ytdlp_checking = True
        threading.Thread(target=self._ytdlp_check_worker, args=(auto,), daemon=True).start()

    def _ytdlp_check_worker(self, auto: bool) -> None:
        installed: str | None = None
        latest = ''
        needs_update = False
        error = ''
        try:
            installed = installed_ytdlp_version()
            latest = latest_ytdlp_version()
            needs_update = is_newer_available(latest, installed)
        except (YtDlpUpdateError, OSError) as exc:
            error = str(exc)
        self.after(0, self._ytdlp_check_done, auto, installed, latest, needs_update, error)

    def _ytdlp_check_done(
        self,
        auto: bool,
        installed: str | None,
        latest: str,
        needs_update: bool,
        error: str,
    ) -> None:
        self._ytdlp_checking = False
        if error:
            if not auto:
                messagebox.showerror('ตรวจสอบอัปเดตไม่สำเร็จ', error, parent=self)
            return
        if installed is None:
            if not auto:
                messagebox.showinfo(
                    'อัปเดต yt-dlp',
                    'ยังไม่พบ yt-dlp ที่ติดตั้งไว้\nกดปุ่ม "เครื่องมือ" เพื่อติดตั้งก่อน',
                    parent=self,
                )
            return
        if not needs_update:
            if not auto:
                messagebox.showinfo(
                    'อัปเดต yt-dlp',
                    f'yt-dlp เป็นเวอร์ชันล่าสุดแล้ว ({latest})',
                    parent=self,
                )
            return
        if auto:
            self._start_ytdlp_update(latest)
            return
        if not messagebox.askyesno(
            'อัปเดต yt-dlp',
            f'พบ yt-dlp เวอร์ชันใหม่ {latest}'
            + f'\nเวอร์ชันที่ติดตั้ง: {installed}'
            + '\n\nต้องการอัปเดตตอนนี้หรือไม่?',
            parent=self,
        ):
            return
        self._start_ytdlp_update(latest)

    def _start_ytdlp_update(self, latest: str) -> None:
        cancellation = CancellationToken()
        self._begin_job(cancellation, f'กำลังอัปเดต yt-dlp เป็น {latest}…', 'กำลังอัปเดต yt-dlp')
        threading.Thread(
            target=self._ytdlp_update_worker,
            args=(latest, cancellation),
            daemon=True,
        ).start()

    def _ytdlp_update_worker(self, latest: str, cancellation: CancellationToken) -> None:
        error = ''
        try:
            update_ytdlp(
                lambda value, message: self.after(0, self._set_progress, value, cancellation)
                and self.after(0, self.status.set, message),
                lambda: cancellation.cancelled,
            )
        except (YtDlpUpdateError, DependencyInstallError, OSError) as exc:
            error = str(exc)
        if cancellation.cancelled:
            self.after(0, self._cancelled, cancellation)
            return
        self.after(0, self._ytdlp_update_done, latest, error, cancellation)

    def _ytdlp_update_done(
        self,
        latest: str,
        error: str,
        cancellation: CancellationToken,
    ) -> None:
        if not self._finish_job(cancellation):
            return
        if error:
            self.status.set('อัปเดต yt-dlp ไม่สำเร็จ')
            messagebox.showerror('อัปเดตไม่สำเร็จ', error[-1200:], parent=self)
            return
        self.progress['value'] = 100
        self.progress_text.set('100%')
        self.status.set(f'อัปเดต yt-dlp เป็น {latest} แล้ว')
        messagebox.showinfo('สำเร็จ', f'อัปเดต yt-dlp เป็น {latest} เรียบร้อย', parent=self)

    def _maybe_check_app_update(self) -> None:
        if self._auto_update_var.get():
            self._check_app_update(auto=True)

    def _check_app_update(self, auto: bool = False) -> None:
        if self._app_update_checking:
            return
        if self._cancellation is not None:
            if not auto:
                messagebox.showwarning(
                    'กำลังทำงาน',
                    'รอให้งานปัจจุบันเสร็จหรือยกเลิกก่อนตรวจสอบอัปเดต',
                    parent=self,
                )
            return
        self._app_update_checking = True
        threading.Thread(target=self._app_update_check_worker, args=(auto,), daemon=True).start()

    def _app_update_check_worker(self, auto: bool) -> None:
        release_info: AppReleaseInfo | None = None
        error: str = ''
        try:
            release_info = fetch_latest_app_release()
        except (AppUpdateError, OSError) as exc:
            error = str(exc)
        self.after(0, self._app_update_check_done, auto, release_info, error)

    def _app_update_check_done(
        self,
        auto: bool,
        release_info: AppReleaseInfo | None,
        error: str,
    ) -> None:
        self._app_update_checking = False
        if error:
            if not auto:
                messagebox.showerror('ตรวจหาการอัปเดตไม่สำเร็จ', error, parent=self)
            return

        if release_info is None or not is_app_update_available(release_info.version, __version__):
            if not auto:
                if hasattr(self, '_toast'):
                    self._toast.show(f'คุณกำลังใช้ Clipora เวอร์ชันล่าสุดแล้ว (v{__version__})', 'success')
                else:
                    messagebox.showinfo('อัปเดต', f'คุณกำลังใช้ Clipora เวอร์ชันล่าสุดแล้ว (v{__version__})', parent=self)
            return

        # Newer version available
        if auto:
            skipped = get_skipped_version()
            if skipped == release_info.version:
                return

        AppUpdateDialog(self, release_info)

    def _open_disclaimer(self) -> None:
        DisclaimerDialog(self)

    def _open_donate_dialog(self) -> None:
        DonateDialog(self)

    def _uninstall_app(self) -> None:
        """Launch the Inno uninstaller (installed build) or open Apps settings."""
        if self._cancellation is not None:
            messagebox.showwarning(
                'กำลังทำงาน',
                'รอให้งานปัจจุบันเสร็จหรือยกเลิกก่อนถอนการติดตั้ง',
                parent=self,
            )
            return
        if getattr(sys, 'frozen', False):
            try:
                app_dir = Path(sys.executable).resolve().parent
            except OSError:
                app_dir = None
            uninstaller = find_clipora_uninstaller(app_dir) if app_dir else None
            if uninstaller is None:
                messagebox.showinfo(
                    'ถอนการติดตั้ง',
                    'ไม่พบตัวถอนการติดตั้ง (unins000.exe) ข้างโปรแกรม',
                    parent=self,
                )
                return
            if messagebox.askyesno(
                'ถอนการติดตั้ง Clipora หมดจด',
                'ปิด Clipora แล้วเปิดตัวถอนการติดตั้ง?\n\n'
                '• ลบโปรแกรม + เครื่องมือที่โหลดมา\n'
                '• ลบตั้งค่า/ประวัติในเครื่องด้วย\n'
                '• ไฟล์งานของคุณไม่ถูกลบ',
                parent=self,
            ):
                try:
                    subprocess.Popen([str(uninstaller)])
                except OSError as exc:
                    messagebox.showerror(
                        'เปิดตัวถอนการติดตั้งไม่สำเร็จ', str(exc), parent=self)
                    return
                self.destroy()
            return
        opener = getattr(os, 'startfile', None)
        try:
            if opener is None:
                raise OSError('no startfile')
            opener('ms-settings:appsfeatures')
        except OSError:
            messagebox.showinfo(
                'ถอนการติดตั้ง',
                'รันจากซอร์สโค้ด: ลบโฟลเดอร์โปรเจกต์ได้เลย (ไม่มีอะไรติดตั้งเพิ่ม)',
                parent=self,
            )

    def _open_history(self) -> None:
        self._show_view('history')

    def _open_settings(self) -> None:
        from .settings_ui import SettingsDialog
        try:
            dialog = SettingsDialog(
                self,
                initial={
                    'theme': THEME_NAME,
                    'chime': self._chime_var.get(),
                    'auto_update': self._auto_update_var.get(),
                    'destination': self.destination.get(),
                    'mode': self.mode.get(),
                    'audio_format': self.audio_format.get(),
                    'video_format': self.video_format.get(),
                    'quality': self.quality.get(),
                    'fps': self.fps.get(),
                    'audio_formats': AUDIO_FORMAT_LABELS,
                    'video_formats': VIDEO_FORMAT_LABELS,
                    'qualities': VIDEO_QUALITY_PRESETS,
                    'fps_options': FPS_LABELS,
                },
                version=__version__,
                on_uninstall=self._uninstall_app,
            )
            self.wait_window(dialog)
            result = dialog.result
        except tk.TclError:
            return
        if result:
            self._apply_settings(result)

    def _apply_settings(self, data: dict) -> None:
        try:
            current = load_settings()
        except Exception:
            current = {}
        if not isinstance(current, dict):
            current = {}
        current.pop('auto_debug', None)  # removed setting; do not persist it
        current.update({
            'theme': data.get('theme', THEME_NAME),
            'chime_enabled': bool(data.get('chime', True)),
            'auto_update_check': bool(data.get('auto_update', True)),
            'destination': data.get('destination', ''),
            'mode': data.get('mode', 'video'),
            'audio_format': data.get('audio_format', 'MP3'),
            'video_format': data.get('video_format', ''),
            'quality': data.get('quality', 'Balanced'),
            'fps': data.get('fps', ''),
        })
        validated = validate_job_settings(current)
        try:
            save_settings({**current, **validated})
        except Exception:
            pass
        self._chime_var.set(validated['chime_enabled'])
        self._auto_update_var.set(validated['auto_update_check'])
        self.destination.set(validated['destination'])
        self._validate_destination_or_hide()
        self.audio_format.set(validated['audio_format'])
        self.video_format.set(validated['video_format'])
        self.quality.set(validated['quality'])
        self.fps.set(validated['fps'])
        if self.mode.get() != validated['mode']:
            self.mode.set(validated['mode'])
            self._sync_options()
        if hasattr(self, '_toast'):
            if validated['theme'] != THEME_NAME:
                self._toast.show(
                    'บันทึกแล้ว เปิดแอปใหม่เพื่อใช้ธีมใหม่', 'info', 6000)
            else:
                self._toast.show('บันทึกตั้งค่าแล้ว', 'success')

    def _toggle_sidebar(self) -> None:
        try:
            if self._sidebar_visible:
                self._sidebar.grid_remove()
            else:
                self._sidebar.grid()
            self._sidebar_visible = not self._sidebar_visible
            self._sync_sidebar_toggle()
        except tk.TclError:
            pass
    def _sync_sidebar_toggle(self) -> None:
        """Topbar button doubles as the hide button: « when open, ☰ when shut."""
        try:
            self._sidebar_toggle.configure(
                text='«' if self._sidebar_visible else '☰')
        except (tk.TclError, AttributeError):
            pass
    def _show_view(self, name: str) -> None:
        """Switch between the job form and the embedded history view."""
        self._view = name
        try:
            if name == 'history':
                self._main_view.grid_remove()
                self._action_bar.grid_remove()
                self._history_panel.refresh()
                self._history_view.grid()
            else:
                self._history_view.grid_remove()
                self._main_view.grid()
                self._action_bar.grid()
        except tk.TclError:
            pass
        for value, button in self._view_buttons.items():
            try:
                button.configure(
                    style='SideActive.TButton' if value == name else 'Side.TButton'
                )
            except tk.TclError:
                pass
    def _record_history(self, targets: list[Path]) -> None:
        """Remember where finished outputs were saved; never breaks the job."""
        try:
            kind = self.mode.get()
            source_kind = self.input_kind.get()
            source = self.source.get().strip()
            for target in targets:
                add_entry(kind, source_kind, target.name, target, source=source)
        except Exception:
            pass

    def _audio_format_value(self) -> str:
        return AUDIO_FORMAT_VALUES.get(self.audio_format.get(), 'mp3')

    def _video_format_value(self) -> str:
        return VIDEO_FORMAT_VALUES.get(self.video_format.get(), 'mp4')

    def _fps_value(self) -> str:
        return FPS_VALUES.get(self.fps.get(), 'สูงสุด')

    def _toggle_details(self) -> None:
        """Expand or collapse the extra options box."""
        self._details_expanded = not self._details_expanded
        self._sync_details()

    # ── Motion effects (main thread only) ──────────────────────────────────
    def _using_animated_start_style(self) -> bool:
        return self._start_accent

    def _paint_start_button(self, color: str) -> None:
        if not self._using_animated_start_style():
            return
        try:
            self.start_button.set_fill(color)
        except tk.TclError:
            pass
        else:
            self._start_button_color = color

    def _tween_start_button(self, target: str) -> None:
        if not self._using_animated_start_style():
            return
        origin = self._start_button_color
        self._button_tween.start(
            lambda progress: self._paint_start_button(mix_color(origin, target, progress)),
        )

    def _on_start_hover_in(self, _event: tk.Event) -> None:
        self._hovering_start = True
        self._tween_start_button(ACCENT_GLOW)

    def _on_start_hover_out(self, _event: tk.Event) -> None:
        self._hovering_start = False
        self._tween_start_button(ACCENT)

    def _on_start_press(self, _event: tk.Event) -> None:
        self._tween_start_button(mix_color(ACCENT, '#000000', 0.30))

    def _on_start_release(self, _event: tk.Event) -> None:
        self._tween_start_button(ACCENT_GLOW if self._hovering_start else ACCENT)

    def _flash_start_success(self) -> None:
        if not self._using_animated_start_style():
            return

        def frame(progress: float) -> None:
            if progress < 0.5:
                color = mix_color(ACCENT, SUCCESS, progress * 2.0)
            else:
                color = mix_color(SUCCESS, ACCENT, (progress - 0.5) * 2.0)
            self._paint_start_button(color)

        self._flash_tween.start(frame, on_done=lambda: self._paint_start_button(ACCENT))

    def _flash_hero(self) -> None:
        try:
            self._mode_control.flash()
        except tk.TclError:
            pass

    def _sync_details(self) -> None:
        """Show/hide the details box, toggle and trim row for the current mode."""
        is_url = self.input_kind.get() == 'url'
        mode = self.mode.get()
        show_trim = not is_url and mode in ('audio', 'video')
        if show_trim and self._trim_options is not None:
            self._trim_options.grid()
        elif self._trim_options is not None:
            self._trim_options.grid_remove()
        has_details = mode == 'video' or show_trim
        if has_details and self._details_expanded:
            self.details_toggle.configure(text='▾ ตัวเลือกเพิ่มเติม')
            self._details_box.grid()
        else:
            if has_details:
                self.details_toggle.configure(text='▸ ตัวเลือกเพิ่มเติม')
            self._details_box.grid_remove()
            self.details_toggle.grid_remove() if not has_details else self.details_toggle.grid()

    def _sync_options(self) -> None:
        is_url = self.input_kind.get() == 'url'
        if self.mode.get() == 'stems':
            self.video_format_box.grid_remove()
            self.quality_label.grid_remove()
            self.quality_box.grid_remove()
            self.fps_label.grid_remove()
            self.fps_box.grid_remove()
            if self._stems_options is not None:
                self._stems_options.grid()
            self.format_box.grid()
            self.option_label.configure(text='รูปแบบเสียง')
            self.mode_desc.set('แยกเสียงร้องและดนตรีบนเครื่องด้วย Demucs (ติดตั้งเครื่องมือครั้งแรกครั้งเดียว)')
            action_text = 'ดาวน์โหลดและแยกสเต็ม' if is_url else 'เริ่มแยกสเต็ม'
        elif self.mode.get() == 'audio':
            self.video_format_box.grid_remove()
            self.quality_label.grid_remove()
            self.quality_box.grid_remove()
            self.fps_label.grid_remove()
            self.fps_box.grid_remove()
            if self._stems_options is not None:
                self._stems_options.grid_remove()
            self.format_box.grid()
            self.option_label.configure(text='รูปแบบเสียง')
            self.mode_desc.set('แยกเสียงเป็น MP3 / M4A / WAV / FLAC / OPUS')
            action_text = 'เริ่มดาวน์โหลดเสียง' if is_url else 'เริ่มแยกเสียง'
        else:
            self.format_box.grid_remove()
            if self._stems_options is not None:
                self._stems_options.grid_remove()
            self.video_format_box.grid()
            self.option_label.configure(text='รูปแบบไฟล์')
            self.quality_label.grid()
            self.quality_box.grid()
            self.fps_label.grid()
            self.fps_box.grid()
            self.mode_desc.set('แปลงเป็น MP4 (H.264) หรือ MOV (ProRes) พร้อมคุมคุณภาพและเฟรมเรต')
            if is_url:
                self.quality_box.configure(values=VIDEO_QUALITIES)
                if self.quality.get() not in VIDEO_QUALITIES:
                    self.quality.set(VIDEO_QUALITIES[0])
                action_text = 'เริ่มดาวน์โหลดวิดีโอ'
            else:
                self.quality_box.configure(values=VIDEO_QUALITY_PRESETS)
                if self.quality.get() not in VIDEO_QUALITY_PRESETS:
                    self.quality.set('Balanced')
                action_text = 'เริ่มแปลงวิดีโอ'
        if self._source_kind_frame is not None:
            if self.mode.get() == 'stems':
                self._source_kind_frame.grid()
            else:
                self._source_kind_frame.grid_remove()
        self._sync_details()
        if self._cancellation is None:
            self.start_button.configure(text=action_text, command=self._start)
            self.start_button.set_mode(True)
            self._start_accent = True


    def _on_mode_change(self, value: str) -> None:
        """Called when segmented control changes mode."""
        if value in ('audio', 'video'):
            self._last_av_mode = value
        self.mode.set(value)
        self._flash_hero()
        self._sync_options()

    def _sync_source_kind(self) -> None:
        new_kind = self.input_kind.get()
        if new_kind not in {'file', 'url'}:
            self.input_kind.set('file')
            new_kind = 'file'
        if new_kind != self._active_source_kind:
            self._source_values[self._active_source_kind] = self.source.get()
            self._active_source_kind = new_kind
            self.source.set(self._source_values[new_kind])
        if new_kind == 'url':
            self.source_hint.set(
                'วางลิงก์สาธารณะจาก YouTube, Facebook, Instagram หรือเว็บที่รองรับ '
                '• เลือกความละเอียด 360p ถึง 4K ได้'
            )
            self.source_button_text.set('วางจากคลิปบอร์ด')
            self.rights_row.grid()
        else:
            self.source_hint.set('เลือกไฟล์ หรือลากมาวางที่นี่')
            self.source_button_text.set('เลือกไฟล์')
            self.rights_row.grid_remove()
        self._on_source_changed()
        self._sync_options()

    def _on_source_changed(self, *_args: object) -> None:
        value = self.source.get()
        self._source_values[self._active_source_kind] = value
        if self.input_kind.get() == 'url':
            self.source_detail.set(url_summary(value))
        else:
            self.source_detail.set(source_summary(value))
        self._schedule_preview()

    def _schedule_preview(self) -> None:
        """Debounced link preview; silent no-op unless a fresh valid URL."""
        self._cancel_preview(keep_card=True)
        if self.input_kind.get() != 'url':
            self._hide_preview()
            return
        url = self.source.get().strip()
        try:
            validate_url(url)
        except ValueError:
            self._hide_preview()
            return
        if not url or url == self._preview_url:
            return
        try:
            self._preview_after = self.after(1200, self._fetch_preview)
        except tk.TclError:
            pass

    def _cancel_preview(self, keep_card: bool = False) -> None:
        if self._preview_after is not None:
            try:
                self.after_cancel(self._preview_after)
            except tk.TclError:
                pass
            self._preview_after = None
        token = self._preview_token
        self._preview_token = None
        if token is not None:
            token.cancel()
        self._preview_gen += 1
        if not keep_card:
            self._hide_preview()

    def _hide_preview(self) -> None:
        self._preview_url = ''
        self._preview_image = None
        try:
            self._preview_frame.grid_remove()
        except tk.TclError:
            pass

    def _fetch_preview(self) -> None:
        self._preview_after = None
        url = self.source.get().strip()
        try:
            validate_url(url)
        except ValueError:
            return
        self._preview_gen += 1
        generation = self._preview_gen
        token = CancellationToken()
        self._preview_token = token
        threading.Thread(
            target=self._preview_worker,
            args=(url, generation, token),
            daemon=True,
        ).start()

    def _preview_worker(self, url: str, generation: int, token: CancellationToken) -> None:
        try:
            preview = fetch_link_preview(url, cancellation=token)
            png_path = None
            if preview.thumbnail_url and not token.cancelled:
                if self._preview_tmp is None:
                    self._preview_tmp = tempfile.TemporaryDirectory(prefix='clipora-preview-')
                png_path = download_thumbnail(
                    preview.thumbnail_url, Path(self._preview_tmp.name) / 'thumb.png'
                )
            self.after(0, self._apply_preview, generation, url, preview,
                       str(png_path) if png_path else None)
        except Exception:
            self.after(0, self._hide_preview_gen, generation)

    def _hide_preview_gen(self, generation: int) -> None:
        if generation == self._preview_gen:
            self._hide_preview()

    def _apply_preview(
        self, generation: int, url: str, preview: LinkPreview, png_path: str | None
    ) -> None:
        if generation != self._preview_gen:
            return
        if not preview.title and not png_path:
            self._hide_preview()
            return
        self._preview_url = url
        self._preview_title.configure(text=preview.title[:80] or url)
        meta = '  •  '.join(part for part in (preview.uploader, preview.duration) if part)
        self._preview_meta.configure(text=meta[:100])
        if png_path:
            try:
                image = fit_photo_image(tk.PhotoImage(file=png_path), 160, 90)
            except tk.TclError:
                image = None
            if image is not None:
                self._preview_image = image
                self._preview_thumb.configure(image=image)
                self._preview_thumb.pack(side='left', padx=(0, 12))
            else:
                self._preview_thumb.pack_forget()
        else:
            self._preview_thumb.pack_forget()
        try:
            self._preview_frame.grid()
        except tk.TclError:
            pass

    def _set_inputs_enabled(self, enabled: bool) -> None:
        state = '!disabled' if enabled else 'disabled'
        for widget in self._input_widgets:
            widget.state([state])

    def _choose_source(self) -> None:
        path = filedialog.askopenfilename(
            title='เลือกวิดีโอ',
            filetypes=[
                ('Video files', '*.mp4 *.mov *.mkv *.avi *.webm *.m4v'),
                ('All files', '*.*'),
            ],
        )
        if path:
            self.source.set(path)

    def _source_action(self) -> None:
        if self.input_kind.get() == 'file':
            self._choose_source()
            return
        self._paste_source_from_clipboard(show_warning=True)

    def _paste_source_from_clipboard(self, show_warning: bool) -> bool:
        try:
            value = self.clipboard_get().strip()
        except tk.TclError:
            value = ''
        if not value:
            if show_warning:
                messagebox.showwarning('ไม่มีลิงก์', 'คัดลอกลิงก์ก่อน แล้วลองวางอีกครั้ง')
            return False
        self.source.set(value)
        self.source_entry.focus_set()
        self.source_entry.icursor('end')
        return True

    def _on_control_keypress(self, event: tk.Event) -> str | None:
        keysym = str(getattr(event, 'keysym', '')).lower()
        keycode = int(getattr(event, 'keycode', 0))
        if keysym == 'v' or (os.name == 'nt' and keycode == 86):
            return self._on_paste_shortcut(event)
        return None

    def _on_paste_shortcut(self, _event: tk.Event) -> str | None:
        focused = self.focus_get()
        if isinstance(focused, (tk.Entry, ttk.Entry, tk.Text)):
            # Editable field (main entries, dialog inputs, reason box):
            # let Tk paste natively instead of hijacking the clipboard.
            return None
        if self.input_kind.get() != 'url':
            return None
        if self._cancellation is not None:
            return 'break'
        self._paste_source_from_clipboard(show_warning=False)
        return 'break'

    # Validation methods
    def _validate_source_or_hide(self) -> None:
        """FocusOut guidance: only nag about content, never about an empty field."""
        if not self.source.get().strip():
            self._source_error.hide()
            return
        self._validate_source()

    def _validate_destination_or_hide(self) -> None:
        """FocusOut guidance: only nag about content, never about an empty field."""
        if not self.destination.get().strip():
            self._dest_error.hide()
            return
        self._validate_destination()
    def _validate_source(self) -> bool:
        value = self.source.get().strip()
        if not value:
            self._source_error.show('กรุณาเลือกไฟล์หรือวางลิงก์')
            return False
        if self.input_kind.get() == 'url':
            try:
                validate_url(value)
            except ValueError as exc:
                self._source_error.show(str(exc))
                return False
        else:
            if not Path(value).is_file():
                self._source_error.show('ไม่พบไฟล์นี้ กรุณาเลือกไฟล์ใหม่')
                return False
        self._source_error.hide()
        return True

    def _validate_destination(self) -> bool:
        value = self.destination.get().strip()
        if not value:
            self._dest_error.show('กรุณาเลือกโฟลเดอร์บันทึก')
            return False
        if not Path(value).is_dir():
            self._dest_error.show('โฟลเดอร์ไม่มีอยู่จริง')
            return False
        self._dest_error.hide()
        return True

    def _validate_stems(self) -> bool:
        if self.mode.get() == 'stems':
            stems = self._selected_stems()
            if not stems:
                return False
        return True

    def _validate_all(self) -> bool:
        return self._validate_source() and self._validate_destination() and self._validate_stems()

    # Destination history
    def _show_destination_history(self, _event: tk.Event) -> None:
        if not hasattr(self, '_recent_destinations'):
            return
        if not self._recent_destinations:
            return
        # Create a simple popup menu
        menu = tk.Menu(self, tearoff=0, bg=MENU_BG, fg=TEXT, activebackground=ACCENT, activeforeground=MENU_ACTIVE_FG, font=(self.ui_font, 10))
        for path in self._recent_destinations[:5]:
            menu.add_command(label=path, command=lambda p=path: self.destination.set(p))
        try:
            menu.tk_popup(self.destination_entry.winfo_rootx(), self.destination_entry.winfo_rooty() + self.destination_entry.winfo_height())
        finally:
            menu.grab_release()

    def _add_to_destination_history(self, path: str) -> None:
        if not hasattr(self, '_recent_destinations'):
            self._recent_destinations = []
        if path in self._recent_destinations:
            self._recent_destinations.remove(path)
        self._recent_destinations.insert(0, path)
        self._recent_destinations = self._recent_destinations[:10]

    # Keyboard shortcuts
    def _bind_shortcuts(self) -> None:
        self.bind('<Control-t>', lambda _e: self._open_tool_setup(repair_mode=True))
        self.bind('<Control-u>', lambda _e: self._check_ytdlp_update(auto=False))
        self.bind('<Control-d>', lambda _e: self._open_donate_dialog())
        self.bind('<Control-o>', lambda _e: self._choose_source())
        self.bind('<Control-s>', lambda _e: self._choose_destination())
        self.bind('<Control-Return>', lambda _e: self._start() if self._cancellation is None else None)
        self.bind('<Escape>', lambda _e: self._cancel() if self._cancellation is not None else None)
        self.bind('<F1>', lambda _e: webbrowser.open('https://github.com/ertyu007/media-toolkit-Open-source/blob/main/docs/USER_GUIDE.md'))

    # Phase-aware progress
    def _set_progress_phase(self, phase: str, percent: float = 0) -> None:
        """Update progress with phase-aware status."""
        phase_text = PROGRESS_PHASES.get(phase, phase)
        self.status.set(phase_text)
        if percent > 0:
            self.progress['value'] = percent
            self.progress_text.set(f'{percent:.0f}%')

    def _choose_destination(self) -> None:
        path = filedialog.askdirectory(title='เลือกโฟลเดอร์บันทึก')
        if path:
            self.destination.set(path)
            self._add_to_destination_history(path)
            self._validate_destination()

    def _start(self) -> None:
        if self._cancellation is not None:
            return
        if not self._validate_all():
            return
        if not self._prepare_destination():
            return
        if self.mode.get() == 'stems':
            if self.input_kind.get() == 'url':
                self._start_stems_url()
            else:
                self._start_stems_local()
            return
        if self.input_kind.get() == 'url':
            self._start_url()
        else:
            self._start_local()

    def _prepare_destination(self) -> bool:
        """Clean stale workspaces and check free disk space before a job.

        Returns ``False`` when the job must not start (disk full). Cleanup
        failures never block a job.
        """
        destination = Path(self.destination.get())
        try:
            cleanup_orphaned_import_workspaces(destination)
        except (OSError, ValueError):
            pass
        try:
            cleanup_orphaned_workspaces(destination)
        except (OSError, ValueError):
            pass
        try:
            if self.input_kind.get() == 'url':
                check_destination_disk_space(destination)
            else:
                check_disk_space(destination)
        except (FFmpegError, URLImportError) as exc:
            messagebox.showwarning('พื้นที่ดิสก์ไม่เพียงพอ', str(exc), parent=self)
            return False
        return True

    def _start_local(self) -> None:
        destination = Path(self.destination.get())
        try:
            trim_start = parse_trim_seconds(self.start_time_entry.get())
            trim_duration = parse_trim_seconds(self.duration_entry.get())
        except ValueError as exc:
            messagebox.showwarning('ตัดช่วงเวลาไม่ถูกต้อง', str(exc), parent=self)
            return
        job = JobSpec(
            source=Path(self.source.get()),
            destination=destination,
            mode=self.mode.get(),
            quality=self.quality.get(),
            audio_format=self._audio_format_value(),
            video_format=self._video_format_value(),
            fps=self._fps_value(),
            trim_start=trim_start,
            trim_duration=trim_duration,
        )
        if not tools_available():
            self.status.set('ต้องติดตั้งเครื่องมือก่อนเริ่มงาน')
            self._open_tool_setup()
            return

        target = output_path(
            job.source,
            job.destination,
            job.mode,
            job.audio_format,
            job.video_format,
        )
        if target.exists():
            existing_size = target.stat().st_size if target.is_file() else 0
            decision = OverwriteDialog(
                self,
                target.name,
                existing_size=existing_size,
            ).result
            if decision in (CANCEL, KEEP):
                return
        self._add_to_destination_history(str(destination))
        cancellation = CancellationToken()
        self._begin_job(cancellation, 'กำลังตรวจสอบไฟล์…', 'validating')
        self._set_progress_phase('validating', 0)
        threading.Thread(
            target=self._run_local,
            args=(job, target, cancellation),
            daemon=True,
        ).start()

    def _selected_stems(self) -> tuple[str, ...]:
        return tuple(stem for stem in SELECTABLE_STEMS if self.stem_vars[stem].get())

    def _report_stems_phase(self, message: str) -> None:
        try:
            self.after(0, self.status.set, message)
        except tk.TclError:
            pass

    def _start_stems_local(self) -> None:
        destination = Path(self.destination.get())
        source = Path(self.source.get())
        if not tools_available():
            self.status.set('ต้องติดตั้งเครื่องมือก่อนเริ่มงาน')
            self._open_tool_setup()
            return
        if not separator_installed():
            self.status.set('ต้องติดตั้งเครื่องมือแยกสเต็มก่อนเริ่มงาน')
            self._open_tool_setup(separator=True)
            return
        stems = self._selected_stems()
        audio_format = self._audio_format_value()
        expected = separate_expected_outputs(source, destination, audio_format, stems)
        existing = [target for target in expected if target.exists()]
        overwrite = False
        if existing:
            first = existing[0]
            existing_size = first.stat().st_size if first.is_file() else 0
            decision = OverwriteDialog(
                self,
                first.name,
                existing_size=existing_size,
                detail=(
                    'มีไฟล์ผลลัพธ์บางไฟล์อยู่แล้ว'
                    if len(existing) > 1
                    else None
                ),
            ).result
            if decision in (CANCEL, KEEP):
                return
            overwrite = True
        self._add_to_destination_history(str(destination))
        cancellation = CancellationToken()
        self._begin_job(cancellation, 'กำลังตรวจสอบไฟล์…', 'validating')
        self._set_progress_phase('validating', 0)
        threading.Thread(
            target=self._run_stems_local,
            args=(source, destination, audio_format, stems, overwrite, cancellation),
            daemon=True,
        ).start()

    def _run_stems_local(
        self,
        source: Path,
        destination: Path,
        audio_format: str,
        stems: tuple[str, ...],
        overwrite: bool,
        cancellation: CancellationToken,
    ) -> None:
        try:
            outputs = separate_audio(
                source,
                destination,
                audio_format,
                stems,
                lambda msg: self.after(0, self._set_progress_phase, 'separating', 0) if 'load' in msg.lower() else None,
                lambda value: self.after(0, self._set_progress_phase, 'separating', value * 100),
                cancellation,
                overwrite=overwrite,
            )
        except ConversionCancelled:
            self.after(0, self._cancelled, cancellation)
        except (SeparatorError, FFmpegError, OSError, ValueError) as exc:
            self.after(0, self._failed, str(exc), cancellation)
        else:
            self.after(0, self._set_progress_phase, 'finalizing', 90)
            self.after(0, self._done_stems, outputs, cancellation)

    def _start_stems_url(self) -> None:
        destination = Path(self.destination.get())
        try:
            url = validate_url(self.source.get())
        except ValueError as exc:
            self._source_error.show(str(exc))
            return
        if not self.authorized.get():
            messagebox.showwarning(
                'กรุณายืนยันสิทธิ์',
                'ทำเครื่องหมายว่าคุณเป็นเจ้าของหรือได้รับอนุญาตให้ดาวน์โหลดสื่อนี้',
            )
            return
        if not tools_available():
            self.status.set('ต้องติดตั้งเครื่องมือก่อนเริ่มงาน')
            self._open_tool_setup()
            return
        if not ytdlp_available():
            self.status.set('ต้องติดตั้งเครื่องมือก่อนเริ่มงาน')
            self._open_tool_setup()
            return
        if not separator_installed():
            self.status.set('ต้องติดตั้งเครื่องมือแยกสเต็มก่อนเริ่มงาน')
            self._open_tool_setup(separator=True)
            return
        stems = self._selected_stems()
        spec = ImportSpec(
            url=url,
            destination=destination,
            mode='audio',
            quality=self.quality.get(),
            audio_format=self._audio_format_value(),
        )
        self._add_to_destination_history(str(destination))
        cancellation = CancellationToken()
        self._begin_job(cancellation, 'กำลังตรวจสอบลิงก์…', 'validating')
        self._set_progress_phase('validating', 0)
        threading.Thread(
            target=self._run_stems_url,
            args=(spec, stems, cancellation),
            daemon=True,
        ).start()

    def _run_stems_url(
        self,
        spec: ImportSpec,
        stems: tuple[str, ...],
        cancellation: CancellationToken,
    ) -> None:
        try:
            self.after(0, self._set_progress_phase, 'downloading', 0)
            completed, workspace = import_audio_for_processing(
                spec,
                lambda value: self.after(0, self._set_progress_phase, 'downloading', value * 50),
                cancellation,
            )
            try:
                self.after(0, self._set_progress_phase, 'separating', 50)
                outputs = separate_audio(
                    completed,
                    spec.destination,
                    spec.audio_format,
                    stems,
                    lambda msg: self.after(0, self._set_progress_phase, 'separating', 50) if 'load' in msg.lower() else None,
                    lambda value: self.after(0, self._set_progress_phase, 'separating', 50 + value * 50),
                    cancellation,
                    collision_free=True,
                )
            finally:
                cleanup_import_workspace(workspace, spec.destination)
        except ConversionCancelled:
            self.after(0, self._cancelled, cancellation)
        except (SeparatorError, URLImportError, FFmpegError, OSError, ValueError) as exc:
            self.after(0, self._failed, str(exc), cancellation)
        else:
            self.after(0, self._set_progress_phase, 'finalizing', 95)
            self.after(0, self._done_stems, outputs, cancellation)

    def _start_url(self) -> None:
        destination = Path(self.destination.get())
        try:
            url = validate_url(self.source.get())
        except ValueError as exc:
            self._source_error.show(str(exc))
            return
        if not self.authorized.get():
            messagebox.showwarning(
                'กรุณายืนยันสิทธิ์',
                'ทำเครื่องหมายว่าคุณเป็นเจ้าของหรือได้รับอนุญาตให้ดาวน์โหลดสื่อนี้',
            )
            return
        if not tools_available():
            self.status.set('ต้องติดตั้งเครื่องมือก่อนเริ่มงาน')
            self._open_tool_setup()
            return
        if not ytdlp_available():
            self.status.set('ต้องติดตั้งเครื่องมือก่อนเริ่มงาน')
            self._open_tool_setup()
            return
        job = ImportSpec(
            url=url,
            destination=destination,
            mode=self.mode.get(),
            quality=self.quality.get(),
            audio_format=self._audio_format_value(),
            video_format=self._video_format_value(),
            fps=self._fps_value(),
        )
        self._add_to_destination_history(str(destination))
        cancellation = CancellationToken()
        self._begin_job(cancellation, 'กำลังตรวจสอบลิงก์…', 'validating')
        self._set_progress_phase('validating', 0)
        threading.Thread(
            target=self._run_import,
            args=(job, cancellation),
            daemon=True,
        ).start()

    def _begin_job(
        self,
        cancellation: CancellationToken,
        initial_status: str,
        progress_action: str,
    ) -> None:
        self._cancellation = cancellation
        self._progress_action = progress_action
        self._cancel_preview(keep_card=True)
        self._set_inputs_enabled(False)
        self.start_button.configure(text='ยกเลิกงาน', command=self._cancel)
        self.start_button.set_mode(False)
        self._start_accent = False
        self.start_button.state(['!disabled'])
        self.progress['value'] = 0
        self.progress_text.set('0%')
        self.status.set(initial_status)
        if hasattr(self, 'result_panel'):
            self.result_panel.grid_remove()
            self._result_targets = []

    def _run_local(self, job: JobSpec, target: Path, cancellation: CancellationToken) -> None:
        temporary = temporary_output_path(target)
        outcome = 'done'
        detail = ''
        try:
            if cancellation.cancelled:
                raise ConversionCancelled('ยกเลิกงานแล้ว')
            info = probe(job.source)
            validate_operation(info, job.mode)
            if cancellation.cancelled:
                raise ConversionCancelled('ยกเลิกงานแล้ว')
            trim_start, trim_duration, effective_duration = normalize_trim(
                job.trim_start, job.trim_duration, info.duration,
            )
            command = build_command(
                job.source,
                temporary,
                job.mode,
                job.quality,
                job.audio_format,
                job.video_format,
                job.fps,
                trim_start,
                trim_duration,
            )
            self.after(0, self._set_progress_phase, 'converting', 0)
            convert(
                command,
                temporary,
                effective_duration,
                lambda value: self.after(0, self._set_progress_phase, 'converting', value * 100),
                cancellation,
            )
            self.after(0, self._set_progress_phase, 'finalizing', 90)
            finalize_output(temporary, target)
        except ConversionCancelled:
            outcome = 'cancelled'
        except (FFmpegError, OSError, ValueError) as exc:
            outcome = 'failed'
            detail = str(exc)
        finally:
            try:
                cleanup_temporary_output(temporary, target)
            except (OSError, ValueError) as exc:
                outcome = 'failed'
                detail = f'ไม่สามารถลบไฟล์ชั่วคราวได้: {exc}\n{temporary}'

        if outcome == 'done':
            self.after(0, self._done, target, cancellation)
        elif outcome == 'cancelled':
            self.after(0, self._cancelled, cancellation)
        else:
            self.after(0, self._failed, detail, cancellation)

    def _ask_overwrite(self, target: Path) -> bool:
        """Ask on the main thread whether to replace an existing output file.

        Runs inside a worker thread; the Tk dialog is scheduled on the main
        thread via ``after`` and the worker blocks on an event until answered.
        Returns True only when the user chose to overwrite.
        """
        result: dict[str, str | None] = {'decision': None}
        ready = threading.Event()

        def ask() -> None:
            try:
                existing_size = target.stat().st_size if target.is_file() else 0
                result['decision'] = OverwriteDialog(
                    self,
                    target.name,
                    existing_size=existing_size,
                ).result
            except tk.TclError:
                result['decision'] = CANCEL
            finally:
                ready.set()

        self.after(0, ask)
        ready.wait()
        return result['decision'] == OVERWRITE

    def _run_import(self, job: ImportSpec, cancellation: CancellationToken) -> None:
        self.after(0, self._set_progress_phase, 'downloading', 0)
        try:
            target = import_url(
                job,
                lambda value: self.after(0, self._set_progress_phase, 'downloading', value * 100),
                cancellation,
                on_conflict=self._ask_overwrite,
            )
        except ConversionCancelled:
            self.after(0, self._cancelled, cancellation)
        except (URLImportError, OSError, ValueError) as exc:
            self.after(0, self._failed, str(exc), cancellation)
        else:
            self.after(0, self._set_progress_phase, 'finalizing', 90)
            self.after(0, self._done, target, cancellation)

    def _set_progress(self, value: float, cancellation: CancellationToken) -> None:
        if cancellation is not self._cancellation or cancellation.cancelled:
            return
        percent = value * 100
        self.progress['value'] = percent
        self.progress_text.set(f'{percent:.0f}%')

    def _finish_job(self, cancellation: CancellationToken) -> bool:
        if cancellation is not self._cancellation:
            return False
        self._cancellation = None
        self._set_inputs_enabled(True)
        self._sync_source_kind()
        self._sync_options()
        self.start_button.state(['!disabled'])
        if self._closing:
            self.destroy()
            return False
        return True

    def _done(self, target: Path, cancellation: CancellationToken) -> None:
        if not self._finish_job(cancellation):
            return
        self._set_progress_phase('done', 100)
        self._show_result([target])
        self._flash_start_success()
        if self.input_kind.get() == 'url':
            self.authorized.set(False)

    def _done_stems(self, outputs: list[Path], cancellation: CancellationToken) -> None:
        if not self._finish_job(cancellation):
            return
        self._set_progress_phase('done', 100)
        self._show_result(outputs)
        self._flash_start_success()
        if self.input_kind.get() == 'url':
            self.authorized.set(False)

    def _show_result(self, targets: list[Path]) -> None:
        self._result_targets = list(targets)
        if self._chime_var.get():
            play_completion_chime()
        self._record_history(targets)
        if hasattr(self, '_toast'):
            names = ' • '.join(target.name for target in targets[:2])
            if len(targets) > 2:
                names += f' และอื่น ๆ {len(targets) - 2} ไฟล์'
            self._toast.show(f'เสร็จแล้ว: {names}', 'success')
        try:
            if len(targets) == 1:
                self.result_summary.configure(text=f'เสร็จแล้ว: {targets[0].name}')
            else:
                self.result_summary.configure(text=f'สร้างไฟล์แล้ว {len(targets)} ไฟล์')
            total = sum(target.stat().st_size for target in targets if target.is_file())
            self.result_size.configure(text=format_file_size(total))
            self.open_file_btn.state(['!disabled'])
            if len(targets) != 1:
                self.open_file_btn.state(['disabled'])
            self.result_panel.grid()
        except OSError:
            self.status.set('เสร็จแล้ว')

    def _cancelled(self, cancellation: CancellationToken) -> None:
        if not self._finish_job(cancellation):
            return
        self.progress['value'] = 0
        self.progress_text.set('0%')
        self.status.set('ยกเลิกงานแล้ว')

    def _open_result_folder(self) -> None:
        if not self._result_targets:
            return
        folder = self._result_targets[0].parent
        try:
            os.startfile(str(folder))
        except OSError as exc:
            messagebox.showerror('เปิดโฟลเดอร์ไม่สำเร็จ', str(exc), parent=self)

    def _open_result_file(self) -> None:
        if len(self._result_targets) != 1:
            return
        try:
            os.startfile(str(self._result_targets[0]))
        except OSError as exc:
            messagebox.showerror('เปิดไฟล์ไม่สำเร็จ', str(exc), parent=self)

    def _failed(self, detail: str, cancellation: CancellationToken) -> None:
        if not self._finish_job(cancellation):
            return
        self._set_progress_phase('error', 0)
        safe_detail = sanitize_error_message(detail)
        if hasattr(self, '_toast'):
            self._toast.show(f'ข้อผิดพลาด: {safe_detail[:200]}', 'error', 8000)
        ErrorDialog(self, 'ทำรายการไม่สำเร็จ', safe_detail)

    def _cancel(self) -> None:
        cancellation = self._cancellation
        if cancellation is None or cancellation.cancelled:
            return
        self.start_button.configure(text='กำลังยกเลิก…')
        self.start_button.set_mode(False)
        self._start_accent = False
        self.start_button.state(['disabled'])
        self.status.set('กำลังยกเลิก…')
        threading.Thread(target=cancellation.cancel, daemon=True).start()

    def _on_close(self) -> None:
        cancellation = self._cancellation
        if cancellation is None:
            self.destroy()
            return
        if not messagebox.askyesno(
            'กำลังประมวลผล',
            'ต้องการยกเลิกงานและปิด Clipora หรือไม่?',
        ):
            return
        self._closing = True
        self._cancel()

class DisclaimerDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.title('คำปฏิเสธด้านลิขสิทธิ์')
        self.geometry('640x560')
        self.minsize(580, 480)
        self.configure(bg=BG)
        self.transient(parent)
        self.resizable(True, True)
        self.protocol('WM_DELETE_WINDOW', self.destroy)

        shell = ttk.Frame(self, padding=(28, 22, 28, 20))
        shell.pack(fill='both', expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(2, weight=1)

        accent_bar = tk.Frame(shell, bg=ACCENT, width=3, height=200)
        accent_bar.grid(row=0, column=0, rowspan=4, sticky='ns', padx=(0, 16))

        ttk.Label(shell, text='คำปฏิเสธด้านลิขสิทธิ์', style='Heading.TLabel').grid(
            row=0, column=1, sticky='w'
        )
        ttk.Label(shell, text='อ่านและทำความเข้าใจก่อนเริ่มใช้งาน', style='Muted.TLabel').grid(
            row=1, column=1, sticky='w', pady=(2, 14)
        )
        text = tk.Text(
            shell,
            wrap='word',
            bg=FIELD,
            fg=TEXT,
            insertbackground=TEXT,
            relief='flat',
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            padx=16,
            pady=14,
            font=(getattr(parent, 'ui_font', FONT_FAMILY), FONT_SIZE_BASE),
        )
        text.grid(row=2, column=1, sticky='nsew')
        text.insert('1.0', DISCLAIMER_TEXT)
        text.configure(state='disabled')
        close = ttk.Button(
            shell,
            text='close',
            style='Accent.TButton',
            command=self.destroy,
        )
        close.grid(row=3, column=1, sticky='e', pady=(16, 0))
        fade_in_window(self, self.after)
        self.grab_set()
        close.focus_set()


class DonateDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.title('โดเนท')
        self.geometry('440x540')
        self.minsize(400, 500)
        self.configure(bg=BG)
        self.transient(parent)
        self.resizable(True, True)
        self.protocol('WM_DELETE_WINDOW', self.destroy)

        self._dialog_canvas = tk.Canvas(self, bg=BG, highlightthickness=0, borderwidth=0)
        dialog_scrollbar = ttk.Scrollbar(self, orient='vertical', command=self._dialog_canvas.yview)
        self._dialog_canvas.grid(row=0, column=0, sticky='nsew')
        dialog_scrollbar.grid(row=0, column=1, sticky='ns')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        shell = ttk.Frame(self._dialog_canvas, padding=(24, 18, 24, 16))
        shell_window = self._dialog_canvas.create_window((0, 0), window=shell, anchor='nw')
        shell.columnconfigure(0, weight=1)

        def _on_dialog_card_configure(_event: tk.Event) -> None:
            self._dialog_canvas.configure(scrollregion=self._dialog_canvas.bbox('all'))

        def _on_dialog_canvas_configure(_event: tk.Event) -> None:
            self._dialog_canvas.itemconfigure(shell_window, width=self._dialog_canvas.winfo_width())

        def _on_dialog_scroll(first: str, last: str) -> None:
            dialog_scrollbar.set(first, last)
            if float(first) <= 0.0 and float(last) >= 1.0:
                dialog_scrollbar.grid_remove()
            else:
                dialog_scrollbar.grid()

        def _on_dialog_mousewheel(event: tk.Event) -> None:
            widget = self.winfo_containing(event.x_root, event.y_root)
            if widget is not None and isinstance(widget, ttk.Combobox):
                return
            delta = int(getattr(event, 'delta', 0))
            if delta:
                self._dialog_canvas.yview_scroll(int(-delta / 120), 'units')

        shell.bind('<Configure>', _on_dialog_card_configure)
        self._dialog_canvas.bind('<Configure>', _on_dialog_canvas_configure)
        self._dialog_canvas.configure(yscrollcommand=_on_dialog_scroll)
        self._dialog_canvas.bind(
            '<Enter>',
            lambda _event: self.bind_all('<MouseWheel>', _on_dialog_mousewheel),
        )
        self._dialog_canvas.bind(
            '<Leave>',
            lambda _event: self.unbind_all('<MouseWheel>'),
        )

        ttk.Label(shell, text=DONATE_HEADING, style='Heading.TLabel').grid(
            row=0, column=0, sticky='w'
        )
        ttk.Label(
            shell,
            text=DONATE_BODY,
            style='Muted.TLabel',
            wraplength=360,
        ).grid(row=1, column=0, sticky='w', pady=(2, 12))

        image_path = donate_image_path()
        if image_path is not None:
            try:
                raw = tk.PhotoImage(file=str(image_path))
                image = fit_photo_image(raw, 280, 300)
            except tk.TclError:
                image = None
            if image is not None:
                frame = ttk.Frame(shell, style='Card.TFrame')
                frame.grid(row=2, column=0, sticky='ew', pady=(0, 12))
                frame.columnconfigure(0, weight=1)
                label = ttk.Label(frame, image=image, style='Card.TLabel')
                label.image = image
                label.grid(row=0, column=0)
            else:
                ttk.Label(
                    shell,
                    text='ไม่พบไฟล์ QR โดเนท',
                    style='CardMuted.TLabel',
                ).grid(row=2, column=0, sticky='w', pady=(0, 12))
        else:
            ttk.Label(
                shell,
                text='ไม่พบไฟล์ QR โดเนท',
                style='CardMuted.TLabel',
            ).grid(row=2, column=0, sticky='w', pady=(0, 12))

        ttk.Label(
            shell,
            text=DONATE_NOTE,
            style='CardMuted.TLabel',
            wraplength=360,
        ).grid(row=3, column=0, sticky='w')
        ttk.Button(
            shell,
            text='ปิด',
            style='DialogAccent.TButton',
            command=self.destroy,
        ).grid(row=4, column=0, sticky='e', pady=(12, 0))
        fade_in_window(self, self.after)
        self.grab_set()
        self.after_idle(self.focus_set)


class HistoryPanel(ttk.Frame):
    """Embedded history browser (history only, media untouched)."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, style='TFrame')
        self._filter = tk.StringVar(value='all')
        self._entries: list = []
        self._selected: int | None = None
        self._selected_id: str | None = load_selected_history_id()
        self._row_widgets: list[tuple[tk.Frame, list[tk.Label]]] = []
        self._filter.trace_add('write', lambda *_: self._render())

        shell = ttk.Frame(self, padding=(28, 22, 28, 20))
        shell.pack(fill='both', expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(2, weight=1)

        ttk.Label(shell, text='ประวัติดาวน์โหลด', style='Heading.TLabel').grid(
            row=0, column=0, sticky='w'
        )
        ttk.Label(
            shell,
            text=(f'จำที่อยู่ไฟล์ที่ทำเสร็จ '
                  f'(ลบย้ายไปถังขยะก่อน หายถาวรใน {TRASH_RETENTION_DAYS} วัน) '
                  '• คลิกขวาเพื่อดูเมนู'),
            style='Muted.TLabel',
            wraplength=560,
            justify='left',
        ).grid(row=1, column=0, sticky='w', pady=(2, 12))

        filter_row = ttk.Frame(shell, style='TFrame')
        filter_row.grid(row=2, column=0, sticky='ew', pady=(0, 10))
        filter_row.columnconfigure(0, weight=1)
        SegmentedControl(
            filter_row,
            options=[
                ('all', 'ทั้งหมด'),
                ('audio', 'เพลง'),
                ('video', 'วิดีโอ'),
                ('stems', 'สเต็ม'),
            ],
            variable=self._filter,
            command=lambda _value: self._render(),
        ).grid(row=0, column=0, sticky='ew')
        self._trash_button = RoundedButton(
            filter_row, text='ถังขยะ', width=6, height=PILL_HEIGHT,
            command=self._toggle_trash_filter,
        )
        self._trash_button.grid(row=0, column=1, padx=(8, 0), sticky='ns')

        header = ttk.Frame(shell, style='TFrame')
        header.grid(row=3, column=0, sticky='ew', pady=(0, 4))
        header.columnconfigure(0, weight=1)
        for column, minsize in _HISTORY_COLUMN_MINSIZES.items():
            header.grid_columnconfigure(column, minsize=minsize)
        ttk.Label(header, text='ชื่อ', style='Muted.TLabel').grid(
            row=0, column=0, sticky='w', padx=(12, 4))
        ttk.Label(header, text='ประเภท', style='Muted.TLabel').grid(
            row=0, column=1, sticky='w')
        ttk.Label(header, text='วันที่', style='Muted.TLabel').grid(
            row=0, column=2, sticky='w')
        ttk.Label(header, text='ขนาด', style='Muted.TLabel').grid(
            row=0, column=3, sticky='e', padx=(0, 4))

        list_frame = ttk.Frame(shell, style='Card.TFrame')
        list_frame.grid(row=4, column=0, sticky='nsew', pady=(0, 12))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self._canvas = tk.Canvas(
            list_frame, bg=FIELD, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=ACCENT,
            borderwidth=0,
        )
        self._canvas.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self._canvas.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self._canvas.configure(yscrollcommand=scrollbar.set)
        self._rows = ttk.Frame(self._canvas, style='Card.TFrame')
        self._rows_window = self._canvas.create_window((0, 0), window=self._rows, anchor='nw')
        self._rows.bind('<Configure>', lambda _e: self._canvas.configure(
            scrollregion=self._canvas.bbox('all')))
        self._canvas.bind('<Configure>', lambda e: self._canvas.itemconfigure(
            self._rows_window, width=e.width))
        self._canvas.bind('<Enter>', lambda _e: self._canvas.bind_all(
            '<MouseWheel>', self._on_wheel))
        self._canvas.bind('<Leave>', lambda _e: self._canvas.unbind_all('<MouseWheel>'))
        # Windows-style context menu on right-click; tk.Menu unposts itself
        # when the user clicks anywhere else, no manual hide needed.
        self._canvas.bind('<Button-3>', self._popup_menu)
        self._rows.bind('<Button-3>', self._popup_menu)

        self._render()

    def refresh(self) -> None:
        """Reload entries (called when the history view is shown)."""
        self._render()

    def _in_trash(self) -> bool:
        return self._filter.get() == 'trash'

    def _toggle_trash_filter(self) -> None:
        self._filter.set('all' if self._in_trash() else 'trash')

    def _sync_trash_button(self) -> None:
        try:
            if self._in_trash():
                self._trash_button.set_fill(ACCENT_SOFT)
            else:
                self._trash_button.reset_fill()
        except tk.TclError:
            pass

    def _render(self) -> None:
        wanted = self._filter.get()
        if self._in_trash():
            self._entries = load_trash()
        else:
            self._entries = [
                entry for entry in load_history()
                if wanted == 'all' or entry.kind == wanted
            ]
        for child in self._rows.winfo_children():
            child.destroy()
        self._row_widgets = []
        self._selected = None
        if not self._entries:
            empty_text = ('ถังขยะว่าง' if self._in_trash() else 'ยังไม่มีประวัติ')
            ttk.Label(self._rows, text=empty_text, style='Muted.TLabel').pack(
                anchor='w', padx=12, pady=12)
        for index, entry in enumerate(self._entries):
            try:
                size_text = format_file_size(Path(entry.target).stat().st_size)
                missing = False
            except OSError:
                size_text = '—'
                missing = True
            text = entry.name
            if len(text) > 40:
                text = text[:40] + '…'
            row = tk.Frame(self._rows, bg=CARD)
            row.pack(fill='x', padx=4, pady=1)
            row.columnconfigure(0, weight=1)
            for column, minsize in _HISTORY_COLUMN_MINSIZES.items():
                row.grid_columnconfigure(column, minsize=minsize)
            font = (getattr(self, 'ui_font', FONT_FAMILY), FONT_SIZE_BASE)
            name_label = tk.Label(
                row, text=text, bg=CARD, fg=MUTED if missing else TEXT,
                font=font, anchor='w', justify='left', cursor='hand2',
            )
            name_label.grid(row=0, column=0, sticky='ew', padx=(8, 4), pady=7)
            kind_label = tk.Label(
                row, text=KIND_LABELS.get(entry.kind, entry.kind),
                bg=CARD, fg=MUTED if missing else TEXT, font=font, anchor='w',
            )
            kind_label.grid(row=0, column=1, sticky='w', pady=7)
            date_label = tk.Label(
                row, text=self._date_text(entry), bg=CARD,
                fg=MUTED if missing else TEXT, font=font, anchor='w',
            )
            date_label.grid(row=0, column=2, sticky='w', pady=7)
            size_label = tk.Label(
                row, text=size_text, bg=CARD, fg=MUTED, font=font, anchor='e',
            )
            size_label.grid(row=0, column=3, sticky='e', padx=(0, 4), pady=7)
            cells = [name_label, kind_label, date_label, size_label]
            for widget in [row, name_label, kind_label, date_label, size_label]:
                widget.bind('<Button-1>', lambda _e, i=index: self._select_row(i))
                widget.bind('<Button-3>', lambda e, i=index: self._popup_menu(e, i))
            name_label.bind(
                '<Double-Button-1>', lambda _e, i=index: self._open_row(i))
            self._row_widgets.append((row, cells))
        # Restore the entry the user picked (same session or a previous run).
        restored = find_history_index(self._entries, self._selected_id)
        if restored is not None:
            self._select_row(restored, persist=False)
        self._sync_trash_button()
        try:
            self._canvas.yview_moveto(0.0)
        except tk.TclError:
            pass

    @staticmethod
    def _date_text(entry) -> str:
        try:
            return datetime.fromtimestamp(entry.finished_at).strftime('%d/%m %H:%M')
        except (OSError, OverflowError, ValueError):
            return ''

    def _select_row(self, index: int, persist: bool = True) -> None:
        self._selected = index
        if persist:
            if 0 <= index < len(self._entries):
                self._selected_id = self._entries[index].id
            else:
                self._selected_id = None
            save_selected_history_id(self._selected_id)
        for i, (row, cells) in enumerate(self._row_widgets):
            bg = ACCENT_SOFT if i == index else CARD
            try:
                row.configure(bg=bg)
                for cell in cells:
                    cell.configure(bg=bg)
            except tk.TclError:
                pass

    def _on_wheel(self, event: tk.Event) -> None:
        delta = int(getattr(event, 'delta', 0))
        if delta:
            self._canvas.yview_scroll(int(-delta / 120), 'units')

    def _selected_entry(self):
        if self._selected is None or self._selected >= len(self._entries):
            messagebox.showinfo('ประวัติ', 'คลิกเลือกรายการก่อน', parent=self)
            return None
        return self._entries[self._selected]

    def _open_selected(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        folder = str(Path(entry.target).parent)
        try:
            os.startfile(folder)
        except OSError as exc:
            messagebox.showerror('เปิดโฟลเดอร์ไม่สำเร็จ', str(exc), parent=self)

    def _open_row(self, index: int) -> None:
        self._select_row(index)
        self._open_selected()

    def _forget_selected_id(self, entry_id: str) -> None:
        if self._selected_id == entry_id:
            self._selected_id = None
            save_selected_history_id(None)

    def _delete_one(self, index: int) -> None:
        if index >= len(self._entries):
            return
        entry = self._entries[index]
        if messagebox.askyesno(
            'ย้ายไปถังขยะ',
            f'ย้าย “{entry.name}” ไปถังขยะ?\n(ไฟล์จริงไม่ถูกลบ กู้คืนได้ใน {TRASH_RETENTION_DAYS} วัน)',
            parent=self,
        ):
            trash_entry(entry.id)
            self._forget_selected_id(entry.id)
            self._render()

    def _restore_one(self, index: int) -> None:
        if index >= len(self._entries):
            return
        restore_entry(self._entries[index].id)
        self._render()

    def _delete_forever_one(self, index: int) -> None:
        if index >= len(self._entries):
            return
        entry = self._entries[index]
        if messagebox.askyesno(
            'ลบถาวร',
            f'ลบ “{entry.name}” ถาวร? (กู้คืนไม่ได้ แต่ไฟล์จริงไม่ถูกลบ)',
            parent=self,
        ):
            remove_entry(entry.id)
            self._forget_selected_id(entry.id)
            self._render()

    def _confirm_empty_trash(self) -> None:
        if not load_trash():
            messagebox.showinfo('ถังขยะ', 'ถังขยะว่าง', parent=self)
            return
        if messagebox.askyesno(
            'ล้างถังขยะ',
            'ลบถังขยะทั้งหมดถาวร? (กู้คืนไม่ได้ แต่ไฟล์จริงไม่ถูกลบ)',
            parent=self,
        ):
            empty_trash()
            self._render()
    def _popup_menu(self, event: tk.Event, index: int | None = None) -> None:
        """Right-click menu (dismisses itself on outside click, like Windows)."""
        if index is not None:
            self._select_row(index)
        has_selection = (
            self._selected is not None and self._selected < len(self._entries)
        )
        menu = tk.Menu(
            self, tearoff=0, bg=MENU_BG, fg=TEXT,
            activebackground=ACCENT, activeforeground=MENU_ACTIVE_FG,
            font=(getattr(self, 'ui_font', FONT_FAMILY), 10),
        )
        if self._in_trash():
            menu.add_command(
                label='กู้คืนรายการนี้',
                state='normal' if has_selection else 'disabled',
                command=lambda: self._restore_one(self._selected or 0),
            )
            menu.add_command(
                label='ลบถาวร…',
                state='normal' if has_selection else 'disabled',
                command=lambda: self._delete_forever_one(self._selected or 0),
            )
            menu.add_separator()
            menu.add_command(label='ล้างถังขยะ…', command=self._confirm_empty_trash)
        else:
            menu.add_command(
                label='เปิดโฟลเดอร์',
                state='normal' if has_selection else 'disabled',
                command=self._open_selected,
            )
            menu.add_command(
                label='ลบรายการนี้…',
                state='normal' if has_selection else 'disabled',
                command=lambda: self._delete_one(self._selected or 0),
            )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        except tk.TclError:
            pass
        finally:
            try:
                menu.grab_release()
            except tk.TclError:
                pass
