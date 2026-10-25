import type { FitParams, SavedRun } from './api'

export type NumberParam = Exclude<keyof FitParams, 'stop_without_improvement'>

/** The name of each number parameter, in the order the forms show them. */
export const paramLabels: Record<NumberParam, string> = {
  population_size: 'Population size',
  n_generations: 'Generations',
  crossovers_prop: 'Crossover share',
  besties_prop: 'Best parents share',
  mutate_prob: 'Mutation probability',
  min_population_size: 'Minimum different',
  random_seed: 'Algorithm seed',
  gene_space_random_seed: 'Gene seed',
}

/** The labelled parameters a saved run holds, in the forms' order. */
export function savedParameters(
  p: SavedRun['fit_parameters'],
): [string, number][] {
  const keys = Object.keys(paramLabels) as NumberParam[]
  return keys
    .filter((k): k is Extract<NumberParam, keyof typeof p> => k in p)
    .map((k) => [
      // A saved run can stop before the generations asked for
      k === 'n_generations' ? 'Generations asked' : paramLabels[k],
      p[k],
    ])
}
