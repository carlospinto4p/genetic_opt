import { describe, expect, it } from 'vitest'
import type { KnapsackProblem } from './api'
import examples from '../fixtures/examples.json'
import { offGenes, tooLarge } from './knapsack'

describe('tooLarge', () => {
  const problem = () => structuredClone(examples.knapsack) as KnapsackProblem

  it('passes the README example', () => {
    expect(tooLarge(problem())).toBe('')
  })

  it('passes the largest number the page can send', () => {
    const p = problem()
    p.values[0] = Number.MAX_SAFE_INTEGER
    expect(tooLarge(p)).toBe('')
  })

  it('names the object whose weight is too large', () => {
    const p = problem()
    p.weights[2] = 1e21
    expect(tooLarge(p)).toBe(
      'The weight of object 3 is over 9,007,199,254,740,991, the largest number the page can send.',
    )
  })

  it('names the object whose value is too large', () => {
    const p = problem()
    p.values[9] = Number.MAX_SAFE_INTEGER + 2
    expect(tooLarge(p)).toMatch(/^The value of object 10 is over/)
  })

  it('names a capacity that is too large', () => {
    const p = problem()
    p.capacity = 1e300
    expect(tooLarge(p)).toMatch(/^The bag capacity is over/)
  })
})

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
