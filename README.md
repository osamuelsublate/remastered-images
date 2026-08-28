# Carousel Studio

Web app para criar **carrosséis de Instagram** a partir de uma demanda.
Você descreve o brief (tema, objetivo, público, CTA, referências) e a aplicação:

1. **Escreve a copy** com um modelo de texto (`gpt-5.5`) usando um *system prompt*
   que força uma copy **pragmática e minimalista** e segue as melhores práticas
   de carrossel de Instagram (hook que prende, 1 ideia por slide, open loops,
   CTA único, legenda + hashtags).
2. **Propõe o visual** de cada slide (direção de arte consistente entre todos).
3. Deixa você **revisar e editar** copy e prompt visual de qualquer slide.
4. **Gera as imagens** com `gemini-3-pro-image` (via OpenRouter), no formato
   4:5 do Instagram.
5. Permite **baixar** tudo num `.zip` (imagens + `caption.txt`).

> Versões anteriores deste repo remasterizavam fotos de produto. Um exemplo de
> carrossel gerado na época está em [`examples/`](examples/).

---

## Stack

- **Backend:** FastAPI (Python) — integração via OpenRouter (API compatível com
  OpenAI), planejamento de copy com Structured Outputs, geração de imagens em
  background com polling de progresso.
- **Frontend:** React + Vite + TypeScript + Tailwind.
- **Vídeo:** Remotion (Player no navegador + render server-side de MP4).
- **Modelos (via OpenRouter):** `openai/gpt-5.5` (copy/estrutura),
  `google/gemini-3-pro-image` (fundos dos slides, com fallback
  `google/gemini-3.1-flash-image`) e `openai/gpt-image-1` (assets transparentes).

---

## Pré-requisitos

- Python 3.10+
- Node 18+ (testado com Node 22)
- Conta OpenRouter com créditos (https://openrouter.ai)
- Chave de API em `.env` (na raiz do projeto)

---

## Setup

```bash
# 1. Chave de API
cp .env.example .env
# edite .env e preencha OPENROUTER_API_KEY=sk-or-v1-...

# 2. Backend
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 3. Frontend
cd frontend && npm install && cd ..

# 4. Remotion (slides animados) — opcional, mas necessário para gerar vídeos
cd remotion && npm install
npx remotion browser ensure   # baixa o Chrome Headless Shell (~90MB, 1ª vez)
npm run build                 # pré-gera o bundle (acelera os renders)
cd ..
```

---

## Rodando em desenvolvimento

Dois processos (dois terminais):

```bash
# Terminal 1 — backend (porta 8000)
source .venv/bin/activate
cd backend && uvicorn app.main:app --reload --port 8000
```

```bash
# Terminal 2 — frontend (porta 5173, com proxy para o backend)
cd frontend && npm run dev
```

Abra **http://localhost:5173**.

---

## Build de produção (servido pelo backend)

```bash
cd frontend && npm run build && cd ..
source .venv/bin/activate
cd backend && uvicorn app.main:app --port 8000
```

Quando `frontend/dist` existe, o backend serve o app em **http://localhost:8000**
(além da API). O frontend continua chamando `/api` e `/media` na mesma origem.

---

## Como funciona o fluxo

1. **Brief** — preencha tema/objetivo/público/CTA, nº de slides, direção de arte
   (opcional) e suba imagens de referência (opcional).
2. **Plano** — a IA devolve a estrutura completa: título, direção de arte global,
   legenda, hashtags e, por slide, `role` (hook/context/value/proof/cta),
   `headline`, `body`, `swipe_cue` e `visual_prompt`.
3. **Edição** — ajuste qualquer texto ou o prompt visual de cada slide.
4. **Geração** — clique em *Gerar imagens*; o progresso aparece slide a slide.
5. **Download** — baixe o `.zip` com as imagens e a legenda.

As **referências** enviadas são usadas como entrada visual na geração
(entram inline na chamada de chat completions do modelo de imagem); sem
referências, o modelo gera do zero.

---

## Slides animados (Remotion)

Alguns slides podem virar **clipes curtos** (vídeo) para o Instagram. A própria
IA decide, por slide, se anima e como — preenchendo o objeto `motion`
(`animate`, `mode`, `preset`, `intensity`, `duration_seconds`). Normalmente
anima só **2-3 slides de maior impacto** (hook, um slide "aha" e o CTA).

Dois modos:

- **`image`** — anima **sobre o PNG** gerado pela IA (ex.: `kenburns`, `parallax`,
  texto entrando). Bom para capas e CTA.
- **`vector`** — **recria** o slide em código a partir dos dados (paleta,
  tipografia, ícone) e anima vetorialmente (`draw_in`, `loop_pulse`, `count_up`).
  Bom para diagramas/ícones.

Fluxo na interface:

1. **Prévia instantânea** — no card de um slide animável, clique em **▶ prévia**.
   Isso roda o **Remotion Player** no navegador (sem render), usando exatamente
   a mesma composição que o renderer — WYSIWYG.
2. **Renderizar vídeo** — clique em **Renderizar vídeos** (todos os animáveis) ou
   selecione slides e use **Renderizar vídeo**. O backend dispara o renderer do
   Remotion (Node, headless) que exporta um **MP4 1080×1350 (H.264)** por slide.
   O progresso aparece como barra de "renderizando vídeos".
3. **Download** — o `.zip` passa a incluir os `slide-XX.mp4` junto dos PNGs.

A composição é única (`remotion/src/SlideMotion.tsx`) e é compartilhada entre o
Player (via alias `@motion` no Vite) e o renderer server-side (`remotion/render.mjs`),
garantindo que a prévia e o vídeo final sejam idênticos.

> **Setup obrigatório** para gerar vídeos: `cd remotion && npm install`,
> `npx remotion browser ensure` e `npm run build` (passo 4 do Setup). O processo
> do backend precisa do `node` no `PATH` (ou defina `NODE_BIN` no `.env`).
>
> **Licença:** o Remotion é gratuito para indivíduos e empresas de até 3 pessoas;
> acima disso, o uso como automação/embed do Player requer Company License.

---

## Boas práticas embutidas (system prompt)

Baseadas em como profissionais montam carrosséis de alta performance:

- Slide 1 = **hook** que cria *information gap* (não título genérico).
- **1 ideia por slide**; cada slide se sustenta sozinho.
- **Open loops** (swipe cues) para puxar o swipe, sem exagero.
- **CTA único** e específico, conectado ao valor entregue.
- Indicador de progresso (`2/8`), 4:5, identidade visual consistente.
- Copy enxuta: só o que importa.

Edite o prompt em [`backend/app/prompts.py`](backend/app/prompts.py)
(`COPY_SYSTEM_PROMPT`).

---

## Formato das imagens

Instagram usa 1080×1350 (4:5). O modelo de imagem devolve a resolução própria
dele em 4:5 e o backend normaliza (cover-resize) para **1088×1360**.
Configurável via `IMAGE_SIZE` no `.env`.

---

## Estrutura

```
remastered-images/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI + rotas + static
│   │   ├── config.py        # modelos, tamanho, paths, .env
│   │   ├── schemas.py       # Pydantic (brief, plano, structured output)
│   │   ├── prompts.py       # system prompt + builder do prompt de imagem
│   │   ├── adapters/ai/     # OpenRouter: texto, imagem e transcrição
│   │   ├── store.py         # persistência em disco por carrossel
│   │   └── jobs.py          # geração em background com progresso
│   ├── data/                # carrosséis gerados (gitignored)
│   └── requirements.txt
├── frontend/                # React + Vite + Tailwind
│   ├── vite.config.ts       # proxy /api,/media + alias @motion -> ../remotion/src
│   └── src/
│       ├── App.tsx
│       ├── api.ts, types.ts
│       └── components/      # ChatPanel, PreviewPanel (Player), ui
├── remotion/                # composições + renderer de vídeo
│   ├── src/
│   │   ├── index.ts, Root.tsx
│   │   ├── SlideMotion.tsx  # composição única (Player + render)
│   │   └── anim.ts          # helpers de animação/props
│   ├── render.mjs           # renderer por clipe (subprocess do backend)
│   └── build.mjs            # pré-bundle (serveUrl cacheado)
├── examples/                # exemplo de carrossel gerado
├── .env / .env.example
└── README.md
```

---

## API (resumo)

| Método | Rota | Função |
|---|---|---|
| POST | `/api/carousels` | cria uma sessão |
| POST | `/api/carousels/{id}/references` | sobe imagens de referência |
| POST | `/api/carousels/{id}/plan` | gera a estrutura/copy a partir do brief |
| POST | `/api/carousels/{id}/generate` | inicia a geração das imagens (background) |
| POST | `/api/carousels/{id}/regenerate` | refaz slides selecionados (background) |
| POST | `/api/carousels/{id}/animate` | renderiza vídeo(s) dos slides animáveis (background) |
| GET  | `/api/carousels/{id}` | estado atual (para polling de progresso) |
| GET  | `/api/carousels/{id}/download` | `.zip` com slides (PNG + MP4) + legenda |
