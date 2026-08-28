"""OpenRouter-backed ``TextAIProvider``: copy + carousel structure planning.

Talks to OpenRouter's OpenAI-compatible API (``/api/v1``) through the OpenAI
SDK — structured outputs (``beta.chat.completions.parse``/``stream``) work
unchanged as long as the routed model supports them (the ``openai/gpt-*``
family does).

Structured-output shapes required by the OpenAI SDK (``_PlannedCarousel`` and
friends) are internal to this adapter — everything crossing the
``TextAIProvider`` port boundary is a domain type (``CarouselPlan``,
``SlideRevision``). ``_planned_to_plan`` is the translation between the two.
"""

from __future__ import annotations

import base64
import io
import json
from typing import Iterator, Literal

import openai
from openai import OpenAI
from pydantic import BaseModel, Field

from ...domain.carousel import (
    ArtDirection,
    Brief,
    CarouselPlan,
    ElementRect,
    Slide,
    SlideElement,
    SlideMotion,
    SlideRevision,
    TextStyle,
)
from ...domain.fonts import normalize_font
from ...domain.layout_defaults import default_elements_for_slide, fonts_for
from ...domain.layout_refine import TextPlacement
from ...prompts import (
    ASSET_AGENT_SYSTEM_PROMPT,
    CHAT_SYSTEM_PROMPT,
    COPY_SYSTEM_PROMPT,
    ICON_NAMES,
    LAYOUT_VISION_SYSTEM_PROMPT,
    build_asset_agent_user_message,
    build_layout_vision_user_message,
    build_plan_user_message,
)

_SlideRole = Literal["hook", "context", "value", "proof", "cta"]


# ---------------------------------------------------------------------------
# Structured-output shapes (adapter-internal — never returned by this class).
# ---------------------------------------------------------------------------

class _PlannedBlock(BaseModel):
    """One EXTRA editable block composing the slide, beyond the automatic
    h1 (headline) / body / chrome blocks."""

    kind: Literal["text", "shape", "icon"] = Field(
        ...,
        description=(
            "text = bloco de texto auxiliar (subtítulo, destaque, legenda...); "
            "shape = forma decorativa (retângulo/elipse/linha/seta); icon = "
            "ícone simples da lista válida."
        ),
    )
    content: str = Field(
        ...,
        description=(
            "Texto do bloco (kind=text); nome do ícone para kind=icon "
            f"(um de: {', '.join(ICON_NAMES)}); \"\" para shape."
        ),
    )
    x: float = Field(..., description="Posição X em % (0-100) do canvas 1080x1350")
    y: float = Field(..., description="Posição Y em % (0-100)")
    w: float = Field(..., description="Largura em % (0-100)")
    h: float = Field(..., description="Altura em % (0-100)")
    color: str = Field(..., description="Cor hex do texto / preenchimento (da paleta)")
    font_size: float = Field(..., description="Tamanho da fonte em px (canvas 1080x1350); 0 para shape/icon")
    weight: int = Field(..., description="Peso da fonte (400-900); 400 para shape/icon")
    align: Literal["left", "center", "right"] = Field(..., description="Alinhamento do texto")
    shape: Literal["rect", "ellipse", "line", "arrow"] = Field(
        ..., description="Forma quando kind=shape; use 'rect' para os demais kinds."
    )
    opacity: float = Field(..., description="Opacidade 0.0-1.0 (1.0 = opaco)")
    z_index: int = Field(..., description="Ordem de empilhamento (blocos de texto padrão usam 8-10)")


class _PlannedSlide(BaseModel):
    role: _SlideRole
    headline: str = Field(..., description="Texto principal do slide (curto, escaneável)")
    body: str = Field(..., description="Linha de apoio opcional; \"\" se não houver")
    visual_prompt: str = Field(
        ...,
        description=(
            "Em INGLÊS: descreve apenas o ELEMENTO VISUAL central + layout do slide "
            "(ícone, diagrama, composição). NÃO inclua o texto da copy aqui."
        ),
    )
    swipe_cue: str = Field(
        ..., description="Open loop / chamada de swipe (ex: 'e tem mais →'); \"\" se não houver"
    )
    motion: SlideMotion
    blocks: list[_PlannedBlock] = Field(
        ...,
        description=(
            "Blocos EXTRAS que complementam o slide (0 a 4): textos auxiliares "
            "(kind=text), formas e ícones. O h1 (headline), body e o chrome "
            "(progresso/handle/swipe) são criados automaticamente — NÃO os "
            "duplique aqui. Use [] quando o slide não precisar de blocos extras."
        ),
    )


class _PlannedCarousel(BaseModel):
    title: str = Field(..., description="Título interno do carrossel")
    handle: str = Field(
        ..., description="@handle da marca para exibir no slide de CTA. \"\" se desconhecido."
    )
    art_direction: ArtDirection
    caption: str = Field(..., description="Legenda do post (com gancho que ecoa o slide 1)")
    hashtags: list[str] = Field(..., description="5 a 12 hashtags relevantes, sem o #")
    slides: list[_PlannedSlide]


class _RevisedSlide(BaseModel):
    index: int = Field(..., description="Índice (1-based) do slide revisado")
    headline: str
    body: str
    visual_prompt: str
    swipe_cue: str


class _RevisedSlides(BaseModel):
    slides: list[_RevisedSlide]


class _CraftedAssetPrompt(BaseModel):
    prompt: str = Field(
        ..., description="Prompt final em inglês para o modelo de assets (gpt-image-1), ativo isolado transparente"
    )


class _PlannedTextPlacement(BaseModel):
    target: Literal["h1", "body", "swipe_cue"] = Field(
        ..., description="Qual bloco de texto este placement posiciona"
    )
    x: float = Field(..., description="Canto superior-esquerdo X em % (0-100) do canvas")
    y: float = Field(..., description="Canto superior-esquerdo Y em % (0-100)")
    w: float = Field(..., description="Largura do bloco em % (0-100)")
    align: Literal["left", "center", "right"] = Field(..., description="Alinhamento do texto")
    font_size: float = Field(..., description="Tamanho da fonte em px do canvas 1080x1350")
    color: str = Field(..., description="Cor hex do texto (uma das cores da paleta)")


class _PlannedTextLayout(BaseModel):
    placements: list[_PlannedTextPlacement]


def _block_to_element(
    block: _PlannedBlock, slide_index: int, seq: int, *, body_font: str
) -> SlideElement:
    rect = ElementRect(x=block.x, y=block.y, w=block.w, h=block.h)
    common = {
        "id": f"s{slide_index}-blk{seq}",
        "rect": rect,
        "z_index": block.z_index,
        "opacity": max(0.0, min(block.opacity, 1.0)),
    }
    if block.kind == "text":
        return SlideElement(
            type="text",
            role="text",
            content=block.content,
            style=TextStyle(
                font_size=block.font_size or 32,
                color=block.color,
                weight=block.weight or 600,
                align=block.align,
                font_family=body_font,
            ),
            **common,
        )
    if block.kind == "icon":
        return SlideElement(
            type="icon",
            role="visual",
            icon_name=block.content.strip() or "sparkles",
            fill=block.color,
            style=TextStyle(color=block.color, font_size=block.font_size or 0),
            **common,
        )
    return SlideElement(
        type="shape",
        role="visual",
        shape=block.shape,
        fill=block.color,
        style=TextStyle(color=block.color),
        **common,
    )


def _planned_to_plan(planned: _PlannedCarousel) -> CarouselPlan:
    total = len(planned.slides)
    planned.art_direction.font_family = normalize_font(planned.art_direction.font_family)
    planned.art_direction.font_family_secondary = normalize_font(
        planned.art_direction.font_family_secondary
    )
    heading_font, body_font = fonts_for(planned.art_direction)
    slides: list[Slide] = []
    for i, p in enumerate(planned.slides):
        slide = Slide(
            index=i + 1,
            role=p.role,
            headline=p.headline,
            body=p.body,
            visual_prompt=p.visual_prompt,
            swipe_cue=p.swipe_cue,
            motion=p.motion,
        )
        slide.elements = default_elements_for_slide(
            slide,
            planned.handle,
            total,
            planned.art_direction.palette,
            heading_font=heading_font,
            body_font=body_font,
        )
        slide.elements.extend(
            _block_to_element(b, slide.index, n + 1, body_font=body_font)
            for n, b in enumerate(p.blocks)
        )
        slides.append(slide)
    return CarouselPlan(
        title=planned.title,
        handle=planned.handle,
        art_direction=planned.art_direction,
        caption=planned.caption,
        hashtags=planned.hashtags,
        slides=slides,
    )


class _ChatTurnStream:
    """Wraps ``client.beta.chat.completions.stream(...)``.

    Entering the underlying context manager (and therefore the actual API
    call) only happens once this object is iterated, so building it has no
    side effects — the request starts lazily, same as the plain iterator
    contract the ``ChatTurnStream`` port expects.
    """

    def __init__(
        self,
        client: OpenAI,
        *,
        model: str,
        messages: list[dict],
        tools: list,
    ) -> None:
        self._client = client
        self._model = model
        self._messages = messages
        self._tools = tools
        self._stream = None

    def __iter__(self) -> Iterator[str]:
        with self._client.beta.chat.completions.stream(
            model=self._model,
            messages=self._messages,
            tools=self._tools,
        ) as stream:
            self._stream = stream
            for event in stream:
                if event.type == "content.delta":
                    yield event.delta

    def result(self) -> tuple[str, CarouselPlan | None]:
        if self._stream is None:
            raise RuntimeError("O stream ainda não foi iterado.")
        completion = self._stream.get_final_completion()
        message = completion.choices[0].message
        if getattr(message, "refusal", None):
            return (f"Não consegui seguir com isso: {message.refusal}", None)

        plan: CarouselPlan | None = None
        if message.tool_calls:
            args = message.tool_calls[0].function.parsed_arguments
            planned: _PlannedCarousel | None = None
            if isinstance(args, _PlannedCarousel):
                planned = args
            elif args is not None:
                planned = _PlannedCarousel.model_validate(args)
            if planned is not None:
                plan = _planned_to_plan(planned)

        text = (message.content or "").strip()
        if plan is not None and not text:
            text = "Montei a estrutura — dá uma olhada no painel ao lado e clique em Gerar quando estiver feliz."
        return text, plan


class OpenRouterTextProvider:
    def __init__(
        self,
        api_key: str | None,
        planning_model: str,
        chat_model: str,
        base_url: str = "https://openrouter.ai/api/v1",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._planning_model = planning_model
        self._chat_model = chat_model
        self._client: OpenAI | None = None
        self._propose_tool = openai.pydantic_function_tool(
            _PlannedCarousel,
            name="propose_carousel",
            description=(
                "Propõe (ou atualiza) a estrutura completa do carrossel: título, handle, "
                "direção de arte, legenda, hashtags e todos os slides. Chame quando tiver "
                "contexto suficiente ou quando o usuário pedir ajustes."
            ),
        )

    def _get_client(self) -> OpenAI:
        if self._client is None:
            if not self._api_key:
                raise RuntimeError(
                    "OPENROUTER_API_KEY não configurada. Crie um .env a partir de .env.example."
                )
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                default_headers={
                    "HTTP-Referer": "http://localhost:5173",
                    "X-Title": "Carousel Studio",
                },
            )
        return self._client

    def plan_carousel(self, brief: Brief) -> CarouselPlan:
        client = self._get_client()
        completion = client.beta.chat.completions.parse(
            model=self._planning_model,
            messages=[
                {"role": "system", "content": COPY_SYSTEM_PROMPT},
                {"role": "user", "content": build_plan_user_message(brief)},
            ],
            response_format=_PlannedCarousel,
        )
        message = completion.choices[0].message
        if getattr(message, "refusal", None):
            raise RuntimeError(f"O modelo recusou a requisição: {message.refusal}")
        parsed = message.parsed
        if parsed is None:
            raise RuntimeError("O modelo não retornou uma estrutura válida.")
        return _planned_to_plan(parsed)

    def _plan_context(self, plan: CarouselPlan) -> str:
        """Compact JSON of the current plan so the model can iterate on it."""
        data = {
            "title": plan.title,
            "handle": plan.handle,
            "art_direction": plan.art_direction.model_dump(),
            "caption": plan.caption,
            "hashtags": plan.hashtags,
            "slides": [
                {
                    "role": s.role,
                    "headline": s.headline,
                    "body": s.body,
                    "visual_prompt": s.visual_prompt,
                    "swipe_cue": s.swipe_cue,
                }
                for s in plan.slides
            ],
        }
        return json.dumps(data, ensure_ascii=False)

    def chat_turn_stream(
        self,
        history: list[dict],
        *,
        current_plan: CarouselPlan | None = None,
        references: list[str] | None = None,
    ) -> _ChatTurnStream:
        """Run one conversational turn, streamed. See ``ChatTurnStream`` port."""
        client = self._get_client()
        messages: list[dict] = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
        if references:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        f"O usuário anexou {len(references)} imagem(ns) de referência "
                        f"({', '.join(references)}). Considere-as ao definir a direção "
                        "de arte."
                    ),
                }
            )
        if current_plan is not None:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Plano atual do carrossel (JSON). Se o usuário pedir ajustes, "
                        "chame propose_carousel com o plano completo atualizado:\n"
                        + self._plan_context(current_plan)
                    ),
                }
            )
        messages.extend(history)

        return _ChatTurnStream(
            client,
            model=self._chat_model,
            messages=messages,
            tools=[self._propose_tool],
        )

    def revise_slides(
        self, plan: CarouselPlan, indices: list[int], instruction: str
    ) -> dict[int, SlideRevision]:
        """Revise copy + visual_prompt of the given slides from a free-text note."""
        client = self._get_client()
        targets = [s for s in plan.slides if s.index in indices]
        payload = {
            "art_direction": plan.art_direction.model_dump(),
            "language_hint": "mantenha o idioma atual da copy",
            "slides_to_revise": [
                {
                    "index": s.index,
                    "role": s.role,
                    "headline": s.headline,
                    "body": s.body,
                    "visual_prompt": s.visual_prompt,
                    "swipe_cue": s.swipe_cue,
                }
                for s in targets
            ],
        }
        user_msg = (
            "Revise APENAS os slides abaixo conforme a instrução do usuário, mantendo "
            "a direção de arte e o estilo do restante do carrossel. Devolva, para cada "
            "um, o index e os campos atualizados (headline, body, visual_prompt em "
            "inglês, swipe_cue).\n\n"
            f"Instrução do usuário: {instruction}\n\n"
            f"Slides (JSON): {json.dumps(payload, ensure_ascii=False)}"
        )
        completion = client.beta.chat.completions.parse(
            model=self._planning_model,
            messages=[
                {"role": "system", "content": COPY_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            response_format=_RevisedSlides,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise RuntimeError("O modelo não retornou a revisão dos slides.")
        return {
            r.index: SlideRevision(
                headline=r.headline,
                body=r.body,
                visual_prompt=r.visual_prompt,
                swipe_cue=r.swipe_cue,
            )
            for r in parsed.slides
        }

    def craft_asset_prompt(
        self, user_request: str, *, art_direction: ArtDirection, slide: Slide
    ) -> str:
        """Dedicated "asset director" agent: turns a short free-text request
        into a fully-directed modelo de assets (gpt-image-1) prompt for an isolated
        transparent block asset. Uses the fast chat model — this is a single,
        cheap text transformation, not full carousel planning."""
        client = self._get_client()
        completion = client.beta.chat.completions.parse(
            model=self._chat_model,
            messages=[
                {"role": "system", "content": ASSET_AGENT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_asset_agent_user_message(user_request, art_direction, slide),
                },
            ],
            response_format=_CraftedAssetPrompt,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise RuntimeError("O modelo não retornou um prompt de ativo válido.")
        return parsed.prompt

    @staticmethod
    def _downscale_for_vision(image_png: bytes, size: tuple[int, int] = (544, 680)) -> bytes:
        """Resize the background to a small, controlled resolution before the
        vision call. Vision pipelines rescale big images unpredictably, which
        is a documented source of coordinate drift — sending a fixed 4:5
        thumbnail (and percent-based coordinates) sidesteps that."""
        from PIL import Image

        img = Image.open(io.BytesIO(image_png)).convert("RGB")
        img = img.resize(size, Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def suggest_text_layout(
        self,
        *,
        image_png: bytes,
        metrics_block: str,
        slide: Slide,
        art_direction: ArtDirection,
        total: int,
    ) -> list[TextPlacement]:
        """Layout-vision agent: the real background image + its metrics grid
        go in, artistic percent-based placements for h1/body/swipe_cue come
        out. Uses the fast multimodal chat model; the caller runs the result
        through ``domain.layout_refine.validate_placements``."""
        client = self._get_client()
        small_png = self._downscale_for_vision(image_png)
        data_url = "data:image/png;base64," + base64.b64encode(small_png).decode()
        completion = client.beta.chat.completions.parse(
            model=self._chat_model,
            messages=[
                {"role": "system", "content": LAYOUT_VISION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": build_layout_vision_user_message(
                                slide, art_direction, total, metrics_block
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            response_format=_PlannedTextLayout,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise RuntimeError("O modelo não retornou um layout de texto válido.")
        return [
            TextPlacement(
                target=p.target,
                x=p.x,
                y=p.y,
                w=p.w,
                align=p.align,
                font_size=p.font_size,
                color=p.color,
            )
            for p in parsed.placements
        ]
