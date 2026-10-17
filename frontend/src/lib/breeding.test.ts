import { describe, expect, it } from 'vitest'
import type { Breeding, Member } from './api'
import { crossedGenes, geneOrigins, parentAt } from './breeding'

describe('parentAt', () => {
  const previous: Member[] = [0, 1, 2, 3].map((n) => ({
    genes: [n],
    decoded: null,
    score: 10 - n,
  }))
  const breeding: Breeding = { n_crossovers: 4, n_besties: 2, parents: [1, 3, 0, 3], pairs: [] }

  it('takes a parent from the last generation at its rank', () => {
    expect(parentAt(breeding, previous, 1)).toMatchObject({ genes: [3], score: 7, rank: 3 })
  })

  it('marks the parents ranked among the besties as best', () => {
    const kinds = [0, 1, 2, 3].map((i) => parentAt(breeding, previous, i).kind)
    expect(kinds).toEqual(['best', 'random', 'best', 'random'])
  })
})

describe('crossedGenes', () => {
  it('flips back the genes the mutation changed', () => {
    const child = { genes: [1, 0, 0, 1], decoded: null, score: 0, changed: [0, 2], stayed: true }
    expect(crossedGenes(child)).toEqual([0, 0, 1, 1])
  })
})

describe('geneOrigins', () => {
  it('names the parent of each gene and both where they agree', () => {
    expect(geneOrigins([1, 1, 0, 1], [1, 1, 1, 0], [0, 1, 0, 1])).toEqual(['a', 'both', 'b', 'b'])
  })
})
