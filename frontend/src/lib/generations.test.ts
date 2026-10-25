import { describe, expect, it } from 'vitest'
import type { Generation } from './api'
import { generationAt } from './generations'

describe('generationAt', () => {
  const generations: Generation[] = [0, 1, 2].map((n) => ({
    population: [{ genes: [n], decoded: null, score: n }],
    metrics: { best: n, mean: n, median: n, var: 0, n_uniques: 1, percent_uniques: 100 },
    breeding: null,
  }))

  it('gives the generation at the index and the population before it', () => {
    const { generation, previous } = generationAt(generations, 1)
    expect(generation).toBe(generations[1])
    expect(previous).toBe(generations[0].population)
  })

  it('gives no population before the first generation', () => {
    expect(generationAt(generations, 0).previous).toEqual([])
  })

  it('gives the last generation for an index past it', () => {
    // As when a shorter run replaces the one the index was set on
    const { generation, previous } = generationAt(generations, 7)
    expect(generation).toBe(generations[2])
    expect(previous).toBe(generations[1].population)
  })
})
