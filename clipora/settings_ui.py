"""Settings popup: general prefs + default job values + about.

All values are plain strings/bools; the caller loads them from settings and
applies the saved dict (persisting is the caller's job). Theme changes need
an app restart — the dialog says so next to the theme picker.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable

from .ui_components.motion import fade_in_window
from .ui_components.theme import BG
from .ui_components.widgets import RoundedButton, RoundedCombobox, RoundedEntry, Switch

THEME_LABELS = {'เข้ม': 'dark', 'อ่อน': 'light', 'ตามระบบ': 'system'}
MODE_LABELS = {
    'แยกเสียง': 'audio',
    'แปลงเป็นวิดีโอ': 'video',
    'แยก Stem เสียง': 'stems',
}


def _label_for(mapping: dict[str, str], value: str, fallback: str) -> str:
    for label, mapped in mapping.items():
        if mapped == value:
            return label
    return fallback


class SettingsDialog(tk.Toplevel):
    """Modal settings editor; ``result`` is None when cancelled."""

    def __init__(
        self,
        parent: tk.Misc,
        initial: dict,
        version: str,
        on_uninstall: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title('ตั้งค่า Clipora')
        self.configure(bg=BG)
        self.transient(parent)
        self.geometry('600x680')
        self.minsize(520, 560)
        self.resizable(True, True)
        self.protocol('WM_DELETE_WINDOW', self._cancel)

        self.result: dict | None = None
        self._on_uninstall = on_uninstall

        self._theme = tk.StringVar(
            value=_label_for(THEME_LABELS, str(initial.get('theme', 'system')), 'ตามระบบ'))
        self._chime = tk.BooleanVar(value=bool(initial.get('chime', True)))
        self._auto_update = tk.BooleanVar(value=bool(initial.get('auto_update', True)))
        self._mode = tk.StringVar(
            value=_label_for(MODE_LABELS, str(initial.get('mode', 'video')), 'แปลงเป็นวิดีโอ'))
        self._audio_format = tk.StringVar(value=str(initial.get('audio_format', 'MP3')))
        self._video_format = tk.StringVar(value=str(initial.get('video_format', '')))
        self._quality = tk.StringVar(value=str(initial.get('quality', 'Balanced')))
        self._fps = tk.StringVar(value=str(initial.get('fps', '')))
        self._destination = tk.StringVar(value=str(initial.get('destination', '')))
        self._audio_formats = tuple(initial.get('audio_formats', ()))
        self._video_formats = tuple(initial.get('video_formats', ()))
        self._qualities = tuple(initial.get('qualities', ()))
        self._fps_options = tuple(initial.get('fps_options', ()))

        shell = ttk.Frame(self, padding=(28, 22, 28, 20))
        shell.pack(fill='both', expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        ttk.Label(shell, text='ตั้งค่า', style='Heading.TLabel').grid(
            row=0, column=0, sticky='w', pady=(0, 14))

        scroll_wrap = ttk.Frame(shell, style='TFrame')
        scroll_wrap.grid(row=1, column=0, sticky='nsew')
        scroll_wrap.columnconfigure(0, weight=1)
        scroll_wrap.rowconfigure(0, weight=1)
        self._body_canvas = tk.Canvas(
            scroll_wrap, bg=BG, highlightthickness=0, borderwidth=0)
        self._body_canvas.grid(row=0, column=0, sticky='nsew')
        body_scroll = ttk.Scrollbar(
            scroll_wrap, orient='vertical', command=self._body_canvas.yview)
        body_scroll.grid(row=0, column=1, sticky='ns')
        self._body_canvas.configure(yscrollcommand=self._scroll_set(body_scroll))
        body = ttk.Frame(self._body_canvas, style='TFrame')
        self._body_window = self._body_canvas.create_window(
            (0, 0), window=body, anchor='nw')
        body.columnconfigure(1, weight=1)
        body.bind('<Configure>', lambda _e: self._body_canvas.configure(
            scrollregion=self._body_canvas.bbox('all')))
        self._body_canvas.bind('<Configure>', self._fit_body_width)
        self._body_canvas.bind('<Enter>', lambda _e: self.bind_all(
            '<MouseWheel>', self._on_body_wheel, add='+'))
        self._body_canvas.bind('<Leave>', lambda _e: self.unbind_all('<MouseWheel>'))

        self._section(body, 'ทั่วไป', 0)
        self._combo_row(
            body, 1, 'ธีม', self._theme,
            tuple(THEME_LABELS), width=14,
            note='เปิดแอปใหม่ถึงมีผล',
        )
        self._switch_row(body, 2, 'เสียงแจ้งเตือน', self._chime)
        self._switch_row(body, 3, 'ตรวจอัปเดตอัตโนมัติ', self._auto_update)

        self._section(body, 'ค่าเริ่มต้นงาน', 4)
        self._combo_row(
            body, 5, 'โหมด', self._mode, tuple(MODE_LABELS), width=18)
        self._combo_row(
            body, 6, 'รูปแบบเสียง', self._audio_format,
            self._audio_formats or ('MP3',), width=18)
        self._combo_row(
            body, 7, 'รูปแบบวิดีโอ', self._video_format,
            self._video_formats or ('MP4',), width=18)
        self._combo_row(
            body, 8, 'คุณภาพ', self._quality,
            self._qualities or ('Balanced',), width=18)
        self._combo_row(
            body, 9, 'FPS', self._fps,
            self._fps_options or ('สูงสุด',), width=18)
        ttk.Label(body, text='โฟลเดอร์บันทึก', style='Muted.TLabel').grid(
            row=10, column=0, columnspan=2, sticky='w', pady=(8, 2))
        dest_row = ttk.Frame(body, style='TFrame')
        dest_row.grid(row=11, column=0, columnspan=2, sticky='ew', pady=(0, 2))
        dest_row.columnconfigure(0, weight=1)
        RoundedEntry(
            dest_row, textvariable=self._destination,
        ).grid(row=0, column=0, sticky='ew', padx=(0, 8))
        RoundedButton(
            dest_row, text='เลือก…', width=6,
            command=self._browse,
        ).grid(row=0, column=1)

        self._section(body, 'เกี่ยวกับ', 12)
        ttk.Label(
            body, text=f'Clipora v{version}', style='Muted.TLabel',
        ).grid(row=13, column=0, columnspan=2, sticky='w', pady=(2, 0))
        ttk.Label(
            body,
            text='แยกเสียง • แปลงวิดีโอ • แยก Stem เสียง ทำในเครื่อง ไม่ต้องสมัครสมาชิก',
            style='Muted.TLabel', wraplength=500, justify='left',
        ).grid(row=14, column=0, columnspan=2, sticky='w')
        ttk.Label(
            body,
            text='ข้อมูลในเครื่อง: %LOCALAPPDATA%\\Clipora (ถอนหมดจดเมื่อถอนติดตั้ง)',
            style='Muted.TLabel', wraplength=500, justify='left',
        ).grid(row=15, column=0, columnspan=2, sticky='w')
        self._danger_expanded = False
        self._danger_toggle = ttk.Button(
            body, text='▸ ถอนการติดตั้ง', style='Ghost.TButton',
            command=self._toggle_danger,
        )
        self._danger_toggle.grid(
            row=16, column=0, columnspan=2, sticky='w', pady=(8, 0))
        self._danger_box = ttk.Frame(body, style='TFrame')
        self._danger_box.grid(
            row=17, column=0, columnspan=2, sticky='ew', pady=(4, 0))
        self._danger_box.columnconfigure(0, weight=1)
        ttk.Label(
            self._danger_box,
            text='ลบโปรแกรม + เครื่องมือ + ตั้งค่าในเครื่อง (ไฟล์งานของคุณไม่ถูกลบ)',
            style='Muted.TLabel', wraplength=500, justify='left',
        ).grid(row=0, column=0, sticky='w')
        RoundedButton(
            self._danger_box, text='ถอนการติดตั้ง…', width=12,
            command=self._uninstall,
        ).grid(row=1, column=0, sticky='w', pady=(8, 0))
        self._danger_box.grid_remove()

        actions = ttk.Frame(shell, style='TFrame')
        actions.grid(row=2, column=0, sticky='e', pady=(16, 0))
        ttk.Button(
            actions, text='ยกเลิก', style='Secondary.TButton',
            command=self._cancel,
        ).pack(side='left', padx=(0, 8))
        ttk.Button(
            actions, text='บันทึก', style='DialogAccent.TButton',
            command=self._save,
        ).pack(side='left')

        fade_in_window(self, self.after)
        self.grab_set()
        self.after_idle(self.focus_set)

    def _toggle_danger(self) -> None:
        self._danger_expanded = not self._danger_expanded
        try:
            if self._danger_expanded:
                self._danger_toggle.configure(text='▾ ถอนการติดตั้ง')
                self._danger_box.grid()
            else:
                self._danger_toggle.configure(text='▸ ถอนการติดตั้ง')
                self._danger_box.grid_remove()
        except tk.TclError:
            pass

    def _uninstall(self) -> None:
        if self._on_uninstall is not None:
            self._on_uninstall()

    def _scroll_set(self, scrollbar: ttk.Scrollbar):
        """Hide the scrollbar when everything fits (like the main view)."""
        def _set(first: str, last: str) -> None:
            scrollbar.set(first, last)
            try:
                if float(first) <= 0.0 and float(last) >= 1.0:
                    scrollbar.grid_remove()
                else:
                    scrollbar.grid()
            except (tk.TclError, ValueError):
                pass
        return _set

    def _fit_body_width(self, event: tk.Event) -> None:
        try:
            self._body_canvas.itemconfigure(self._body_window, width=event.width)
        except tk.TclError:
            pass

    def _on_body_wheel(self, event: tk.Event) -> None:
        try:
            delta = int(getattr(event, 'delta', 0))
        except (TypeError, ValueError):
            return
        if delta:
            try:
                self._body_canvas.yview_scroll(int(-delta / 120), 'units')
            except tk.TclError:
                pass

    def _section(self, parent: ttk.Frame, title: str, row: int) -> None:
        ttk.Label(parent, text=title, style='SectionTitle.TLabel').grid(
            row=row, column=0, columnspan=2, sticky='w', pady=(10 if row else 0, 4))

    def _combo_row(self, parent: ttk.Frame, row: int, label: str,
                   variable: tk.StringVar, values: tuple[str, ...],
                   width: int, note: str = '') -> None:
        text = label if not note else f'{label} ({note})'
        ttk.Label(parent, text=text, style='Muted.TLabel').grid(
            row=row, column=0, sticky='e', padx=(0, 10), pady=(2, 0))
        RoundedCombobox(
            parent, textvariable=variable, values=values, width=width,
        ).grid(row=row, column=1, sticky='w', pady=(2, 0))

    def _switch_row(self, parent: ttk.Frame, row: int, label: str,
                    variable: tk.BooleanVar) -> None:
        ttk.Label(parent, text=label, style='Muted.TLabel').grid(
            row=row, column=0, sticky='e', padx=(0, 10), pady=(2, 0))
        Switch(parent, text='', variable=variable).grid(
            row=row, column=1, sticky='w', pady=(2, 0))

    def _browse(self) -> None:
        path = filedialog.askdirectory(title='เลือกโฟลเดอร์บันทึก', parent=self)
        if path:
            self._destination.set(path)

    def _close_popups(self) -> None:
        try:
            RoundedCombobox.close_open()
        except (tk.TclError, AttributeError):
            pass

    def _save(self) -> None:
        self._close_popups()
        self.result = {
            'theme': THEME_LABELS.get(self._theme.get(), 'system'),
            'chime': bool(self._chime.get()),
            'auto_update': bool(self._auto_update.get()),
            'mode': MODE_LABELS.get(self._mode.get(), 'video'),
            'audio_format': self._audio_format.get(),
            'video_format': self._video_format.get(),
            'quality': self._quality.get(),
            'fps': self._fps.get(),
            'destination': self._destination.get().strip(),
        }
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()

    def _cancel(self) -> None:
        self._close_popups()
        self.result = None
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
