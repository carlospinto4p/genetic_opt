import { describe, expect, it } from 'vitest'
import { offGenes } from './knapsack'

describe('offGenes', () => {
  it('finds the objects asked for and left out of the bag', () => {
    const c = { genes: [1, 0, 1, 1, 0], decoded: [1, 0, 0, 1, 0], score: 3 }
    expect(offGenes(c)).toEqual([2])
  })

  it('finds none when the bag holds every object asked for', () => {
    const c = { genes: [0, 1, 1], decoded: [0, 1, 1], score: 2 }
    expect(offGenes(c)).toEqual([])
  })
})
