
## Changelog - Genetic-Opt


### v9.0.17 - 7th November 2026

- `README.md`: three screenshots of the explainer in its "Explainer"
  section, in `docs/screenshots/`: the "How it works" page, a "Find a
  maximum" run, and one Knapsack generation being bred. Taken from real
  runs with the default parameters.


### v9.0.16 - 7th November 2026

- Rotated changelog: archived 4 entries to `changelog/2026.md`.


### v9.0.15 - 6th November 2026

- Removed the name of the downstream project from every tracked file:
  `changelog.md`, `changelog/2026.md`, `roadmap.md`,
  `frontend/src/lib/format.test.ts` and
  `tests/unit/web/test_saved_runs.py` (comments only), so the repository
  can be public.


### v9.0.14 - 6th November 2026

- Made the agent instructions generic for the public repository:
  - `CLAUDE.md`, `AGENTS.md`: removed the section on changes that break
    the downstream project. It moved to `CLAUDE.local.md`, which
    `.gitignore` already excludes.
  - `docs/releasing.md`: no longer names the downstream project or the version it needed.


### v9.0.13 - 6th November 2026

- Prepared the repository to be public on GitHub:
  - Added `LICENSE` (MIT) and the `license` and `license-files` fields in
    `pyproject.toml`.
  - `pyproject.toml`: the author email is now the GitHub account's.
  - `AGENTS.md`, `CLAUDE.md`, `docs/releasing.md`: removed the paths to the
    owner's home folder and the references to personal global rules.


### v9.0.12 - 28th October 2026

- Rotated changelog: archived 25 entries to `changelog/2026.md`.


### v9.0.11 - 25th October 2026

- Added component tests for the explainer, 57 of them, run in jsdom by
  `pnpm --dir frontend test` with the other front-end tests:
  - `frontend/src/components/`: `LineChart`, `GeneStrip`,
    `PopulationTable`, `BreedingView`, `RunView`, `FunctionPlot` and
    `Sidebar`.
  - `frontend/src/pages/`: `Knapsack`, `FunctionLab` and `SavedRun`,
    with `FitForm` through them.
  - `frontend/src/App.test.ts`: the name and version from `/api/info`,
    and the page shown for the address.
- `Guide.svelte` and `ServerError.svelte` have none: they show fixed
  text.
- Added the set-up:
  - `frontend/package.json`: `jsdom` and `@testing-library/svelte` as
    dev dependencies. Neither has an install script.
  - `frontend/vite.config.ts`: the `svelteTesting` plugin, and
    `test-setup.ts` as a setup file. A component test sets
    `// @vitest-environment jsdom`; the rest still run without a DOM.
  - `frontend/src/test-setup.ts`: `ResizeObserver` and `scrollTo`,
    which jsdom lacks, and a width of 600 for every element.
  - `frontend/src/test-pages.ts`: `serve`, the server's replies in
    place of `fetch`, and `renderPage`, a page with an empty store.
  - `frontend/src/fixtures/`: four replies recorded from the server, on
    small runs of the default problems.


### v9.0.10 - 25th October 2026

- Fixed: the explainer's score chart drew a mean or median too large
  for a float, sent as `null` since v9.0.8, at 0, and stretched its
  axis down to it. It now leaves a gap in the line:
  - `frontend/src/lib/chart.ts`: `linePath` takes `null` points and
    starts the line again after them. Added `lonePoints`, the values
    with a gap on both sides, which the chart draws as dots.
  - `frontend/src/components/LineChart.svelte`: the axis ignores the
    gaps, a line ending in a gap is labelled at its last value, and the
    tooltip reads "too large" for one.
  - `frontend/src/lib/api.ts`: `Metrics` types `mean`, `median` and
    `var` as `number | null`.
- Added 6 tests to `frontend/src/lib/chart.test.ts`.


### v9.0.9 - 25th October 2026

- Added `frontend/src/lib/generations.ts`: `generationAt`, the
  generation at an index, or the last one when the index is past it,
  and the population before it. `RunView.svelte` used to work these out
  inline.
- Added `frontend/src/lib/generations.test.ts`: 3 tests, including an
  index past the last generation, as when a shorter run replaces the
  one the index was set on.


### v9.0.8 - 25th October 2026

- Fixed two `OverflowError`s on scores too large for a float, each a
  500 error in the explainer's Knapsack page:
  - `algorithms/base.py`: an `int` score too large for a float stops
    the run with "a score that is not finite", as an infinite one does
    since v9.0.7. Added `_is_finite`, used by `_sort_population` and
    `_first_chromosomes`.
  - `metrics.py`: `get_population_metrics` turns the scores into
    floats first, so finite `int` scores whose sum is too large give an
    infinite mean instead of raising.
- Decided what a mean, median or variance too large for a float does:
  it is infinite, the run goes on, and the explainer gets `null`. Said
  in the `Metric` docstring and `README.md`.
- Added tests:
  - `tests/unit/test_metrics.py`: an infinite variance of finite
    scores, and an infinite mean of `int` scores.
  - `tests/unit/algorithms/test_base.py`: an `int` score too large for
    a float, from the fitness function and in a first population.
  - `tests/integration/web/test_app.py`: the Knapsack run refuses
    values too large for a float, and sends an infinite variance as
    `null`.


### v9.0.7 - 25th October 2026

- Fixed: a score that is infinite stops the run with a validation
  error, as a NaN score has since v5.0.4, in both implementations and
  for both a scored Chromosome and a given first population. The error
  now names the value: "gave a score that is not finite, inf, to the
  Chromosome ...". Before, an infinite score made the variance of the
  generation NaN, kept the stop when the mean does not change from
  firing, and reached the explainer as a `null` score.
  - `algorithms/base.py`: `_sort_population` and `_first_chromosomes`
    check `isfinite`.
  - `crates/genetic_opt/src/algorithm.rs`: `not_finite_score_error`
    replaces `nan_score_error`.
  - `README.md` and the `Problem::fitness` doc say so.
- Updated the tests to NaN, infinity and minus infinity:
  - `tests/unit/algorithms/test_base.py`:
    `test_fit_refuses_a_score_that_is_not_finite`, and a first
    population with a `-inf` score.
  - `crates/genetic_opt/tests/algorithm.rs`:
    `a_score_that_is_not_finite_stops_the_run`, and a first population
    with an infinite score.


### v9.0.6 - 25th October 2026

- Fixed `loadExamples` in `frontend/src/lib/store.svelte.ts` keeping
  the error of a failed load after a later load succeeds, so the
  Knapsack, Function and Guide pages kept showing the server error
  with the examples loaded.
- Added two tests of `loadExamples` to `frontend/src/lib/store.test.ts`:
  it asks again after a failed load, and asks nothing more once loaded.


### v9.0.5 - 25th October 2026

- Added `frontend/src/lib/api.test.ts`: 5 tests of the error `request()`
  throws, from a text `detail`, from the list of errors of a refused
  request, from a body that is not JSON and from JSON without a
  `detail`, and of the JSON of a response that is ok.


### v9.0.4 - 25th October 2026

- Added tests of what a run gives and what the explainer opens:
  - `tests/unit/algorithms/test_base.py`: the bests of a run are
    unique, at most `N_BESTS` and best first, maximizing and
    minimizing.
  - `crates/genetic_opt/tests/algorithm.rs`: the same cap and order in
    `the_population_keeps_its_size_and_is_sorted_best_first`.
  - `tests/integration/test_rust_layout.py`: `saved_run` opens a run
    saved by the crate, a list and a set, as BSON and as JSON.
  - `tests/unit/web/test_saved_runs.py`: `saved_run` sends the
    dictionary genes of a set as sorted JSON text.


### v9.0.3 - 25th October 2026

- Fixed `niceTicks` in `frontend/src/lib/format.ts` never ending on a
  range that is not finite, such as the ±Infinity that `LineChart`
  passes for an empty series. Such a range gets the ticks of 0 to 1.
- Added two tests to `frontend/src/lib/format.test.ts`.


### v9.0.2 - 25th October 2026

- Fixed a set Chromosome whose genes are of types that do not compare,
  such as `{1, "a"}` from a `ValuesGeneSpace`: its `repr`, and so its
  `id`, and its mutation raised `TypeError`.
  - Added `sorted_genes` to `gene_collection.py`: the plain sort, or
    the sort by type name first when the plain one raises. Genes that
    compare keep their order, so saved ids do not change.
  - `Chromosome.__repr__`, `GeneSet.random_mutate` and
    `web/saved_runs.py` use it.
- Added three tests to `tests/unit/test_chromosome.py`.


### v9.0.1 - 25th October 2026

- `algorithms/base.py`: `no_improvement_condition` compares the means of
  the last two generations directly, as the crate's `mean_stalled` does,
  in place of building every difference to read one.
- Added a test that the condition is not met before two generations.


### v9.0.0 - 25th October 2026

- `gene_collection.py`: removed `select_random` from `GeneCollection`,
  `GeneList` and `GeneSet`. Nothing called it; a run draws its genes
  from the gene space's own `select_random`.


### v8.1.9 - 25th October 2026

- `App.svelte`: a failed `/api/info` request is now logged with
  `console.warn`, in place of an empty `.catch`, so the browser console
  says why the sidebar shows no version.


### v8.1.8 - 25th October 2026

- `BreedingView.svelte`: renamed `n_random` to `nRandom`, to match the
  camelCase names around it.
- `RunView.svelte`: `stopText` is now a `switch` with one case for each
  `StopReason` and a `string` return type, so `svelte-check` fails when
  a new stop reason has no text. Before, an unknown reason fell through
  to the "mean score was the same" text.


### v8.1.7 - 25th October 2026

- `web/app.py`: typed the `func` argument of `_run` as
  `Callable[..., dict[str, Any]]`, in place of `Any`.
- `frontend/src/lib/api.ts`: added `n_jobs`, `selection` and
  `tournament_size` to `SavedRun.fit_parameters`, which both
  implementations save. `savedParameters` in `params.ts` now keeps only
  the number parameters the forms show, and its test sample holds the
  new fields.
- Moved the sidebar's page icons into `pages` in `router.svelte.ts`, as
  an `icon` field of each page, in place of a map keyed by path string
  in `Sidebar.svelte`.


### v8.1.6 - 25th October 2026

- Added shared helpers to `frontend/src/lib`, each with tests:
  - `params.ts`: `paramLabels`, the name of each number parameter, used
    by `FitForm.svelte`, and `savedParameters`, the list the Open a
    saved run page shows. The page no longer has its own copy of the
    labels.
  - `knapsack.ts`: `offGenes`, the genes the decoding leaves out of the
    bag, used by the Knapsack and How it works pages in place of a copy
    each.
  - `genes.ts`: `geneKey`, used by `PopulationTable.svelte` and
    `FunctionPlot.svelte` to find copies of a chromosome.
- Fixed `FunctionPlot.svelte` taking two chromosomes as copies when
  their genes read the same once joined, such as `[1, 23]` and
  `[12, 3]`.


### v8.1.5 - 25th October 2026

- `frontend/src/lib/store.svelte.ts`:
  - Added `Request`, the `running` and `error` of a page's request,
    which `Lab` and `Saved` extend in place of a copy each. `Saved`'s
    `loading` is now `running`.
  - Added `track`, which sets them around a request, for `runLab` and
    the new `openSaved`.
  - Added `openSaved`, which opens the saved run at the path typed. The
    Open a saved run page calls it, in place of its own copy.
- Added `frontend/src/lib/store.test.ts`: 5 tests of `runLab` and
  `openSaved`, with `fetch` answered without a server.


### v8.1.4 - 25th October 2026

- Added `nan_score_error` to the crate's `algorithm.rs`: the error of a
  NaN score, which the first population and `score` both return, in
  place of a copy each. The messages are unchanged.


### v8.1.3 - 25th October 2026

- Added `tests/unit/test_rust_defaults.py`: two tests that the Rust
  crate's `FitConfig::new` and `AlgorithmConfig::default` in
  `algorithm.rs` have the defaults of `FitConfig` and `seeds.py`'s
  `RANDOM_SEED`. They read the Rust source, and skip without the crate.


### v8.1.2 - 25th October 2026

- Added `docs/releasing.md`: how to upload a release by hand, since
  GitLab CI is off, and how to check what the registry serves.
- `pyproject.toml`: added the `gitlab_genetic_opt` index entry, whose
  `publish-url` makes `uv publish --index gitlab_genetic_opt` work.
- `.gitlab-ci.yml`: a note that the publish job cannot run while CI is
  off, pointing to `docs/releasing.md`.


### v8.1.1 - 25th October 2026

- Added `GeneticAlgorithm._new_chromosome(genes)` in
  `algorithms/base.py`: a Chromosome of the Algorithm's length, kind
  and seed. `_first_chromosomes` and `BinaryGeneticAlgorithm`'s
  `crossover_func` use it, in place of a copy each.
- Added `seeds.py`: `RANDOM_SEED` (442) and `GENE_SPACE_RANDOM_SEED`
  (2), the default seeds. The defaults of these read them, in place of
  the numbers:
  - `GeneticAlgorithm`, `BinaryGeneticAlgorithm`.
  - `Chromosome`, `AbstractGeneSpace`, `ValuesGeneSpace`.
  - `examples/binary.py`'s `BinaryFunction`.
  - `web/app.py`'s `FitParams`.
- `tests/unit/web/test_runs.py`:
  - Added two tests that the knapsack of the README example and of the
    Rust `examples/knapsack.rs` are `web/runs.py`'s `KNAPSACK_WEIGHTS`,
    `KNAPSACK_VALUES` and `KNAPSACK_CAPACITY`.
  - The knapsack runs use those constants, in place of a copy.


### v8.1.0 - 25th October 2026

- Added `serialize_fitness_func_calls` to `runs/fit_result_io.py`: the
  `fitness_func_calls` of a run with an infinite `space_points` as
  `None`. `serialize_fit_result` and `web/saved_runs.py`'s `saved_run`
  both use it, in place of a copy each.
- Added tests:
  - `tests/unit/runs/test_fit_result_io.py`: 3 cases of
    `serialize_fitness_func_calls`.
  - `tests/unit/web/test_saved_runs.py`: `saved_run` sends an infinite
    `space_points` as `None`.


### v8.0.5 - 25th October 2026

- `pyproject.toml`: ruff checks line length (`E501`) on top of its
  default rules. `line-length = 78` was set but the rule was off.
- Shortened the 5 lines over 78 characters:
  - `algorithms/base.py`: two docstring lines.
  - `functions.py`: the log line of `time_it_with_logger`.
  - `runs/fit_result.py`: the docstring of `Bests`.
  - `tests/unit/algorithms/test_base.py`: the docstring of
    `_counting_bag`.


### v8.0.4 - 25th October 2026

- `GeneticAlgorithm.fit` refuses a Chromosome set of more genes than
  the gene space has before the run starts, with the message of the
  Rust crate. It was refused only when the first Chromosome was built.
- Added `test_fit_refuses_a_set_larger_than_the_gene_space` in
  `tests/unit/algorithms/test_base.py`.


### v8.0.3 - 25th October 2026

- Rotated changelog: archived 2 entries to `changelog/2026.md`.
