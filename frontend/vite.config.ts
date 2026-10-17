import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig } from 'vite'

// The API, `uv run python -m genetic_opt.web.app`, listens on 5209.
const API_PORT = Number(process.env.GENETIC_OPT_WEB_PORT ?? 5209)

export default defineConfig({
  plugins: [svelte()],
  server: {
    port: 5208,
    strictPort: true,
    proxy: { '/api': `http://127.0.0.1:${API_PORT}` },
  },
  preview: { port: 5208, strictPort: true },
})
