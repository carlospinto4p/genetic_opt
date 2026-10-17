// What the pages keep while the user moves between them

import {
  getExamples,
  type Examples,
  type FunctionProblem,
  type KnapsackProblem,
  type Run,
  type SavedRun,
} from './api'

// Classes, so the store below does not proxy their fields. A run holds
// every generation's genes and is only ever replaced whole, so it is
// kept raw
class Lab<P, D> {
  problem = $state<P | null>(null)
  // The problem the run was made with: the form can change after it
  ran = $state.raw<P | null>(null)
  run = $state.raw<Run<D> | null>(null)
  running = $state(false)
  error = $state('')
}

// The saved run opened, and the path typed
class Saved {
  path = $state('')
  run = $state.raw<SavedRun | null>(null)
  loading = $state(false)
  error = $state('')
}

export const store = $state({
  examples: null as Examples | null,
  examplesError: '',
  knapsack: new Lab<KnapsackProblem, number[]>(),
  fn: new Lab<FunctionProblem, number>(),
  // The run of the default Knapsack the guide shows
  guide: new Lab<KnapsackProblem, number[]>(),
  saved: new Saved(),
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

/** Put a lab's problem back to a copy of its default. */
export function resetLab<P, D>(target: Lab<P, D>, example: P): void {
  target.problem = structuredClone($state.snapshot(example)) as P
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
