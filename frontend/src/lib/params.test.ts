import { describe, expect, it } from 'vitest'
import { savedParameters } from './params'

describe('savedParameters', () => {
  it('labels what a saved run holds, in the forms order', () => {
    const p = {
      random_seed: 7,
      n_generations: 30,
      population_size: 50,
      crossovers_prop: 0.5,
      besties_prop: 0.6,
      mutate_prob: 0.05,
      min_population_size: 2,
    }
    expect(savedParameters(p)).toEqual([
      ['Population size', 50],
      ['Generations asked', 30],
      ['Crossover share', 0.5],
      ['Best parents share', 0.6],
      ['Mutation probability', 0.05],
      ['Minimum different', 2],
      ['Algorithm seed', 7],
    ])
  })
})
