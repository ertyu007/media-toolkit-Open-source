from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont, ttk
from typing import Callable, Optional

from .motion import Tween, mix_color
from .theme import (
    ACCENT,
    ACCENT_SOFT,
    BG,
    BORDER,
    DISABLED_BG,
    DISABLED_FG,
    ERROR,
    FIELD,
    FONT_FAMILY,
    MUTED,
    SECONDARY_BG,
    SECONDARY_HOVER,
    SUCCESS,
    TEXT,
    TOAST_BG,
    WARNING,
)


class InlineError(ttk.Frame):
    """Inline error message shown below a field."""

    def __init__(
        self,
        parent: tk.Misc,
        frame_style: str = 'Card.TFrame',
        label_style: str = 'Error.TLabel',
        **kwargs,
    ) -> None:
        super().__init__(parent, style=frame_style, **kwargs)
        self._label = ttk.Label(self, text='', style=label_style, wraplength=500)
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


PILL_HEIGHT = 48


def segment_index_at(x: float, width: float, count: int) -> int:
    """Pure hit-test: which of *count* equal segments contains canvas-x *x*."""
    if count <= 0 or width <= 0:
        return 0
    return max(0, min(count - 1, int(x / width * count)))


class SegmentedControl(tk.Canvas):
    """Pill-style segmented control drawn on a canvas.

    Rounded track with a sliding accent pill behind the selected option.
    Drop-in replacement for the previous ttk.Radiobutton version: same
    constructor, syncs from *variable*, fires *command* only on user clicks.
    *frame_style*/*button_style* are accepted for compatibility and ignored.
    """

    def __init__(
        self,
        parent: tk.Misc,
        options: list[tuple[str, str]],
        variable: tk.StringVar,
        command: Optional[Callable[[str], None]] = None,
        frame_style: str = 'Card.TFrame',
        button_style: str = 'Segment.TRadiobutton',
        **kwargs,
    ) -> None:
        self._values = [value for value, _ in options]
        self._labels = [label for _, label in options]
        self._variable = variable
        self._command = command
        self._enabled = True
        self._font_family = getattr(parent, 'ui_font', FONT_FAMILY)
        self._track = FIELD
        self._target = self._index_of(variable.get())
        self._pos = float(self._target)
        super().__init__(
            parent,
            height=PILL_HEIGHT,
            highlightthickness=0,
            borderwidth=0,
            bg=self._track,
            takefocus=True,
            **kwargs,
        )
        self._slide = Tween(self.after, self.after_cancel, duration_ms=140)
        self._flash_anim = Tween(self.after, self.after_cancel, duration_ms=180)
        variable.trace_add('write', lambda *_: self._on_trace())
        self.bind('<Button-1>', self._on_click)
        self.bind('<Configure>', lambda _e: self._snap())
        self.bind('<Left>', lambda _e: self._step(-1))
        self.bind('<Right>', lambda _e: self._step(1))
        self._draw()

    def _index_of(self, value: str) -> int:
        try:
            return self._values.index(value)
        except ValueError:
            current = getattr(self, '_target', 0)
            return min(current, len(self._values) - 1) if self._values else 0

    def _stadium(self, x0: float, y0: float, x1: float, y1: float, fill: str) -> None:
        radius = (y1 - y0) / 2
        self.create_rectangle(x0 + radius, y0, x1 - radius, y1, fill=fill, outline='')
        self.create_oval(x0, y0, x0 + radius * 2, y1, fill=fill, outline='')
        self.create_oval(x1 - radius * 2, y0, x1, y1, fill=fill, outline='')

    def _draw(self) -> None:
        try:
            width = self.winfo_width()
            height = self.winfo_height()
        except tk.TclError:
            return
        if width <= 1 or height <= 1 or not self._values:
            return
        self.delete('all')
        self.configure(bg=self._track)
        count = len(self._values)
        self._stadium(2, 2, width - 2, height - 2, self._track)
        seg_width = width / count
        inset = 5
        pill = ACCENT if self._enabled else DISABLED_BG
        self._stadium(
            self._pos * seg_width + inset, inset,
            (self._pos + 1) * seg_width - inset, height - inset, pill,
        )
        for index, label in enumerate(self._labels):
            if not self._enabled:
                fill = DISABLED_FG
            elif index == self._target:
                fill = TEXT
            else:
                fill = MUTED
            self.create_text(
                seg_width * (index + 0.5), height / 2,
                text=label, fill=fill, font=(self._font_family, 11, 'bold'),
            )

    def _on_trace(self) -> None:
        index = self._index_of(self._variable.get())
        if index == self._target and self._pos == float(index):
            return
        self._target = index
        start = self._pos

        def frame(progress: float) -> None:
            self._pos = start + (index - start) * progress
            self._draw()

        try:
            self._slide.start(frame)
        except tk.TclError:
            self._pos = float(index)
            self._draw()

    def _snap(self) -> None:
        self._slide.cancel()
        self._pos = float(self._target)
        self._draw()

    def _select(self, index: int) -> None:
        if not self._enabled or not 0 <= index < len(self._values):
            return
        value = self._values[index]
        if value != self._variable.get():
            self._variable.set(value)
        if self._command:
            self._command(value)

    def _on_click(self, event: tk.Event) -> None:
        self.focus_set()
        self._select(segment_index_at(event.x, self.winfo_width(), len(self._values)))

    def _step(self, direction: int) -> None:
        if not self._values:
            return
        self._select((self._target + direction) % len(self._values))

    def flash(self) -> None:
        """Brief track glow, used as mode-change feedback (replaces HeroBox flash)."""
        def frame(progress: float) -> None:
            try:
                if progress < 0.5:
                    self._track = mix_color(FIELD, ACCENT_SOFT, progress * 2.0)
                else:
                    self._track = mix_color(ACCENT_SOFT, FIELD, (progress - 0.5) * 2.0)
                self._draw()
            except tk.TclError:
                self._flash_anim.cancel()

        try:
            self._flash_anim.start(frame)
        except tk.TclError:
            pass

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self._slide.cancel()
        self._draw()




FIELD_HEIGHT = 40
_FIELD_PAD_X = 16


def _stadium_items(canvas: tk.Canvas, x0: float, y0: float, x1: float, y1: float,
                   fill: str, outline: str = '', tags: str = '') -> None:
    """Draw a stadium (pill) shape: rectangle capped with two half-discs."""
    radius = (y1 - y0) / 2
    canvas.create_rectangle(
        x0 + radius, y0, x1 - radius, y1, fill=fill, outline=outline, tags=tags,
    )
    canvas.create_oval(
        x0, y0, x0 + radius * 2, y1, fill=fill, outline=outline, tags=tags,
    )
    canvas.create_oval(
        x1 - radius * 2, y0, x1, y1, fill=fill, outline=outline, tags=tags,
    )


class RoundedEntry(tk.Frame):
    """Pill-shaped text field: borderless Entry embedded in a drawn rounded shell.

    Forwards ``bind``/``focus_set``/``icursor`` to the inner Entry and accepts
    ttk-style ``state(['disabled'])`` so existing call sites keep working.
    """

    def __init__(
        self,
        parent: tk.Misc,
        textvariable: tk.StringVar | None = None,
        font_family: str | None = None,
        font_size: int = 10,
        bg: str = BG,
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=bg, **kwargs)
        self._bg = bg
        self._enabled = True
        self._focused = False
        family = font_family or getattr(parent, 'ui_font', FONT_FAMILY)
        self._canvas = tk.Canvas(
            self, height=FIELD_HEIGHT, bg=bg,
            highlightthickness=0, borderwidth=0,
        )
        self._canvas.pack(fill='x', expand=True)
        self.entry = tk.Entry(
            self._canvas, textvariable=textvariable,
            relief='flat', borderwidth=0, highlightthickness=0,
            bg=FIELD, fg=TEXT, disabledbackground=FIELD,
            disabledforeground=DISABLED_FG, insertbackground=TEXT,
            font=(family, font_size),
        )
        self._window = self._canvas.create_window(
            _FIELD_PAD_X, FIELD_HEIGHT // 2, window=self.entry, anchor='w',
        )
        self.entry.bind('<FocusIn>', lambda _e: self._set_focus(True), add='+')
        self.entry.bind('<FocusOut>', lambda _e: self._set_focus(False), add='+')
        self._canvas.bind('<Button-1>', lambda _e: self.entry.focus_set())
        self._canvas.bind('<Configure>', lambda _e: (self._layout(), self._draw()))
        self._layout()
        self._draw()

    def _layout(self) -> None:
        try:
            width = self._canvas.winfo_width()
        except tk.TclError:
            return
        if width > 1:
            self._canvas.itemconfigure(self._window, width=width - _FIELD_PAD_X * 2)

    def _set_focus(self, focused: bool) -> None:
        self._focused = focused
        self._draw()

    def _draw(self) -> None:
        try:
            width = self._canvas.winfo_width()
        except tk.TclError:
            return
        if width <= 1:
            return
        self._canvas.delete('bg')
        border = ACCENT if (self._focused and self._enabled) else BORDER
        _stadium_items(self._canvas, 1, 1, width - 1, FIELD_HEIGHT - 1, border, tags='bg')
        inner = 3
        _stadium_items(
            self._canvas, inner, inner, width - inner, FIELD_HEIGHT - inner,
            FIELD, tags='bg',
        )
        self._canvas.tag_lower('bg')

    def bind(self, sequence: str, func, add: bool | str = True):  # type: ignore[override]
        # Inner Entry gets the binding; the pill canvas gets a copy too so
        # clicks on the padding (e.g. destination history popup) still fire.
        # No double-fire: events on the embedded window never reach the canvas.
        self._canvas.bind(sequence, func, add='+')
        return self.entry.bind(sequence, func, add=add)

    def focus_set(self) -> None:  # type: ignore[override]
        self.entry.focus_set()

    def icursor(self, index) -> None:
        self.entry.icursor(index)

    def state(self, states) -> None:
        states = set(states)
        enabled = 'disabled' not in states
        self._enabled = enabled
        try:
            self.entry.configure(state='normal' if enabled else 'disabled')
        except tk.TclError:
            pass
        self._draw()


class RoundedButton(tk.Canvas):
    """Pill-shaped button with hover/press states and auto-growing width."""

    def __init__(
        self,
        parent: tk.Misc,
        text: str = '',
        textvariable: tk.StringVar | None = None,
        command: Optional[Callable[[], None]] = None,
        width: int = 14,
        font_family: str | None = None,
        font_size: int = 10,
        bg: str = BG,
        **kwargs,
    ) -> None:
        self._text = text
        self._variable = textvariable
        self._command = command
        self._enabled = True
        self._hover = False
        self._pressed = False
        family = font_family or getattr(parent, 'ui_font', FONT_FAMILY)
        self._font = (family, font_size, 'bold')
        self._bg = bg
        super().__init__(
            parent, height=FIELD_HEIGHT, bg=bg,
            highlightthickness=0, borderwidth=0, takefocus=True, **kwargs,
        )
        measure = tkfont.Font(font=self._font).measure
        self._measure = measure
        self._min_width = self._measure('0' * width) + 44
        self.configure(width=int(self._min_width))
        if textvariable is not None:
            textvariable.trace_add('write', lambda *_: self._refit())
        self.bind('<Enter>', lambda _e: self._set_hover(True))
        self.bind('<Leave>', lambda _e: (self._set_hover(False), self._set_pressed(False)))
        self.bind('<ButtonPress-1>', lambda _e: self._set_pressed(True))
        self.bind('<ButtonRelease-1>', self._on_release)
        self.bind('<Return>', lambda _e: self.invoke())
        self.bind('<space>', lambda _e: self.invoke())
        self.bind('<Configure>', lambda _e: self._draw())
        self._draw()

    def _label(self) -> str:
        if self._variable is not None:
            return self._variable.get()
        return self._text

    def _refit(self) -> None:
        needed = self._measure(self._label() or '') + 44
        if needed > self._min_width:
            self._min_width = needed
            try:
                self.configure(width=int(needed))
            except tk.TclError:
                pass
        self._draw()

    def _set_hover(self, value: bool) -> None:
        self._hover = value
        self._draw()

    def _set_pressed(self, value: bool) -> None:
        self._pressed = value
        self._draw()

    def _on_release(self, event: tk.Event) -> None:
        was_pressed = self._pressed
        self._pressed = False
        self._draw()
        if (
            was_pressed
            and self._enabled
            and 0 <= event.x <= self.winfo_width()
            and 0 <= event.y <= FIELD_HEIGHT
        ):
            self.invoke()

    def invoke(self) -> None:
        if self._enabled and self._command:
            self._command()

    def _draw(self) -> None:
        try:
            width = self.winfo_width()
        except tk.TclError:
            return
        if width <= 1:
            return
        self.delete('all')
        if not self._enabled:
            fill, fg = DISABLED_BG, DISABLED_FG
        elif self._pressed:
            fill, fg = ACCENT_SOFT, TEXT
        elif self._hover:
            fill, fg = SECONDARY_HOVER, TEXT
        else:
            fill, fg = SECONDARY_BG, TEXT
        _stadium_items(self, 1, 1, width - 1, FIELD_HEIGHT - 1, fill)
        self.create_text(
            width / 2, FIELD_HEIGHT / 2,
            text=self._label(), fill=fg, font=self._font,
        )

    def state(self, states) -> None:
        self._enabled = 'disabled' not in set(states)
        self._draw()


class Switch(tk.Canvas):
    """iOS-style toggle switch with sliding knob; checkbox replacement."""

    _TRACK_W = 46
    _HEIGHT = 28

    def __init__(
        self,
        parent: tk.Misc,
        variable: tk.BooleanVar,
        text: str = '',
        command: Optional[Callable[[bool], None]] = None,
        font_family: str | None = None,
        font_size: int = 10,
        bg: str = BG,
        **kwargs,
    ) -> None:
        self._variable = variable
        self._text = text
        self._command = command
        self._enabled = True
        family = font_family or getattr(parent, 'ui_font', FONT_FAMILY)
        self._font = (family, font_size)
        self._pos = 1.0 if variable.get() else 0.0
        super().__init__(
            parent, height=self._HEIGHT, bg=bg,
            highlightthickness=0, borderwidth=0, takefocus=True, **kwargs,
        )
        self._slide = Tween(self.after, self.after_cancel, duration_ms=120)
        variable.trace_add('write', lambda *_: self._on_trace())
        self.bind('<Button-1>', lambda _e: (self.focus_set(), self.toggle()))
        self.bind('<Return>', lambda _e: self.toggle())
        self.bind('<space>', lambda _e: self.toggle())
        self.bind('<Configure>', lambda _e: self._draw())
        self.configure(width=self._TRACK_W + 10 + self._text_width() + 4)
        self._draw()

    def _text_width(self) -> int:
        if not self._text:
            return 0
        return tkfont.Font(font=self._font).measure(self._text)

    def _on_trace(self) -> None:
        target = 1.0 if self._variable.get() else 0.0
        start = self._pos

        def frame(progress: float) -> None:
            self._pos = start + (target - start) * progress
            self._draw()

        try:
            self._slide.start(frame)
        except tk.TclError:
            self._pos = target
            self._draw()

    def toggle(self) -> None:
        if not self._enabled:
            return
        value = not self._variable.get()
        self._variable.set(value)
        if self._command:
            self._command(value)

    def _draw(self) -> None:
        try:
            self.winfo_width()
        except tk.TclError:
            return
        self.delete('all')
        track_h = 24
        y0 = (self._HEIGHT - track_h) / 2
        y1 = y0 + track_h
        on = self._pos > 0.5
        if not self._enabled:
            track, knob = DISABLED_BG, DISABLED_FG
        elif on:
            track, knob = ACCENT, '#ffffff'
        else:
            track, knob = SECONDARY_BG, MUTED
        _stadium_items(self, 1, y0, self._TRACK_W, y1, track)
        knob_r = (track_h - 6) / 2
        knob_x = 1 + 3 + knob_r + self._pos * (self._TRACK_W - 2 - 6 - knob_r * 2)
        knob_y = (y0 + y1) / 2
        self.create_oval(
            knob_x - knob_r, knob_y - knob_r,
            knob_x + knob_r, knob_y + knob_r,
            fill=knob, outline='',
        )
        if self._text:
            self.create_text(
                self._TRACK_W + 10, self._HEIGHT / 2,
                text=self._text, fill=TEXT if self._enabled else DISABLED_FG,
                font=self._font, anchor='w',
            )

    def state(self, states) -> None:
        self._enabled = 'disabled' not in set(states)
        self._slide.cancel()
        self._draw()


class ToastManager:
    """Non-blocking toast notifications stacked at the window's bottom-right."""

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
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

        frame = ttk.Frame(toast, padding=(18, 13), style='Toast.TFrame')
        frame.pack(fill='both', expand=True)

        accent_bar = tk.Frame(frame, bg=bg_color, width=5, height=48)
        accent_bar.pack(side='left', fill='y', padx=(0, 14))

        ttk.Label(
            frame,
            text=message,
            foreground=fg_color,
            background=TOAST_BG,
            font=(FONT_FAMILY, 10, 'bold'),
            wraplength=340,
        ).pack(side='left')

        close_btn = ttk.Label(frame, text='✕', foreground=fg_color, background=TOAST_BG, cursor='hand2', font=(FONT_FAMILY, 9, 'bold'))
        close_btn.pack(side='left', padx=(12, 0))
        close_btn.bind('<Button-1>', lambda _e: self._dismiss(toast))

        self._toasts.append(toast)
        self._position_toasts()
        self._animate_in(toast)
        self._root.after(duration, lambda: self._dismiss(toast))

    def _animate_in(self, toast: tk.Toplevel) -> None:
        """Slide the toast up a few pixels while fading in."""
        try:
            info = toast.geometry().split('+')
            target_x, target_y = int(info[1]), int(info[2])
            toast.attributes('-alpha', 0.0)
        except (tk.TclError, ValueError, IndexError):
            return
        start_y = target_y + 18
        tween = Tween(self._root.after, self._root.after_cancel, duration_ms=140)

        def frame(progress: float) -> None:
            try:
                toast.attributes('-alpha', progress)
                current_y = round(start_y + (target_y - start_y) * progress)
                toast.geometry(f'+{target_x}+{current_y}')
            except tk.TclError:
                tween.cancel()

        tween.start(frame)

    def _position_toasts(self) -> None:
        self._root.update_idletasks()
        root_x = self._root.winfo_rootx()
        root_y = self._root.winfo_rooty()
        root_w = self._root.winfo_width()
        root_h = self._root.winfo_height()

        for i, toast in enumerate(self._toasts):
            toast.update_idletasks()
            w = toast.winfo_width()
            h = toast.winfo_height()
            x = root_x + root_w - w - 16
            y = root_y + root_h - (i + 1) * (h + 10) - 48
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