from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk

from .ffmpeg import (
    CancellationToken,
    ConversionCancelled,
    FFmpegError,
    JobSpec,
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
    import_url,
    url_summary,
    validate_url,
    ytdlp_available,
)
from .setup_ui import ToolSetupDialog
from .tools import missing_required_tools


BG = '#090d15'
CARD = '#141a26'
FIELD = '#0d1320'
BORDER = '#293348'
TEXT = '#f7f8fc'
MUTED = '#96a3b8'
ACCENT = '#7c5cff'
ACCENT_HOVER = '#6c4df0'
DANGER = '#e35d6a'


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
        self.minsize(780, 650)
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
        self.audio_format = tk.StringVar(value='mp3')
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
        self._build()
        self.source.trace_add('write', self._on_source_changed)
        self.bind_all('<Control-KeyPress>', self._on_control_keypress, add='+')
        self.bind_all('<Shift-Insert>', self._on_paste_shortcut, add='+')
        self.after_idle(self.source_entry.focus_set)
        self.after(120, self._maybe_offer_tool_setup)
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
            text='ดาวน์โหลด แปลงวิดีโอ และแยกเสียงบนเครื่องของคุณ',
            style='Muted.TLabel',
        ).grid(row=1, column=1, sticky='w')
        ttk.Button(
            header,
            text='เครื่องมือ',
            style='Header.TButton',
            command=lambda: self._open_tool_setup(repair_mode=True),
        ).grid(
            row=0,
            column=2,
            rowspan=2,
            sticky='e',
        )

        card = ttk.Frame(main, style='Card.TFrame', padding=(24, 16))
        card.grid(row=1, column=0, sticky='nsew')
        card.columnconfigure(0, weight=1)

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
        self.rights_check = ttk.Checkbutton(
            source_meta,
            text='ฉันมีสิทธิ์ดาวน์โหลดสื่อนี้',
            variable=self.authorized,
        )
        self.rights_check.grid(row=1, column=0, sticky='w', pady=(5, 0))
        self.rights_check.grid_remove()

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
        ttk.Label(card, text='03  เลือกรูปแบบ', style='Step.TLabel').grid(row=8, column=0, sticky='w')
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
            text='แปลงเป็น MP4',
            variable=self.mode,
            value='video',
            command=self._sync_options,
            style='Segment.TRadiobutton',
        )
        self.video_radio.pack(side='left', padx=(6, 0))

        format_options = ttk.Frame(options, style='Card.TFrame')
        format_options.grid(row=0, column=1, sticky='e')
        self.option_label = ttk.Label(format_options, style='CardMuted.TLabel')
        self.option_label.grid(row=0, column=0, padx=(0, 10))
        self.format_box = ttk.Combobox(
            format_options,
            textvariable=self.audio_format,
            values=('mp3', 'm4a'),
            state='readonly',
            style='Dark.TCombobox',
            width=10,
        )
        self.format_box.grid(row=0, column=1)
        self.quality_box = ttk.Combobox(
            format_options,
            textvariable=self.quality,
            values=('High', 'Balanced', 'Small'),
            state='readonly',
            style='Dark.TCombobox',
            width=12,
        )
        self.quality_box.grid(row=0, column=1)

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
            text='ประมวลผลบนเครื่อง  •  ไม่มีโฆษณา  •  ไม่แก้ไขไฟล์ต้นฉบับ',
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
            self.format_box,
            self.quality_box,
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

    def _sync_options(self) -> None:
        if self.mode.get() == 'audio':
            self.quality_box.grid_remove()
            self.format_box.grid()
            self.option_label.configure(text='ไฟล์เสียง')
            action_text = (
                'เริ่มดาวน์โหลดเสียง'
                if self.input_kind.get() == 'url'
                else 'เริ่มแยกเสียง'
            )
        else:
            self.format_box.grid_remove()
            self.quality_box.grid()
            self.option_label.configure(text='คุณภาพ')
            if self.input_kind.get() == 'url':
                self.quality_box.configure(values=VIDEO_QUALITIES)
                if self.quality.get() not in VIDEO_QUALITIES:
                    self.quality.set(VIDEO_QUALITIES[0])
                action_text = 'เริ่มดาวน์โหลดวิดีโอ'
            else:
                local_qualities = ('High', 'Balanced', 'Small')
                self.quality_box.configure(values=local_qualities)
                if self.quality.get() not in local_qualities:
                    self.quality.set('Balanced')
                action_text = 'เริ่มแปลงเป็น MP4'
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
            self.source_hint.set('วางลิงก์สาธารณะจาก YouTube, Facebook, Instagram หรือเว็บที่รองรับ')
            self.source_button_text.set('วางจากคลิปบอร์ด')
            self.audio_radio.configure(text='ดาวน์โหลดเฉพาะเสียง')
            self.video_radio.configure(text='ดาวน์โหลดวิดีโอ')
            self.rights_check.grid()
        else:
            self.source_hint.set('เลือกวิดีโอที่ต้องการประมวลผล')
            self.source_button_text.set('เลือกไฟล์')
            self.audio_radio.configure(text='แยกเสียง')
            self.video_radio.configure(text='แปลงเป็น MP4')
            self.rights_check.grid_remove()
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
        if self.input_kind.get() == 'url':
            self._start_url()
        else:
            self._start_local()

    def _start_local(self) -> None:
        job = JobSpec(
            source=Path(self.source.get()),
            destination=Path(self.destination.get()),
            mode=self.mode.get(),
            quality=self.quality.get(),
            audio_format=self.audio_format.get(),
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

        target = output_path(job.source, job.destination, job.mode, job.audio_format)
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

    def _start_url(self) -> None:
        destination = Path(self.destination.get())
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
            audio_format=self.audio_format.get(),
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
