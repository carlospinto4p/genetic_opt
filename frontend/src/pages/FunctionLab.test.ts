// @vitest-environment jsdom
import { screen } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import type { FunctionProblem } from '../lib/api'
import examples from '../fixtures/examples.json'
import functionRun from '../fixtures/function-run.json'
import { renderPage, serve } from '../test-pages'

async function page() {
  const library = await renderPage(() => import('./FunctionLab.svelte'))
  await screen.findByText('The problem')
  return library.fireEvent
}

const text = () => document.body.textContent!.replace(/\s+/g, ' ')

describe('Function page', () => {
  it('runs the interval in the form, and reads the best chromosome', async () => {
    const fetch = serve({ '/api/examples': examples, '/api/runs/function': () => functionRun })
    const fireEvent = await page()
    const bits = screen.getByLabelText('Bits per chromosome') as HTMLInputElement
    expect(bits.max).toBe('40')
    await fireEvent.input(bits, { target: { value: '8' } })
    await fireEvent.click(screen.getByText('Run the algorithm'))
    await screen.findByText('The run')
    const sent = JSON.parse(fetch.mock.calls[1][1]!.body as string) as FunctionProblem
    expect([sent.low, sent.high, sent.n_bits]).toEqual([-1, 2, 8])
    // The best of generation 2, 11001110, is 206 of 255
    expect(text()).toContain(
      'bits 11001110 → number 206 of 255 → x = -1 + (2 − -1) × 206 / 255 = 1.42353 → f(x) = 1.95903',
    )
    expect(document.querySelectorAll('circle[role="presentation"]')).toHaveLength(5)
  })

  it('goes back to the default interval', async () => {
    serve({ '/api/examples': examples })
    const fireEvent = await page()
    const low = screen.getByLabelText('Lowest x') as HTMLInputElement
    await fireEvent.input(low, { target: { value: '0' } })
    expect(low.value).toBe('0')
    await fireEvent.click(screen.getByText('Back to the defaults'))
    expect((screen.getByLabelText('Lowest x') as HTMLInputElement).value).toBe('-1')
  })
})
