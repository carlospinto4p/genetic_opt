// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'

// `route` reads the hash once, when the module loads: each test sets
// the hash, then loads a fresh copy.
async function load(hash: string) {
  location.hash = hash
  vi.resetModules()
  return (await import('./router.svelte')).route
}

afterEach(() => {
  location.hash = ''
})

describe('route', () => {
  it('shows the page the hash names', async () => {
    expect((await load('#/knapsack')).path).toBe('/knapsack')
  })

  it('falls back to / for a hash naming no page', async () => {
    expect((await load('#/no-such-page')).path).toBe('/')
  })

  it('falls back to / with no hash', async () => {
    expect((await load('')).path).toBe('/')
  })

  it('follows a hash change, unknown pages included', async () => {
    const route = await load('#/knapsack')
    location.hash = '#/function'
    window.dispatchEvent(new HashChangeEvent('hashchange'))
    expect(route.path).toBe('/function')
    location.hash = '#/nowhere'
    window.dispatchEvent(new HashChangeEvent('hashchange'))
    expect(route.path).toBe('/')
  })
})
