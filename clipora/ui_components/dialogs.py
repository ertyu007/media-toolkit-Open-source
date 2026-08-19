"""Application-styled modal dialogs shared by the main window."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from .format import format_file_size
from .theme import (
    ACCENT,
    ACCENT_HOVER,
    BORDER,
    CARD,
    DISABLED_FG,
    ERROR,
    FIELD,
    MUTED,
    TEXT,
)

OVERWRITE = 'overwrite'
KEEP = 'keep'
CANCEL = 'cancel'


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

        ui_font = getattr(parent, 'ui_font', 'Segoe UI')
        shell = ttk.Frame(self, style='Card.TFrame', padding=(24, 20))
        shell.pack(fill='both', expand=True)
        shell.columnconfigure(0, weight=1)

        ttk.Label(
            shell,
            text='มีไฟล์ชื่อเดียวกันอยู่แล้ว',
            style='Card.TLabel',
            font=(ui_font, 13, 'bold'),
        ).grid(row=0, column=0, sticky='w')

        ttk.Label(
            shell,
            text=filename,
            style='CardMuted.TLabel',
            font=(ui_font, 10),
            wraplength=420,
            justify='left',
        ).grid(row=1, column=0, sticky='w', pady=(4, 12))

        if detail:
            ttk.Label(
                shell,
                text=detail,
                style='CardMuted.TLabel',
                font=(ui_font, 9),
                wraplength=420,
                justify='left',
            ).grid(row=2, column=0, sticky='w', pady=(0, 12))

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
        size_lbl.grid(row=3, column=0, sticky='w', pady=(0, 18))

        buttons = ttk.Frame(shell, style='Card.TFrame')
        buttons.grid(row=4, column=0, sticky='ew')
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