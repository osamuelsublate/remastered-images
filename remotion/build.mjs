// Pre-bundles the Remotion project once so renders can reuse the serveUrl
// instead of re-bundling on every clip. Output: ./bundle
import { bundle } from '@remotion/bundler'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))

const serveUrl = await bundle({
  entryPoint: path.join(here, 'src', 'index.ts'),
  outDir: path.join(here, 'bundle'),
  onProgress: (p) => {
    if (p % 20 === 0) console.log(`BUNDLE ${p}%`)
  },
})

console.log(`BUNDLE_DONE ${serveUrl}`)
