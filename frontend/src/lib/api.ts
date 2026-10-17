// What the server in `src/genetic_opt/web` sends back.

export type Origin = 'initial' | 'child' | 'survivor'
export type GeneOrigin = 'a' | 'b' | 'both'
// 0 or 1 in the runs the explainer makes. A gene of a saved run can be
// any value, sent as JSON text when it is not a number or a text.
export type Gene = number | string | null

export interface Chromosome<D = unknown> {
  genes: Gene[]
  decoded: D
  score: number
}

export interface Member<D = unknown> extends Chromosome<D> {
  // Not known for a saved run
  origin?: Origin
}

// A child after the mutation. `lib/breeding.ts` works out its genes
// before it.
export interface Child<D = unknown> extends Chromosome<D> {
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
  // The rank of each parent in the last generation
  parents: number[]
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

// `stopped`: a saved run that ended early, for a reason its files do not hold
export type StopReason = 'completed' | 'no_improvement' | 'min_population' | 'stopped'

export interface Run<D = unknown> {
  chromosome_length: number
  // `null` for a saved run: its files do not say
  minimize: boolean | null
  generations: Generation<D>[]
  stop_reason: StopReason
  fit_metrics: {
    total: number
    processed: number
    cached: number
    // `null` when too many to count
    space_points: number | null
    exploration_percentage: number
  }
  curve?: [number, number][]
}

// A run saved by the package or the Rust crate
export interface SavedRun extends Run<null> {
  folder: string
  fit_parameters: {
    n_generations: number
    population_size: number
    crossovers_prop: number
    besties_prop: number
    mutate_prob: number
    min_population_size: number
    random_seed: number
  }
  genetic_opt_version: string
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

export const openSavedRun = (path: string) =>
  request<SavedRun>('/api/runs/saved', { path })
