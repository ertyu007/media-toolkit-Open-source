"""Application-styled modal dialogs shared by the main window."""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from .format import format_file_size
from .motion import fade_in_window
from .theme import (
    ACCENT,
    BORDER,
    CARD,
    FIELD,
    FONT_FAMILY,
    TEXT,
)

OVERWRITE = 'overwrite'
KEEP = 'keep'
CANCEL = 'cancel'

ACTION_UPDATE = 'update'
ACTION_REMIND_LATER = 'remind_later'
ACTION_SKIP_VERSION = 'skip_version'
ACTION_CANCEL_UPDATE = 'cancel_update'
ACTION_RESTART_UPDATE = 'restart_update'

MAX_ERROR_CHARS = 1500
_LOCAL_PATH_PLACEHOLDER = '<เส้นทางในเครื่อง>'
_UNC_PATH_RE = re.compile(r'\\\\[^\s"\']+')
# Lookbehind keeps the scheme letter of URLs (https://…) from matching as a
# drive letter; real drive paths start a segment (start/space/quote/paren).
_DRIVE_PATH_RE = re.compile(r'(?<![A-Za-z])[A-Za-z]:[\\/][^\s"\']*')


def sanitize_error_message(message: str, max_chars: int = MAX_ERROR_CHARS) -> str:
    """Redact full local paths and cap length for user-facing errors."""
    text = _UNC_PATH_RE.sub(_LOCAL_PATH_PLACEHOLDER, message)
    text = _DRIVE_PATH_RE.sub(_LOCAL_PATH_PLACEHOLDER, text)
    if len(text) > max_chars:
        text = '…' + text[-max_chars:]
    return text


class OverwriteDialog(tk.Toplevel):
    """Ask whether to replace an existing output file.

    Returns one of :data:`OVERWRITE`, :data:`KEEP` or :data:`CANCEL` through
    the ``on_result`` callback (or the :attr:`result` attribute after the
    dialog closes). Displays the existing size and, when known, the size of the
    new file so the user can decide before overwriting.
    """

    def __init__(
        self,
        parent: tk.Misc,
        filename: str,
        existing_size: int = 0,
        new_size: int | None = None,
        detail: str | None = None,
        on_result: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.result: str | None = None
        self._on_result = on_result
        self.title('ไฟล์มีอยู่แล้ว')
        self.configure(bg=CARD)
        self.transient(parent)
        self.resizable(False, False)
        self.protocol('WM_DELETE_WINDOW', lambda: self._close(CANCEL))

        ui_font = getattr(parent, 'ui_font', FONT_FAMILY)
        shell = ttk.Frame(self, style='Card.TFrame', padding=(24, 20))
        shell.pack(fill='both', expand=True)
        shell.columnconfigure(1, weight=1)

        accent_bar = tk.Frame(shell, bg=ACCENT, width=3, height=200)
        accent_bar.grid(row=0, column=0, rowspan=5, sticky='ns', padx=(0, 18))

        ttk.Label(
            shell,
            text='มีไฟล์ชื่อเดียวกันอยู่แล้ว',
            style='Card.TLabel',
            font=(ui_font, 13, 'bold'),
        ).grid(row=0, column=1, sticky='w')

        ttk.Label(
            shell,
            text=filename,
            style='CardMuted.TLabel',
            font=(ui_font, 10),
            wraplength=420,
            justify='left',
        ).grid(row=1, column=1, sticky='w', pady=(4, 12))

        if detail:
            ttk.Label(
                shell,
                text=detail,
                style='CardMuted.TLabel',
                font=(ui_font, 9),
                wraplength=420,
                justify='left',
            ).grid(row=2, column=1, sticky='w', pady=(0, 12))

        # Size comparison
        sizes = f'ขนาดไฟล์เดิม: {format_file_size(existing_size)}'
        if new_size is not None:
            sizes += f'\nขนาดไฟล์ใหม่: {format_file_size(new_size)}'
        size_lbl = ttk.Label(
            shell,
            text=sizes,
            style='CardMuted.TLabel',
            font=(ui_font, 9),
            justify='left',
        )
        size_lbl.grid(row=3, column=1, sticky='w', pady=(0, 18))

        buttons = ttk.Frame(shell, style='Card.TFrame')
        buttons.grid(row=4, column=1, sticky='ew')
        buttons.columnconfigure(0, weight=1)

        keep_btn = ttk.Button(
            buttons,
            text='เก็บทั้งสองไฟล์',
            style='Secondary.TButton',
            command=lambda: self._close(KEEP),
        )
        keep_btn.grid(row=0, column=1, padx=(8, 0))

        cancel_btn = ttk.Button(
            buttons,
            text='ยกเลิก',
            style='Secondary.TButton',
            command=lambda: self._close(CANCEL),
        )
        cancel_btn.grid(row=0, column=2, padx=(8, 0))

        overwrite_btn = ttk.Button(
            buttons,
            text='เขียนทับ',
            style='DialogAccent.TButton',
            command=lambda: self._close(OVERWRITE),
        )
        overwrite_btn.grid(row=0, column=3, padx=(8, 0))

        self._center_on(parent)
        fade_in_window(self, self.after)
        self.grab_set()
        self.bind('<Escape>', lambda _e: self._close(CANCEL))
        overwrite_btn.focus_set()
        self.wait_window(self)

    def _close(self, result: str) -> None:
        self.result = result
        if self._on_result is not None:
            self._on_result(result)
        self.destroy()

    def _center_on(self, parent: tk.Misc) -> None:
        self.update_idletasks()
        try:
            parent_x = parent.winfo_rootx()
            parent_y = parent.winfo_rooty()
            parent_w = parent.winfo_width()
            parent_h = parent.winfo_height()
        except tk.TclError:
            return
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        x = parent_x + (parent_w - width) // 2
        y = parent_y + (parent_h - height) // 2
        self.geometry(f'+{max(0, x)}+{max(0, y)}')


class ErrorDialog(tk.Toplevel):
    """Dialog showing an error detail with a convenient copy button."""

    def __init__(self, parent: tk.Misc, title: str, message: str) -> None:
        super().__init__(parent)
        self.title(title)
        message = sanitize_error_message(message)
        self.configure(bg=CARD)
        self.transient(parent)
        self.resizable(True, True)

        ui_font = getattr(parent, 'ui_font', FONT_FAMILY)
        shell = ttk.Frame(self, style='Card.TFrame', padding=(24, 20))
        shell.pack(fill='both', expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        ttk.Label(
            shell,
            text=title,
            style='Card.TLabel',
            font=(ui_font, 12, 'bold'),
        ).grid(row=0, column=0, sticky='w', pady=(0, 10))

        text_frame = ttk.Frame(shell, style='Card.TFrame')
        text_frame.grid(row=1, column=0, sticky='nsew', pady=(0, 14))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        text_widget = tk.Text(
            text_frame,
            wrap='word',
            bg=FIELD,
            fg=TEXT,
            insertbackground=TEXT,
            font=(ui_font, 9),
            height=10,
            width=60,
            borderwidth=1,
            relief='solid',
        )
        text_widget.insert('1.0', message)
        text_widget.configure(state='disabled')
        text_widget.grid(row=0, column=0, sticky='nsew')

        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=text_widget.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        text_widget.configure(yscrollcommand=scrollbar.set)

        buttons = ttk.Frame(shell, style='Card.TFrame')
        buttons.grid(row=2, column=0, sticky='e')

        copy_btn = ttk.Button(
            buttons,
            text='คัดลอก Error Log',
            style='Secondary.TButton',
            command=lambda: self._copy_to_clipboard(message),
        )
        copy_btn.grid(row=0, column=0, padx=(0, 8))

        close_btn = ttk.Button(
            buttons,
            text='ปิด',
            style='DialogAccent.TButton',
            command=self.destroy,
        )
        close_btn.grid(row=0, column=1)

        self._center_on(parent)
        fade_in_window(self, self.after)
        self.grab_set()
        self.bind('<Escape>', lambda _e: self.destroy())
        close_btn.focus_set()

    def _copy_to_clipboard(self, message: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(message)
        self.update()

    def _center_on(self, parent: tk.Misc) -> None:
        self.update_idletasks()
        try:
            parent_x = parent.winfo_rootx()
            parent_y = parent.winfo_rooty()
            parent_w = parent.winfo_width()
            parent_h = parent.winfo_height()
        except tk.TclError:
            return
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        x = parent_x + (parent_w - width) // 2
        y = parent_y + (parent_h - height) // 2
        self.geometry(f'+{max(0, x)}+{max(0, y)}')


class AppUpdateDialog(tk.Toplevel):
    """OBS Studio-styled modal update notification dialog for Clipora."""

    def __init__(
        self,
        parent: tk.Misc,
        release_info: Any,
        on_action: Callable[[str], bool | None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.result: str | None = None
        self._release_info = release_info
        self._on_action = on_action
        self._downloading = False
        self._ready_to_restart = False
        self.title('พบการอัปเดตใหม่')
        self.configure(bg=CARD)
        self.transient(parent)
        self.geometry('560x560')
        self.minsize(480, 460)
        self.protocol('WM_DELETE_WINDOW', lambda: self._close(ACTION_REMIND_LATER))

        ui_font = getattr(parent, 'ui_font', FONT_FAMILY)

        shell = ttk.Frame(self, style='Card.TFrame', padding=(24, 20))
        shell.pack(fill='both', expand=True)
        shell.rowconfigure(1, weight=1)
        shell.columnconfigure(0, weight=1)

        # Header label
        ttk.Label(
            shell,
            text='มี Clipora เวอร์ชันใหม่พร้อมให้อัปเดต:',
            style='CardMuted.TLabel',
            font=(ui_font, 10),
        ).grid(row=0, column=0, sticky='w', pady=(0, 10))

        # Main release container / card
        card = ttk.Frame(shell, style='CardBorder.TFrame', padding=(16, 14))
        card.grid(row=1, column=0, sticky='nsew', pady=(0, 18))
        card.rowconfigure(1, weight=1)
        card.columnconfigure(0, weight=1)

        # Release title
        title_text = getattr(release_info, 'title', None) or f'Clipora {getattr(release_info, "version", "")}'
        ttk.Label(
            card,
            text=title_text,
            style='Card.TLabel',
            font=(ui_font, 14, 'bold'),
        ).grid(row=0, column=0, sticky='w', pady=(0, 10))

        # Release notes text area with scrollbar
        text_frame = tk.Frame(card, bg=FIELD, highlightbackground=BORDER, highlightthickness=1)
        text_frame.grid(row=1, column=0, sticky='nsew')
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        notes_text = tk.Text(
            text_frame,
            bg=FIELD,
            fg=TEXT,
            insertbackground=TEXT,
            selectbackground=ACCENT,
            selectforeground='#ffffff',
            relief='flat',
            wrap='word',
            font=(ui_font, 10),
            padx=10,
            pady=8,
            borderwidth=0,
            highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=notes_text.yview)
        notes_text.configure(yscrollcommand=scrollbar.set)

        notes_text.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')

        raw_notes = getattr(release_info, 'release_notes', '') or ''
        notes_content = raw_notes.strip() if raw_notes.strip() else 'มีการปรับปรุงประสิทธิภาพและแก้ไขข้อผิดพลาดทั่วไป'
        notes_text.insert('1.0', notes_content)
        notes_text.configure(state='disabled')

        from ..app_update import AppUpdateError, update_space_requirements

        download_size = getattr(release_info, 'download_size', None)
        status_text = 'ตรวจสอบพื้นที่ว่างก่อนดาวน์โหลด'
        space_valid = False
        if isinstance(download_size, int) and download_size > 0:
            try:
                _cache_required, temp_required = update_space_requirements(download_size)
            except AppUpdateError:
                status_text = 'ขนาดไฟล์อัปเดตเกินขีดจำกัดที่รองรับ'
            else:
                space_valid = True
                status_text = (
                    f'ขนาดดาวน์โหลด {format_file_size(download_size)} · '
                    f'แนะนำพื้นที่ว่างชั่วคราวประมาณ {format_file_size(temp_required)}'
                )
        self.status_var = tk.StringVar(value=status_text)
        ttk.Label(
            shell,
            textvariable=self.status_var,
            style='CardMuted.TLabel',
            font=(ui_font, 9),
        ).grid(row=2, column=0, sticky='w', pady=(0, 6))
        self.progress = ttk.Progressbar(
            shell,
            orient='horizontal',
            mode='determinate',
            maximum=100,
        )
        self.progress.grid(row=3, column=0, sticky='ew', pady=(0, 14))

        # Buttons row
        buttons = ttk.Frame(shell, style='Card.TFrame')
        buttons.grid(row=4, column=0, sticky='ew')
        buttons.columnconfigure(0, weight=1)

        btn_box = ttk.Frame(buttons, style='Card.TFrame')
        btn_box.pack(side='right')

        self.update_btn = ttk.Button(
            btn_box,
            text='อัปเดตทันที',
            style='DialogAccent.TButton',
            command=self._on_update,
        )
        self.update_btn.pack(side='left', padx=(0, 8))

        self.remind_btn = ttk.Button(
            btn_box,
            text='เตือนฉันภายหลัง',
            style='Secondary.TButton',
            command=lambda: self._close(ACTION_REMIND_LATER),
        )
        self.remind_btn.pack(side='left', padx=(0, 8))

        self.skip_btn = ttk.Button(
            btn_box,
            text='ข้ามเวอร์ชันนี้',
            style='Secondary.TButton',
            command=self._on_skip,
        )
        self.skip_btn.pack(side='left')
        if (
            not getattr(release_info, 'download_url', None)
            or not getattr(release_info, 'checksum_url', None)
            or not space_valid
        ):
            self.update_btn.state(['disabled'])
            self.status_var.set('Release นี้ไม่มีข้อมูล installer/checksum สำหรับอัปเดตในแอป')

        self._center_on(parent)
        fade_in_window(self, self.after)
        self.grab_set()
        self.bind('<Escape>', lambda _e: self._close(ACTION_REMIND_LATER))
        self.update_btn.focus_set()

    def _on_update(self) -> None:
        if self._on_action is None or self._downloading or self._ready_to_restart:
            return
        self._downloading = True
        self.update_btn.state(['disabled'])
        self.remind_btn.configure(text='ยกเลิกดาวน์โหลด', command=self._cancel_download)
        self.skip_btn.state(['disabled'])
        self.status_var.set('กำลังเตรียมดาวน์โหลด…')
        self._on_action(ACTION_UPDATE)

    def start_download(self, status: str | None = None) -> None:
        if status:
            self.status_var.set(status)

    def update_download_progress(self, downloaded: int, total: int, elapsed_seconds: float) -> None:
        if not self.winfo_exists():
            return
        percent = min(100.0, downloaded * 100 / total) if total > 0 else 0.0
        self.progress['value'] = percent
        speed = downloaded / elapsed_seconds if elapsed_seconds > 0 else 0.0
        remaining = max(0.0, (total - downloaded) / speed) if speed > 0 else 0.0
        self.status_var.set(
            f'กำลังดาวน์โหลด {percent:.0f}% · {format_file_size(downloaded)} / '
            f'{format_file_size(total)} · เหลือประมาณ {self._format_eta(remaining)}'
        )

    def download_ready(self) -> None:
        if not self.winfo_exists():
            return
        self._downloading = False
        self._ready_to_restart = True
        self.progress['value'] = 100
        self.status_var.set('ดาวน์โหลดและตรวจสอบ SHA-256 เรียบร้อย พร้อมติดตั้ง')
        self.update_btn.configure(text='รีสตาร์ทเพื่ออัปเดต', command=self._on_restart)
        self.update_btn.state(['!disabled'])
        self.remind_btn.configure(text='ภายหลัง', command=lambda: self._close(ACTION_REMIND_LATER))
        self.remind_btn.state(['!disabled'])

    def download_failed(self, message: str, cancelled: bool = False) -> None:
        if not self.winfo_exists():
            return
        self._downloading = False
        self._ready_to_restart = False
        self.progress['value'] = 0
        self.status_var.set(message)
        self.update_btn.configure(text='ลองดาวน์โหลดอีกครั้ง', command=self._on_update)
        self.update_btn.state(['!disabled'])
        remind_text = 'ปิด' if cancelled else 'เตือนฉันภายหลัง'
        self.remind_btn.configure(text=remind_text, command=lambda: self._close(ACTION_REMIND_LATER))
        self.remind_btn.state(['!disabled'])
        self.skip_btn.state(['!disabled'])

    def restart_failed(self, message: str) -> None:
        if not self.winfo_exists():
            return
        self.status_var.set(message)
        self.update_btn.configure(text='ลองรีสตาร์ทอีกครั้ง', command=self._on_restart)
        self.update_btn.state(['!disabled'])

    def _cancel_download(self) -> None:
        if self._on_action is not None:
            self.remind_btn.state(['disabled'])
            self.status_var.set('กำลังยกเลิกการดาวน์โหลด…')
            self._on_action(ACTION_CANCEL_UPDATE)

    def _on_restart(self) -> None:
        if self._on_action is not None:
            accepted = self._on_action(ACTION_RESTART_UPDATE)
            if accepted is not False:
                self._close(ACTION_RESTART_UPDATE, notify=False)

    @staticmethod
    def _format_eta(seconds: float) -> str:
        total_seconds = max(0, int(seconds))
        minutes, remainder = divmod(total_seconds, 60)
        return f'{minutes} นาที {remainder} วินาที' if minutes else f'{remainder} วินาที'

    def _on_skip(self) -> None:
        from ..app_update import set_skipped_version
        version = getattr(self._release_info, 'version', None)
        if version:
            set_skipped_version(str(version))
        self._close(ACTION_SKIP_VERSION)

    def _close(self, result: str, notify: bool = True) -> None:
        self.result = result
        if notify and self._on_action is not None:
            self._on_action(result)
        self.destroy()

    def _center_on(self, parent: tk.Misc) -> None:
        self.update_idletasks()
        try:
            parent_x = parent.winfo_rootx()
            parent_y = parent.winfo_rooty()
            parent_w = parent.winfo_width()
            parent_h = parent.winfo_height()
        except tk.TclError:
            return
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        x = parent_x + (parent_w - width) // 2
        y = parent_y + (parent_h - height) // 2
        self.geometry(f'+{max(0, x)}+{max(0, y)}')
