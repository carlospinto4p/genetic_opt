import type { Gene } from './api'

/** The same text for two chromosomes only when their genes are equal. */
export function geneKey(genes: Gene[]): string {
  return JSON.stringify(genes)
}
