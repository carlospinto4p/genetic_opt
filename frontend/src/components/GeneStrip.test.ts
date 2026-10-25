// @vitest-environment jsdom
import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import GeneStrip from './GeneStrip.svelte'

const squares = (c: HTMLElement) => [...c.querySelectorAll<HTMLElement>('.gene')]

describe('GeneStrip', () => {
  it('draws one square per gene, filled for 1', () => {
    const { container } = render(GeneStrip, { genes: [1, 0, 1] })
    expect(squares(container).map((s) => s.classList.contains('on'))).toEqual([
      true,
      false,
      true,
    ])
    expect(container.querySelector('[role="img"]')!.getAttribute('aria-label')).toBe(
      'genes 101',
    )
  })

  it('rings the changed genes and crosses out the ones turned off', () => {
    const { container } = render(GeneStrip, { genes: [1, 0, 1], changed: [1], off: [2] })
    const marks = squares(container).map((s) =>
      ['changed', 'off'].filter((c) => s.classList.contains(c)),
    )
    expect(marks).toEqual([[], ['changed'], ['off']])
  })

  it('draws the parent of each gene under it', () => {
    const { container } = render(GeneStrip, { genes: [1, 0], origins: ['a', 'both'] })
    const bars = [...container.querySelectorAll('.origin')].map((o) => o.className)
    expect(bars[0]).toContain('origin-a')
    expect(bars[1]).toContain('origin-both')
  })

  it('builds the tooltip of a square when the pointer reaches it', async () => {
    const { container } = render(GeneStrip, {
      genes: [1, 0, 1],
      origins: ['a', 'b', 'a'],
      changed: [1],
      off: [2],
    })
    const [, b, c] = squares(container)
    expect(b.title).toBe('')
    await fireEvent.pointerOver(b)
    await fireEvent.pointerOver(c)
    expect(b.title).toBe('gene 2: 0, from parent B, changed by the mutation')
    expect(c.title).toBe('gene 3: 1, from parent A, turned off when decoded')
  })
})
