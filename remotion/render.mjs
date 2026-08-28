// Renders one SlideMotion composition: MP4 clip or final composited PNG,
// chosen by the output file extension.
//
//   node render.mjs <inputPropsJsonPath> <outputPath(.mp4|.png)>
//
// Reuses a pre-built bundle in ./bundle when present (created by build.mjs);
// otherwise it bundles on the fly and caches it there. Progress is printed as
// "PROGRESS <0..1>" lines on stdout so the Python worker can follow along.
import { bundle } from '@remotion/bundler'
import { renderMedia, renderStill, selectComposition } from '@remotion/renderer'
import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))

async function main() {
  const [, , propsPath, outPath] = process.argv
  if (!propsPath || !outPath) {
    console.error('usage: node render.mjs <inputPropsJson> <output.mp4|output.png>')
    process.exit(2)
  }

  const inputProps = JSON.parse(readFileSync(propsPath, 'utf-8'))

  const cachedBundle = path.join(here, 'bundle')
  const serveUrl = existsSync(path.join(cachedBundle, 'index.html'))
    ? cachedBundle
    : await bundle({ entryPoint: path.join(here, 'src', 'index.ts') })

  const composition = await selectComposition({
    serveUrl,
    id: 'SlideMotion',
    inputProps,
  })

  if (outPath.toLowerCase().endsWith('.png')) {
    // Final composited frame (background + all blocks settled): the last
    // frame, where every entrance animation has finished.
    await renderStill({
      composition,
      serveUrl,
      output: outPath,
      inputProps,
      imageFormat: 'png',
      frame: composition.durationInFrames - 1,
    })
    console.log('PROGRESS 1.000')
  } else {
    await renderMedia({
      composition,
      serveUrl,
      codec: 'h264',
      outputLocation: outPath,
      inputProps,
      // Silent clip: Instagram accepts it; avoids audio-track edge cases.
      muted: true,
      onProgress: ({ progress }) => {
        console.log(`PROGRESS ${progress.toFixed(3)}`)
      },
    })
  }

  console.log(`DONE ${outPath}`)
}

main().catch((err) => {
  console.error(err?.stack || String(err))
  process.exit(1)
})
