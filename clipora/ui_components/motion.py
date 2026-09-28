"""Tiny animation toolkit for the Clipora UI.

Everything here runs on the Tk main thread via ``after`` callbacks — never
call these helpers from a worker thread. The classes take ``after``/``cancel``
callables (instead of a widget) so the timing logic is unit-testable without
a display; pass ``widget.after`` / ``widget.after_cancel`` in production.
"""

from __future__ import annotations

from typing import Callable

AfterFn = Callable[[int, Callable[[], None]], object]
CancelFn = Callable[[object], None]
EaseFn = Callable[[float], float]
FrameFn = Callable[[float], None]


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def ease_out_cubic(time: float) -> float:
    time = clamp01(time)
    return 1.0 - (1.0 - time) ** 3


def ease_in_out_quad(time: float) -> float:
    time = clamp01(time)
    if time < 0.5:
        return 2.0 * time * time
    return 1.0 - (-2.0 * time + 2.0) ** 2 / 2.0


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    cleaned = color.strip().lstrip('#')
    if len(cleaned) != 6:
        raise ValueError(f'สีต้องเป็น hex 6 หลัก: {color}')
    try:
        return (int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16))
    except ValueError:
        raise ValueError(f'สีต้องเป็น hex 6 หลัก: {color}') from None


def rgb_to_hex(red: int, green: int, blue: int) -> str:
    return f'#{red:02x}{green:02x}{blue:02x}'


def mix_color(first: str, second: str, amount: float) -> str:
    """Blend two hex colors; ``amount=0`` gives ``first``, ``1`` gives ``second``."""
    amount = clamp01(amount)
    first_rgb = hex_to_rgb(first)
    second_rgb = hex_to_rgb(second)
    return rgb_to_hex(
        round(first_rgb[0] + (second_rgb[0] - first_rgb[0]) * amount),
        round(first_rgb[1] + (second_rgb[1] - first_rgb[1]) * amount),
        round(first_rgb[2] + (second_rgb[2] - first_rgb[2]) * amount),
    )


class Tween:
    """One-shot 0→1 animation driven by ``after`` callbacks."""

    def __init__(
        self,
        after: AfterFn,
        cancel: CancelFn,
        duration_ms: int = 160,
        frame_ms: int = 16,
        ease: EaseFn = ease_out_cubic,
    ) -> None:
        self._after = after
        self._cancel = cancel
        self._duration_ms = max(1, duration_ms)
        self._frame_ms = max(1, frame_ms)
        self._ease = ease
        self._pending: object | None = None
        self._token = 0

    @property
    def running(self) -> bool:
        return self._pending is not None

    def start(self, on_frame: FrameFn, on_done: Callable[[], None] | None = None) -> None:
        """Restart the tween; a running tween is cancelled first."""
        self.cancel()
        self._token += 1
        token = self._token
        steps = max(1, self._duration_ms // self._frame_ms)
        state = {'tick': 0}

        def advance() -> None:
            if token != self._token:
                return
            self._pending = None
            state['tick'] += 1
            progress = self._ease(state['tick'] / steps)
            try:
                on_frame(progress)
            except Exception:
                if on_done is not None:
                    on_done()
                return
            if state['tick'] >= steps:
                if on_done is not None:
                    on_done()
                return
            self._pending = self._after(self._frame_ms, advance)

        self._pending = self._after(self._frame_ms, advance)

    def cancel(self) -> None:
        self._token += 1
        if self._pending is not None:
            try:
                self._cancel(self._pending)
            except Exception:
                pass
            self._pending = None


class Pulse:
    """Ping-pong 0→1→0 loop (e.g. progress glow); stop with :meth:`stop`."""

    def __init__(
        self,
        after: AfterFn,
        cancel: CancelFn,
        period_ms: int = 900,
        frame_ms: int = 50,
    ) -> None:
        self._after = after
        self._cancel = cancel
        self._period_ms = max(1, period_ms)
        self._frame_ms = max(1, frame_ms)
        self._pending: object | None = None
        self._token = 0

    @property
    def running(self) -> bool:
        return self._pending is not None

    def start(self, on_frame: FrameFn) -> None:
        self.stop()
        self._token += 1
        token = self._token
        steps = max(2, self._period_ms // self._frame_ms)
        state = {'tick': 0}

        def advance() -> None:
            if token != self._token:
                return
            self._pending = None
            state['tick'] += 1
            position = (state['tick'] % steps) / steps
            phase = position * 2.0 if position < 0.5 else 2.0 - position * 2.0
            try:
                on_frame(ease_in_out_quad(phase))
            except Exception:
                return
            self._pending = self._after(self._frame_ms, advance)

        self._pending = self._after(self._frame_ms, advance)

    def stop(self) -> None:
        self._token += 1
        if self._pending is not None:
            try:
                self._cancel(self._pending)
            except Exception:
                pass
            self._pending = None


def fade_in_window(window, after: AfterFn, duration_ms: int = 140) -> Tween:
    """Fade a Toplevel from transparent to opaque; tolerates early destroy."""
    tween = Tween(after, lambda _handle: None, duration_ms=duration_ms)

    def apply(progress: float) -> None:
        try:
            window.attributes('-alpha', progress)
        except Exception:
            tween.cancel()

    try:
        window.attributes('-alpha', 0.0)
    except Exception:
        return tween
    tween.start(apply)
    return tween
