from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from .theme import (
    ACCENT,
    DROPZONE_BG,
    DROPZONE_HOVER_BG,
    ERROR,
    SUCCESS,
    TEXT,
    TOAST_BG,
    WARNING,
)


class InlineError(ttk.Frame):
    """Inline error message shown below a field."""

    def __init__(self, parent: tk.Misc, **kwargs) -> None:
        super().__init__(parent, style='Card.TFrame', **kwargs)
        self._label = ttk.Label(self, text='', style='Error.TLabel', wraplength=500)
        self._label.pack(fill='x', padx=4, pady=(4, 0))
        self.grid_remove()

    def show(self, message: str) -> None:
        self._label.configure(text=message)
        self.grid()

    def hide(self) -> None:
        self._label.configure(text='')
        self.grid_remove()

    def is_visible(self) -> bool:
        return self._label.cget('text') != ''


class SegmentedControl(ttk.Frame):
    """Segmented control (tab-like) for mutually exclusive options."""

    def __init__(
        self,
        parent: tk.Misc,
        options: list[tuple[str, str]],
        variable: tk.StringVar,
        command: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, style='Card.TFrame', **kwargs)
        self._variable = variable
        self._command = command
        self._buttons: list[ttk.Radiobutton] = []

        for i, (value, label) in enumerate(options):
            btn = ttk.Radiobutton(
                self,
                text=label,
                variable=variable,
                value=value,
                style='Segment.TRadiobutton',
                command=lambda v=value: self._on_change(v),
            )
            btn.grid(row=0, column=i, sticky='nsew', padx=(0 if i == 0 else 2, 0))
            self._buttons.append(btn)
            self.columnconfigure(i, weight=1)

        variable.trace_add('write', lambda *_: self._sync())

    def _on_change(self, value: str) -> None:
        if self._command:
            self._command(value)

    def _sync(self) -> None:
        pass

    def set_enabled(self, enabled: bool) -> None:
        state = '!disabled' if enabled else 'disabled'
        for btn in self._buttons:
            btn.state([state])




class DropZone(ttk.Frame):
    """Drag-and-drop zone for files/URLs."""

    def __init__(
        self,
        parent: tk.Misc,
        on_drop: Callable[[list[str]], None],
        on_paste: Callable[[str], None],
        **kwargs,
    ) -> None:
        super().__init__(parent, style='DropZone.TFrame', **kwargs)
        self._on_drop = on_drop
        self._on_paste = on_paste

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._label = ttk.Label(
            self,
            text='ลากไฟล์วิดีโอ/เสียงมาที่นี่\nหรือกด Ctrl+V เพื่อวางลิงก์',
            style='DropZoneLabel.TLabel',
            anchor='center',
            justify='center',
        )
        self._label.grid(row=0, column=0, sticky='nsew', padx=20, pady=30)

        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Button-1>', self._on_click)
        self._label.bind('<Enter>', self._on_enter)
        self._label.bind('<Leave>', self._on_leave)
        self._label.bind('<Button-1>', self._on_click)

    def _on_enter(self, _event: tk.Event) -> None:
        self.configure(style='DropZoneHover.TFrame')
        self._label.configure(style='DropZoneLabelHover.TLabel')

    def _on_leave(self, _event: tk.Event) -> None:
        self.configure(style='DropZone.TFrame')
        self._label.configure(style='DropZoneLabel.TLabel')

    def _on_click(self, _event: tk.Event) -> None:
        self.focus_set()

    def handle_drop(self, files: list[str]) -> None:
        self._on_drop(files)

    def handle_paste(self, text: str) -> None:
        self._on_paste(text)


class ToastManager:
    """Non-blocking toast notifications."""

    def __init__(self, root: tk.Tk, anchor_widget: tk.Widget) -> None:
        self._root = root
        self._anchor = anchor_widget
        self._toasts: list[tk.Toplevel] = []
        self._max_toasts = 3

    def show(self, message: str, type_: str = 'info', duration: int = 4000) -> None:
        if len(self._toasts) >= self._max_toasts:
            self._dismiss_oldest()

        toast = tk.Toplevel(self._root)
        toast.overrideredirect(True)
        toast.attributes('-topmost', True)
        toast.configure(bg=TOAST_BG)

        colors = {
            'info': (ACCENT, TEXT),
            'success': (SUCCESS, TEXT),
            'warning': (WARNING, TOAST_BG),
            'error': (ERROR, TEXT),
        }
        bg_color, fg_color = colors.get(type_, colors['info'])

        frame = ttk.Frame(toast, padding=(16, 10), style='Toast.TFrame')
        frame.pack()

        ttk.Label(
            frame,
            text=message,
            foreground=fg_color,
            background=TOAST_BG,
            font=('Segoe UI', 9),
            wraplength=300,
        ).pack(side='left')

        close_btn = ttk.Label(frame, text='✕', foreground=fg_color, background=TOAST_BG, cursor='hand2', font=('Segoe UI', 9, 'bold'))
        close_btn.pack(side='left', padx=(12, 0))
        close_btn.bind('<Button-1>', lambda _e: self._dismiss(toast))

        self._toasts.append(toast)
        self._position_toasts()
        self._root.after(duration, lambda: self._dismiss(toast))

    def _position_toasts(self) -> None:
        self._root.update_idletasks()
        anchor_x = self._anchor.winfo_rootx()
        anchor_y = self._anchor.winfo_rooty()
        anchor_w = self._anchor.winfo_width()

        for i, toast in enumerate(self._toasts):
            toast.update_idletasks()
            w = toast.winfo_width()
            h = toast.winfo_height()
            x = anchor_x + anchor_w - w - 20
            y = anchor_y - (i + 1) * (h + 8) - 20
            toast.geometry(f'+{x}+{y}')

    def _dismiss(self, toast: tk.Toplevel) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
            toast.destroy()
            self._position_toasts()

    def _dismiss_oldest(self) -> None:
        if self._toasts:
            self._dismiss(self._toasts[0])


class ValidationMixin:
    """Mixin for inline validation support."""

    def __init__(self) -> None:
        self._validators: dict[str, Callable[[], tuple[bool, str]]] = {}
        self._error_widgets: dict[str, InlineError] = {}

    def add_validator(self, field_name: str, validator: Callable[[], tuple[bool, str]], error_widget: InlineError) -> None:
        self._validators[field_name] = validator
        self._error_widgets[field_name] = error_widget

    def validate_field(self, field_name: str) -> bool:
        if field_name not in self._validators:
            return True
        valid, message = self._validators[field_name]()
        if valid:
            self._error_widgets[field_name].hide()
        else:
            self._error_widgets[field_name].show(message)
        return valid

    def validate_all(self) -> bool:
        return all(self.validate_field(name) for name in self._validators)

    def clear_errors(self) -> None:
        for widget in self._error_widgets.values():
            widget.hide()