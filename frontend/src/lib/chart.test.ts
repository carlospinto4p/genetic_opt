import { describe, expect, it } from 'vitest'
import { linePath, linearScale, lonePoints, plotSize } from './chart'

describe('plotSize', () => {
  it('takes the padding off both sides', () => {
    const pad = { l: 60, r: 90, t: 14, b: 32 }
    expect(plotSize(600, 240, pad)).toEqual({ w: 450, h: 194 })
  })

  it('keeps the plot at least 10 pixels wide', () => {
    const pad = { l: 60, r: 90, t: 14, b: 32 }
    expect(plotSize(100, 240, pad).w).toBe(10)
  })
})

describe('linearScale', () => {
  it('puts the ends of the range at the ends of the axis', () => {
    const x = linearScale(-1, 2, 52, 300)
    expect([x(-1), x(0.5), x(2)]).toEqual([52, 202, 352])
  })

  it('draws upwards with a negative length', () => {
    // As the y axis of a chart: the lowest value at the bottom
    const y = linearScale(0, 10, 208, -194)
    expect([y(0), y(10)]).toEqual([208, 14])
  })

  it('puts every value at the start when the range is one value', () => {
    const y = linearScale(5, 5, 100, -50)
    expect(y(5)).toBe(100)
    expect(Number.isFinite(y(7))).toBe(true)
  })
})

describe('linePath', () => {
  it('moves to the first point and draws to the rest', () => {
    expect(
      linePath([
        [0, 1],
        [2, 3],
        [4, 5],
      ]),
    ).toBe('M0,1L2,3L4,5')
  })

  it('is empty without points', () => {
    expect(linePath([])).toBe('')
  })

  it('stops at a gap and starts again after it', () => {
    expect(linePath([[0, 1], [2, 3], null, null, [8, 9], [10, 11]])).toBe(
      'M0,1L2,3M8,9L10,11',
    )
  })

  it('starts after a gap at the beginning', () => {
    expect(linePath([null, [2, 3], [4, 5]])).toBe('M2,3L4,5')
  })
})

describe('lonePoints', () => {
  it('finds a value between two gaps', () => {
    expect(lonePoints([1, 2, null, 4, null, 6, 7])).toEqual([3])
  })

  it('finds a value at either end next to a gap', () => {
    expect(lonePoints([1, null, 3])).toEqual([0, 2])
  })

  it('finds the value of a series of one', () => {
    expect(lonePoints([5])).toEqual([0])
  })

  it('finds none in a line without gaps, or in a gap', () => {
    expect(lonePoints([1, 2, 3])).toEqual([])
    expect(lonePoints([null, null])).toEqual([])
  })
})
