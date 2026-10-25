// @vitest-environment jsdom
import { fireEvent, render } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'
import type { Run } from '../lib/api'
import functionRun from '../fixtures/function-run.json'
import FunctionPlot from './FunctionPlot.svelte'

// JSON types the curve's points as `number[]`
const run = functionRun as unknown as Run<number>
const curve = run.curve!
// Generation 2: six chromosomes, two of them the same
const population = run.generations[2].population

const plot = () => render(FunctionPlot, { curve, population })
const dots = (c: HTMLElement) => [...c.querySelectorAll('circle[role="presentation"]')]

describe('FunctionPlot', () => {
  it('draws the curve, and one dot per different chromosome', () => {
    const { container } = plot()
    expect(container.querySelector('path')!.getAttribute('d')!.match(/L/g)).toHaveLength(
      curve.length - 1,
    )
    expect(dots(container)).toHaveLength(5)
  })

  it('draws a chromosome with copies as a larger dot', () => {
    const radii = dots(plot().container).map((d) => d.getAttribute('r'))
    expect(radii.sort()).toEqual(['5', '5', '5', '5', '6'])
  })

  it('draws the best chromosome over its dot', () => {
    const { container } = plot()
    const best = container.querySelector('circle[r="8"]')!
    const first = dots(container)[0]
    expect([best.getAttribute('cx'), best.getAttribute('cy')]).toEqual([
      first.getAttribute('cx'),
      first.getAttribute('cy'),
    ])
  })

  it('shows x, f(x) and the bits of the chromosome under the mouse', async () => {
    const { container } = plot()
    await fireEvent.mouseEnter(dots(container)[0])
    const tooltip = container.querySelector('.tooltip')!
    expect(tooltip.textContent).toContain('x = 1.42353')
    expect(tooltip.textContent).toContain('f(x) = 1.95903')
    expect(tooltip.textContent).toContain('11001110')
    await fireEvent.mouseLeave(dots(container)[0])
    expect(container.querySelector('.tooltip')).toBeNull()
  })
})
