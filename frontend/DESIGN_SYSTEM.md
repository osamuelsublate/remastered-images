# Carousel Studio — Design System

Reconstrução fundamentada (mesa redonda Norman · Nielsen · Krug · Rams · Wroblewski · Frost).
Tema escuro, mobile-first, atômico. Fonte única de verdade: os tokens em
[`src/index.css`](src/index.css) (bloco `@theme` do Tailwind v4).

## Princípios

1. **Honestidade material.** Nenhum token mente; nada de fonte declarada e não
   carregada, nada de sombra/raio "mágicos". (Rams + Frost)
2. **Um significante, um significado.** O laranja de marca pertence à ação
   primária e a acentos pontuais (60-30-10). Estado tem sinal próprio. (Norman + Krug)
3. **Acessível e tocável por padrão.** Contraste ≥ 4.5:1, foco visível, alvos
   ≥ 44px, nada dependente só de cor, tudo operável por teclado. (Nielsen + Wroblewski)
4. **Sistema sobre tela.** Token → átomo → molécula → organismo. (Frost, com a
   guarda do Krug: hierarquia de botão restrita a 4.)

> **Frase-guia:** minimalismo honesto, mobile-first e atômico — a única cor de
> marca pertence à ação principal e o conteúdo gerado é o herói.

---

## Antes → Depois

| Elemento | Antes | Depois | Quem sustenta |
|---|---|---|---|
| Fonte | `--font-sans: 'Inter'` **nunca carregada** → fallback silencioso | Stack de sistema honesta e determinística (upgrade opcional p/ Inter abaixo) | Rams (honesto), Frost (verdade única) |
| Texto secundário | `text-zinc-500` ≈ **4.0:1** (reprova) | `text-fg-muted` ≈ 6.9:1 / `text-fg-subtle` ≈ 5.2:1 | Nielsen, WCAG 1.4.3 |
| Placeholder | `text-zinc-600` ≈ **2.3:1** (reprova) | `text-fg-subtle` ≈ 5.2:1 | Nielsen, WCAG 1.4.3 |
| Cor primária | Laranja = botão + balão + seleção + badge + progresso + selo (7 papéis) | Laranja só p/ ação primária + acento de marca (60-30-10) | Norman (significante), Rams (60-30-10) |
| Balão do usuário | `bg-accent` (rouba o sinal do botão) | `bg-surface-3` neutro elevado | Rams × Nielsen (consenso) |
| Foco | Inputs com anel; **botões/cards sem foco** | `focus-visible:ring` em todo interativo | Norman, Nielsen #7, WCAG 2.4.7 |
| Card de slide | `<div onClick>` (sem teclado/ARIA) | `role=button` + `tabIndex` + `aria-pressed` + Enter/Espaço | WCAG 2.1.1, Norman |
| Botões | 3 variantes, sem loading/active/destrutivo | `primary/secondary/ghost/danger` + `loading` + `:active` + tamanhos ≥ 44px | Frost, Nielsen #5, Wroblewski |
| "Gerar tudo de novo" | `primary` (igual a gerar do zero) | `secondary` (evita re-render acidental e custoso) | Nielsen #5 (prevenção de erro) |
| Ícones | Glifos de texto soltos (`◫ + ↑ ✓ ✕ ▶ ❚❚`) | Set SVG line único (`icons.tsx`, stroke 1.5) | Rams (estilo único), Krug |
| Ações por ícone | `+` / `↑` sem rótulo | `IconButton` com `aria-label`/`title` | Krug, Nielsen #6 |
| Erro (app) | `<div>` vermelho ad hoc com `✕` minúsculo | `Alert role="alert"` + dismiss acessível | Nielsen #1/#9 |
| Selo "vídeo" | Chip laranja (compete com a ação) | Chip neutro `bg-black/60` + ícone | Norman, Rams |
| Raio/sombra | `rounded-md/lg/xl/2xl/full` + sombra laranja inline | Escala (`md` controles, `xl` painéis, `full` pílulas) + elevação sóbria | Frost, Rams |
| Estados | Sem skeleton/empty/erro sistematizados | `Skeleton`, `EmptyState`, `Alert`, overlay de loading tokenizado | Nielsen #1 |

---

## Tokens

### Cor (`@theme`)

| Token | Uso |
|---|---|
| `bg` `surface` `surface-2` `surface-3` `line` | Fundo, painéis, controles, hover, bordas |
| `fg` `fg-muted` `fg-subtle` | Texto primário / secundário / terciário+placeholder |
| `primary` `primary-press` | Ação primária e acento de marca (10%) |
| `success` `warning` `error` `info` | Cores semânticas (um significado cada) |

Utilitários Tailwind seguem o nome: `bg-surface`, `text-fg-muted`, `border-line`,
`bg-primary/15`, `ring-error/40`, etc.

### Tipografia
Escala `12 / 14 / 16 / 20 / 24 / 32 / 48` (Tailwind `text-xs…text-5xl`). Corpo
`line-height 1.5`, títulos ~`1.2`. Uma família. Medida-alvo 50–75 caracteres
(`[overflow-wrap:anywhere]` nos balões de chat).

### Espaçamento
Base 4/8 (escala nativa do Tailwind). Padrão de respiro: `p-3`/`p-4` em painéis,
`gap-2`/`gap-3` em grupos.

### Raio
`md` (10px) controles · `lg` (14px) → `xl` (16px) painéis e cards · `full` pílulas/badges.

### Elevação e movimento
`--shadow-sm` / `--shadow-md` sóbrios (sem brilho colorido). Transições
`duration-150` (controles) a `duration-300` (barras), `--ease-standard`.

---

## Componentes

**Átomos:** `Button` · `IconButton` · `TextInput` · `TextArea` · `Field` · `Badge` · `Spinner`
**Moléculas:** `Skeleton` · `EmptyState` · `Alert` · `ProgressBar`
**Organismos:** `SlideCard` (em `PreviewPanel.tsx`), `ChatPanel`, `PreviewPanel`

### Regras de uso

- **Botões:** **um `primary` por contexto** (a ação dominante). `secondary` para
  ações de apoio (baixar, renderizar, re-gerar). `ghost` para ações terciárias
  (novo). `danger` apenas para destrutivo. Todo botão tem alvo ≥ 44px (`size="md"`);
  `size="sm"` (40px) só em densidade alta e nunca como ação primária móvel.
- **Cor:** ~60% neutros (`bg`/`surface*`), ~30% texto/estrutura, ~10% `primary`.
  Status usa **sempre** o token semântico correspondente — nunca a primária.
- **Ícones:** somente de `icons.tsx`. Ícone sem texto ⇒ `IconButton` com `label`.
- **Texto:** `fg` para conteúdo, `fg-muted` para secundário, `fg-subtle` para
  hints/placeholder. Não usar tons abaixo de `fg-subtle` para texto.
- **Espaço/raio:** seguir a escala; não introduzir valores avulsos.

---

## Upgrade opcional: Inter (self-hosted, offline)

A stack de sistema é o default honesto. Para fixar Inter de forma determinística
sem depender de CDN:

```bash
npm i @fontsource-variable/inter
```

```ts
// src/main.tsx
import '@fontsource-variable/inter'
```

```css
/* src/index.css — dentro de @theme */
--font-sans: 'Inter Variable', ui-sans-serif, system-ui, sans-serif;
```

---

## Validação

- **WCAG:** contraste de texto ≥ 4.5:1 (tokens `fg-*` verificados sobre `surface`),
  foco visível em todo interativo, alvos ≥ 44px, estado nunca só por cor.
- **Build:** `npm run lint && npm run build` (tsc + vite) sem erros/avisos.
- Checklist completo (10 heurísticas de Nielsen + 10 princípios de Rams) na
  entrega da Fase 4.
