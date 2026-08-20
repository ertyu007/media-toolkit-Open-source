"""Central theme palette shared by the main window and dialogs.

Design language: "Midnight Amethyst" — a deep blue-black base with a violet
accent and layered surface hierarchy so every element reads clearly on a dark
UI while staying cohesive.
"""

# ── Base surfaces (layered dark) ─────────────────────────────────────────────
BG = '#0b0e16'            # window background (deepest)
TOP_BAR_BG = '#0a0d14'    # top bar / action bar strip
ACTION_BG = '#0a0d14'     # bottom action bar
CARD = '#141926'          # card surface
FIELD = '#0e1320'         # input well (entry / combobox)
SECONDARY_BG = '#1a2133'  # secondary / neutral button
BUTTON_BG = '#1a2133'     # plain button surface

# ── Borders / hairlines ──────────────────────────────────────────────────────
BORDER = '#232b3f'        # default border
BORDER_LIGHT = '#1b2335'  # faint hairline (under top bar, card edges)
SECONDARY_BORDER = '#2a3550'
BUTTON_BORDER = '#2a3550'

# ── Text ─────────────────────────────────────────────────────────────────────
TEXT = '#f2f4fb'          # primary text
MUTED = '#8b94ad'         # secondary text
DISABLED_FG = '#5b6478'
TOPBAR_BUTTON_FG = '#c6cde0'

# ── Accent (violet family) ───────────────────────────────────────────────────
ACCENT = '#8b5cf6'        # primary action
ACCENT_HOVER = '#7c4df0'  # pressed / hover
ACCENT_SOFT = '#2a2350'   # tinted fill (active segment, focus chip)
ACCENT_GLOW = '#a78bfa'   # highlight / active stepper
SECTION_ACCENT = '#c4b5fd'  # section header text

# ── Status ───────────────────────────────────────────────────────────────────
DANGER = '#f26d6d'
ERROR = '#f87171'
SUCCESS = '#34d399'
WARNING = '#fbbf24'
TOAST_BG = '#161b29'

# ── Interactives ─────────────────────────────────────────────────────────────
SECONDARY_HOVER = '#232d45'
BUTTON_HOVER = '#232d45'
TOPBAR_BUTTON_BG = '#161c2c'
TOPBAR_BUTTON_HOVER = '#202942'
DISABLED_BG = '#1a2133'

# ── Progress ──────────────────────────────────────────────────────────
PROGRESS_TROUGH = '#1d2436'

# ── Menus / popups ────────────────────────────────────────────────────
MENU_BG = '#161c2c'
MENU_ACTIVE_BG = ACCENT
MENU_ACTIVE_FG = '#ffffff'

# ── Disabled accent state ────────────────────────────────────────────────────
ACCENT_DISABLED_BG = '#3d3660'
ACCENT_DISABLED_FG = '#8f88b8'

# ── Typography ───────────────────────────────────────────────────────────────
FONT_FAMILY = 'Segoe UI'
FONT_SIZE_BASE = 10
FONT_SIZE_SMALL = 9
FONT_SIZE_TITLE = 13
FONT_SIZE_TOP = 12