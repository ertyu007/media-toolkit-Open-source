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
    separate_output_paths,
    separator_installed,
)
from .dependencies import DependencyInstallError
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


BG = '#090d15'
CARD = '#141a26'
FIELD = '#0d1320'
BORDER = '#293348'
TEXT = '#f7f8fc'
MUTED = '#96a3b8'
ACCENT = '#7c5cff'
ACCENT_HOVER = '#6c4df0'
DANGER = '#e35d6a'

AUDIO_FORMAT_LABELS = ('MP3', 'M4A', 'WAV', 'FLAC', 'OPUS')
AUDIO_FORMAT_VALUES = {'MP3': 'mp3', 'M4A': 'm4a', 'WAV': 'wav', 'FLAC': 'flac', 'OPUS': 'opus'}
VIDEO_FORMAT_LABELS = ('MP4  •  เล่นได้ทั่วไป', 'MOV  •  ProRes (After Effects)')
VIDEO_FORMAT_VALUES = {
    'MP4  •  เล่นได้ทั่วไป': 'mp4',
    'MOV  •  ProRes (After Effects)': 'mov',
}
FPS_LABELS = ('สูงสุด', '60fps', '30fps')
FPS_VALUES = {'สูงสุด': 'สูงสุด', '60fps': '60', '30fps': '30'}


def format_file_size(size: int) -> str:
    value = float(max(0, size))
    units = ('B', 'KB', 'MB', 'GB', 'TB')
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == 'B':
                return f'{int(value)} {unit}'
            return f'{value:.1f} {unit}'
        value /= 1024
    return '0 B'


def destination_path(value: str) -> Path:
    text = value.strip()
    if not text:
        raise ValueError('กรุณาเลือกโฟลเดอร์บันทึกก่อนเริ่มงาน')
    return Path(text)


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
        self.geometry('900x700')
        self.minsize(660, 480)
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
        self._build()
        self.source.trace_add('write', self._on_source_changed)
        self.bind_all('<Control-KeyPress>', self._on_control_keypress, add='+')
        self.bind_all('<Shift-Insert>', self._on_paste_shortcut, add='+')
        self.after_idle(self.source_entry.focus_set)
        self.after(120, self._maybe_offer_tool_setup)
        self.after(3000, self._maybe_check_ytdlp_update)
        self.protocol('WM_DELETE_WINDOW', self._on_close)

    def _create_icon(self) -> tk.PhotoImage:
        image = tk.PhotoImage(width=32, height=32)
        image.put(BG, to=(0, 0, 32, 32))
        for y in range(4, 28):
            inset = 2 if y in (4, 5, 26, 27) else 0
            image.put(ACCENT, to=(4 + inset, y, 28 - inset, y + 1))
        for y in range(10, 23):
            width = min(y - 9, 23 - y)
            image.put(TEXT, to=(12, y, 12 + width, y + 1))
        return image

    def _build(self) -> None:
        style = ttk.Style(self)
        style.theme_use('clam')
        self.option_add('*TCombobox*Listbox.background', FIELD)
        self.option_add('*TCombobox*Listbox.foreground', TEXT)
        self.option_add('*TCombobox*Listbox.selectBackground', ACCENT)
        self.option_add('*TCombobox*Listbox.selectForeground', TEXT)

        style.configure('TFrame', background=BG)
        style.configure('Card.TFrame', background=CARD)
        style.configure('Action.TFrame', background='#111827', borderwidth=1, relief='solid')
        style.configure('TLabel', background=BG, foreground=TEXT, font=(self.ui_font, 10))
        style.configure('Card.TLabel', background=CARD, foreground=TEXT, font=(self.ui_font, 10))
        style.configure('Heading.TLabel', background=BG, foreground=TEXT, font=('Segoe UI Semibold', 28))
        style.configure('Muted.TLabel', background=BG, foreground=MUTED, font=(self.ui_font, 10))
        style.configure('CardMuted.TLabel', background=CARD, foreground=MUTED, font=(self.ui_font, 9))
        style.configure('Section.TLabel', background=CARD, foreground=TEXT, font=(self.ui_font, 10, 'bold'))
        style.configure(
            'Step.TLabel',
            background=CARD,
            foreground='#b8aaff',
            font=(self.ui_font, 10, 'bold'),
        )
        style.configure(
            'Pill.TLabel',
            background='#1d1838',
            foreground='#c8bcff',
            font=(self.ui_font, 8, 'bold'),
            padding=(10, 5),
        )
        style.configure(
            'Header.TButton',
            background='#1d1838',
            foreground='#c8bcff',
            bordercolor='#302758',
            lightcolor='#302758',
            darkcolor='#302758',
            font=(self.ui_font, 8, 'bold'),
            padding=(10, 5),
        )
        style.map(
            'Header.TButton',
            background=[('active', '#2a2250')],
            foreground=[('active', TEXT)],
        )
        style.configure(
            'Action.TLabel',
            background='#111827',
            foreground=TEXT,
            font=(self.ui_font, 10, 'bold'),
        )
        style.configure(
            'ActionMuted.TLabel',
            background='#111827',
            foreground=MUTED,
            font=(self.ui_font, 9),
        )
        style.configure(
            'Pill.TLabel',
            background=ACCENT,
            foreground='#ffffff',
            font=(self.ui_font, 9, 'bold'),
            padding=(10, 4),
        )
        style.configure(
            'Dark.TEntry',
            fieldbackground=FIELD,
            foreground=TEXT,
            insertcolor=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=(12, 9),
        )
        style.map(
            'Dark.TEntry',
            fieldbackground=[('disabled', CARD), ('focus', FIELD)],
            foreground=[('disabled', MUTED)],
            bordercolor=[('focus', ACCENT)],
        )
        style.configure(
            'Secondary.TButton',
            background='#232c3b',
            foreground=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            font=(self.ui_font, 10, 'bold'),
            padding=(14, 9),
        )
        style.map(
            'Secondary.TButton',
            background=[('active', '#303b4f'), ('disabled', CARD)],
            foreground=[('disabled', '#626d7f')],
            bordercolor=[('focus', ACCENT)],
        )
        style.configure(
            'Accent.TButton',
            background=ACCENT,
            foreground=TEXT,
            bordercolor=ACCENT,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            font=(self.ui_font, 11, 'bold'),
            padding=(18, 13),
        )
        style.map(
            'Accent.TButton',
            background=[('active', ACCENT_HOVER), ('disabled', '#41395f')],
            bordercolor=[('active', ACCENT_HOVER), ('disabled', '#41395f')],
            foreground=[('disabled', '#9b94b8')],
        )
        style.configure(
            'Danger.TButton',
            background=DANGER,
            foreground=TEXT,
            bordercolor=DANGER,
            lightcolor=DANGER,
            darkcolor=DANGER,
            font=(self.ui_font, 11, 'bold'),
            padding=(18, 13),
        )
        style.map(
            'Danger.TButton',
            background=[('active', '#cc4b59'), ('disabled', '#503036')],
            foreground=[('disabled', '#9d777d')],
        )
        style.configure(
            'TRadiobutton',
            background=CARD,
            foreground=TEXT,
            font=(self.ui_font, 10),
            indicatorcolor=FIELD,
            padding=(0, 4),
        )
        style.map(
            'TRadiobutton',
            background=[('active', CARD)],
            foreground=[('disabled', '#626d7f')],
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
            font=(self.ui_font, 9, 'bold'),
            padding=(13, 7),
            anchor='center',
        )
        style.map(
            'Segment.TRadiobutton',
            background=[('selected', ACCENT), ('active', '#222b3c'), ('disabled', CARD)],
            foreground=[('selected', TEXT), ('active', TEXT), ('disabled', '#626d7f')],
        )
        style.configure(
            'TCheckbutton',
            background=CARD,
            foreground=MUTED,
            font=(self.ui_font, 9),
            indicatorcolor=FIELD,
            padding=(0, 3),
        )
        style.map(
            'TCheckbutton',
            background=[('active', CARD)],
            foreground=[('active', TEXT), ('disabled', '#626d7f')],
            indicatorcolor=[('selected', ACCENT), ('disabled', CARD)],
        )
        style.configure(
            'Dark.TCombobox',
            fieldbackground=FIELD,
            background='#232c3b',
            foreground=TEXT,
            arrowcolor=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=(10, 7),
        )
        style.map(
            'Dark.TCombobox',
            fieldbackground=[('readonly', FIELD), ('disabled', CARD)],
            foreground=[('readonly', TEXT), ('disabled', '#626d7f')],
            bordercolor=[('focus', ACCENT)],
            arrowcolor=[('disabled', '#626d7f')],
        )
        style.configure(
            'Clipora.Horizontal.TProgressbar',
            background=ACCENT,
            troughcolor='#202838',
            bordercolor='#202838',
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            thickness=11,
        )
        style.configure('Card.TSeparator', background=BORDER)

        main = ttk.Frame(self, padding=(38, 24, 38, 20))
        main.pack(fill='both', expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        header = ttk.Frame(main)
        header.grid(row=0, column=0, sticky='ew', pady=(0, 14))
        header.columnconfigure(1, weight=1)
        ttk.Label(header, image=self._icon).grid(row=0, column=0, rowspan=2, padx=(0, 13))
        ttk.Label(header, text='Clipora', style='Heading.TLabel').grid(row=0, column=1, sticky='w')
        ttk.Label(
            header,
            text='แปลงวิดีโอ 360p–4K, แยกเสียง และ ProRes สำหรับ After Effects — บนเครื่องของคุณ',
            style='Muted.TLabel',
        ).grid(row=1, column=1, sticky='w')
        ttk.Label(header, text='สร้างโดย ertyu.dev', style='Pill.TLabel').grid(
            row=0,
            column=2,
            rowspan=2,
            padx=(0, 10),
            sticky='e',
        )
        ttk.Button(
            header,
            text='เครื่องมือ',
            style='Header.TButton',
            command=lambda: self._open_tool_setup(repair_mode=True),
        ).grid(
            row=0,
            column=3,
            rowspan=2,
            sticky='e',
        )
        ttk.Button(
            header,
            text='อัปเดต yt-dlp',
            style='Header.TButton',
            command=lambda: self._check_ytdlp_update(auto=False),
        ).grid(
            row=0,
            column=4,
            rowspan=2,
            padx=(8, 0),
            sticky='e',
        )

        card_scroll = ttk.Frame(main, style='TFrame')
        card_scroll.grid(row=1, column=0, sticky='nsew')
        card_scroll.rowconfigure(0, weight=1)
        card_scroll.columnconfigure(0, weight=1)
        self.card_canvas = tk.Canvas(
            card_scroll,
            bg=CARD,
            highlightthickness=0,
            borderwidth=0,
        )
        self.card_scrollbar = ttk.Scrollbar(
            card_scroll,
            orient='vertical',
            command=self.card_canvas.yview,
        )
        self.card_canvas.grid(row=0, column=0, sticky='nsew')
        self.card_scrollbar.grid(row=0, column=1, sticky='ns')

        card = ttk.Frame(self.card_canvas, style='Card.TFrame', padding=(24, 16))
        card_window = self.card_canvas.create_window((0, 0), window=card, anchor='nw')
        card.columnconfigure(0, weight=1)

        def _on_card_configure(_event: tk.Event) -> None:
            self.card_canvas.configure(scrollregion=self.card_canvas.bbox('all'))

        def _on_canvas_configure(_event: tk.Event) -> None:
            self.card_canvas.itemconfigure(card_window, width=self.card_canvas.winfo_width())

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

        def _bind_wheel(_event: tk.Event) -> None:
            self.bind_all('<MouseWheel>', _on_mousewheel)

        def _unbind_wheel(_event: tk.Event) -> None:
            self.unbind_all('<MouseWheel>')

        card.bind('<Configure>', _on_card_configure)
        self.card_canvas.bind('<Configure>', _on_canvas_configure)
        self.card_canvas.configure(yscrollcommand=_on_scroll_command)
        self.card_canvas.bind('<Enter>', _bind_wheel)
        self.card_canvas.bind('<Leave>', _unbind_wheel)

        source_header = ttk.Frame(card, style='Card.TFrame')
        source_header.grid(row=0, column=0, sticky='ew')
        source_header.columnconfigure(0, weight=1)
        ttk.Label(source_header, text='01  เลือกแหล่งสื่อ', style='Step.TLabel').grid(
            row=0,
            column=0,
            sticky='w',
        )
        source_kind_options = ttk.Frame(source_header, style='Card.TFrame')
        source_kind_options.grid(row=0, column=1, sticky='e')
        self.file_source_radio = ttk.Radiobutton(
            source_kind_options,
            text='ไฟล์ในเครื่อง',
            variable=self.input_kind,
            value='file',
            command=self._sync_source_kind,
            style='Segment.TRadiobutton',
        )
        self.file_source_radio.pack(side='left')
        self.url_source_radio = ttk.Radiobutton(
            source_kind_options,
            text='วางลิงก์',
            variable=self.input_kind,
            value='url',
            command=self._sync_source_kind,
            style='Segment.TRadiobutton',
        )
        self.url_source_radio.pack(side='left', padx=(6, 0))
        ttk.Label(
            card,
            textvariable=self.source_hint,
            style='CardMuted.TLabel',
        ).grid(row=1, column=0, sticky='w', pady=(1, 9))
        source_row = ttk.Frame(card, style='Card.TFrame')
        source_row.grid(row=2, column=0, sticky='ew')
        source_row.columnconfigure(0, weight=1)
        self.source_entry = ttk.Entry(source_row, textvariable=self.source, style='Dark.TEntry')
        self.source_entry.grid(
            row=0,
            column=0,
            sticky='ew',
            padx=(0, 10),
        )
        self.source_button = ttk.Button(
            source_row,
            textvariable=self.source_button_text,
            style='Secondary.TButton',
            command=self._source_action,
            width=18,
        )
        self.source_button.grid(
            row=0,
            column=1,
        )
        source_meta = ttk.Frame(card, style='Card.TFrame')
        source_meta.grid(row=3, column=0, sticky='ew', pady=(6, 10))
        source_meta.columnconfigure(0, weight=1)
        ttk.Label(
            source_meta,
            textvariable=self.source_detail,
            style='CardMuted.TLabel',
        ).grid(row=0, column=0, sticky='w')
        link_font = (self.ui_font, 9, 'underline')
        self.rights_row = ttk.Frame(source_meta, style='Card.TFrame')
        self.rights_row.grid(row=1, column=0, sticky='w', pady=(6, 0))
        self.rights_check = ttk.Checkbutton(
            self.rights_row,
            text='ฉันยืนยันว่าอ่านและยอมรับ',
            variable=self.authorized,
        )
        self.rights_check.pack(side='left')
        self.disclaimer_link = tk.Label(
            self.rights_row,
            text='คำปฏิเสธด้านลิขสิทธิ์',
            bg=CARD,
            fg=ACCENT,
            font=link_font,
            cursor='hand2',
        )
        self.disclaimer_link.pack(side='left')
        self.disclaimer_link.bind('<Button-1>', lambda _event: self._open_disclaimer())
        ttk.Label(
            self.rights_row,
            text='แล้ว และจะไม่ดาวน์โหลดเนื้อหาที่มีลิขสิทธิ์',
            style='CardMuted.TLabel',
        ).pack(side='left')
        self.dmca_row = ttk.Frame(source_meta, style='Card.TFrame')
        self.dmca_row.grid(row=2, column=0, sticky='w', pady=(2, 0))
        ttk.Label(
            self.dmca_row,
            text='ต้องการบล็อกการดาวน์โหลดวิดีโอที่มีลิขสิทธิ์?',
            style='CardMuted.TLabel',
        ).pack(side='left')
        self.dmca_link = tk.Label(
            self.dmca_row,
            text='รายงานได้ที่นี่',
            bg=CARD,
            fg=ACCENT,
            font=link_font,
            cursor='hand2',
        )
        self.dmca_link.pack(side='left', padx=(4, 0))
        self.dmca_link.bind('<Button-1>', lambda _event: self._open_dmca())
        self.rights_row.grid_remove()
        self.dmca_row.grid_remove()

        ttk.Separator(card, style='Card.TSeparator').grid(row=4, column=0, sticky='ew', pady=(0, 12))

        ttk.Label(card, text='02  เลือกที่บันทึก', style='Step.TLabel').grid(row=5, column=0, sticky='w')
        destination_row = ttk.Frame(card, style='Card.TFrame')
        destination_row.grid(row=6, column=0, sticky='ew', pady=(8, 12))
        destination_row.columnconfigure(0, weight=1)
        self.destination_entry = ttk.Entry(
            destination_row,
            textvariable=self.destination,
            style='Dark.TEntry',
        )
        self.destination_entry.grid(
            row=0,
            column=0,
            sticky='ew',
            padx=(0, 10),
        )
        self.destination_button = ttk.Button(
            destination_row,
            text='เลือกโฟลเดอร์',
            style='Secondary.TButton',
            command=self._choose_destination,
            width=14,
        )
        self.destination_button.grid(
            row=0,
            column=1,
        )

        ttk.Separator(card, style='Card.TSeparator').grid(row=7, column=0, sticky='ew', pady=(0, 12))
        ttk.Label(card, text='03  เลือกรูปแบบผลลัพธ์', style='Step.TLabel').grid(row=8, column=0, sticky='w')
        options = ttk.Frame(card, style='Card.TFrame')
        options.grid(row=9, column=0, sticky='ew', pady=(5, 0))
        options.columnconfigure(0, weight=1)

        mode_options = ttk.Frame(options, style='Card.TFrame')
        mode_options.grid(row=0, column=0, sticky='w')
        self.audio_radio = ttk.Radiobutton(
            mode_options,
            text='แยกเสียง',
            variable=self.mode,
            value='audio',
            command=self._sync_options,
            style='Segment.TRadiobutton',
        )
        self.audio_radio.pack(side='left')
        self.video_radio = ttk.Radiobutton(
            mode_options,
            text='แปลงเป็นวิดีโอ',
            variable=self.mode,
            value='video',
            command=self._sync_options,
            style='Segment.TRadiobutton',
        )
        self.video_radio.pack(side='left', padx=(6, 0))
        self.stems_radio = ttk.Radiobutton(
            mode_options,
            text='แยกสเต็มเสียง',
            variable=self.mode,
            value='stems',
            command=self._sync_options,
            style='Segment.TRadiobutton',
        )
        self.stems_radio.pack(side='left', padx=(6, 0))

        result_options = ttk.Frame(options, style='Card.TFrame')
        result_options.grid(row=0, column=1, sticky='e')
        self.option_label = ttk.Label(result_options, style='CardMuted.TLabel')
        self.option_label.grid(row=0, column=0, padx=(0, 10), sticky='e')
        self.format_box = ttk.Combobox(
            result_options,
            textvariable=self.audio_format,
            values=AUDIO_FORMAT_LABELS,
            state='readonly',
            style='Dark.TCombobox',
            width=12,
        )
        self.format_box.grid(row=0, column=1)
        self.video_format_box = ttk.Combobox(
            result_options,
            textvariable=self.video_format,
            values=VIDEO_FORMAT_LABELS,
            state='readonly',
            style='Dark.TCombobox',
            width=30,
        )
        self.video_format_box.grid(row=0, column=1)

        detail_options = ttk.Frame(options, style='Card.TFrame')
        detail_options.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(10, 0))
        detail_options.columnconfigure(1, weight=1)
        detail_options.columnconfigure(3, weight=1)
        self.quality_label = ttk.Label(detail_options, text='คุณภาพ', style='CardMuted.TLabel')
        self.quality_label.grid(row=0, column=0, padx=(0, 8), sticky='e')
        self.quality_box = ttk.Combobox(
            detail_options,
            textvariable=self.quality,
            values=VIDEO_QUALITY_PRESETS,
            state='readonly',
            style='Dark.TCombobox',
            width=12,
        )
        self.quality_box.grid(row=0, column=1, sticky='w')
        self.fps_label = ttk.Label(detail_options, text='เฟรมเรต', style='CardMuted.TLabel')
        self.fps_label.grid(row=0, column=2, padx=(16, 8), sticky='e')
        self.fps_box = ttk.Combobox(
            detail_options,
            textvariable=self.fps,
            values=FPS_LABELS,
            state='readonly',
            style='Dark.TCombobox',
            width=10,
        )
        self.fps_box.grid(row=0, column=3, sticky='w')

        stems_options = ttk.Frame(options, style='Card.TFrame')
        stems_options.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(10, 0))
        stems_options.columnconfigure(0, weight=1)
        self._stems_options = stems_options
        ttk.Label(
            stems_options,
            text='สเต็มที่ต้องการ',
            style='CardMuted.TLabel',
        ).grid(row=0, column=0, sticky='w')
        self._stem_check_widgets: list[ttk.Checkbutton] = []
        stem_row = ttk.Frame(stems_options, style='Card.TFrame')
        stem_row.grid(row=1, column=0, sticky='w', pady=(6, 0))
        for stem in SELECTABLE_STEMS:
            check = ttk.Checkbutton(
                stem_row,
                text=STEM_LABELS[stem],
                variable=self.stem_vars[stem],
                style='TCheckbutton',
            )
            check.pack(side='left', padx=(0, 14))
            self._stem_check_widgets.append(check)
        stems_options.grid_remove()

        action_card = ttk.Frame(main, style='Action.TFrame', padding=(20, 14))
        action_card.grid(row=2, column=0, sticky='ew', pady=(14, 8))
        action_card.columnconfigure(0, weight=1)
        progress_header = ttk.Frame(action_card, style='Action.TFrame')
        progress_header.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        progress_header.columnconfigure(0, weight=1)
        ttk.Label(progress_header, textvariable=self.status, style='Action.TLabel').grid(
            row=0,
            column=0,
            sticky='w',
        )
        ttk.Label(progress_header, textvariable=self.progress_text, style='ActionMuted.TLabel').grid(
            row=0,
            column=1,
            sticky='e',
        )
        self.progress = ttk.Progressbar(
            action_card,
            mode='determinate',
            maximum=100,
            style='Clipora.Horizontal.TProgressbar',
        )
        self.progress.grid(row=1, column=0, sticky='ew')
        self.start_button = ttk.Button(
            action_card,
            text='เริ่มแยกเสียง',
            style='Accent.TButton',
            command=self._start,
        )
        self.start_button.grid(row=2, column=0, sticky='ew', pady=(12, 0))
        ttk.Label(
            main,
            text='สร้างโดย ertyu.dev  •  ประมวลผลบนเครื่อง  •  ไม่มีโฆษณา  •  ไม่แก้ไขไฟล์ต้นฉบับ',
            style='Muted.TLabel',
            anchor='center',
        ).grid(row=3, column=0, sticky='ew')

        self._input_widgets = [
            self.file_source_radio,
            self.url_source_radio,
            self.source_entry,
            self.source_button,
            self.rights_check,
            self.destination_entry,
            self.destination_button,
            self.audio_radio,
            self.video_radio,
            self.stems_radio,
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
            self.audio_radio.configure(text='ดาวน์โหลดเฉพาะเสียง')
            self.video_radio.configure(text='ดาวน์โหลดวิดีโอ')
            self.stems_radio.configure(text='ดาวน์โหลดและแยกสเต็ม')
            self.rights_row.grid()
            self.dmca_row.grid()
        else:
            self.source_hint.set('เลือกวิดีโอที่ต้องการประมวลผล')
            self.source_button_text.set('เลือกไฟล์')
            self.audio_radio.configure(text='แยกเสียง')
            self.video_radio.configure(text='แปลงเป็นวิดีโอ')
            self.stems_radio.configure(text='แยกสเต็มเสียง')
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

    def _choose_destination(self) -> None:
        path = filedialog.askdirectory(title='เลือกโฟลเดอร์บันทึก')
        if path:
            self.destination.set(path)

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
        try:
            destination = destination_path(self.destination.get())
        except ValueError as exc:
            messagebox.showwarning('ไม่พบโฟลเดอร์', str(exc))
            return
        job = JobSpec(
            source=Path(self.source.get()),
            destination=destination,
            mode=self.mode.get(),
            quality=self.quality.get(),
            audio_format=self._audio_format_value(),
            video_format=self._video_format_value(),
            fps=self._fps_value(),
        )
        if not job.source.is_file():
            messagebox.showwarning('ยังไม่มีไฟล์', 'กรุณาเลือกไฟล์วิดีโอก่อน')
            return
        if not job.destination.is_dir():
            messagebox.showwarning('ไม่พบโฟลเดอร์', 'กรุณาเลือกโฟลเดอร์บันทึกที่มีอยู่')
            return
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
        if target.exists() and not messagebox.askyesno(
            'ไฟล์มีอยู่แล้ว',
            f'{target.name} มีอยู่แล้ว ต้องการเขียนทับหรือไม่?',
        ):
            return
        cancellation = CancellationToken()
        self._begin_job(cancellation, 'กำลังตรวจสอบไฟล์…', 'กำลังประมวลผล')
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
        try:
            destination = destination_path(self.destination.get())
        except ValueError as exc:
            messagebox.showwarning('ไม่พบโฟลเดอร์', str(exc))
            return
        source = Path(self.source.get())
        if not source.is_file():
            messagebox.showwarning('ยังไม่มีไฟล์', 'กรุณาเลือกไฟล์วิดีโอหรือเสียงก่อน')
            return
        if not destination.is_dir():
            messagebox.showwarning('ไม่พบโฟลเดอร์', 'กรุณาเลือกโฟลเดอร์บันทึกที่มีอยู่')
            return
        if not tools_available():
            self.status.set('ต้องติดตั้งเครื่องมือก่อนเริ่มงาน')
            self._open_tool_setup()
            return
        if not separator_installed():
            self.status.set('ต้องติดตั้งเครื่องมือแยกสเต็มก่อนเริ่มงาน')
            self._open_tool_setup(separator=True)
            return
        stems = self._selected_stems()
        if not stems:
            messagebox.showwarning('ยังไม่ได้เลือกสเต็ม', 'เลือกสเต็มอย่างน้อยหนึ่งรายการก่อนเริ่มงาน')
            return
        audio_format = self._audio_format_value()
        expected = separate_output_paths(source, destination, audio_format, stems)
        existing = [target for target in expected if target.exists()]
        overwrite = False
        if existing and not messagebox.askyesno(
            'ไฟล์มีอยู่แล้ว',
            'มีไฟล์ผลลัพธ์บางไฟล์อยู่แล้ว\n\n'
            + '\n'.join(target.name for target in existing[:5])
            + '\n\nต้องการเขียนทับหรือไม่?',
        ):
            return
        if existing:
            overwrite = True
        cancellation = CancellationToken()
        self._begin_job(cancellation, 'กำลังตรวจสอบไฟล์…', 'กำลังแยกสเต็ม')
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
                self._report_stems_phase,
                lambda value: self.after(0, self._set_progress, value, cancellation),
                cancellation,
                overwrite=overwrite,
            )
        except ConversionCancelled:
            self.after(0, self._cancelled, cancellation)
        except (SeparatorError, FFmpegError, OSError, ValueError) as exc:
            self.after(0, self._failed, str(exc), cancellation)
        else:
            self.after(0, self._done_stems, outputs, cancellation)

    def _start_stems_url(self) -> None:
        try:
            destination = destination_path(self.destination.get())
        except ValueError as exc:
            messagebox.showwarning('ไม่พบโฟลเดอร์', str(exc))
            return
        if not destination.is_dir():
            messagebox.showwarning('ไม่พบโฟลเดอร์', 'กรุณาเลือกโฟลเดอร์บันทึกที่มีอยู่')
            return
        try:
            url = validate_url(self.source.get())
        except ValueError as exc:
            messagebox.showwarning('ลิงก์ไม่ถูกต้อง', str(exc))
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
        if not stems:
            messagebox.showwarning('ยังไม่ได้เลือกสเต็ม', 'เลือกสเต็มอย่างน้อยหนึ่งรายการก่อนเริ่มงาน')
            return
        spec = ImportSpec(
            url=url,
            destination=destination,
            mode='audio',
            quality=self.quality.get(),
            audio_format=self._audio_format_value(),
        )
        cancellation = CancellationToken()
        self._begin_job(cancellation, 'กำลังตรวจสอบลิงก์…', 'กำลังแยกสเต็ม')
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
            completed, workspace = import_audio_for_processing(
                spec,
                lambda value: self.after(0, self._set_progress, value * 0.5, cancellation),
                cancellation,
            )
            try:
                outputs = separate_audio(
                    completed,
                    spec.destination,
                    spec.audio_format,
                    stems,
                    self._report_stems_phase,
                    lambda value: self.after(
                        0, self._set_progress, 0.5 + value * 0.5, cancellation
                    ),
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
            self.after(0, self._done_stems, outputs, cancellation)

    def _start_url(self) -> None:
        try:
            destination = destination_path(self.destination.get())
        except ValueError as exc:
            messagebox.showwarning('ไม่พบโฟลเดอร์', str(exc))
            return
        if not destination.is_dir():
            messagebox.showwarning('ไม่พบโฟลเดอร์', 'กรุณาเลือกโฟลเดอร์บันทึกที่มีอยู่')
            return
        try:
            url = validate_url(self.source.get())
        except ValueError as exc:
            messagebox.showwarning('ลิงก์ไม่ถูกต้อง', str(exc))
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
        cancellation = CancellationToken()
        self._begin_job(cancellation, 'กำลังตรวจสอบลิงก์…', 'กำลังดาวน์โหลด')
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
            command = build_command(
                job.source,
                temporary,
                job.mode,
                job.quality,
                job.audio_format,
                job.video_format,
                job.fps,
            )
            self.after(0, self.status.set, 'กำลังประมวลผล…')
            convert(
                command,
                temporary,
                info.duration,
                lambda value: self.after(0, self._set_progress, value, cancellation),
                cancellation,
            )
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

    def _run_import(self, job: ImportSpec, cancellation: CancellationToken) -> None:
        try:
            target = import_url(
                job,
                lambda value: self.after(0, self._set_progress, value, cancellation),
                cancellation,
            )
        except ConversionCancelled:
            self.after(0, self._cancelled, cancellation)
        except (URLImportError, OSError, ValueError) as exc:
            self.after(0, self._failed, str(exc), cancellation)
        else:
            self.after(0, self._done, target, cancellation)

    def _set_progress(self, value: float, cancellation: CancellationToken) -> None:
        if cancellation is not self._cancellation or cancellation.cancelled:
            return
        self.progress['value'] = value * 100
        self.progress_text.set(f'{value * 100:.0f}%')
        if self.mode.get() != 'stems':
            self.status.set(f'{self._progress_action}… {value * 100:.0f}%')

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
        self.progress['value'] = 100
        self.progress_text.set('100%')
        self.status.set(f'เสร็จแล้ว: {target.name}')
        if self.input_kind.get() == 'url':
            self.authorized.set(False)
        if messagebox.askyesno(
            'สำเร็จ',
            f'บันทึกไฟล์แล้ว\n{target}\n\nเปิดโฟลเดอร์หรือไม่?',
        ):
            os.startfile(target.parent)

    def _done_stems(self, outputs: list[Path], cancellation: CancellationToken) -> None:
        if not self._finish_job(cancellation):
            return
        self.progress['value'] = 100
        self.progress_text.set('100%')
        self.status.set(f'เสร็จแล้ว: {len(outputs)} ไฟล์')
        if self.input_kind.get() == 'url':
            self.authorized.set(False)
        lines = '\n'.join(str(path) for path in outputs[:20])
        extra = '' if len(outputs) <= 20 else f'\nและอีก {len(outputs) - 20} ไฟล์'
        if messagebox.askyesno(
            'สำเร็จ',
            f'แยกสเต็มเสร็จแล้ว {len(outputs)} ไฟล์\n\n{lines}{extra}\n\nเปิดโฟลเดอร์หรือไม่?',
        ):
            os.startfile(outputs[0].parent)

    def _cancelled(self, cancellation: CancellationToken) -> None:
        if not self._finish_job(cancellation):
            return
        self.progress['value'] = 0
        self.progress_text.set('0%')
        self.status.set('ยกเลิกงานแล้ว')

    def _failed(self, detail: str, cancellation: CancellationToken) -> None:
        if not self._finish_job(cancellation):
            return
        self.status.set('เกิดข้อผิดพลาด')
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

        ttk.Label(shell, text='คำปฏิเสธด้านลิขสิทธิ์', style='Heading.TLabel').grid(
            row=0, column=0, sticky='w'
        )
        ttk.Label(shell, text='อ่านและทำความเข้าใจก่อนเริ่มใช้งาน', style='Muted.TLabel').grid(
            row=1, column=0, sticky='w', pady=(2, 14)
        )
        text = tk.Text(
            shell,
            wrap='word',
            bg=FIELD,
            fg=TEXT,
            insertbackground=TEXT,
            relief='flat',
            borderwidth=0,
            padx=16,
            pady=14,
            font=(getattr(parent, 'ui_font', 'Segoe UI'), 10),
        )
        text.grid(row=2, column=0, sticky='nsew')
        text.insert('1.0', DISCLAIMER_TEXT)
        text.configure(state='disabled')
        close = ttk.Button(
            shell,
            text='ปิด',
            style='Accent.TButton',
            command=self.destroy,
        )
        close.grid(row=3, column=0, sticky='e', pady=(16, 0))
        self.grab_set()
        close.focus_set()


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
            font=(getattr(parent, 'ui_font', 'Segoe UI'), 10),
        )
        self.reason.grid(row=9, column=0, sticky='ew', pady=(4, 10))
        ttk.Label(shell, text=DMCA_NOTE, style='CardMuted.TLabel', wraplength=560).grid(
            row=10, column=0, sticky='w', pady=(0, 16)
        )
        ttk.Button(
            shell,
            text='ส่งรายงานทางอีเมล',
            style='Accent.TButton',
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
