import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Examples, KnapsackProblem, Run } from './api'
import { loadExamples, openSaved, runLab, store } from './store.svelte'

const problem = { weights: [1], values: [2], capacity: 3 } as KnapsackProblem
const run = { generations: [] } as unknown as Run<number[]>

// What `fetch` answers, without a server
function answer(status: number, body: unknown) {
  const fetch = vi.fn(
    async (_path: string, _init: RequestInit) =>
      new Response(JSON.stringify(body), { status }),
  )
  vi.stubGlobal('fetch', fetch)
  return fetch
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('loadExamples', () => {
  const examples = {
    knapsack: problem,
    function: { low: 0, high: 1, n_bits: 4 },
    limits: { n_generations: 200, population_size: 200, genes: 40 },
  } as Examples

  it('asks again after a failed load, and clears its error', async () => {
    answer(500, { detail: 'the server stopped' })
    await loadExamples()
    expect([store.examples, store.examplesError]).toEqual([null, 'the server stopped'])
    const fetch = answer(200, examples)
    await loadExamples()
    expect(fetch).toHaveBeenCalledTimes(1)
    expect([store.examples, store.examplesError]).toEqual([examples, ''])
  })

  // The examples are loaded by the test above
  it('asks nothing more once loaded', async () => {
    const fetch = answer(200, examples)
    await loadExamples()
    await loadExamples()
    expect(fetch).not.toHaveBeenCalled()
  })
})

describe('runLab', () => {
  it('keeps the run and the problem it ran with', async () => {
    const lab = store.knapsack
    lab.problem = structuredClone(problem)
    const done = runLab(lab, async () => run)
    expect(lab.running).toBe(true)
    await done
    expect([lab.run, lab.ran, lab.running, lab.error]).toEqual([run, problem, false, ''])
  })

  it('keeps the error of a failed run', async () => {
    const lab = store.fn
    lab.problem = { low: 0, high: 1, n_bits: 4 } as never
    await runLab(lab, async () => {
      throw new Error('population_size is too large')
    })
    expect([lab.running, lab.error]).toEqual([false, 'population_size is too large'])
  })
})

describe('openSaved', () => {
  it('opens the run at the path typed, trimmed', async () => {
    const fetch = answer(200, { path: '/runs/a' })
    store.saved.path = '  /runs/a '
    await openSaved()
    const [path, init] = fetch.mock.calls[0]
    expect([path, JSON.parse(init.body as string)]).toEqual([
      '/api/runs/saved',
      { path: '/runs/a' },
    ])
    expect([store.saved.run, store.saved.running]).toEqual([{ path: '/runs/a' }, false])
  })

  it('keeps the error the server gives', async () => {
    answer(404, { detail: 'no run at /runs/b' })
    store.saved.path = '/runs/b'
    await openSaved()
    expect([store.saved.running, store.saved.error]).toEqual([false, 'no run at /runs/b'])
  })

  it('asks nothing with no path typed', async () => {
    const fetch = answer(200, {})
    store.saved.path = '  '
    await openSaved()
    expect(fetch).not.toHaveBeenCalled()
  })
})
