// For the page tests: each page rendered with an empty store, and the
// replies of the server, recorded from real runs in `fixtures/`, given
// in place of `fetch`.
//
// The replies were recorded from `uv run python -m genetic_opt.web.app`
// with `curl`, on 25th October 2026 (v9.0.10):
// - `examples.json`: `GET /api/examples`.
// - `knapsack-run.json`: `POST /api/runs/knapsack`, the README example
//   with `population_size` 8, `min_population_size` 2, `n_generations`
//   3 and `stop_without_improvement` off.
// - `function-run.json`: `POST /api/runs/function`, the default with
//   `n_bits` 8, `population_size` 6, `min_population_size` 2 and
//   `n_generations` 2, `stop_without_improvement` off.
// - `saved-run.json`: `POST /api/runs/saved` on a JSON run saved by
//   `ones_algorithm` of `tests/unit/conftest.py`, with `population_size`
//   6, `min_population_size` 2 and `n_generations` 3. Its `folder` is
//   replaced with `<folder of the run>`.
import type { Component } from 'svelte'
import { afterEach, vi } from 'vitest'

type Reply = unknown | ((body: unknown) => unknown)

/**
 * Answer each path of `replies` with its JSON, or with what its
 * function returns for the request's body. A thrown `Error` is a 422
 * with its message as the `detail`, as the server sends. A path not
 * given is a 404. Returns the mock, to check the requests made.
 */
export function serve(replies: Record<string, Reply>) {
  const fetch = vi.fn(async (path: string, init?: RequestInit) => {
    if (!(path in replies)) {
      return new Response('', { status: 404, statusText: 'Not Found' })
    }
    const reply = replies[path]
    try {
      const body = init?.body ? JSON.parse(init.body as string) : undefined
      const data = typeof reply === 'function' ? reply(body) : reply
      return Response.json(data)
    } catch (e) {
      return Response.json({ detail: (e as Error).message }, { status: 422 })
    }
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

let unmount = () => {}

afterEach(() => {
  unmount()
  vi.unstubAllGlobals()
})

/**
 * Render the page `load` imports, with every module loaded afresh, so
 * the store starts empty. The testing library is loaded afresh with
 * it, to use the same copy of Svelte; use the `fireEvent` returned.
 */
export async function renderPage(load: () => Promise<{ default: Component }>) {
  vi.resetModules()
  const [{ default: page }, library] = await Promise.all([
    load(),
    import('@testing-library/svelte'),
  ])
  library.render(page)
  unmount = library.cleanup
  return library
}
