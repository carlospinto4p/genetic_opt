// @vitest-environment jsdom
import { screen } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import type { KnapsackProblem } from '../lib/api'
import examples from '../fixtures/examples.json'
import knapsackRun from '../fixtures/knapsack-run.json'
import { renderPage, serve } from '../test-pages'

async function page() {
  const library = await renderPage(() => import('./Knapsack.svelte'))
  await screen.findByText('The problem')
  return library.fireEvent
}

const text = () => document.body.textContent!.replace(/\s+/g, ' ')
const rows = () => document.querySelectorAll('.objects-card tbody tr')

describe('Knapsack page', () => {
  it('loads the README example', async () => {
    serve({ '/api/examples': examples })
    await page()
    expect(rows()).toHaveLength(10)
    expect(text()).toContain('All 10 objects weigh 537 together.')
    expect(text()).toContain('= 1,024 possible chromosomes.')
  })

  it('shows the error when the examples cannot be loaded', async () => {
    serve({})
    await renderPage(() => import('./Knapsack.svelte'))
    expect(await screen.findByText(/404 Not Found/)).toBeTruthy()
  })

  it('adds and removes objects, and goes back to the example', async () => {
    serve({ '/api/examples': examples })
    const fireEvent = await page()
    await fireEvent.click(screen.getByText('Add an object'))
    expect(rows()).toHaveLength(11)
    await fireEvent.click(screen.getByLabelText('Remove object 1'))
    expect(rows()).toHaveLength(10)
    expect(text()).toContain('All 10 objects weigh 524 together.')
    await fireEvent.click(screen.getByText('Back to the README example'))
    expect(text()).toContain('All 10 objects weigh 537 together.')
  })

  it('runs the problem in the form, and shows the best bag', async () => {
    const fetch = serve({
      '/api/examples': examples,
      '/api/runs/knapsack': () => knapsackRun,
    })
    const fireEvent = await page()
    const size = screen.getByLabelText(/Population size/) as HTMLInputElement
    await fireEvent.input(size, { target: { value: '8' } })
    await fireEvent.click(screen.getByText('Run the algorithm'))
    await screen.findByText('The run')
    const sent = JSON.parse(fetch.mock.calls[1][1]!.body as string) as KnapsackProblem
    expect(sent.fit.population_size).toBe(8)
    expect(sent.weights).toEqual(examples.knapsack.weights)
    // The best of generation 3 asks for objects 2 to 5 and 9; 9 does not fit
    expect(text()).toContain('Weight 157 of 165. Value 234.')
    const states = [...document.querySelectorAll('.object-state')].map((s) => s.textContent)
    expect(states).toEqual([
      'left out',
      ...Array(4).fill('in the bag'),
      ...Array(3).fill('left out'),
      'did not fit',
      'left out',
    ])
  })

  it('names the objects of each bag in the population', async () => {
    serve({ '/api/examples': examples, '/api/runs/knapsack': () => knapsackRun })
    const fireEvent = await page()
    await fireEvent.click(screen.getByText('Run the algorithm'))
    await screen.findByText('The run')
    await fireEvent.click(screen.getByText('Its population (8)'))
    const population = [...document.querySelectorAll('table')].at(-1)!
    const bags = [...population.querySelectorAll('tbody tr')].map((r) =>
      r.children[2].textContent!.trim(),
    )
    expect(bags[0]).toBe('objects 2, 3, 4, 5')
    expect(bags[4]).toBe('objects 1, 4, 7')
  })

  it('shows the error of a run the server refuses', async () => {
    serve({
      '/api/examples': examples,
      '/api/runs/knapsack': () => {
        throw new Error('ValidationException: 10 is greater than population_size = 8')
      },
    })
    const fireEvent = await page()
    await fireEvent.click(screen.getByText('Run the algorithm'))
    expect(await screen.findByText(/10 is greater than population_size = 8/)).toBeTruthy()
    expect(screen.queryByText('The run')).toBeNull()
  })
})
