"""Central theme palette shared by the main window and dialogs.

Design language: "Dev-Tool Charcoal" — a neutral near-black base with sharp
1px borders, clear type hierarchy, and a single violet accent reserved for
the primary action and active states.
"""

# ── Base surfaces (neutral charcoal) ─────────────────────────────────────────
BG = '#121214'            # window background (deepest)
TOP_BAR_BG = '#17171a'    # top bar / action bar strip
ACTION_BG = '#17171a'     # bottom action bar
CARD = '#1a1a1f'          # card surface
FIELD = '#232329'         # input well (entry / combobox)
SECONDARY_BG = '#26262c'  # secondary / neutral button
BUTTON_BG = '#26262c'     # plain button surface

# ── Borders / hairlines ──────────────────────────────────────────────────────
BORDER = '#2e2e35'        # default border
BORDER_LIGHT = '#222227'  # faint hairline (under top bar, card edges)
SECONDARY_BORDER = '#34343c'
BUTTON_BORDER = '#34343c'

# ── Text ─────────────────────────────────────────────────────────────────────
TEXT = '#e9e9ec'          # primary text
MUTED = '#9b9ba4'         # secondary text
DISABLED_FG = '#5f5f68'
TOPBAR_BUTTON_FG = '#c9c9d1'

# ── Accent (single violet, primary action + active states only) ─────────────
ACCENT = '#8b5cf6'        # primary action
ACCENT_HOVER = '#7c4df0'  # pressed
ACCENT_SOFT = '#262038'   # tinted fill (active segment, focus chip)
ACCENT_GLOW = '#a78bfa'   # hover glow / highlight
SECTION_ACCENT = '#a78bfa'  # section marker

# ── Status ───────────────────────────────────────────────────────────────────
DANGER = '#f26d6d'
ERROR = '#f87171'
SUCCESS = '#34d399'
WARNING = '#fbbf24'
TOAST_BG = '#1e1e24'

# ── Interactives ─────────────────────────────────────────────────────────────
SECONDARY_HOVER = '#2e2e36'
BUTTON_HOVER = '#2e2e36'
TOPBAR_BUTTON_BG = '#1e1e23'
TOPBAR_BUTTON_HOVER = '#2a2a31'
DISABLED_BG = '#222228'

# ── Progress ──────────────────────────────────────────────────────────
PROGRESS_TROUGH = '#26262c'

# ── Menus / popups ────────────────────────────────────────────────────
MENU_BG = '#1e1e24'
MENU_ACTIVE_BG = ACCENT
MENU_ACTIVE_FG = '#ffffff'

# ── Disabled accent state ────────────────────────────────────────────────────
ACCENT_DISABLED_BG = '#3a3454'
ACCENT_DISABLED_FG = '#8f88b8'

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
