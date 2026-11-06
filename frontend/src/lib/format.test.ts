import { describe, expect, it } from 'vitest'
import { niceTicks } from './format'

describe('niceTicks', () => {
  it('covers an ordinary range with round steps', () => {
    expect(niceTicks(0, 10)).toEqual([0, 2, 4, 6, 8, 10])
  })

  it('ends on a range of float noise', () => {
    // Best and mean of every generation of a saved run, equal
    // but for the last digit. This range looped forever before v5.10.0.
    const min = 3.6298514769120786e-5
    const max = 3.629851476912079e-5
    const ticks = niceTicks(min, max)
    expect(ticks.length).toBeLessThan(20)
    expect(ticks[0]).toBeLessThanOrEqual(min)
    expect(ticks[ticks.length - 1]).toBeGreaterThanOrEqual(max)
  })

  it('ends on a range of one value', () => {
    const ticks = niceTicks(100, 100)
    expect(ticks.length).toBeLessThan(20)
    expect(ticks[0]).toBeLessThan(100)
    expect(ticks[ticks.length - 1]).toBeGreaterThan(100)
  })

  it('ends on the range of an empty series', () => {
    // `Math.min()` and `Math.max()` of no values, as `LineChart` passes
    expect(niceTicks(Math.min(), Math.max())).toEqual([0, 0.2, 0.4, 0.6, 0.8, 1])
  })

  it('ends on a range that is not a number', () => {
    expect(niceTicks(NaN, 1)).toEqual([0, 0.2, 0.4, 0.6, 0.8, 1])
  })

  it('ends on a range of zero', () => {
    const ticks = niceTicks(0, 0)
    expect(ticks.length).toBeLessThan(20)
    expect(ticks[0]).toBeLessThan(0)
    expect(ticks[ticks.length - 1]).toBeGreaterThan(0)
  })
})
