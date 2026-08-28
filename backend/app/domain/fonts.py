"""Curated font library available to slides.

Names must match EXACTLY the families registered in ``remotion/src/fonts.ts``
(the single place that actually loads them, for both the in-browser Player and
the server-side Remotion render). Keep the two lists in sync.

The selection covers the styles of well-known design-led products (Inter /
Space Grotesk / Archivo ≈ OpenAI / Anthropic / Stripe; Source Serif / Lora ≈
Claude's editorial serif) plus a few artistic display options (Syne,
Unbounded, Bebas Neue, Playfair Display).
"""

from __future__ import annotations

# (family, short vibe description used in prompts/UI)
CURATED_FONTS: list[tuple[str, str]] = [
    ("Inter", "sans neutra e impecável — padrão de apps modernos (OpenAI, Linear)"),
    ("Geist", "sans minimalista da Vercel — precisão técnica e modernidade"),
    ("Space Grotesk", "grotesca com personalidade técnica — ótima para headlines tech"),
    ("Archivo", "grotesca sólida e versátil, estilo Stripe/Anthropic"),
    ("DM Sans", "sans geométrica limpa e amigável"),
    ("Poppins", "geométrica arredondada, popular em apps consumer"),
    ("Montserrat", "sans elegante de títulos, inspirada em cartazes urbanos"),
    ("Manrope", "sans moderna semi-condensada, ótima legibilidade"),
    ("IBM Plex Sans", "sans corporativa com caráter, estilo IBM"),
    ("Sora", "sans futurista para produtos de tecnologia"),
    ("Syne", "display artística e expressiva — statement pieces"),
    ("Unbounded", "display arredondada ousada — hooks de alto impacto"),
    ("Bebas Neue", "condensada all-caps de pôster — headlines gigantes"),
    ("Playfair Display", "serifada editorial de alto contraste — luxo/moda"),
    ("Lora", "serifada de leitura confortável, tom editorial (estilo Claude)"),
    ("Source Serif 4", "serifada contemporânea para body/citações"),
]

FONT_FAMILIES: list[str] = [name for name, _ in CURATED_FONTS]

DEFAULT_FONT = "Inter"


def normalize_font(family: str | None) -> str:
    """Coerce any free-text family into a valid curated one."""
    if not family:
        return DEFAULT_FONT
    wanted = family.strip().lower()
    for name in FONT_FAMILIES:
        if name.lower() == wanted:
            return name
    return DEFAULT_FONT


def fonts_prompt_block() -> str:
    """Curated list rendered for system prompts (valid names + vibe)."""
    lines = [f'- "{name}" — {desc}' for name, desc in CURATED_FONTS]
    return "\n".join(lines)
