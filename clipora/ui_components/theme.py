"""Central theme palette shared by the main window and dialogs.

Design language: "Dev-Tool Charcoal" — a neutral near-black base with sharp
1px borders, clear type hierarchy, and a single violet accent reserved for
the primary action and active states. The light palette mirrors it.

The active palette is picked once at import from ``settings.json``
(``theme``: ``dark``/``light``/``system``, default ``system``), so every
consumer keeps working unchanged. Switching themes needs an app restart.
"""

from __future__ import annotations

THEME_DARK = 'dark'
THEME_LIGHT = 'light'
THEME_SYSTEM = 'system'
THEMES = (THEME_DARK, THEME_LIGHT, THEME_SYSTEM)
DEFAULT_THEME = THEME_SYSTEM

_DARK = {
    # Base surfaces (neutral charcoal)
    'BG': '#121214',
    'TOP_BAR_BG': '#17171a',
    'ACTION_BG': '#17171a',
    'CARD': '#1a1a1f',
    'FIELD': '#232329',
    'SECONDARY_BG': '#26262c',
    'BUTTON_BG': '#26262c',
    # Borders / hairlines
    'BORDER': '#2e2e35',
    'BORDER_LIGHT': '#222227',
    'SECONDARY_BORDER': '#34343c',
    'BUTTON_BORDER': '#34343c',
    # Text
    'TEXT': '#e9e9ec',
    'MUTED': '#9b9ba4',
    'DISABLED_FG': '#5f5f68',
    'TOPBAR_BUTTON_FG': '#c9c9d1',
    # Accent (single violet)
    'ACCENT': '#8b5cf6',
    'ACCENT_HOVER': '#7c4df0',
    'ACCENT_SOFT': '#262038',
    'ACCENT_GLOW': '#a78bfa',
    'SECTION_ACCENT': '#a78bfa',
    # Status
    'DANGER': '#f26d6d',
    'ERROR': '#f87171',
    'SUCCESS': '#34d399',
    'WARNING': '#fbbf24',
    'TOAST_BG': '#1e1e24',
    # Interactives
    'SECONDARY_HOVER': '#2e2e36',
    'BUTTON_HOVER': '#2e2e36',
    'TOPBAR_BUTTON_BG': '#1e1e23',
    'TOPBAR_BUTTON_HOVER': '#2a2a31',
    'DISABLED_BG': '#222228',
    # Progress
    'PROGRESS_TROUGH': '#26262c',
    # Menus / popups
    'MENU_BG': '#1e1e24',
    'MENU_ACTIVE_BG': '#8b5cf6',
    'MENU_ACTIVE_FG': '#ffffff',
    # Disabled accent state
    'ACCENT_DISABLED_BG': '#3a3454',
    'ACCENT_DISABLED_FG': '#8f88b8',
}

_LIGHT = {
    # Base surfaces (neutral paper)
    'BG': '#f2f2f5',
    'TOP_BAR_BG': '#ffffff',
    'ACTION_BG': '#ffffff',
    'CARD': '#ffffff',
    'FIELD': '#e8e8ec',
    'SECONDARY_BG': '#e4e4e9',
    'BUTTON_BG': '#e4e4e9',
    # Borders / hairlines
    'BORDER': '#d8d8de',
    'BORDER_LIGHT': '#e4e4e9',
    'SECONDARY_BORDER': '#cfcfd6',
    'BUTTON_BORDER': '#cfcfd6',
    # Text
    'TEXT': '#1a1a1e',
    'MUTED': '#6b6b75',
    'DISABLED_FG': '#a8a8b0',
    'TOPBAR_BUTTON_FG': '#3a3a42',
    # Accent (same violet, tint lightened for white surfaces)
    'ACCENT': '#8b5cf6',
    'ACCENT_HOVER': '#7c4df0',
    'ACCENT_SOFT': '#e6defa',
    'ACCENT_GLOW': '#a78bfa',
    'SECTION_ACCENT': '#7c4df0',
    # Status (darkened for contrast on white)
    'DANGER': '#e02424',
    'ERROR': '#e02424',
    'SUCCESS': '#0e9f6e',
    'WARNING': '#c27803',
    'TOAST_BG': '#ffffff',
    # Interactives
    'SECONDARY_HOVER': '#dcdce2',
    'BUTTON_HOVER': '#dcdce2',
    'TOPBAR_BUTTON_BG': '#f0f0f4',
    'TOPBAR_BUTTON_HOVER': '#e4e4ea',
    'DISABLED_BG': '#e8e8ec',
    # Progress
    'PROGRESS_TROUGH': '#e0e0e6',
    # Menus / popups
    'MENU_BG': '#ffffff',
    'MENU_ACTIVE_BG': '#8b5cf6',
    'MENU_ACTIVE_FG': '#ffffff',
    # Disabled accent state
    'ACCENT_DISABLED_BG': '#d9d2f0',
    'ACCENT_DISABLED_FG': '#8f88b8',
}


def normalize_theme(value: object) -> str:
    """Validate a theme setting; anything unknown falls back to system."""
    text = str(value or '').strip().lower()
    return text if text in THEMES else DEFAULT_THEME


def detect_system_dark() -> bool:
    """True when the OS is in dark mode (Windows registry; safe fallback)."""
    try:
        import winreg
    except ImportError:
        return True
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize',
        ) as key:
            value, _kind = winreg.QueryValueEx(key, 'AppsUseLightTheme')
            return int(value) == 0
    except OSError:
        return True


def resolve_palette(theme: str, system_dark: bool) -> dict[str, str]:
    """Pick the dark/light color dict; pure (no I/O) for testability."""
    name = normalize_theme(theme)
    if name == THEME_LIGHT or (name == THEME_SYSTEM and not system_dark):
        return dict(_LIGHT)
    return dict(_DARK)


def _read_theme_setting() -> str:
    try:
        from .app_update import load_settings
    except ImportError:
        return DEFAULT_THEME
    try:
        return normalize_theme(load_settings().get('theme'))
    except Exception:
        return DEFAULT_THEME


THEME_NAME = _read_theme_setting()
_PALETTE = resolve_palette(THEME_NAME, detect_system_dark())

# Active palette, exposed under the historic constant names.
BG = _PALETTE['BG']
TOP_BAR_BG = _PALETTE['TOP_BAR_BG']
ACTION_BG = _PALETTE['ACTION_BG']
CARD = _PALETTE['CARD']
FIELD = _PALETTE['FIELD']
SECONDARY_BG = _PALETTE['SECONDARY_BG']
BUTTON_BG = _PALETTE['BUTTON_BG']
BORDER = _PALETTE['BORDER']
BORDER_LIGHT = _PALETTE['BORDER_LIGHT']
SECONDARY_BORDER = _PALETTE['SECONDARY_BORDER']
BUTTON_BORDER = _PALETTE['BUTTON_BORDER']
TEXT = _PALETTE['TEXT']
MUTED = _PALETTE['MUTED']
DISABLED_FG = _PALETTE['DISABLED_FG']
TOPBAR_BUTTON_FG = _PALETTE['TOPBAR_BUTTON_FG']
ACCENT = _PALETTE['ACCENT']
ACCENT_HOVER = _PALETTE['ACCENT_HOVER']
ACCENT_SOFT = _PALETTE['ACCENT_SOFT']
ACCENT_GLOW = _PALETTE['ACCENT_GLOW']
SECTION_ACCENT = _PALETTE['SECTION_ACCENT']
DANGER = _PALETTE['DANGER']
ERROR = _PALETTE['ERROR']
SUCCESS = _PALETTE['SUCCESS']
WARNING = _PALETTE['WARNING']
TOAST_BG = _PALETTE['TOAST_BG']
SECONDARY_HOVER = _PALETTE['SECONDARY_HOVER']
BUTTON_HOVER = _PALETTE['BUTTON_HOVER']
TOPBAR_BUTTON_BG = _PALETTE['TOPBAR_BUTTON_BG']
TOPBAR_BUTTON_HOVER = _PALETTE['TOPBAR_BUTTON_HOVER']
DISABLED_BG = _PALETTE['DISABLED_BG']
PROGRESS_TROUGH = _PALETTE['PROGRESS_TROUGH']
MENU_BG = _PALETTE['MENU_BG']
MENU_ACTIVE_BG = _PALETTE['MENU_ACTIVE_BG']
MENU_ACTIVE_FG = _PALETTE['MENU_ACTIVE_FG']
ACCENT_DISABLED_BG = _PALETTE['ACCENT_DISABLED_BG']
ACCENT_DISABLED_FG = _PALETTE['ACCENT_DISABLED_FG']

# ── Typography ───────────────────────────────────────────────────────────────
FONT_FAMILY = 'Segoe UI'
FONT_SIZE_BASE = 10
FONT_SIZE_SMALL = 9
FONT_SIZE_TITLE = 14
FONT_SIZE_TOP = 13

# Preferred UI font, first available wins. 'Segoe UI Variable Text' is the
# Windows 11 system font tuned for small sizes; older Windows falls back to
# 'Leelawadee UI' (Thai-optimized) and finally plain 'Segoe UI'.
FONT_FALLBACK_CHAIN = (
    'Segoe UI Variable Text',
    'Segoe UI Variable',
    'Leelawadee UI',
    'Segoe UI',
)


def pick_ui_font(available: object) -> str:
    """Return the first :data:`FONT_FALLBACK_CHAIN` entry present in *available*."""
    try:
        names = set(available)  # ponytail: O(n) scan once at startup, no cache needed
    except TypeError:
        return FONT_FAMILY
    for family in FONT_FALLBACK_CHAIN:
        if family in names:
            return family
    return FONT_FAMILY
