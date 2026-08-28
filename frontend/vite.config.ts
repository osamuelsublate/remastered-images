import { defineConfig } from 'vite'
import { fileURLToPath, URL } from 'node:url'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: [
      // Share the Remotion compositions with the in-browser Player.
      { find: '@motion', replacement: fileURLToPath(new URL('../remotion/src', import.meta.url)) },
      // `remotion/src` lives in a sibling npm project with its OWN
      // node_modules (its own react/react-dom/remotion copies). Without
      // forcing these to resolve to this project's single copies,
      // `@remotion/player` (using this project's React) and `AbsoluteFill`
      // etc. (resolved from `remotion/node_modules` when imported by the
      // aliased source) end up as two different React instances in the
      // same page — causing "Invalid hook call" / broken Player rendering.
      { find: /^react$/, replacement: fileURLToPath(new URL('./node_modules/react', import.meta.url)) },
      { find: /^react\/(.+)$/, replacement: fileURLToPath(new URL('./node_modules/react/$1', import.meta.url)) },
      { find: /^react-dom$/, replacement: fileURLToPath(new URL('./node_modules/react-dom', import.meta.url)) },
      { find: /^react-dom\/(.+)$/, replacement: fileURLToPath(new URL('./node_modules/react-dom/$1', import.meta.url)) },
      // Same single-instance treatment for @remotion/google-fonts (imported
      // by the aliased `@motion/fonts`), which itself imports `remotion`.
      // Subpath imports (`@remotion/google-fonts/Inter`) must map straight
      // to the ESM build files — a plain directory alias would bypass the
      // package's `exports` map and fail to resolve.
      {
        find: /^@remotion\/google-fonts\/(.+)$/,
        replacement: fileURLToPath(
          new URL('./node_modules/@remotion/google-fonts/dist/esm/$1.mjs', import.meta.url),
        ),
      },
      { find: /^remotion$/, replacement: fileURLToPath(new URL('./node_modules/remotion', import.meta.url)) },
      { find: /^remotion\/(.+)$/, replacement: fileURLToPath(new URL('./node_modules/remotion/$1', import.meta.url)) },
    ],
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/media': 'http://127.0.0.1:8000',
    },
  },
})
