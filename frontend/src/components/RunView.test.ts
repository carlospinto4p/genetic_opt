// @vitest-environment jsdom
import { fireEvent, render, screen } from '@testing-library/svelte'
import { tick } from 'svelte'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Run, StopReason } from '../lib/api'
import knapsackRun from '../fixtures/knapsack-run.json'
import savedRun from '../fixtures/saved-run.json'
import RunView from './RunView.svelte'

const run = knapsackRun as Run<number[]>
const saved = savedRun as unknown as Run<null>
const params = { n_generations: 5, min_population_size: 2 }

const text = (c: HTMLElement) => c.textContent!.replace(/\s+/g, ' ')
const shown = () => document.querySelector('.gen')!.textContent

afterEach(() => {
  vi.useRealTimers()
})

describe('RunView', () => {
  it('sums up the run', () => {
    const { container } = render(RunView, { run, params })
    const tiles = [...container.querySelectorAll('.tile-value')].map((t) => t.textContent)
    expect(tiles).toEqual(['234', '3', '15', '1.5%'])
    expect(text(container)).toContain('15 of 1,024 possible chromosomes.')
  })

  it('says when the search space is too large to count', () => {
    const fit_metrics = { ...run.fit_metrics, space_points: null }
    const { container } = render(RunView, { run: { ...run, fit_metrics }, params })
    expect(text(container)).toContain('15 of more possible chromosomes than can be counted.')
  })

  it.each([
    ['completed', 'It ran all 3 generations.'],
    ['stopped', 'It stopped at generation 3 of the 5 asked. The saved files do not say why.'],
    ['min_population', 'It stopped at generation 3: fewer than 2 different chromosomes'],
    ['no_improvement', 'It stopped at generation 3: the mean score was the same'],
  ] as [StopReason, string][])('says why a run that ended %s stopped', (reason, says) => {
    const { container } = render(RunView, { run: { ...run, stop_reason: reason }, params })
    expect(text(container.querySelector('.stop')!)).toContain(says)
  })

  it('starts on the last generation, and steps with the buttons', async () => {
    render(RunView, { run, params })
    expect(shown()).toBe('Generation 3 of 3')
    const next = screen.getByLabelText('Next generation') as HTMLButtonElement
    expect(next.disabled).toBe(true)
    await fireEvent.click(screen.getByLabelText('Previous generation'))
    expect(shown()).toBe('Generation 2 of 3')
  })

  it('plays from the first generation, one every 700 ms, and stops at the last', async () => {
    vi.useFakeTimers()
    render(RunView, { run, params })
    await fireEvent.click(screen.getByText('Play'))
    expect(shown()).toBe('Generation 0 of 3')
    expect(screen.getByText('Pause')).toBeTruthy()
    await vi.advanceTimersByTimeAsync(700)
    expect(shown()).toBe('Generation 1 of 3')
    await vi.advanceTimersByTimeAsync(2100)
    await tick()
    expect(shown()).toBe('Generation 3 of 3')
    expect(screen.getByText('Play')).toBeTruthy()
  })

  it('shows how a generation was made, and its population on the other tab', async () => {
    const { container } = render(RunView, { run, params })
    expect(screen.getByText('How generation 3 was made').getAttribute('aria-selected')).toBe(
      'true',
    )
    expect(container.querySelector('.ranks')).not.toBeNull()
    await fireEvent.click(screen.getByText('Its population (8)'))
    expect(container.querySelectorAll('tbody tr')).toHaveLength(8)
  })

  it('says generation 0 has no parents', async () => {
    const { container } = render(RunView, { run, params })
    await fireEvent.input(screen.getByLabelText('Generation'), { target: { value: '0' } })
    expect(text(container)).toContain(
      'Each of its 8 chromosomes gets 10 genes drawn at random from the gene space.',
    )
  })

  it('shows only the population of a saved run, which has no breeding', () => {
    const { container } = render(RunView, { run: saved, params })
    expect(screen.queryByRole('tablist')).toBeNull()
    expect(screen.getByText('Population of generation 3 (6)')).toBeTruthy()
    expect(container.querySelectorAll('tbody tr')).toHaveLength(6)
  })

  it('starts a new run on its last generation', async () => {
    const { rerender } = render(RunView, { run, params })
    await fireEvent.click(screen.getByLabelText('Previous generation'))
    const shorter = { ...run, generations: run.generations.slice(0, 2) }
    await rerender({ run: shorter, params })
    expect(shown()).toBe('Generation 1 of 1')
  })
})
