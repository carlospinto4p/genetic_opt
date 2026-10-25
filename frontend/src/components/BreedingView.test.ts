// @vitest-environment jsdom
import { fireEvent, render, screen } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import type { Breeding, Run } from '../lib/api'
import knapsackRun from '../fixtures/knapsack-run.json'
import BreedingView from './BreedingView.svelte'

const run = knapsackRun as Run<number[]>
// Generation 1, made from generation 0 by parents of ranks 4, 6, 0 and 1
const breeding = run.generations[1].breeding!
const previous = run.generations[0].population

function view(b: Breeding<number[]> = breeding) {
  return render(BreedingView, { breeding: b, previous, populationSize: 8 })
}

const text = (c: Element) => c.textContent!.replace(/\s+/g, ' ')

describe('BreedingView', () => {
  it('says how the parents were picked, and marks their ranks', () => {
    const { container } = view()
    expect(text(container)).toContain(
      '4 parents: the 2 best of the last generation, and 2 drawn at random',
    )
    const ranks = [...container.querySelectorAll('.rank')]
    const kind = (r: Element) =>
      r.classList.contains('best') ? 'best' : r.classList.contains('random') ? 'random' : ''
    expect(ranks.map(kind)).toEqual(['best', 'best', '', '', 'random', '', 'random', ''])
    expect(ranks[4].getAttribute('title')).toBe('rank 5: picked 1 time')
  })

  it('shows each pair: the parents, and each child crossed and mutated', () => {
    const { container } = view()
    const pair = container.querySelector('.pair')!
    // Parents 0 and 1 of the breeding are ranks 4 and 6, both random
    expect(text(pair)).toContain('score 177 · rank 5 random')
    expect(text(pair)).toContain('score 149 · rank 7 random')
    const strips = [...pair.querySelectorAll('.strip')].map((s) =>
      s.getAttribute('aria-label'),
    )
    // Child 1 had its third gene changed by the mutation
    expect(strips.slice(2, 4)).toEqual(['genes 0010010101', 'genes 0000010101'])
    expect(pair.querySelectorAll('.gene.changed')).toHaveLength(2)
    expect([...pair.querySelectorAll('.chip.stayed')]).toHaveLength(1)
  })

  it('counts the changed genes and the children that stayed', () => {
    const { container } = view()
    expect(text(container)).toContain('the mutation changed 4 genes over 4 children')
    expect(text(container)).toContain('3 children came in and 3 older chromosomes left')
  })

  it('shows the first 4 pairs, and the rest on a click', async () => {
    const pairs = [...breeding.pairs, ...breeding.pairs, breeding.pairs[0]]
    const { container } = view({ ...breeding, pairs })
    expect(container.querySelectorAll('.pair')).toHaveLength(4)
    await fireEvent.click(screen.getByText('Show all 5 pairs'))
    expect(container.querySelectorAll('.pair')).toHaveLength(5)
    expect(screen.getByText('Show the first 4 pairs')).toBeTruthy()
  })

  it('says the generation is the same when no parents are picked', () => {
    const { container } = view({ ...breeding, n_crossovers: 0, parents: [], pairs: [] })
    expect(text(container)).toContain('this generation is the same as the one before')
    expect(container.querySelector('.ranks')).toBeNull()
  })
})
