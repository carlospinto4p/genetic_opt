// @vitest-environment jsdom
import { fireEvent, render, screen } from '@testing-library/svelte'
import { tick } from 'svelte'
import { beforeEach, describe, expect, it } from 'vitest'
import Sidebar from './Sidebar.svelte'

const KEY = 'genetic_opt.sidebarWidth'

const width = (c: HTMLElement) => c.querySelector<HTMLElement>('.sidebar')!.style.width
const handle = () => screen.getByLabelText('Resize sidebar')

async function goTo(hash: string) {
  window.location.hash = hash
  window.dispatchEvent(new HashChangeEvent('hashchange'))
  await tick()
}

beforeEach(() => {
  localStorage.clear()
})

describe('Sidebar', () => {
  it('shows the name and version of the app', () => {
    const { container } = render(Sidebar, { name: 'genetic-opt', version: '9.0.10' })
    expect(container.querySelector('.brand-name')!.textContent).toBe('genetic-opt')
    expect(container.querySelector('.brand-sub')!.textContent).toBe('v9.0.10')
  })

  it('shows no version before it is loaded', () => {
    const { container } = render(Sidebar)
    expect(container.querySelector('.brand-name')!.textContent).toBe('genetic_opt')
    expect(container.querySelector('.brand-sub')!.textContent).toBe('')
  })

  it('marks the page shown, and follows the address', async () => {
    await goTo('#/knapsack')
    render(Sidebar)
    const current = () => screen.getByRole('link', { current: 'page' }).textContent!.trim()
    expect(current()).toBe('Knapsack')
    await goTo('#/saved')
    expect(current()).toBe('Open a saved run')
  })

  it('resizes with the arrow keys, keeps within its limits, and saves the width', async () => {
    const { container } = render(Sidebar)
    expect(width(container)).toBe('260px')
    await fireEvent.keyDown(handle(), { key: 'ArrowRight' })
    expect(width(container)).toBe('268px')
    await fireEvent.keyDown(handle(), { key: 'ArrowLeft', shiftKey: true })
    expect(width(container)).toBe('244px')
    await fireEvent.keyDown(handle(), { key: 'End' })
    await fireEvent.keyDown(handle(), { key: 'ArrowRight' })
    expect(width(container)).toBe('420px')
    expect(localStorage.getItem(KEY)).toBe('420')
  })

  it('resizes by dragging its edge, and goes back to the default on a double click', async () => {
    const { container } = render(Sidebar)
    await fireEvent.mouseDown(handle(), { clientX: 260 })
    await fireEvent.mouseMove(window, { clientX: 300 })
    expect(width(container)).toBe('300px')
    await fireEvent.mouseUp(window)
    expect(localStorage.getItem(KEY)).toBe('300')
    expect(document.body.style.cursor).toBe('')
    await fireEvent.dblClick(handle())
    expect(width(container)).toBe('260px')
  })

  it('starts at the width saved, unless it is out of its limits', () => {
    localStorage.setItem(KEY, '320')
    expect(width(render(Sidebar).container)).toBe('320px')
    localStorage.setItem(KEY, '9000')
    expect(width(render(Sidebar).container)).toBe('260px')
  })
})
