"""Kivy colours, ported from ``clipora/ui_components/theme.py``.

The PC palette is "Dev-Tool Charcoal": neutral near-black surfaces, 1px
borders, one violet accent. Only the dark palette is carried over for the
first APK; add the light one when the app grows a settings screen.

ponytail: dark only. Add the PC light palette + a dark-mode follow-system
switch when an Android user asks for it.
"""

from __future__ import annotations

_PALETTE = {
    'BG': '#121214',
    'CARD': '#1a1a1f',
    'FIELD': '#232329',
    'BUTTON_BG': '#26262c',
    'BORDER': '#2e2e35',
    'TEXT': '#e9e9ec',
    'MUTED': '#9b9ba4',
    'ACCENT': '#8b5cf6',
    'ACCENT_GLOW': '#a78bfa',
    'ERROR': '#f87171',
    'SUCCESS': '#34d399',
    'WARNING': '#fbbf24',
    'DISABLED_BG': '#222228',
    'PROGRESS_TROUGH': '#26262c',
}


def rgba(hex_color: str, alpha: float = 1.0) -> list[float]:
    value = hex_color.lstrip('#')
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    return [*channels, alpha]


def color(name: str, alpha: float = 1.0) -> list[float]:
    return rgba(_PALETTE[name], alpha)
