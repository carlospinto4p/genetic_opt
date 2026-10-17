// What the pages keep while the user moves between them

import {
  getExamples,
  type Examples,
  type FunctionProblem,
  type KnapsackProblem,
  type Run,
  type SavedRun,
} from './api'

interface Lab<P, D> {
  problem: P | null
  // The problem the run was made with: the form can change after it
  ran: P | null
  run: Run<D> | null
  running: boolean
  error: string
}

const lab = <P, D>(): Lab<P, D> => ({
  problem: null,
  ran: null,
  run: null,
  running: false,
  error: '',
})

export const store = $state({
  examples: null as Examples | null,
  examplesError: '',
  knapsack: lab<KnapsackProblem, number[]>(),
  fn: lab<FunctionProblem, number>(),
  // The run of the default Knapsack the guide shows
  guide: lab<KnapsackProblem, number[]>(),
  // The saved run opened, and the path typed
  saved: { path: '', run: null as SavedRun | null, loading: false, error: '' },
})

let loading: Promise<void> | null = null

/** Load the default problems once, and give each page a copy. */
export function loadExamples(): Promise<void> {
  loading ??= getExamples()
    .then((examples) => {
      store.examples = examples
      store.knapsack.problem ??= structuredClone(examples.knapsack)
      store.fn.problem ??= structuredClone(examples.function)
      store.guide.problem ??= structuredClone(examples.knapsack)
    })
    .catch((e: Error) => {
      store.examplesError = e.message
      loading = null
    })
  return loading
}

/** Run a lab's problem, keeping a copy of what it ran with. */
export async function runLab<P, D>(
  target: Lab<P, D>,
  call: (problem: P) => Promise<Run<D>>,
): Promise<void> {
  if (!target.problem) return
  const problem = $state.snapshot(target.problem) as P
  target.running = true
  target.error = ''
  try {
    target.run = await call(problem)
    target.ran = problem
  } catch (e) {
    target.error = (e as Error).message
  } finally {
    target.running = false
  }
}
