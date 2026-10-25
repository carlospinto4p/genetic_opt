// @vitest-environment jsdom
import { screen } from '@testing-library/svelte'
import { tick } from 'svelte'
import { describe, expect, it, vi } from 'vitest'
import examples from './fixtures/examples.json'
import { renderPage, serve } from './test-pages'

const heading = () => document.querySelector('h1')!.textContent

describe('App', () => {
  it('shows the name and version the server sends', async () => {
    serve({ '/api/info': { name: 'genetic-opt', version: '9.0.10' }, '/api/examples': examples })
    await renderPage(() => import('./App.svelte'))
    expect(await screen.findByText('v9.0.10')).toBeTruthy()
    expect(document.querySelector('.brand-name')!.textContent).toBe('genetic-opt')
  })

  it('says in the console why there is no version', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    serve({ '/api/examples': examples })
    await renderPage(() => import('./App.svelte'))
    await vi.waitFor(() => expect(warn).toHaveBeenCalledOnce())
    expect(warn.mock.calls[0][0]).toBe('Could not load /api/info:')
    expect(document.querySelector('.brand-sub')!.textContent).toBe('')
    warn.mockRestore()
  })

  it('shows the page of the address, from its top, and another when it changes', async () => {
    window.location.hash = '#/saved'
    serve({ '/api/examples': examples })
    const scrollTo = vi.spyOn(Element.prototype, 'scrollTo')
    await renderPage(() => import('./App.svelte'))
    expect(heading()).toBe('Open a saved run')
    window.location.hash = '#/knapsack'
    window.dispatchEvent(new HashChangeEvent('hashchange'))
    await tick()
    expect(heading()).toBe('The knapsack problem')
    expect(scrollTo.mock.calls.at(-1)).toEqual([0, 0])
    expect(scrollTo.mock.contexts.at(-1)).toBe(document.querySelector('main'))
    scrollTo.mockRestore()
  })
})
