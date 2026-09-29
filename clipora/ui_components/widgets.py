from __future__ import annotations

import colorsys
import tkinter as tk
from tkinter import font as tkfont, ttk
from typing import Callable, Optional, Sequence

from .motion import Tween, mix_color
from .theme import (
    ACCENT,
    ACCENT_SOFT,
    BG,
    BORDER,
    DANGER,
    DISABLED_BG,
    DISABLED_FG,
    ERROR,
    FIELD,
    FONT_FAMILY,
    MUTED,
    PROGRESS_TROUGH,
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


def segment_index_at(x: float, width: float, count: int, gap: float = 0.0) -> int:
    """Pure hit-test: which of *count* equal segments contains canvas-x *x*."""
    if count <= 0 or width <= 0:
        return 0
    seg, stride = segment_layout(width, count, gap)
    if stride <= 0:
        return 0
    return max(0, min(count - 1, int(x // stride)))


_TRANSPARENT_KEY = '#ff00ff'  # transparency key for rounded popups; in no palette


def _rounded_rect(canvas: tk.Canvas, x0: float, y0: float,
                  x1: float, y1: float, radius: float, **kwargs) -> None:
    """Draw a rounded rectangle from rects + corner ovals."""
    canvas.create_rectangle(x0 + radius, y0, x1 - radius, y1, **kwargs)
    canvas.create_rectangle(x0, y0 + radius, x1, y1 - radius, **kwargs)
    for cx, cy in ((x0 + radius, y0 + radius),
                   (x1 - radius, y0 + radius),
                   (x0 + radius, y1 - radius),
                   (x1 - radius, y1 - radius)):
        canvas.create_oval(
            cx - radius, cy - radius, cx + radius, cy + radius, **kwargs)


def segment_layout(width: float, count: int, gap: float = 0.0) -> tuple[float, float]:
    """Return ``(segment_width, stride)`` for a gapped segmented row."""
    if count <= 0:
        return (0.0, 0.0)
    seg = max(0.0, (width - gap * (count - 1)) / count)
    return (seg, seg + gap)


def segment_origin(index: int, width: float, count: int, gap: float = 0.0) -> float:
    """Left edge x of segment *index* (fractional positions slide too)."""
    _seg, stride = segment_layout(width, count, gap)
    return index * stride


def parent_surface_bg(parent: tk.Misc, fallback: str = BG) -> str:
    """Background color behind *parent*.

    Tk canvases cannot be transparent, so pill/stadium widgets paint their
    canvas with the parent surface color to hide the square corners.
    """
    style_name = ''
    try:
        style_name = parent.cget('style')
    except tk.TclError:
        style_name = ''
    if not style_name:
        try:
            style_name = parent.winfo_class()
        except tk.TclError:
            style_name = ''
    if style_name:
        try:
            color = ttk.Style().lookup(style_name, 'background')
        except tk.TclError:
            color = ''
        if color:
            return str(color)
    try:
        return str(parent.cget('background'))
    except tk.TclError:
        return fallback


class SegmentedControl(tk.Canvas):
    """Pill-style segmented control drawn on a canvas.

    Rounded track with a sliding accent pill behind the selected option.
    Drop-in replacement for the previous ttk.Radiobutton version: same
    constructor, syncs from *variable*, fires *command* only on user clicks.
    *frame_style*/*button_style* are accepted for compatibility and ignored.

    *gap* separates the options into individual pills while the selection
    still slides across all of them. Options in *locked* show a 🔒 prefix,
    cannot be picked, and fire *on_locked* instead.
    """

    def __init__(
        self,
        parent: tk.Misc,
        options: list[tuple[str, str]],
        variable: tk.StringVar,
        command: Optional[Callable[[str], None]] = None,
        frame_style: str = 'Card.TFrame',
        button_style: str = 'Segment.TRadiobutton',
        gap: float = 0,
        locked: Sequence[str] = (),
        on_locked: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        self._values = [value for value, _ in options]
        self._labels = [label for _, label in options]
        self._variable = variable
        self._command = command
        self._enabled = True
        self._gap = max(0.0, float(gap))
        self._locked = set(locked)
        self._on_locked = on_locked
        self._font_family = getattr(parent, 'ui_font', FONT_FAMILY)
        self._track = FIELD
        self._surface = parent_surface_bg(parent)
        self._target = self._index_of(variable.get())
        self._pos = float(self._target)
        super().__init__(
            parent,
            height=PILL_HEIGHT,
            highlightthickness=0,
            borderwidth=0,
            bg=self._surface,
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
        self.configure(bg=self._surface)
        count = len(self._values)
        seg_width, _stride = segment_layout(width, count, self._gap)
        inset = 5
        for index in range(count):
            x0 = segment_origin(index, width, count, self._gap)
            self._stadium(x0 + 2, inset, x0 + seg_width - 2, height - inset, self._track)
        pill = ACCENT if self._enabled else DISABLED_BG
        px0 = segment_origin(self._pos, width, count, self._gap)
        self._stadium(
            px0 + inset, inset,
            px0 + seg_width - inset, height - inset, pill,
        )
        for index, label in enumerate(self._labels):
            if not self._enabled:
                fill = DISABLED_FG
            elif index == self._target:
                fill = TEXT
            elif self._values[index] in self._locked:
                fill = DISABLED_FG
            else:
                fill = MUTED
            text = f'🔒 {label}' if self._values[index] in self._locked else label
            self.create_text(
                segment_origin(index, width, count, self._gap) + seg_width / 2,
                height / 2,
                text=text, fill=fill, font=(self._font_family, 11, 'bold'),
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
        if value in self._locked:
            if self._on_locked is not None:
                try:
                    self._on_locked(value)
                except tk.TclError:
                    pass
            return
        if value != self._variable.get():
            self._variable.set(value)
        if self._command:
            self._command(value)

    def set_locked(self, values: Sequence[str]) -> None:
        """Update which options show 🔒 (redraws only on change)."""
        locked = set(values)
        if locked != self._locked:
            self._locked = locked
            self._draw()

    def _on_click(self, event: tk.Event) -> None:
        self.focus_set()
        self._select(segment_index_at(
            event.x, self.winfo_width(), len(self._values), self._gap))

    def _step(self, direction: int) -> None:
        if not self._values:
            return
        index = self._target
        for _ in range(len(self._values)):
            index = (index + direction) % len(self._values)
            if self._values[index] not in self._locked:
                break
        self._select(index)

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


def _draw_pill_shell(canvas: tk.Canvas, width: float, height: float, border: str) -> None:
    """Redraw the double-stadium field shell (border outside, fill inside)."""
    canvas.delete('bg')
    _stadium_items(canvas, 1, 1, width - 1, height - 1, border, tags='bg')
    inner = 3
    _stadium_items(canvas, inner, inner, width - inner, height - inner, FIELD, tags='bg')
    canvas.tag_lower('bg')


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
        bg: str | None = None,
        width: int | None = None,
        **kwargs,
    ) -> None:
        bg = bg or parent_surface_bg(parent)
        super().__init__(parent, bg=bg, **kwargs)
        self._bg = bg
        self._enabled = True
        self._focused = False
        family = font_family or getattr(parent, 'ui_font', FONT_FAMILY)
        self._canvas = tk.Canvas(
            self, height=FIELD_HEIGHT, bg=bg,
            highlightthickness=0, borderwidth=0,
        )
        if width is not None:
            fixed = tkfont.Font(font=(family, font_size)).measure('0' * width)
            self._canvas.configure(width=fixed + _FIELD_PAD_X * 2 + 6)
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
        border = ACCENT if (self._focused and self._enabled) else BORDER
        _draw_pill_shell(self._canvas, width, FIELD_HEIGHT, border)

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

    def get(self) -> str:
        return self.entry.get()

    def delete(self, first, last=None) -> None:
        self.entry.delete(first, last)

    def insert(self, index, string: str) -> None:
        self.entry.insert(index, string)

    def state(self, states) -> None:
        states = set(states)
        enabled = 'disabled' not in states
        self._enabled = enabled
        try:
            self.entry.configure(state='normal' if enabled else 'disabled')
        except tk.TclError:
            pass
        self._draw()


class RoundedCombobox(tk.Frame):
    """Pill dropdown with a custom rounded popup (no native square edges)."""

    _ROW_H = 34
    _POP_PAD = 8

    def __init__(
        self,
        parent: tk.Misc,
        textvariable: tk.StringVar | None = None,
        values: Sequence[str] = (),
        width: int = 12,
        font_family: str | None = None,
        font_size: int = 10,
        bg: str | None = None,
        **kwargs,
    ) -> None:
        bg = bg or parent_surface_bg(parent)
        super().__init__(parent, bg=bg, **kwargs)
        self._variable = textvariable
        self._values = list(values)
        self._enabled = True
        self._focused = False
        self._hover = -1
        self._popup: tk.Toplevel | None = None
        self._pop_canvas: tk.Canvas | None = None
        family = font_family or getattr(parent, 'ui_font', FONT_FAMILY)
        self._family = family
        self._font = (family, font_size)
        self._canvas = tk.Canvas(
            self, height=FIELD_HEIGHT, bg=bg,
            highlightthickness=0, borderwidth=0, takefocus=True,
        )
        fixed = tkfont.Font(font=(family, font_size)).measure('0' * width) + 44
        self._canvas.configure(width=fixed)
        self._canvas.pack(fill='x', expand=True)
        if textvariable is not None:
            textvariable.trace_add('write', lambda *_: self._draw())
        self._canvas.bind('<Button-1>', lambda _e: (self.focus_set(), self.toggle()))
        self._canvas.bind('<FocusIn>', lambda _e: self._set_focus(True))
        self._canvas.bind('<FocusOut>', lambda _e: self._set_focus(False))
        self._canvas.bind('<Down>', lambda _e: self.open())
        self._canvas.bind('<Return>', lambda _e: self.toggle())
        self._canvas.bind('<space>', lambda _e: self.toggle())
        self._canvas.bind('<Configure>', lambda _e: self._draw())
        self.bind('<Destroy>', lambda _e: self.close(), add='+')
        self._draw()

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
        self._canvas.delete('all')
        border = ACCENT if (self._focused and self._enabled) else BORDER
        _draw_pill_shell(self._canvas, width, FIELD_HEIGHT, border)
        fg = DISABLED_FG if not self._enabled else TEXT
        text = self._variable.get() if self._variable is not None else ''
        self._canvas.create_text(
            _FIELD_PAD_X, FIELD_HEIGHT / 2, text=text, fill=fg,
            font=self._font, anchor='w',
        )
        self._canvas.create_text(
            width - _FIELD_PAD_X, FIELD_HEIGHT / 2, text='▼',
            fill=DISABLED_FG if not self._enabled else MUTED,
            font=(self._family, 9), anchor='e',
        )

    def focus_set(self) -> None:  # type: ignore[override]
        try:
            self._canvas.focus_set()
        except tk.TclError:
            pass

    def configure(self, cnf=None, **kw):  # type: ignore[override]
        if 'values' in kw:
            self._values = list(kw.pop('values'))
            self.close()
            self._draw()
        if kw:
            try:
                super().configure(cnf, **kw)
            except tk.TclError:
                pass
        return None

    def state(self, states) -> None:
        self._enabled = 'disabled' not in set(states)
        if not self._enabled:
            self.close()
        self._draw()

    # ── Popup ─────────────────────────────────────────────────────────────
    def toggle(self) -> None:
        if self._popup is not None:
            self.close()
        else:
            self.open()

    def open(self) -> None:
        if not self._enabled or self._popup is not None or not self._values:
            return
        try:
            popup = tk.Toplevel(self)
            popup.overrideredirect(True)
            popup.attributes('-topmost', True)
            try:
                popup.attributes('-transparentcolor', _TRANSPARENT_KEY)
                popup.configure(bg=_TRANSPARENT_KEY)
                base_bg = _TRANSPARENT_KEY
            except tk.TclError:
                popup.configure(bg=FIELD)
                base_bg = FIELD
        except tk.TclError:
            return
        try:
            width = max(self._canvas.winfo_width(), 160)
            rows = len(self._values)
            height = self._POP_PAD * 2 + rows * self._ROW_H
            x = self._canvas.winfo_rootx()
            y = self._canvas.winfo_rooty() + self._canvas.winfo_height() + 6
            if y + height > popup.winfo_screenheight():
                y = self._canvas.winfo_rooty() - height - 6
        except tk.TclError:
            popup.destroy()
            return
        canvas = tk.Canvas(
            popup, width=width, height=height, bg=base_bg,
            highlightthickness=0, borderwidth=0,
        )
        canvas.pack(fill='both', expand=True)
        _rounded_rect(
            canvas, 0, 0, width, height, 12, fill=FIELD, outline=BORDER)
        current = self._variable.get() if self._variable is not None else None
        self._hover = (
            self._values.index(current) if current in self._values else 0)
        self._popup = popup
        self._pop_canvas = canvas
        self._paint_rows()
        canvas.bind('<Motion>', self._on_pop_motion)
        canvas.bind('<Button-1>', self._on_pop_click)
        popup.bind('<Escape>', lambda _e: self.close())
        popup.bind('<Up>', lambda _e: self._move_hover(-1))
        popup.bind('<Down>', lambda _e: self._move_hover(1))
        popup.bind('<Return>', lambda _e: self._choose_hovered())
        popup.geometry(f'{width}x{height}+{x}+{y}')
        try:
            popup.grab_set()
        except tk.TclError:
            pass

    def _row_at(self, y: int) -> int:
        index = (y - self._POP_PAD) // self._ROW_H
        if 0 <= index < len(self._values):
            return index
        return -1

    def _paint_rows(self) -> None:
        canvas = self._pop_canvas
        if canvas is None:
            return
        try:
            width = int(canvas.cget('width'))
        except tk.TclError:
            return
        canvas.delete('row')
        current = self._variable.get() if self._variable is not None else None
        for index, value in enumerate(self._values):
            top = self._POP_PAD + index * self._ROW_H
            if index == self._hover:
                _rounded_rect(
                    canvas, 4, top + 2, width - 4, top + self._ROW_H - 2, 8,
                    fill=ACCENT, outline='', tags=('row',))
                fg = '#ffffff'
            else:
                fg = ACCENT if value == current else TEXT
            canvas.create_text(
                self._POP_PAD + 10, top + self._ROW_H / 2, text=value,
                fill=fg, font=self._font, anchor='w', tags=('row',))

    def _on_pop_motion(self, event: tk.Event) -> None:
        index = self._row_at(event.y)
        if index != self._hover:
            self._hover = index
            self._paint_rows()

    def _on_pop_click(self, event: tk.Event) -> None:
        index = self._row_at(event.y)
        if index < 0:
            self.close()
        else:
            self._choose(index)

    def _move_hover(self, direction: int) -> None:
        if not self._values:
            return
        self._hover = (self._hover + direction) % len(self._values)
        self._paint_rows()

    def _choose_hovered(self) -> None:
        if 0 <= self._hover < len(self._values):
            self._choose(self._hover)
        else:
            self.close()

    def _choose(self, index: int) -> None:
        try:
            if self._variable is not None:
                self._variable.set(self._values[index])
            self.event_generate('<<ComboboxSelected>>')
        except (tk.TclError, IndexError):
            pass
        self.close()
        self.focus_set()

    def close(self) -> None:
        popup, self._popup = self._popup, None
        self._pop_canvas = None
        self._hover = -1
        if popup is not None:
            try:
                popup.destroy()
            except tk.TclError:
                pass


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
        bg: str | None = None,
        height: int = FIELD_HEIGHT,
        fill: str | None = None,
        hover_fill: str | None = None,
        hover_internal: bool = True,
        **kwargs,
    ) -> None:
        self._text = text
        self._variable = textvariable
        self._command = command
        self._enabled = True
        self._hover = False
        self._pressed = False
        self._base_fill = fill or SECONDARY_BG
        self._base_hover = hover_fill or SECONDARY_HOVER
        self._accent_pair = (self._base_fill, self._base_hover)
        self._custom_fill: str | None = None
        self._height = height
        family = font_family or getattr(parent, 'ui_font', FONT_FAMILY)
        self._font = (family, font_size, 'bold')
        self._bg = bg or parent_surface_bg(parent)
        super().__init__(
            parent, height=height, bg=self._bg,
            highlightthickness=0, borderwidth=0, takefocus=True, **kwargs,
        )
        measure = tkfont.Font(font=self._font).measure
        self._measure = measure
        self._min_width = self._measure('0' * width) + 44
        self.configure(width=int(self._min_width))
        if textvariable is not None:
            textvariable.trace_add('write', lambda *_: self._refit())
        if hover_internal:
            self.bind('<Enter>', lambda _e: self._set_hover(True))
            self.bind('<Leave>', lambda _e: (self._set_hover(False), self._set_pressed(False)))
        # Press tracking always stays on: _on_release needs it to detect a
        # real click (ui may add its own ButtonPress tween with add='+').
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
            and 0 <= event.y <= self.winfo_height()
        ):
            self.invoke()

    def invoke(self) -> None:
        if self._enabled and self._command:
            self._command()

    def set_fill(self, color: str) -> None:
        """Paint an explicit base fill (used by external tween/flash drivers)."""
        self._custom_fill = color
        self._draw()

    def reset_fill(self) -> None:
        self._custom_fill = None
        self._draw()

    def set_mode(self, accent: bool) -> None:
        """Switch between the accent look and the danger (cancel) look."""
        if accent:
            self._base_fill, self._base_hover = self._accent_pair
        else:
            self._base_fill = DANGER
            self._base_hover = '#d9534f'
        self._custom_fill = None
        self._draw()

    def configure(self, cnf=None, **kw):  # type: ignore[override]
        if 'text' in kw:
            self._text = kw.pop('text')
        if 'command' in kw:
            self._command = kw.pop('command')
        kw.pop('style', None)
        if kw:
            try:
                super().configure(cnf, **kw)
            except tk.TclError:
                pass
        self._draw()
        return None

    def _draw(self) -> None:
        try:
            width = self.winfo_width()
            height = self.winfo_height()
        except tk.TclError:
            return
        if width <= 1 or height <= 1:
            return
        self.delete('all')
        if not self._enabled:
            fill, fg = DISABLED_BG, DISABLED_FG
        elif self._pressed:
            fill, fg = ACCENT_SOFT, TEXT
        elif self._custom_fill is not None:
            fill, fg = self._custom_fill, TEXT
        elif self._hover:
            fill, fg = self._base_hover, TEXT
        else:
            fill, fg = self._base_fill, TEXT
        _stadium_items(self, 1, 1, width - 1, height - 1, fill)
        self.create_text(
            width / 2, height / 2,
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
        bg: str | None = None,
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
            parent, height=self._HEIGHT, bg=bg or parent_surface_bg(parent),
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


class RainbowBar(tk.Canvas):
    """Rounded progress bar with an animated rainbow fill.

    Drop-in for the ttk Progressbar on the main window: supports
    ``bar['value']`` / ``bar['maximum']`` item access. The hue drifts while
    0 < value < maximum and rests on solid SUCCESS at 100%.
    """

    _SLICE = 4

    def __init__(
        self,
        parent: tk.Misc,
        height: int = 14,
        bg: str | None = None,
        maximum: float = 100.0,
        **kwargs,
    ) -> None:
        super().__init__(
            parent, height=height, bg=bg or parent_surface_bg(parent),
            highlightthickness=0, borderwidth=0, **kwargs,
        )
        self._height = height
        self._maximum = maximum
        self._value = 0.0
        self._hue = 0.0
        self._ticking = False
        self.bind('<Configure>', lambda _e: self._draw())

    def __setitem__(self, key: str, value: float) -> None:
        if key == 'value':
            self._value = max(0.0, min(float(value), self._maximum))
        elif key == 'maximum':
            self._maximum = float(value) or 100.0
        self._draw()
        self._ensure_tick()

    def __getitem__(self, key: str) -> float:
        if key == 'value':
            return self._value
        if key == 'maximum':
            return self._maximum
        raise KeyError(key)

    @staticmethod
    def _rainbow(hue: float) -> str:
        red, green, blue = colorsys.hsv_to_rgb(hue % 1.0, 0.85, 1.0)
        return f'#{int(red * 255):02x}{int(green * 255):02x}{int(blue * 255):02x}'

    def _draw(self) -> None:
        try:
            width = self.winfo_width()
        except tk.TclError:
            return
        if width <= 1:
            return
        height = self._height
        self.delete('all')
        _stadium_items(self, 0, 0, width, height, PROGRESS_TROUGH)
        if self._maximum <= 0 or self._value <= 0:
            return
        fill_w = width * min(self._value / self._maximum, 1.0)
        if fill_w <= 4:
            return
        pad = 2
        if self._value >= self._maximum:
            _stadium_items(self, pad, pad, fill_w - pad, height - pad, SUCCESS)
            return
        span = max(fill_w - pad * 2, 1)
        x = pad
        while x < fill_w - pad:
            step = min(self._SLICE, fill_w - pad - x)
            hue = self._hue + (x - pad) / max(span, 1) * 0.8
            self.create_rectangle(
                x, pad, x + step, height - pad,
                fill=self._rainbow(hue), outline='',
            )
            x += step

    def _ensure_tick(self) -> None:
        if self._ticking:
            return
        if 0 < self._value < self._maximum:
            self._ticking = True
            self.after(60, self._tick)

    def _tick(self) -> None:
        try:
            self._hue += 0.015
            self._draw()
        except tk.TclError:
            self._ticking = False
            return
        if 0 < self._value < self._maximum:
            self.after(60, self._tick)
        else:
            self._ticking = False


class ToastManager:
    """Non-blocking rounded toast notifications at the window's bottom-right.

    Rounded corners use the ``-transparentcolor`` trick (opaque fallback when
    the platform refuses it); content is drawn straight on the canvas.
    """
    _KEY = _TRANSPARENT_KEY  # transparency key; in neither palette
    _RADIUS = 14

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._toasts: list[tk.Toplevel] = []
        self._max_toasts = 3

    @staticmethod
    def _rounded_rect(canvas: tk.Canvas, x0: float, y0: float,
                      x1: float, y1: float, radius: float, **kwargs) -> None:
        _rounded_rect(canvas, x0, y0, x1, y1, radius, **kwargs)

    def show(self, message: str, type_: str = 'info', duration: int = 4000) -> None:
        if len(self._toasts) >= self._max_toasts:
            self._dismiss_oldest()

        toast = tk.Toplevel(self._root)
        toast.overrideredirect(True)
        toast.attributes('-topmost', True)
        try:
            toast.attributes('-transparentcolor', self._KEY)
            rounded = True
        except tk.TclError:
            rounded = False
        toast.configure(bg=self._KEY if rounded else TOAST_BG)

        colors = {
            'info': (ACCENT, 'i'),
            'success': (SUCCESS, '✓'),
            'warning': (WARNING, '!'),
            'error': (ERROR, '✕'),
        }
        accent, glyph = colors.get(type_, colors['info'])

        pad = 16
        radius = self._RADIUS if rounded else 0
        max_msg = 340
        icon_d = 22
        font_glyph = tkfont.Font(font=(FONT_FAMILY, 11, 'bold'))
        font_msg = tkfont.Font(font=(FONT_FAMILY, 10))
        font_close = tkfont.Font(font=(FONT_FAMILY, 9))
        close_w = font_close.measure('✕')
        msg_w = min(max(font_msg.measure(message), 60), max_msg)
        lines = max(1, -(-font_msg.measure(message) // max(msg_w, 1)))
        line_h = font_msg.metrics('linespace')
        body_h = max(icon_d, lines * line_h)
        width = pad + 4 + 12 + icon_d + 10 + msg_w + 12 + close_w + pad
        height = body_h + pad * 2

        canvas = tk.Canvas(
            toast, width=width, height=height,
            bg=self._KEY if rounded else TOAST_BG,
            highlightthickness=0, borderwidth=0,
        )
        canvas.pack(fill='both', expand=True)
        if rounded:
            self._rounded_rect(
                canvas, 0, 0, width, height, radius,
                fill=TOAST_BG, outline=BORDER)
        else:
            canvas.create_rectangle(
                0, 0, width, height, fill=TOAST_BG, outline=BORDER)
        top = (height - body_h) / 2
        self._rounded_rect(
            canvas, pad, top, pad + 4, top + body_h, 2, fill=accent, outline='')
        mid_y = top + body_h / 2
        icon_x = pad + 4 + 12
        # Drawn ring + plain letter: no font-fallback boxes on any machine.
        canvas.create_oval(
            icon_x, mid_y - icon_d / 2, icon_x + icon_d, mid_y + icon_d / 2,
            outline=accent, width=2)
        canvas.create_text(
            icon_x + icon_d / 2, mid_y, text=glyph, fill=accent,
            font=font_glyph)
        canvas.create_text(
            icon_x + icon_d + 10, mid_y, text=message, fill=TEXT,
            font=font_msg, anchor='w', justify='left', width=msg_w)
        canvas.create_text(
            width - pad, mid_y, text='✕', fill=MUTED,
            font=font_close, anchor='e', tags=('close',))
        canvas.tag_bind('close', '<Button-1>', lambda _e: self._dismiss(toast))
        canvas.tag_bind(
            'close', '<Enter>', lambda _e: canvas.configure(cursor='hand2'))
        canvas.tag_bind(
            'close', '<Leave>', lambda _e: canvas.configure(cursor=''))

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