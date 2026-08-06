"""Built-in Textual themes for FalkorTerm."""

from __future__ import annotations

from textual.theme import Theme

# Shared dark base (Blade Runner blacks with a slight purple cast).
_FLUX_BG = "#050508"
_FLUX_SURFACE = "#0C0A10"
_FLUX_PANEL = "#121018"
_FLUX_FG = "#F2E6F0"


def _flux_variables(*, accent: str, primary: str) -> dict[str, str]:
    """Cursor/selection overrides. Values must be concrete colors (no $vars)."""
    return {
        "block-cursor-background": accent,
        "block-cursor-text-style": "bold",
        "input-cursor-background": accent,
        "input-selection-background": f"{primary}66",
    }


FALKORTERM_THEME = Theme(
    name="falkorterm",
    primary="#1A6B6B",
    secondary="#2A8F8F",
    accent="#3ECFCF",
    warning="#D4A017",
    error="#E05C5C",
    success="#3CB371",
    foreground="#D8E6E6",
    background="#0D1416",
    surface="#121C1F",
    panel="#162428",
    dark=True,
)

# Flux 1 — fuchsia only
_FLUX_1_ACCENT = "#FF2D95"
_FLUX_1_PRIMARY = "#8B1E5A"
FLUX_1 = Theme(
    name="flux-1",
    primary=_FLUX_1_PRIMARY,
    secondary="#C2186B",
    accent=_FLUX_1_ACCENT,
    warning="#E8A0C8",
    error="#FF4D6D",
    success="#3DDC97",
    foreground=_FLUX_FG,
    background=_FLUX_BG,
    surface=_FLUX_SURFACE,
    panel=_FLUX_PANEL,
    dark=True,
    variables=_flux_variables(accent=_FLUX_1_ACCENT, primary=_FLUX_1_PRIMARY),
)

# Flux 2 — fuchsia + cyan Tron
_FLUX_2_ACCENT = "#FF2D95"
_FLUX_2_PRIMARY = "#7A1F5C"
FLUX_2 = Theme(
    name="flux-2",
    primary=_FLUX_2_PRIMARY,
    secondary="#00C8E0",
    accent=_FLUX_2_ACCENT,
    warning="#00E5FF",
    error="#FF4D6D",
    success="#39FF14",
    foreground=_FLUX_FG,
    background=_FLUX_BG,
    surface=_FLUX_SURFACE,
    panel=_FLUX_PANEL,
    dark=True,
    variables=_flux_variables(accent=_FLUX_2_ACCENT, primary=_FLUX_2_PRIMARY),
)

# Flux 3 — fuchsia + deep magenta + amber warning (default)
_FLUX_3_ACCENT = "#FF1F8F"
_FLUX_3_PRIMARY = "#6B1548"
FLUX_3 = Theme(
    name="flux-3",
    primary=_FLUX_3_PRIMARY,
    secondary="#A0126B",
    accent=_FLUX_3_ACCENT,
    warning="#FFB020",
    error="#FF3D5A",
    success="#2EE6A6",
    foreground=_FLUX_FG,
    background=_FLUX_BG,
    surface=_FLUX_SURFACE,
    panel=_FLUX_PANEL,
    dark=True,
    variables=_flux_variables(accent=_FLUX_3_ACCENT, primary=_FLUX_3_PRIMARY),
)

# Luan — neon cyan/purple on pure black (cheat-sheet inspired)
_LUAN_ACCENT = "#5CFFE7"
_LUAN_PRIMARY = "#3D9EFF"
LUAN = Theme(
    name="luan",
    primary=_LUAN_PRIMARY,
    secondary="#B388FF",
    accent=_LUAN_ACCENT,
    warning="#FFB020",
    error="#FF4D8D",
    success="#7CFF6B",
    foreground="#F5F7FA",
    background="#000000",
    surface="#0A0A0F",
    panel="#12121A",
    dark=True,
    variables=_flux_variables(accent=_LUAN_ACCENT, primary=_LUAN_PRIMARY),
)

# Rhodia — Dotpad-inspired flat black/white with signature orange
_RHODIA_ACCENT = "#FF6315"
_RHODIA_PRIMARY = "#C8C8C8"
RHODIA = Theme(
    name="rhodia",
    primary=_RHODIA_PRIMARY,
    secondary="#FF8C42",
    accent=_RHODIA_ACCENT,
    warning="#F0E68C",
    error="#FF4D4D",
    success="#7CB87C",
    foreground="#FFFFFF",
    background="#000000",
    surface="#0A0A0A",
    panel="#141414",
    dark=True,
    variables=_flux_variables(accent=_RHODIA_ACCENT, primary=_RHODIA_PRIMARY),
)

ALL_THEMES: tuple[Theme, ...] = (FLUX_3, FLUX_2, FLUX_1, LUAN, RHODIA, FALKORTERM_THEME)
DEFAULT_THEME_NAME = "flux-3"
