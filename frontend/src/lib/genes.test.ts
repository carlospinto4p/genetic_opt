import { describe, expect, it } from 'vitest'
import { geneKey } from './genes'

describe('geneKey', () => {
  it('is the same for equal genes', () => {
    expect(geneKey([1, 0, 'a', null])).toBe(geneKey([1, 0, 'a', null]))
  })

  it('tells apart genes that read the same once joined', () => {
    expect(geneKey([1, 23])).not.toBe(geneKey([12, 3]))
    expect(geneKey([1, 0])).not.toBe(geneKey(['1', '0']))
  })
})
