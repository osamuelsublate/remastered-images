"""Domain entities: the carousel and everything that composes it.

These models know nothing about HTTP, OpenAI, or the filesystem — they are
the shared vocabulary used by ``application/`` and returned by every port in
``ports/``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

SlideRole = Literal["hook", "context", "value", "proof", "cta"]
MotionPreset = Literal[
    "none",
    "kenburns",
    "fade_up",
    "typewriter",
    "pop",
    "parallax",
    "draw_in",
    "loop_pulse",
    "count_up",
]


class Brief(BaseModel):
    topic: str = Field(..., description="Tema / assunto do carrossel")
    goal: str = Field("", description="Objetivo (ex: gerar saves, leads, autoridade)")
    audience: str = Field("", description="Público-alvo")
    cta: str = Field("", description="Ação desejada no final (salvar, comentar X, DM, link)")
    tone: str = Field("", description="Tom de voz (ex: direto, técnico, descontraído)")
    num_slides: int = Field(8, ge=3, le=12, description="Quantidade de slides")
    language: str = Field("pt-BR", description="Idioma da copy")
    art_direction: str = Field(
        "",
        description="Direção de arte desejada (cores, estilo, vibe). Vazio = a IA propõe.",
    )
    notes: str = Field("", description="Observações livres / referências em texto")


class PaletteColor(BaseModel):
    hex: str = Field(..., description="Cor em hexadecimal, ex: #0a0a0a")
    role: str = Field(
        ...,
        description="Uso da cor: background | accent | text | secondary | muted | etc.",
    )


class ArtDirection(BaseModel):
    palette: list[PaletteColor] = Field(
        ...,
        description=(
            "Paleta com hex e uso. Inclua no mínimo: background, accent e text. "
            "Use no máximo 4 cores para manter coesão."
        ),
    )
    typography: str = Field(
        ...,
        description=(
            "Tipografia: família/estilo (ex: 'grotesca pesada condensada'), pesos, "
            "hierarquia (tamanho da headline vs body), alinhamento e nº máximo de "
            "linhas por bloco."
        ),
    )
    font_family: str = Field(
        "Inter",
        description=(
            "Fonte principal (headlines) escolhida da biblioteca curada de fontes. "
            "Use EXATAMENTE um dos nomes válidos da biblioteca."
        ),
    )
    font_family_secondary: str = Field(
        "Inter",
        description=(
            "Fonte secundária (body/apoio) da biblioteca curada; pode ser igual à "
            "principal. Use EXATAMENTE um dos nomes válidos."
        ),
    )
    icon_style: str = Field(
        ...,
        description=(
            "Estilo de ícones/ilustração (ex: 'line icons monocromáticos, traço "
            "grosso, cantos arredondados'). Deve ser idêntico em todos os slides."
        ),
    )
    layout: str = Field(
        ...,
        description=(
            "Grid, margens/safe-area, posição fixa do indicador de progresso e do "
            "@handle, e a regra de espaço negativo."
        ),
    )
    logo_policy: str = Field(
        ...,
        description="Como tratar logos das ferramentas/marcas citadas no carrossel.",
    )
    mood: str = Field(..., description="Vibe/atmosfera em poucas palavras. \"\" se não houver.")
    motion: str = Field(
        ...,
        description=(
            "Linguagem de movimento global para os slides animados: easing/tempo, "
            "fps alvo (30), regra de manter movimento sutil, coeso e loopável, e "
            "de animar apenas 2-3 slides de maior impacto."
        ),
    )


# Text hierarchy simplified to "h1" (the one headline per slide) + generic
# "text" (any other text block — former body/h2/h3/caption, all free-form in
# style) + carousel chrome roles (swipe_cue/handle/progress) + "visual" for
# non-text blocks (shape/icon/image/video). Legacy roles are migrated on load.
ElementRole = Literal[
    "h1",
    "text",
    "swipe_cue",
    "handle",
    "progress",
    "visual",
]
ElementType = Literal["text", "shape", "icon", "image", "video"]
ShapeKind = Literal["rect", "ellipse", "line", "arrow"]


class ElementRect(BaseModel):
    """Position/size as percentages (0-100) of the 1080x1350 canvas.

    Percent-based so the same rect works at any render resolution (editor
    preview, Player, or the server-side Remotion export) without unit
    conversion beyond a single multiply by the current canvas size.
    """

    x: float = 0.0
    y: float = 0.0
    w: float = 100.0
    h: float = 100.0


class TextStyle(BaseModel):
    font_size: float = 48.0
    color: str = "#ffffff"
    weight: int = 800
    align: Literal["left", "center", "right"] = "left"
    # Must be one of the curated library names (see ``domain/fonts.py``).
    font_family: str = "Inter"
    line_height: float | None = None
    letter_spacing: float | None = None


class SlideElement(BaseModel):
    """One independently positionable, editable block on a slide.

    A slide is a composition of N of these blocks: text at any hierarchy
    level (h1/h2/h3/body/caption), shapes, icons, and user-provided
    image/video blocks. The AI-generated slide image is deliberately NOT one
    of these — it's a single opaque layer addressed via
    ``Slide.background_rect`` instead, the same way Canva treats a photo as
    one draggable/resizable block rather than a set of sub-elements.
    """

    id: str
    type: ElementType = "text"
    role: ElementRole
    rect: ElementRect = Field(default_factory=ElementRect)
    z_index: int = 0
    content: str = ""
    style: TextStyle = Field(default_factory=TextStyle)
    # shape/icon blocks
    shape: ShapeKind | None = None
    fill: str | None = None
    stroke: str | None = None
    stroke_width: float = 0.0
    corner_radius: float = 0.0
    icon_name: str | None = None
    # image/video blocks (user uploads served from /media)
    media_url: str | None = None
    fit: Literal["cover", "contain"] = "cover"
    # Video block duration (seconds), measured client-side on upload so the
    # MP4 export can be at least as long as the clip.
    media_duration_seconds: float | None = None
    # generic
    opacity: float = 1.0
    rotation: float = 0.0

    @field_validator("role", mode="before")
    @classmethod
    def _migrate_legacy_role(cls, v: object) -> object:
        # Carousels persisted before the block model used "headline", and
        # before the h2/h3/body/caption hierarchy collapsed into "text".
        if v == "headline":
            return "h1"
        if v in ("h2", "h3", "body", "caption"):
            return "text"
        return v


class SlideMotion(BaseModel):
    animate: bool = Field(..., description="Se este slide deve virar um vídeo curto animado.")
    mode: Literal["image", "vector"] = Field(
        ...,
        description="image = anima sobre a imagem da IA; vector = recria o slide em código.",
    )
    preset: MotionPreset = Field(
        ..., description="Animação principal; use 'none' quando animate=false."
    )
    intensity: Literal["subtle", "medium", "strong"] = Field(
        ..., description="Intensidade do movimento; prefira 'subtle'."
    )
    duration_seconds: float = Field(
        ..., ge=2, le=8, description="Duração do clipe em segundos, loopável."
    )
    note: str = Field(..., description="O que se move e por quê; \"\" se óbvio.")


class Slide(BaseModel):
    index: int
    role: SlideRole
    headline: str
    body: str = ""
    visual_prompt: str
    swipe_cue: str = ""
    motion: SlideMotion | None = None
    # Layered-editing overlay: independently positioned/styled text/icon
    # elements drawn on top of the background image. Populated with
    # defaults from ``default_elements_for_slide`` when a slide is (re)planned;
    # afterwards the user's own edits (position/style) are the source of
    # truth here, patched (not replaced) on future AI copy revisions.
    elements: list[SlideElement] = Field(default_factory=list)
    # Filled during image generation
    status: Literal["pending", "running", "done", "error"] = "pending"
    image_url: str | None = None
    # Where the background image sits within the 1080x1350 canvas; the area
    # outside it shows the palette's background color. Defaults to full-bleed.
    background_rect: ElementRect = Field(default_factory=ElementRect)
    error: str | None = None
    # Filled during video rendering (Remotion)
    motion_status: Literal["idle", "pending", "running", "done", "error"] = "idle"
    video_url: str | None = None
    motion_error: str | None = None
    # Filled during final export (composited PNG or MP4 for the download zip)
    export_status: Literal["idle", "pending", "running", "done", "error"] = "idle"
    export_error: str | None = None


class CarouselPlan(BaseModel):
    title: str
    handle: str = ""
    art_direction: ArtDirection
    caption: str
    hashtags: list[str]
    slides: list[Slide]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CarouselState(BaseModel):
    id: str
    brief: Brief | None = None
    plan: CarouselPlan | None = None
    references: list[str] = []
    messages: list[ChatMessage] = []
    status: Literal["draft", "planned", "generating", "rendering", "done", "error"] = "draft"
    quality: str = "medium"
    error: str | None = None


class SlideRevision(BaseModel):
    """One slide's revised copy/visual, keyed by ``index`` by the caller."""

    headline: str
    body: str
    visual_prompt: str
    swipe_cue: str
