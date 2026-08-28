/**
 * Curated font library — the single place that loads fonts for slides.
 *
 * Used by BOTH the in-browser `@remotion/player` (editor, preview,
 * thumbnails, via the frontend's `@motion` alias) and the server-side
 * Remotion render, so what you pick in the editor is exactly what exports.
 *
 * Family names must stay in sync with `backend/app/domain/fonts.py`
 * (`CURATED_FONTS`), which exposes the same list to the planning prompts.
 */

import { loadFont as loadArchivo } from '@remotion/google-fonts/Archivo'
import { loadFont as loadBebasNeue } from '@remotion/google-fonts/BebasNeue'
import { loadFont as loadDMSans } from '@remotion/google-fonts/DMSans'
import { loadFont as loadGeist } from '@remotion/google-fonts/Geist'
import { loadFont as loadIBMPlexSans } from '@remotion/google-fonts/IBMPlexSans'
import { loadFont as loadInter } from '@remotion/google-fonts/Inter'
import { loadFont as loadLora } from '@remotion/google-fonts/Lora'
import { loadFont as loadManrope } from '@remotion/google-fonts/Manrope'
import { loadFont as loadMontserrat } from '@remotion/google-fonts/Montserrat'
import { loadFont as loadPlayfairDisplay } from '@remotion/google-fonts/PlayfairDisplay'
import { loadFont as loadPoppins } from '@remotion/google-fonts/Poppins'
import { loadFont as loadSora } from '@remotion/google-fonts/Sora'
import { loadFont as loadSourceSerif4 } from '@remotion/google-fonts/SourceSerif4'
import { loadFont as loadSpaceGrotesk } from '@remotion/google-fonts/SpaceGrotesk'
import { loadFont as loadSyne } from '@remotion/google-fonts/Syne'
import { loadFont as loadUnbounded } from '@remotion/google-fonts/Unbounded'

type Loader = () => { fontFamily: string }

const LOADERS: Record<string, Loader> = {
  Inter: () => loadInter(),
  Geist: () => loadGeist(),
  'Space Grotesk': () => loadSpaceGrotesk(),
  Archivo: () => loadArchivo(),
  'DM Sans': () => loadDMSans(),
  Poppins: () => loadPoppins(),
  Montserrat: () => loadMontserrat(),
  Manrope: () => loadManrope(),
  'IBM Plex Sans': () => loadIBMPlexSans(),
  Sora: () => loadSora(),
  Syne: () => loadSyne(),
  Unbounded: () => loadUnbounded(),
  'Bebas Neue': () => loadBebasNeue(),
  'Playfair Display': () => loadPlayfairDisplay(),
  Lora: () => loadLora(),
  'Source Serif 4': () => loadSourceSerif4(),
}

/** Family names available in the editor's font picker, in menu order. */
export const FONT_FAMILIES = Object.keys(LOADERS)

const SERIF = new Set(['Playfair Display', 'Lora', 'Source Serif 4'])

const loaded = new Map<string, string>()

/**
 * Idempotently load a curated family and return the CSS `font-family` value
 * (with a sane fallback stack). Unknown names fall back to Inter.
 */
export function ensureFont(family: string | undefined | null): string {
  const name = family && LOADERS[family] ? family : 'Inter'
  let resolved = loaded.get(name)
  if (!resolved) {
    resolved = LOADERS[name]().fontFamily
    loaded.set(name, resolved)
  }
  const fallback = SERIF.has(name) ? 'serif' : 'ui-sans-serif, system-ui, sans-serif'
  return `"${resolved}", ${fallback}`
}
