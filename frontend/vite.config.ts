/// <reference types="vitest/config" />
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { svelteTesting } from '@testing-library/svelte/vite'
import { defineConfig } from 'vite'

// The API, `uv run python -m genetic_opt.web.app`, listens on 5209.
const API_PORT = Number(process.env.GENETIC_OPT_WEB_PORT ?? 5209)

export default defineConfig({
  // `svelteTesting` only acts under Vitest. A component test sets
  // `// @vitest-environment jsdom` itself; the rest run without a DOM.
  plugins: [svelte(), svelteTesting()],
  server: {
    port: 5208,
    strictPort: true,
    proxy: { '/api': `http://127.0.0.1:${API_PORT}` },
  },
  preview: { port: 5208, strictPort: true },
  test: { setupFiles: ['src/test-setup.ts'] },
})
