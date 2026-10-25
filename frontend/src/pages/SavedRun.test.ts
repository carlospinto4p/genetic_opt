// @vitest-environment jsdom
import { screen } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import savedRun from '../fixtures/saved-run.json'
import { renderPage, serve } from '../test-pages'

async function page() {
  const { fireEvent } = await renderPage(() => import('./SavedRun.svelte'))
  return fireEvent
}

const open = () => screen.getByText('Open') as HTMLButtonElement
const text = () => document.body.textContent!.replace(/\s+/g, ' ')

describe('Saved run page', () => {
  it('opens the folder typed, and shows its parameters and its run', async () => {
    const fetch = serve({ '/api/runs/saved': () => savedRun })
    const fireEvent = await page()
    expect(open().disabled).toBe(true)
    await fireEvent.input(screen.getByLabelText('Folder of the run'), {
      target: { value: '  <folder of the run>  ' },
    })
    await fireEvent.click(open())
    await screen.findByText('The run')
    expect(JSON.parse(fetch.mock.calls[0][1]!.body as string)).toEqual({
      path: '<folder of the run>',
    })
    expect(text()).toContain('<folder of the run>, saved by genetic_opt 9.0.10.')
    const dd = (label: string) => screen.getByText(label).nextElementSibling!.textContent
    expect(dd('Population size')).toBe('6')
    expect(dd('Mutation probability')).toBe('0.05')
    expect(screen.getByText('Population of generation 3 (6)')).toBeTruthy()
  })

  it('shows the error of a folder the server cannot read', async () => {
    serve({
      '/api/runs/saved': () => {
        throw new Error('No run in <folder of the run>')
      },
    })
    const fireEvent = await page()
    await fireEvent.input(screen.getByLabelText('Folder of the run'), {
      target: { value: '<folder of the run>' },
    })
    await fireEvent.click(open())
    expect(await screen.findByText('No run in <folder of the run>')).toBeTruthy()
    expect(screen.queryByText('The run')).toBeNull()
  })
})
