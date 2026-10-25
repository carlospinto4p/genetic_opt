// @vitest-environment jsdom
import { fireEvent, render, screen } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import type { Run } from '../lib/api'
import knapsackRun from '../fixtures/knapsack-run.json'
import savedRun from '../fixtures/saved-run.json'
import PopulationTable from './PopulationTable.svelte'

const run = knapsackRun as Run<number[]>
// Generation 2: three copies of one chromosome, and two of another
const population = run.generations[2].population

const column = (c: HTMLElement, i: number) =>
  [...c.querySelectorAll('tbody tr')].map((r) => r.children[i].textContent!.trim())

describe('PopulationTable', () => {
  it('shows each chromosome by rank, with where it came from and its copies', () => {
    const { container } = render(PopulationTable, { population })
    expect(column(container, 0)).toEqual(['1', '2', '3', '4', '5', '6', '7', '8'])
    expect(column(container, 2)).toEqual(population.map((m) => String(m.score)))
    expect(column(container, 3)).toEqual([
      'new child',
      'kept',
      'kept',
      'kept',
      'kept',
      'new child',
      'new child',
      'kept',
    ])
    expect(column(container, 4)).toEqual(['2', '2', '1', '1', '1', '3', '3', '3'])
  })

  it('sorts by a column clicked, and the other way on a second click', async () => {
    const { container } = render(PopulationTable, { population })
    const copies = screen.getByText('Copies')
    await fireEvent.click(copies)
    expect(copies.textContent).toBe('Copies ▲')
    // Equal copies keep their rank order
    expect(column(container, 0)).toEqual(['3', '4', '5', '1', '2', '6', '7', '8'])
    await fireEvent.click(copies)
    expect(copies.textContent).toBe('Copies ▼')
    expect(column(container, 0)).toEqual(['8', '7', '6', '2', '1', '5', '4', '3'])
  })

  it('marks the genes the decoding turned off', () => {
    const { container } = render(PopulationTable, {
      population,
      off: (m) => (m.genes[0] === 1 ? [0] : []),
    })
    expect(container.querySelectorAll('.gene.off')).toHaveLength(2)
  })

  it('has no "Where from" column for a saved run', () => {
    const saved = savedRun as unknown as Run<null>
    render(PopulationTable, { population: saved.generations[1].population })
    expect(screen.queryByText('Where from')).toBeNull()
  })

  it('shows genes that are not bits as text', () => {
    const { container } = render(PopulationTable, {
      population: [{ genes: ['red', 2.5, null], decoded: null, score: 1 }],
    })
    expect(container.querySelector('.strip')).toBeNull()
    expect([...container.querySelectorAll('code')].map((c) => c.textContent)).toEqual([
      'red',
      '2.5',
      '',
    ])
  })
})
