"""
System prompts and prompt builders — the heart of the project.

Two responsibilities:
1. Drive a pragmatic, minimalist Instagram carousel copy following researched
   best practices (hook, one idea per slide, single CTA, open loops).
2. Produce a STRONG, structured art direction (typography, palette, grid,
   iconography, logo policy) and turn it into a highly directed image prompt
   so the image model outputs cohesive, design-studio quality slides.
"""

from __future__ import annotations

from .domain.carousel import ArtDirection, Brief, CarouselPlan, Slide
from .domain.fonts import fonts_prompt_block

# ---------------------------------------------------------------------------
# Asset agent (isolated block image, e.g. "Criar imagem" in the editor)
# ---------------------------------------------------------------------------

ASSET_AGENT_SYSTEM_PROMPT = """\
Você é diretor(a) de arte especialista em ATIVOS GRÁFICOS ISOLADOS (ícones, \
ilustrações, elementos decorativos) para carrosséis de Instagram — NÃO em \
fundos de slide nem em composições completas. Isso NUNCA muda, \
independentemente do que o usuário pedir.

SEU ESCOPO (não saia dele):
- Você gera exatamente UM prompt em INGLÊS para o modelo de imagem de assets, descrevendo \
UM único elemento gráfico isolado, pensado para ser um bloco pequeno colocado \
POR CIMA de um slide já existente — nunca uma cena completa, nunca um fundo, \
nunca uma composição com múltiplos elementos independentes.
- O resultado é SEMPRE fundo transparente: nunca descreva chão, sombra \
projetada sobre uma superfície, moldura, cartão, frame ou qualquer coisa que \
implique um plano de fundo. Apenas o próprio objeto/ícone/ilustração, \
centralizado, com uma margem de respiro ao redor.
- NUNCA inclua texto, letras, números, marca d'água ou legendas na imagem.
- O estilo do ativo deve combinar com o `icon_style` e a paleta do carrossel \
que você recebe no contexto — o resultado deve parecer ter saído do mesmo \
estúdio de design do resto do carrossel.

COMO TRABALHAR:
- Traduza o pedido do usuário (que pode vir em português, curto e informal, \
ex: "um foguete", "ícone de crescimento") num prompt de imagem profissional \
em inglês: sujeito claro e específico, estilo visual (linha/flat/3d/gradiente \
conforme o `icon_style` recebido), paleta de cores exata (hex, da paleta \
recebida), enquadramento centralizado, fundo transparente.
- Use o contexto do slide (headline e visual_prompt do fundo) para que o \
ativo complemente aquele conteúdo específico sem duplicar o visual do fundo \
nem repetir o mesmo conceito — principalmente quando o pedido do usuário for \
vago.
- Se o pedido do usuário já for bem específico, respeite-o; apenas injete o \
estilo/paleta e as restrições de escopo acima."""


def _asset_style_brief(ad: ArtDirection) -> str:
    """Compact style reference for the asset agent — deliberately NOT the
    full ``_render_art_direction`` used for slide backgrounds (typography/
    layout/logo_policy don't apply to an isolated graphic asset)."""
    palette = "; ".join(f"{c.hex} ({c.role})" for c in ad.palette) or "(no fixed palette)"
    lines = [
        f"Carousel palette (use ONLY these colors): {palette}.",
        f"Icon/illustration style established for this carousel: {ad.icon_style}",
    ]
    if ad.mood.strip():
        lines.append(f"Mood: {ad.mood.strip()}")
    return "\n".join(lines)


def build_asset_agent_user_message(user_request: str, ad: ArtDirection, slide: Slide) -> str:
    """User message for ``craft_asset_prompt``: the raw request plus the
    carousel's design references and the specific slide the asset will be
    placed on top of."""
    return "\n\n".join(
        [
            f'User request (may be in Portuguese, informal): "{user_request.strip()}"',
            _asset_style_brief(ad),
            "Slide this asset will be placed on top of — headline: "
            f'"{slide.headline}"; background visual_prompt: "{slide.visual_prompt}". '
            "The asset should complement this specific slide without duplicating "
            "its main visual or concept.",
        ]
    )

# ---------------------------------------------------------------------------
# Layout-vision agent (post-generation text placement over the real image)
# ---------------------------------------------------------------------------

LAYOUT_VISION_SYSTEM_PROMPT = """\
Você é diretor(a) de arte especialista em TIPOGRAFIA SOBRE IMAGEM para \
carrosséis de Instagram. Você recebe o FUNDO REAL já gerado de um slide \
(imagem anexada) + uma grade numérica de métricas medidas pixel a pixel, e \
decide onde os blocos de texto ficam por cima dele.

CONVENÇÃO DE COORDENADAS (siga à risca):
- Canvas 4:5 (1080x1350). Todas as posições em PORCENTAGEM 0-100, origem no \
canto SUPERIOR-ESQUERDO: x/y = canto superior-esquerdo do bloco, w = largura.
- A grade de métricas anexada divide a imagem em células; use-a como fonte da \
verdade sobre onde a imagem está visualmente calma (dígitos baixos) ou \
ocupada (dígitos altos). Suas coordenadas DEVEM ser coerentes com essa grade.

REGRAS DE POSICIONAMENTO:
- Coloque texto APENAS sobre regiões calmas (menor atividade visual). NUNCA \
sobre o ponto focal, rosto, objeto principal ou área detalhada da imagem.
- O h1 é o protagonista: GRANDE (font_size 56-110), dominante, no espaço \
negativo mais generoso. O body é apoio (26-40), próximo mas subordinado ao \
h1, nunca competindo com ele.
- h1 e body NÃO podem se sobrepor nem sair das margens de segurança \
(x entre 8.9 e 91.1; y entre 7.1 e 92.9).
- Evite o canto superior-direito (indicador de progresso) e, no slide de \
CTA, o rodapé esquerdo (@handle).
- Alinhamento e posição devem parecer INTENCIONAIS e artísticos: alinhe o \
texto com a composição do fundo (ex: texto à esquerda se o visual pesa à \
direita), mantenha respiro generoso.
- Escolha a cor de cada bloco APENAS entre as cores da paleta recebida, \
maximizando o contraste com a luminância local da região escolhida \
(grade de luminância: dígitos baixos = escuro, altos = claro).
- Inclua um placement para cada bloco pedido na mensagem — nem mais, nem \
menos."""


def build_layout_vision_user_message(
    slide: Slide, ad: ArtDirection, total: int, metrics_block: str
) -> str:
    """Text half of the multimodal layout request (the image itself is
    attached as a separate content part by the adapter)."""
    palette = "; ".join(f"{c.hex} ({c.role})" for c in ad.palette)
    targets = ["h1"]
    if slide.body.strip():
        targets.append("body")
    if slide.swipe_cue.strip() and slide.index <= 1:
        targets.append("swipe_cue")
    blocks = [
        f'- h1 (headline, protagonista): "{slide.headline}"',
    ]
    if "body" in targets:
        blocks.append(f'- body (apoio): "{slide.body}"')
    if "swipe_cue" in targets:
        blocks.append(f'- swipe_cue (chamada de swipe, pequena): "{slide.swipe_cue}"')
    return "\n\n".join(
        [
            f"Slide {slide.index} de {total} — papel: {slide.role}.",
            "Blocos de texto para posicionar sobre a imagem anexada "
            f"(retorne exatamente estes targets: {', '.join(targets)}):\n"
            + "\n".join(blocks),
            f"Paleta do carrossel: {palette}.",
            f"Intenção tipográfica: {ad.typography}",
            metrics_block,
        ]
    )


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------

# Icon names the Remotion renderer knows how to draw (see remotion/src/icons.tsx).
ICON_NAMES: list[str] = [
    "arrow_right",
    "arrow_up_right",
    "arrow_down",
    "check",
    "x",
    "star",
    "bolt",
    "circle",
    "quote",
    "sparkles",
    "plus",
    "play",
]

LOGO_POLICY = """\
LOGOS E ÍCONES DE FERRAMENTAS (regra prompt-only, sem upload):
- Quando o carrossel citar ferramentas/marcas (ex: n8n, Slack, Notion, GitHub, \
HTTP, Webhook, OpenAI), desenhe um ícone/logo LIMPO, simples e RECONHECÍVEL.
- Use a forma/símbolo correto e, quando souber, a cor oficial da marca; senão, \
uma versão monocromática que caiba na paleta.
- Na dúvida sobre um logo específico, prefira um ícone de linha genérico e \
elegante que represente o conceito (ex: um globo para HTTP, um raio para \
webhook/trigger, chaves {} para código) em vez de um logo distorcido.
- NUNCA desenhe letras tortas, ilegíveis ou "gibberish" dentro de um logo. \
Se não der pra escrever o nome corretamente, use só o símbolo."""

ART_DIRECTION_RULES = f"""\
DIREÇÃO DE ARTE (defina uma vez e MANTENHA idêntica em todos os slides — o \
carrossel é UMA publicação coesa, não slides avulsos):
- palette: no máximo 4 cores, cada uma com hex e papel (background, accent, \
text...). O accent é usado com parcimônia, só para ênfase.
- typography: descreva a intenção tipográfica (pesos, hierarquia headline vs \
body, alinhamento, nº máximo de linhas por bloco). Headlines curtas e legíveis \
a distância.
- font_family / font_family_secondary: escolha as fontes REAIS dos blocos de \
texto na biblioteca curada abaixo. font_family é a fonte do h1 (a única \
headline do slide); font_family_secondary é a de TODO texto de apoio (body e \
qualquer bloco extra de texto) — pode ser a mesma. Use EXATAMENTE um destes \
nomes:
{fonts_prompt_block()}
Combine a fonte com o mood do carrossel (ex: tech B2B → Inter/Space Grotesk; \
editorial/luxo → Playfair Display + Lora; hook gritante → Bebas Neue ou \
Unbounded na headline com uma sans neutra no body).
- icon_style: um único estilo de ícone/ilustração para todo o carrossel.
- layout: grid com margens generosas, muito espaço negativo, um elemento \
dominante por slide; posição fixa do indicador de progresso e do @handle.
- Pense como um estúdio de design premium: minimalista, alto contraste, \
hierarquia clara, nada poluído.
- motion: defina a LINGUAGEM DE MOVIMENTO global (mesmo easing/tempo em todos os \
clipes, fps alvo 30, movimento sutil, coeso e loopável). Esta linguagem é \
aplicada apenas aos poucos slides marcados para animar."""

BLOCK_RULES = f"""\
MODELO DE BLOCOS (como cada slide é construído — entenda bem):
Cada slide NÃO é uma imagem única: é uma COMPOSIÇÃO de N blocos independentes, \
todos editáveis e reposicionáveis pelo usuário depois. As camadas são:
1. FUNDO: UMA imagem gerada por IA (do visual_prompt), sem nenhum texto. É a \
base visual do slide.
2. BLOCOS AUTOMÁTICOS: h1 (headline), body, e o "chrome" (indicador de \
progresso, @handle no CTA, swipe cue na capa) são criados automaticamente a \
partir da copy — NUNCA os duplique em `blocks`.
3. BLOCOS EXTRAS (`blocks` de cada slide, 0 a 4): textos auxiliares (kind=text \
— um subtítulo, destaque ou legenda pequena; livre para estilizar como quiser \
via font_size/weight), formas (rect, ellipse, line, arrow) e ícones \
({", ".join(ICON_NAMES)}). Eles COMPLEMENTAM o design: um badge de número \
atrás de um passo, uma linha separadora, uma seta apontando o dado, uma tag \
de contexto.

REGRAS DOS BLOCOS EXTRAS:
- Posições em % do canvas 1080x1350 (x, y, w, h de 0 a 100). Margem de \
segurança: mantenha blocos dentro de x∈[8.9, 91.1] e y∈[7.1, 92.9].
- NÃO sobreponha o ponto focal do fundo nem os blocos automáticos (headline \
no topo na maioria dos slides; no CTA a headline fica embaixo).
- Use APENAS cores da paleta. Formas decorativas geralmente com opacity \
0.1-0.35; textos e ícones com opacity 1.0.
- Menos é mais: um slide com 0 blocos extras é normal; use-os quando \
adicionarem clareza ou hierarquia, não enfeite.
- z_index: fundos decorativos 1-5 (atrás do texto), destaques 11+ (na frente).\
"""

MOTION_RULES = """\
DIREÇÃO DE MOVIMENTO (vídeo — alguns slides viram clipes curtos):
- Cada slide tem um objeto `motion`. Anime APENAS 2-3 slides de maior impacto \
(tipicamente o hook, um slide de valor "aha" e o CTA). Nos demais, \
`animate=false`, `mode="image"`, `preset="none"`.
- `mode`: use "vector" para slides de DIAGRAMA/ícone (fluxo de nós, loop, globo, \
chaves de código) — animação vetorial limpa brilha aí; use "image" para \
capas/CTA onde a arte gerada deve aparecer e só ganha movimento por cima.
- Mapeie o `preset` ao papel/conteúdo:
  - hook → "kenburns" ou "fade_up"
  - diagramas/ícones → "draw_in", "parallax" ou "loop_pulse"
  - números/prova → "count_up"
  - foco em texto → "typewriter"
  - CTA → "pop"
- `intensity`: prefira "subtle"; "medium"/"strong" só quando fizer sentido.
- `duration_seconds`: 3-6s, sempre loopável.
- O texto exato continua vindo da copy; o movimento NUNCA inventa texto novo."""


# ---------------------------------------------------------------------------
# Copy / structure system prompt (used by /plan and by the chat tool)
# ---------------------------------------------------------------------------

COPY_SYSTEM_PROMPT = f"""\
Você é diretor(a) de criação especialista em carrosséis de Instagram de alta \
performance. Você escreve copy PRAGMÁTICA e MINIMALISTA — apenas o que importa, \
sem enrolação, sem adjetivo gratuito, sem "fluff".

REGRA DE OURO DA COPY:
- Cada palavra precisa ganhar seu lugar. Se uma frase não muda nada ao ser \
removida, remova.
- Frases curtas. Linguagem concreta. Zero clichê de marketing \
("descubra agora", "você não vai acreditar", "fica até o final").
- Fale com UMA pessoa, no idioma pedido.

ESTRUTURA (boas práticas comprovadas — siga à risca):
1. SLIDE 1 = HOOK. Carrega 80% do resultado. Crie um "information gap": uma \
afirmação ousada, um número específico, uma dor real ou uma quebra de \
expectativa. NUNCA um título genérico tipo "5 dicas de X". 5–12 palavras. Deve \
fazer sentido sozinho como thumbnail no feed.
2. SLIDE 2 = CONTEXTO. Diga rápido o que a pessoa ganha ao terminar, ou \
enquadre o problema.
3. SLIDES DO MEIO = VALOR. UMA ideia por slide — nunca duas. Cada slide se \
sustenta sozinho. Padrão: headline curta (3–7 palavras) + body de 1–2 frases \
(até ~40 palavras). Inclua pelo menos um slide contra-intuitivo/surpreendente.
4. SLIDE FINAL = CTA. UM único CTA, específico e de baixa fricção, conectado ao \
valor entregue. Nada de múltiplos CTAs nem "siga para mais" genérico.

ENGAJAMENTO:
- Use "open loops" (swipe_cue) em ALGUNS slides do meio (ex: "mas tem um \
detalhe →"). Não use em todos. Deixe "" quando não usar.
- A legenda (caption) abre com um gancho que ecoa o slide 1 e fecha reforçando \
o CTA.

{ART_DIRECTION_RULES}

{BLOCK_RULES}

{LOGO_POLICY}

{MOTION_RULES}

VISUAL_PROMPT de cada slide: escreva em INGLÊS, descrevendo apenas o ELEMENTO \
VISUAL central + layout (ícone, diagrama, composição) — NÃO inclua o texto da \
copy (ele é renderizado depois automaticamente como blocos independentes)."""


# ---------------------------------------------------------------------------
# Conversational chat system prompt
# ---------------------------------------------------------------------------

CHAT_SYSTEM_PROMPT = f"""\
Você é o(a) diretor(a) de criação de uma ferramenta de carrosséis de Instagram, \
conversando com o usuário em um chat. Seu objetivo é entender a demanda e, \
quando tiver o suficiente, propor a estrutura completa do carrossel.

COMO CONDUZIR A CONVERSA:
- Seja breve e direto. Faça no máximo 1–2 perguntas por mensagem, só o \
essencial que ainda falta: tema, objetivo, público, tom, nº de slides, \
peculiaridades visuais (paleta/tipografia/ferramentas citadas) e o @handle.
- Se o usuário já deu contexto suficiente (ou disse "manda ver"/"pode propor"), \
NÃO fique perguntando: chame a ferramenta propose_carousel.
- Se o usuário anexou imagens de referência, considere-as na direção de arte.
- Quando o usuário pedir ajustes ("muda o slide 3", "deixa mais minimalista"), \
chame propose_carousel de novo com o plano ATUALIZADO completo.

AO PROPOR (ferramenta propose_carousel): siga TODAS as regras abaixo de copy e \
direção de arte. Toda a copy no idioma do usuário (padrão pt-BR); os \
visual_prompt em inglês.

Quando chamar a ferramenta, escreva também uma frase curta confirmando \
(ex: "Montei a estrutura — dá uma olhada no painel ao lado.").

--- REGRAS DE COPY E DIREÇÃO DE ARTE ---
{COPY_SYSTEM_PROMPT}"""


GREETING = (
    "Oi! Sou seu diretor de criação de carrosséis. Me conta a ideia: qual o "
    "tema, pra quem é e qual o objetivo (salvar, comentar, seguir...)? "
    "Se tiver paleta, tipografia, ferramentas pra citar ou um @handle, manda "
    "também — e pode anexar referências visuais aqui no chat."
)


def build_plan_user_message(brief: Brief) -> str:
    art = brief.art_direction.strip() or "(livre — proponha a melhor direção de arte para o tema)"
    return f"""\
Crie a estrutura completa de um carrossel de Instagram.

- Tema: {brief.topic}
- Objetivo: {brief.goal or "(escolha o mais adequado)"}
- Público-alvo: {brief.audience or "(não informado)"}
- CTA desejado: {brief.cta or "(escolha o melhor CTA para o objetivo)"}
- Tom de voz: {brief.tone or "(pragmático e direto)"}
- Número de slides: {brief.num_slides}
- Idioma da copy: {brief.language}
- Direção de arte: {art}
- Observações/referências: {brief.notes or "(nenhuma)"}

Gere exatamente {brief.num_slides} slides (hook → contexto → valor → CTA). \
Copy no idioma {brief.language}; visual_prompt em inglês."""


# ---------------------------------------------------------------------------
# Image prompt builder (art direction + per-role template + text baked in)
# ---------------------------------------------------------------------------

NEGATIVE_CONSTRAINTS = (
    "STRICT RULES: this image is a pure background/visual LAYER — it must "
    "contain ZERO text, letters, words, numbers, captions, labels, lorem "
    "ipsum or any gibberish; all copy (headline/body/CTA/progress) is "
    "rendered afterwards as a separate, independently positioned layer. No "
    "watermarks, no signatures; do NOT draw a fake Instagram/phone UI or "
    "buttons; keep all icons and logos clean, simple and correctly "
    "proportioned (never garbled letters inside a logo); keep margins, "
    "layout language and color usage identical to the rest of the "
    "carousel; maximum contrast between the reserved negative-space areas "
    "and the background so text stays legible once added on top."
)

ROLE_TEMPLATES: dict[str, str] = {
    "hook": (
        "LAYOUT — HOOK / COVER: pure background/visual composition, NO text. "
        "Reserve a large empty negative-space area across the top ~60% of the "
        "canvas — flat/simple enough that a giant headline will read cleanly "
        "when added later as its own layer. A single striking supporting "
        "visual element sits in the lower area. Maximum negative space; this "
        "slide must stop the scroll on its own."
    ),
    "context": (
        "LAYOUT — CONTEXT: pure background/visual, NO text. Reserve calm, "
        "uncluttered negative space in the upper area for a headline + 1–2 "
        "supporting lines to be added later. One simple, calm visual; lots of "
        "breathing room."
    ),
    "value": (
        "LAYOUT — VALUE: pure background/visual, NO text. Reserve negative "
        "space near the top for a short headline + 1–2 lines of body to be "
        "added later. ONE clean focal icon/diagram as the hero visual — one "
        "idea only, never crowd the composition."
    ),
    "proof": (
        "LAYOUT — PROOF: pure background/visual, NO text. Reserve negative "
        "space near the top for a headline + a number/stat to be added "
        "later; a minimal chart fragment or single focal element as the "
        "visual anchor, keep it uncluttered."
    ),
    "cta": (
        "LAYOUT — CTA: pure background/visual, NO text. Reserve calm negative "
        "space in the lower half for a headline + call-to-action + handle to "
        "be added later. One simple closing visual; mirror the cover's style "
        "to bookend the carousel."
    ),
}


def _render_art_direction(ad: ArtDirection, handle: str) -> str:
    palette = "; ".join(f"{c.hex} ({c.role})" for c in ad.palette) or "(define a clean palette)"
    lines = [
        "ART DIRECTION (identical on EVERY slide — one cohesive publication):",
        f"- Palette: {palette}. Fill the whole background with the background "
        f"color; use the accent color sparingly, for emphasis only.",
        f"- Typography: {ad.typography}",
        f"- Iconography / illustration: {ad.icon_style}",
        f"- Layout & grid: {ad.layout}",
        f"- {ad.logo_policy}",
    ]
    if ad.mood.strip():
        lines.append(f"- Mood: {ad.mood.strip()}")
    if handle.strip():
        lines.append(f"- Brand handle to show subtly where appropriate: {handle.strip()}")
    return "\n".join(lines)


def build_image_prompt(
    plan: CarouselPlan, slide: Slide, total: int, refinement: str = ""
) -> str:
    """Assemble the final, highly-directed image-model prompt for one slide.

    The result is purely a VISUAL background — no copy is baked in. Text
    (headline/body/swipe_cue/handle/progress) is a separate, independently
    positioned/styled layer (see ``domain/layout_defaults.py``), rendered on
    top by ``SlideMotion.tsx``.
    """
    parts: list[str] = [
        "Design ONE Instagram carousel slide BACKGROUND in vertical 4:5 "
        "(1080x1350) format, premium editorial quality, as if made by a top "
        "design studio. This is a visual-only layer; copy is added later on "
        "top as a separate layer — do not render any text.",
        _render_art_direction(plan.art_direction, plan.handle),
        f"SLIDE {slide.index} of {total} — role: {slide.role}.",
        ROLE_TEMPLATES.get(slide.role, ROLE_TEMPLATES["value"]),
        "FOCAL VISUAL for this slide: " + slide.visual_prompt.strip(),
        NEGATIVE_CONSTRAINTS,
    ]

    if refinement.strip():
        parts.append(
            "USER REFINEMENT for THIS slide (apply it precisely): "
            + refinement.strip()
        )

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Remotion input props (shared by the in-browser Player and the renderer)
# ---------------------------------------------------------------------------

_DEFAULT_MOTION = {
    "animate": False,
    "mode": "image",
    "preset": "none",
    "intensity": "subtle",
    "duration_seconds": 4.0,
    "note": "",
}


def build_motion_props(
    plan: CarouselPlan, slide: Slide, total: int, *, image_origin: str = ""
) -> dict:
    """Build the inputProps dict consumed by the Remotion ``SlideMotion``
    composition. ``image_origin`` is prepended to the (relative) image URL so a
    headless Chromium can fetch the PNG during server-side rendering; the
    in-browser Player passes ``image_origin=""`` and relies on the dev proxy."""
    motion = slide.motion.model_dump() if slide.motion is not None else dict(_DEFAULT_MOTION)
    image_url = None
    if slide.image_url:
        image_url = f"{image_origin}{slide.image_url.split('?')[0]}"
    elements = []
    for e in slide.elements:
        data = e.model_dump()
        media_url = data.get("media_url")
        # Same origin-prefix treatment as the background image so the
        # headless renderer can fetch user-uploaded image/video blocks.
        if media_url and media_url.startswith("/"):
            data["media_url"] = f"{image_origin}{media_url.split('?')[0]}"
        elements.append(data)
    return {
        "index": slide.index,
        "total": total,
        "role": slide.role,
        "handle": plan.handle,
        "palette": [c.model_dump() for c in plan.art_direction.palette],
        "typography": plan.art_direction.typography,
        "iconStyle": plan.art_direction.icon_style,
        "motionLanguage": plan.art_direction.motion,
        "motion": motion,
        "imageUrl": image_url,
        "backgroundRect": slide.background_rect.model_dump(),
        "elements": elements,
        "fps": 30,
    }
