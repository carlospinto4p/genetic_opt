// What the server in `src/genetic_opt/web` sends back.

export type Origin = 'initial' | 'child' | 'survivor'
export type GeneOrigin = 'a' | 'b' | 'both'

export interface Chromosome<D = unknown> {
  genes: number[]
  decoded: D
  score: number
}

export interface Member<D = unknown> extends Chromosome<D> {
  origin: Origin
}

export interface Parent<D = unknown> extends Chromosome<D> {
  rank: number
  kind: 'best' | 'random'
}

export interface Child<D = unknown> extends Chromosome<D> {
  crossed: number[]
  origins: GeneOrigin[]
  changed: number[]
  stayed: boolean
}

export interface Pair<D = unknown> {
  a: number
  b: number
  children: Child<D>[]
}

export interface Breeding<D = unknown> {
  n_crossovers: number
  n_besties: number
  parents: Parent<D>[]
  pairs: Pair<D>[]
}

export interface Metrics {
  best: number
  mean: number
  median: number
  var: number
  n_uniques: number
  percent_uniques: number
}

export interface Generation<D = unknown> {
  population: Member<D>[]
  metrics: Metrics
  breeding: Breeding<D> | null
}

export type StopReason = 'completed' | 'no_improvement' | 'min_population'

export interface Run<D = unknown> {
  chromosome_length: number
  minimize: boolean
  generations: Generation<D>[]
  stop_reason: StopReason
  fit_metrics: {
    total: number
    processed: number
    cached: number
    space_points: number
    exploration_percentage: number
  }
  curve?: [number, number][]
}

export interface FitParams {
  n_generations: number
  population_size: number
  crossovers_prop: number
  besties_prop: number
  mutate_prob: number
  min_population_size: number
  stop_without_improvement: boolean
  random_seed: number
  gene_space_random_seed: number
}

export interface KnapsackProblem {
  weights: number[]
  values: number[]
  capacity: number
  fit: FitParams
}

export interface FunctionProblem {
  low: number
  high: number
  n_bits: number
  fit: FitParams
}

export interface Examples {
  knapsack: KnapsackProblem
  function: FunctionProblem
  limits: { n_generations: number; population_size: number; genes: number }
}

async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const data = await response.json()
      detail =
        typeof data.detail === 'string'
          ? data.detail
          : data.detail.map((d: { msg: string }) => d.msg).join('; ')
    } catch {
      // The status line is all there is
    }
    throw new Error(detail)
  }
  return response.json()
}

export const getInfo = () =>
  request<{ name: string; version: string }>('/api/info')

export const getExamples = () => request<Examples>('/api/examples')

export const runKnapsack = (problem: KnapsackProblem) =>
  request<Run<number[]>>('/api/runs/knapsack', problem)

export const runFunction = (problem: FunctionProblem) =>
  request<Run<number>>('/api/runs/function', problem)
