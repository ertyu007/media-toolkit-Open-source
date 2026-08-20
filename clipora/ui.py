from __future__ import annotations

import os
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk

from .ffmpeg import (
    CancellationToken,
    ConversionCancelled,
    FFmpegError,
    JobSpec,
    VIDEO_QUALITY_PRESETS,
    build_command,
    cleanup_temporary_output,
    convert,
    finalize_output,
    output_path,
    probe,
    temporary_output_path,
    tools_available,
    validate_operation,
)
from .importer import (
    ImportSpec,
    URLImportError,
    VIDEO_QUALITIES,
    cleanup_import_workspace,
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
    separate_output_zip_path,
    separator_installed,
)
from .dependencies import DependencyInstallError
from .donate import DONATE_BODY, DONATE_HEADING, DONATE_NOTE, donate_image_path
from .legal import DMCA_EMAIL, DMCA_NOTE, DISCLAIMER_TEXT, build_dmca_mailto
from .setup_ui import ToolSetupDialog
from .tools import missing_required_tools
from .ytdlp_update import (
    YtDlpUpdateError,
    installed_ytdlp_version,
    is_newer_available,
    latest_ytdlp_version,
    update_ytdlp,
)
from .ui_components.dialogs import CANCEL, KEEP, OVERWRITE, OverwriteDialog
from .ui_components.format import format_file_size
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
    BUTTON_BG,
    BUTTON_BORDER,
    BUTTON_HOVER,
    CARD,
    DANGER,
    DISABLED_BG,
    DISABLED_FG,
    ERROR,
    FIELD,
    FONT_SIZE_BASE,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    FONT_SIZE_TOP,
    MENU_ACTIVE_BG,
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
    TOAST_BG,
    TOP_BAR_BG,
    TOPBAR_BUTTON_BG,
    TOPBAR_BUTTON_HOVER,
    TOPBAR_BUTTON_FG,
    WARNING,
)
from .ui_components.widgets import (
    InlineError,
    SegmentedControl,
    ToastManager,
)

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
        self.geometry('940x720')
        self.minsize(680, 480)
        self.configure(bg=BG)
        self._first_run_setup = bool(missing_required_tools())
        if self._first_run_setup:
            self.withdraw()

        available_fonts = set(tkfont.families(self))
        self.ui_font = 'Leelawadee UI' if 'Leelawadee UI' in available_fonts else 'Segoe UI'
        self._icon = self._create_icon()
        self.iconphoto(True, self._icon)

        self.source = tk.StringVar()
        self.input_kind = tk.StringVar(value='url')
        self.destination = tk.StringVar(value=str(Path.home() / 'Downloads'))
        self.mode = tk.StringVar(value='video')
        self.stem_vars = {
            stem: tk.BooleanVar(value=stem in ('vocals', 'instrumental'))
            for stem in SELECTABLE_STEMS
        }
        self._stems_options: ttk.Frame | None = None
        self.audio_format = tk.StringVar(value='MP3')
        self.video_format = tk.StringVar(value=VIDEO_FORMAT_LABELS[0])
        self.fps = tk.StringVar(value=FPS_LABELS[0])
        self.quality = tk.StringVar(value='Balanced')
        self.authorized = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value='พร้อมเริ่มงาน')
        self.source_detail = tk.StringVar(value=source_summary(''))
        self.source_hint = tk.StringVar(value='เลือกวิดีโอที่ต้องการประมวลผล')
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
        self._recent_destinations: list[str] = []
        self._result_targets: list[Path] = []
        self._build()
        self._toast = ToastManager(self, self._menu_btn)
        self._bind_shortcuts()
        self.source.trace_add('write', self._on_source_changed)
        self.bind_all('<Control-KeyPress>', self._on_control_keypress, add='+')
        self.bind_all('<Shift-Insert>', self._on_paste_shortcut, add='+')
        self.after_idle(self.source_entry.focus_set)
        self.after(120, self._maybe_offer_tool_setup)
        self.after(3000, self._maybe_check_ytdlp_update)
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
        style.configure('Action.TFrame', background=ACTION_BG, borderwidth=1, relief='solid')

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
        style.configure(
            'DialogAccent.TButton',
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
        style.configure(
            'Danger.TButton',
            background=DANGER,
            foreground=TEXT,
            bordercolor=DANGER,
            lightcolor=DANGER,
            darkcolor=DANGER,
            font=(self.ui_font, FONT_SIZE_BASE + 1, 'bold'),
            padding=(20, 14),
        )
        style.map(
            'Danger.TButton',
            background=[('active', '#d9534f'), ('disabled', '#3a2626')],
            foreground=[('disabled', '#9d777d')],
        )

        # ── Form controls ─────────────────────────────────────────────────────
        style.configure(
            'TRadiobutton',
            background=CARD,
            foreground=TEXT,
            font=(self.ui_font, FONT_SIZE_BASE),
            indicatorcolor=FIELD,
            padding=(0, 4),
        )
        style.map(
            'TRadiobutton',
            background=[('active', CARD)],
            foreground=[('disabled', DISABLED_FG)],
            indicatorcolor=[('selected', ACCENT), ('disabled', CARD)],
        )
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
        style.configure(
            'TCheckbutton',
            background=CARD,
            foreground=MUTED,
            font=(self.ui_font, FONT_SIZE_BASE),
            indicatorcolor=FIELD,
            indicatorsize=18,
            indicatorborderwidth=2,
            padding=(0, 4),
        )
        style.map(
            'TCheckbutton',
            background=[('active', CARD)],
            foreground=[('active', TEXT), ('disabled', DISABLED_FG)],
            indicatorcolor=[('selected', ACCENT), ('disabled', CARD)],
        )
        style.configure(
            'Dark.TEntry',
            fieldbackground=FIELD,
            foreground=TEXT,
            insertcolor=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=(12, 10),
        )
        style.map(
            'Dark.TEntry',
            fieldbackground=[('disabled', DISABLED_BG), ('focus', FIELD)],
            foreground=[('disabled', MUTED)],
            bordercolor=[('focus', ACCENT)],
        )
        style.configure(
            'Dark.TCombobox',
            fieldbackground=FIELD,
            background=SECONDARY_BG,
            foreground=TEXT,
            arrowcolor=TEXT,
            bordercolor=SECONDARY_BORDER,
            lightcolor=SECONDARY_BORDER,
            darkcolor=SECONDARY_BORDER,
            padding=(10, 8),
        )
        style.map(
            'Dark.TCombobox',
            fieldbackground=[('readonly', FIELD), ('disabled', DISABLED_BG)],
            foreground=[('readonly', TEXT), ('disabled', DISABLED_FG)],
            bordercolor=[('focus', ACCENT)],
            arrowcolor=[('disabled', DISABLED_FG)],
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
        # Row 0 = top bar, row 1 = scrollable content, row 2 = action bar, row 3 = footer
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=0)
        self.rowconfigure(3, weight=0)
        self.columnconfigure(0, weight=1)

        # ── Top bar ───────────────────────────────────────────────────────────
        topbar = ttk.Frame(self, style='TopBar.TFrame', padding=(20, 12, 16, 12))
        topbar.grid(row=0, column=0, sticky='ew')
        topbar.columnconfigure(1, weight=1)

        icon_box = tk.Frame(topbar, bg=ACCENT_SOFT, padx=4, pady=4)
        icon_box.grid(row=0, column=0, padx=(0, 12), pady=2)
        ttk.Label(icon_box, image=self._icon, background=ACCENT_SOFT).grid(row=0, column=0)

        brand_col = ttk.Frame(topbar, style='TopBar.TFrame')
        brand_col.grid(row=0, column=1, sticky='w')
        ttk.Label(brand_col, text='Clipora', style='TopBarTitle.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(
            brand_col,
            text='แปลงวิดีโอ  •  แยกเสียง  •  ดาวน์โหลด',
            style='TopBarMuted.TLabel',
        ).grid(row=1, column=0, sticky='w')

        # Right side: Tools | Update | ♥ สนับสนุน
        topbar_actions = ttk.Frame(topbar, style='TopBar.TFrame')
        topbar_actions.grid(row=0, column=2, sticky='e', padx=(8, 0))

        self._menu_btn = ttk.Menubutton(
            topbar_actions, text='☰  เมนู', style='TopBar.TButton', direction='below',
        )
        menu = tk.Menu(
            self._menu_btn, tearoff=0, bg=MENU_BG, fg=TEXT,
            activebackground=ACCENT, activeforeground=MENU_ACTIVE_FG,
            font=(self.ui_font, FONT_SIZE_BASE),
        )
        menu.add_command(label='เครื่องมือ (Ctrl+T)', command=lambda: self._open_tool_setup(repair_mode=True))
        menu.add_command(label='อัปเดต yt-dlp (Ctrl+U)', command=lambda: self._check_ytdlp_update(auto=False))
        menu.add_separator()
        menu.add_command(
            label='คู่มือผู้ใช้ (F1)',
            command=lambda: webbrowser.open('https://github.com/ertyu007/media-toolkit-Open-source/blob/main/docs/USER_GUIDE.md'),
        )
        menu.add_command(
            label='รายงานปัญหา',
            command=lambda: webbrowser.open('https://github.com/ertyu007/media-toolkit-Open-source/issues'),
        )
        self._menu_btn.configure(menu=menu)
        self._menu_btn.pack(side='left', padx=(0, 6))

        ttk.Button(
            topbar_actions,
            text='♥  สนับสนุน',
            style='TopBarAccent.TButton',
            command=self._open_donate_dialog,
        ).pack(side='left')

        # Thin separator under topbar
        tk.Frame(self, bg=BORDER, height=1).grid(row=0, column=0, sticky='sew')

        # ── Scrollable content area ───────────────────────────────────────────
        content_outer = ttk.Frame(self, style='TFrame')
        content_outer.grid(row=1, column=0, sticky='nsew')
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

        # Inner content frame — holds the three cards
        content = ttk.Frame(self.card_canvas, style='TFrame', padding=(28, 16, 28, 16))
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

        # ── Helper: build a card frame with a section header row ─────────────
        def _make_card(parent: ttk.Frame, num: str, title: str, row: int) -> ttk.Frame:
            """Create a bordered card with a left accent strip and return its inner frame."""
            outer = tk.Frame(parent, bg=BORDER, pady=1, padx=1)
            outer.grid(row=row, column=0, sticky='ew', pady=(0, 12))
            outer.columnconfigure(1, weight=1)

            accent = tk.Frame(outer, bg=ACCENT, width=3)
            accent.grid(row=0, column=0, sticky='ns')
            accent.grid_propagate(False)

            inner = ttk.Frame(outer, style='Card.TFrame', padding=(20, 16, 20, 18))
            inner.grid(row=0, column=1, sticky='ew')
            inner.columnconfigure(0, weight=1)

            # Section header row
            hdr = ttk.Frame(inner, style='Card.TFrame')
            hdr.grid(row=0, column=0, sticky='ew', pady=(0, 14))
            hdr.columnconfigure(1, weight=1)

            num_lbl = ttk.Label(hdr, text=num, style='CardSectionNum.TLabel')
            num_lbl.grid(row=0, column=0, padx=(0, 10))
            ttk.Label(hdr, text=title, style='CardSection.TLabel').grid(row=0, column=1, sticky='w')

            return inner, hdr

        # ── Card 1: Source ────────────────────────────────────────────────────
        source_card, source_hdr = _make_card(content, '01', 'แหล่งสื่อ', row=0)

        # Source type toggle — right side of header
        source_kind_frame = ttk.Frame(source_hdr, style='Card.TFrame')
        source_kind_frame.grid(row=0, column=2, sticky='e')
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

        # Hint text
        ttk.Label(
            source_card, textvariable=self.source_hint, style='CardMuted.TLabel',
        ).grid(row=1, column=0, sticky='w', pady=(0, 8))

        # Inline error
        self._source_error = InlineError(source_card)
        self._source_error.grid(row=2, column=0, sticky='ew', pady=(0, 6))
        self._source_error.grid_remove()

        # Input + button row
        source_row = ttk.Frame(source_card, style='Card.TFrame')
        source_row.grid(row=3, column=0, sticky='ew')
        source_row.columnconfigure(0, weight=1)
        self.source_entry = ttk.Entry(source_row, textvariable=self.source, style='Dark.TEntry')
        self.source_entry.grid(row=0, column=0, sticky='ew', padx=(0, 8))
        self.source_entry.bind('<FocusOut>', lambda _e: self._validate_source())
        self.source_button = ttk.Button(
            source_row, textvariable=self.source_button_text,
            style='Secondary.TButton', command=self._source_action, width=16,
        )
        self.source_button.grid(row=0, column=1)

        # Source detail + rights rows
        source_meta = ttk.Frame(source_card, style='Card.TFrame')
        source_meta.grid(row=4, column=0, sticky='ew', pady=(8, 0))
        source_meta.columnconfigure(0, weight=1)
        ttk.Label(
            source_meta, textvariable=self.source_detail, style='CardMuted.TLabel',
        ).grid(row=0, column=0, sticky='w')

        link_font = (self.ui_font, 9, 'underline')
        self.rights_row = ttk.Frame(source_meta, style='Card.TFrame')
        self.rights_row.grid(row=1, column=0, sticky='w', pady=(6, 0))
        self.rights_check = ttk.Checkbutton(
            self.rights_row, text='ฉันยืนยันว่าอ่านและยอมรับ', variable=self.authorized,
        )
        self.rights_check.pack(side='left')
        self.disclaimer_link = tk.Label(
            self.rights_row, text='คำปฏิเสธด้านลิขสิทธิ์',
            bg=CARD, fg=ACCENT, font=link_font, cursor='hand2',
        )
        self.disclaimer_link.pack(side='left')
        self.disclaimer_link.bind('<Button-1>', lambda _event: self._open_disclaimer())
        ttk.Label(
            self.rights_row, text='แล้ว และจะไม่ดาวน์โหลดเนื้อหาที่มีลิขสิทธิ์',
            style='CardMuted.TLabel',
        ).pack(side='left')

        self.dmca_row = ttk.Frame(source_meta, style='Card.TFrame')
        self.dmca_row.grid(row=2, column=0, sticky='w', pady=(2, 0))
        ttk.Label(
            self.dmca_row, text='ต้องการบล็อกการดาวน์โหลดวิดีโอที่มีลิขสิทธิ์?',
            style='CardMuted.TLabel',
        ).pack(side='left')
        self.dmca_link = tk.Label(
            self.dmca_row, text='รายงานได้ที่นี่',
            bg=CARD, fg=ACCENT, font=link_font, cursor='hand2',
        )
        self.dmca_link.pack(side='left', padx=(4, 0))
        self.dmca_link.bind('<Button-1>', lambda _event: self._open_dmca())
        self.rights_row.grid_remove()
        self.dmca_row.grid_remove()

        # ── Card 2: Destination ───────────────────────────────────────────────
        dest_card, _ = _make_card(content, '02', 'ที่บันทึก', row=1)

        self._dest_error = InlineError(dest_card)
        self._dest_error.grid(row=1, column=0, sticky='ew', pady=(0, 6))
        self._dest_error.grid_remove()

        dest_row = ttk.Frame(dest_card, style='Card.TFrame')
        dest_row.grid(row=2, column=0, sticky='ew')
        dest_row.columnconfigure(0, weight=1)
        self.destination_entry = ttk.Entry(
            dest_row, textvariable=self.destination, style='Dark.TEntry',
        )
        self.destination_entry.grid(row=0, column=0, sticky='ew', padx=(0, 8))
        self.destination_entry.bind('<FocusOut>', lambda _e: self._validate_destination())
        self.destination_entry.bind('<Button-1>', self._show_destination_history)
        self.destination_button = ttk.Button(
            dest_row, text='เลือกโฟลเดอร์',
            style='Secondary.TButton', command=self._choose_destination, width=14,
        )
        self.destination_button.grid(row=0, column=1)

        # ── Card 3: Format / Options ──────────────────────────────────────────
        fmt_card, _ = _make_card(content, '03', 'รูปแบบผลลัพธ์', row=2)

        # Segmented mode control — full width
        self._mode_control = SegmentedControl(
            fmt_card,
            options=[
                ('audio', 'แยกเสียง'),
                ('video', 'แปลงเป็นวิดีโอ'),
                ('stems', 'แยกสเต็มเสียง'),
            ],
            variable=self.mode,
            command=self._on_mode_change,
        )
        self._mode_control.grid(row=1, column=0, sticky='ew', pady=(0, 14))

        # Format dropdowns
        result_options = ttk.Frame(fmt_card, style='Card.TFrame')
        result_options.grid(row=2, column=0, sticky='ew')
        result_options.columnconfigure(1, weight=1)
        self.option_label = ttk.Label(result_options, style='CardMuted.TLabel')
        self.option_label.grid(row=0, column=0, padx=(0, 10), sticky='e')
        self.format_box = ttk.Combobox(
            result_options, textvariable=self.audio_format, values=AUDIO_FORMAT_LABELS,
            state='readonly', style='Dark.TCombobox', width=12,
        )
        self.format_box.grid(row=0, column=1, sticky='w')
        self.video_format_box = ttk.Combobox(
            result_options, textvariable=self.video_format, values=VIDEO_FORMAT_LABELS,
            state='readonly', style='Dark.TCombobox', width=30,
        )
        self.video_format_box.grid(row=0, column=1, sticky='w')

        detail_options = ttk.Frame(fmt_card, style='Card.TFrame')
        detail_options.grid(row=3, column=0, sticky='ew', pady=(10, 0))
        detail_options.columnconfigure(1, weight=1)
        detail_options.columnconfigure(3, weight=1)
        self.quality_label = ttk.Label(detail_options, text='คุณภาพ', style='CardMuted.TLabel')
        self.quality_label.grid(row=0, column=0, padx=(0, 8), sticky='e')
        self.quality_box = ttk.Combobox(
            detail_options, textvariable=self.quality, values=VIDEO_QUALITY_PRESETS,
            state='readonly', style='Dark.TCombobox', width=12,
        )
        self.quality_box.grid(row=0, column=1, sticky='w')
        self.fps_label = ttk.Label(detail_options, text='เฟรมเรต', style='CardMuted.TLabel')
        self.fps_label.grid(row=0, column=2, padx=(16, 8), sticky='e')
        self.fps_box = ttk.Combobox(
            detail_options, textvariable=self.fps, values=FPS_LABELS,
            state='readonly', style='Dark.TCombobox', width=10,
        )
        self.fps_box.grid(row=0, column=3, sticky='w')

        stems_options = ttk.Frame(fmt_card, style='Card.TFrame')
        stems_options.grid(row=4, column=0, sticky='ew', pady=(10, 0))
        stems_options.columnconfigure(0, weight=1)
        self._stems_options = stems_options
        ttk.Label(stems_options, text='สเต็มที่ต้องการ', style='CardMuted.TLabel').grid(
            row=0, column=0, sticky='w',
        )
        self._stem_check_widgets: list[ttk.Checkbutton] = []
        stem_row = ttk.Frame(stems_options, style='Card.TFrame')
        stem_row.grid(row=1, column=0, sticky='w', pady=(8, 0))
        for stem in SELECTABLE_STEMS:
            check = ttk.Checkbutton(
                stem_row, text=STEM_LABELS[stem],
                variable=self.stem_vars[stem], style='TCheckbutton',
            )
            check.pack(side='left', padx=(0, 14))
            self._stem_check_widgets.append(check)
        stems_options.grid_remove()

        # ── Action bar (sticky bottom) ─────────────────────────────────────────
        action_bar = ttk.Frame(self, style='Action.TFrame', padding=(24, 12, 24, 10))
        action_bar.grid(row=2, column=0, sticky='ew')
        action_bar.columnconfigure(0, weight=1)

        # Primary action button — full width, on top for prominence
        self.start_button = ttk.Button(
            action_bar, text='เริ่มแยกเสียง',
            style='Accent.TButton', command=self._start,
        )
        self.start_button.grid(row=0, column=0, sticky='ew', pady=(0, 10))

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

        self.progress = ttk.Progressbar(
            action_bar, mode='determinate', maximum=100,
            style='Clipora.Horizontal.TProgressbar',
        )
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
        self.open_folder_btn = ttk.Button(
            result_actions, text='เปิดโฟลเดอร์', style='Secondary.TButton',
            command=self._open_result_folder, width=14,
        )
        self.open_folder_btn.pack(side='left', padx=(0, 8))
        self.open_file_btn = ttk.Button(
            result_actions, text='เปิดไฟล์', style='Secondary.TButton',
            command=self._open_result_file, width=14,
        )
        self.open_file_btn.pack(side='left')
        self.result_panel.grid_remove()

        # ── Footer ─────────────────────────────────────────────────────────────
        footer = ttk.Frame(self, style='TFrame', padding=(0, 8, 0, 8))
        footer.grid(row=3, column=0, sticky='ew')
        ttk.Label(
            footer,
            text='สร้างโดย ertyu.dev  •  ประมวลผลบนเครื่อง  •  ไม่มีโฆษณา  •  ไม่แก้ไขไฟล์ต้นฉบับ',
            style='Muted.TLabel',
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
            self.quality_box,
            self.fps_box,
            *self._stem_check_widgets,
        ]
        self._sync_source_kind()
        self._sync_options()

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

    def _open_disclaimer(self) -> None:
        DisclaimerDialog(self)

    def _open_dmca(self) -> None:
        DmcaDialog(self)

    def _open_donate_dialog(self) -> None:
        DonateDialog(self)

    def _audio_format_value(self) -> str:
        return AUDIO_FORMAT_VALUES.get(self.audio_format.get(), 'mp3')

    def _video_format_value(self) -> str:
        return VIDEO_FORMAT_VALUES.get(self.video_format.get(), 'mp4')

    def _fps_value(self) -> str:
        return FPS_VALUES.get(self.fps.get(), 'สูงสุด')

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
        if self._cancellation is None:
            self.start_button.configure(text=action_text, style='Accent.TButton', command=self._start)


    def _on_mode_change(self, value: str) -> None:
        """Called when segmented control changes mode."""
        self.mode.set(value)
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
            self.dmca_row.grid()
        else:
            self.source_hint.set('เลือกวิดีโอที่ต้องการประมวลผล')
            self.source_button_text.set('เลือกไฟล์')
            self.rights_row.grid_remove()
            self.dmca_row.grid_remove()
        self._on_source_changed()
        self._sync_options()

    def _on_source_changed(self, *_args: object) -> None:
        value = self.source.get()
        self._source_values[self._active_source_kind] = value
        if self.input_kind.get() == 'url':
            self.source_detail.set(url_summary(value))
        else:
            self.source_detail.set(source_summary(value))

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
        if self.input_kind.get() != 'url':
            return None
        if self.focus_get() is self.destination_entry:
            return None
        if self._cancellation is not None:
            return 'break'
        self._paste_source_from_clipboard(show_warning=False)
        return 'break'

    # Validation methods
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

    def _start_local(self) -> None:
        destination = Path(self.destination.get())
        job = JobSpec(
            source=Path(self.source.get()),
            destination=destination,
            mode=self.mode.get(),
            quality=self.quality.get(),
            audio_format=self._audio_format_value(),
            video_format=self._video_format_value(),
            fps=self._fps_value(),
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
        expected = (separate_output_zip_path(source, destination),)
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
        self._set_inputs_enabled(False)
        self.start_button.configure(text='ยกเลิกงาน', style='Danger.TButton', command=self._cancel)
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
                raise ConversionCancelled('ยกเลิกงาน已取消')
            command = build_command(
                job.source,
                temporary,
                job.mode,
                job.quality,
                job.audio_format,
                job.video_format,
                job.fps,
            )
            self.after(0, self._set_progress_phase, 'converting', 0)
            convert(
                command,
                temporary,
                info.duration,
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
        if self.input_kind.get() == 'url':
            self.authorized.set(False)

    def _done_stems(self, outputs: list[Path], cancellation: CancellationToken) -> None:
        if not self._finish_job(cancellation):
            return
        self._set_progress_phase('done', 100)
        self._show_result(outputs)
        if self.input_kind.get() == 'url':
            self.authorized.set(False)

    def _show_result(self, targets: list[Path]) -> None:
        self._result_targets = list(targets)
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
        if hasattr(self, '_toast'):
            self._toast.show(f'ข้อผิดพลาด: {detail[:200]}', 'error', 8000)
        else:
            messagebox.showerror('ทำรายการไม่สำเร็จ', detail[-1200:])

    def _cancel(self) -> None:
        cancellation = self._cancellation
        if cancellation is None or cancellation.cancelled:
            return
        self.start_button.configure(text='กำลังยกเลิก…', style='Danger.TButton')
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
            font=(getattr(parent, 'ui_font', 'Segoe UI'), FONT_SIZE_BASE),
        )
        text.grid(row=2, column=1, sticky='nsew')
        text.insert('1.0', DISCLAIMER_TEXT)
        text.configure(state='disabled')
        close = ttk.Button(
            shell,
            text='ปิด',
            style='Accent.TButton',
            command=self.destroy,
        )
        close.grid(row=3, column=1, sticky='e', pady=(16, 0))
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
        self.grab_set()
        self.after_idle(self.focus_set)


class DmcaDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.title('รายงาน DMCA')
        self.geometry('620x600')
        self.minsize(500, 360)
        self.configure(bg=BG)
        self.transient(parent)
        self.resizable(True, True)
        self.protocol('WM_DELETE_WINDOW', self.destroy)

        self.video_url = tk.StringVar()
        self.email = tk.StringVar()

        self._dialog_canvas = tk.Canvas(self, bg=BG, highlightthickness=0, borderwidth=0)
        dialog_scrollbar = ttk.Scrollbar(self, orient='vertical', command=self._dialog_canvas.yview)
        self._dialog_canvas.grid(row=0, column=0, sticky='nsew')
        dialog_scrollbar.grid(row=0, column=1, sticky='ns')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        shell = ttk.Frame(self._dialog_canvas, padding=(28, 22, 28, 20))
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

        ttk.Label(shell, text='รายงาน DMCA', style='Heading.TLabel').grid(
            row=0, column=0, sticky='w'
        )
        ttk.Label(
            shell,
            text='คุณเป็นเจ้าของสิทธิ์ของวิดีโอ YouTube ที่ถูกดาวน์โหลดผ่าน Clipora ใช่หรือไม่ '
            'ส่ง URL ด้านล่าง แล้ววิดีโอนั้นจะถูกบล็อกจากการดาวน์โหลดต่อไป',
            style='Muted.TLabel',
            wraplength=560,
        ).grid(row=1, column=0, sticky='w', pady=(2, 16))

        ttk.Label(shell, text='YouTube Video URL', style='CardMuted.TLabel').grid(
            row=2, column=0, sticky='w'
        )
        ttk.Entry(shell, textvariable=self.video_url, style='Dark.TEntry').grid(
            row=3, column=0, sticky='ew', pady=(4, 4)
        )
        ttk.Label(
            shell,
            text='วางลิงก์เต็ม เช่น https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            style='CardMuted.TLabel',
        ).grid(row=4, column=0, sticky='w', pady=(0, 12))

        ttk.Label(shell, text='อีเมลของคุณ', style='CardMuted.TLabel').grid(
            row=5, column=0, sticky='w'
        )
        ttk.Entry(shell, textvariable=self.email, style='Dark.TEntry').grid(
            row=6, column=0, sticky='ew', pady=(4, 4)
        )
        ttk.Label(
            shell,
            text='เราอาจติดต่อกลับเพื่อขอข้อมูลเพิ่มเติมหรือแจ้งผลการคัดค้าน (counter-notice)',
            style='CardMuted.TLabel',
        ).grid(row=7, column=0, sticky='w', pady=(0, 12))

        ttk.Label(shell, text='เหตุผล', style='CardMuted.TLabel').grid(
            row=8, column=0, sticky='w'
        )
        self.reason = tk.Text(
            shell,
            height=6,
            wrap='word',
            bg=FIELD,
            fg=TEXT,
            insertbackground=TEXT,
            relief='flat',
            borderwidth=0,
            padx=12,
            pady=10,
            font=(getattr(parent, 'ui_font', 'Segoe UI'), FONT_SIZE_BASE),
        )
        self.reason.grid(row=9, column=0, sticky='ew', pady=(4, 10))
        ttk.Label(shell, text=DMCA_NOTE, style='CardMuted.TLabel', wraplength=560).grid(
            row=10, column=0, sticky='w', pady=(0, 16)
        )
        ttk.Button(
            shell,
            text='ส่งรายงานทางอีเมล',
            style='DialogAccent.TButton',
            command=self._submit,
        ).grid(row=11, column=0, sticky='e')
        self.grab_set()
        self.after_idle(lambda: self.reason.focus_set())

    def _submit(self) -> None:
        url = self.video_url.get().strip()
        email = self.email.get().strip()
        reason = self.reason.get('1.0', 'end').strip()
        try:
            video_url = validate_url(url)
        except ValueError as exc:
            messagebox.showwarning('ลิงก์ไม่ถูกต้อง', str(exc), parent=self)
            return
        if not email or '@' not in email:
            messagebox.showwarning('อีเมลไม่ถูกต้อง', 'กรุณากรอกอีเมลที่ติดต่อกลับได้', parent=self)
            return
        if not reason:
            messagebox.showwarning('ยังไม่มีเหตุผล', 'กรุณาอธิบายความเป็นเจ้าของและเหตุผลที่ต้องบล็อก', parent=self)
            return
        self.grab_release()
        webbrowser.open(build_dmca_mailto(video_url, email, reason))
        self.destroy()
        messagebox.showinfo(
            'ส่งรายงาน DMCA',
            f'เปิดโปรแกรมอีเมลพร้อมรายงานถึง {DMCA_EMAIL} แล้ว\n\n'
            'เราจะตรวจสอบคำร้องและบล็อกวิดีโอนั้นจากการดาวน์โหลดต่อไป',
        )
