
## Changelog - Genetic-Opt


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


### v8.0.2 - 22nd October 2026

- `.claude/rules/committing.md`: synced the trimmed canonical
  from programme (7.9k to 5.5k characters, same headings and
  instructions) to cut the instruction text loaded per session.


### v8.0.1 - 19th October 2026

- Rotated changelog: archived 74 entries to `changelog/2026.md`.


### v8.0.0 - 18th October 2026

- Moved the code that saves a run, reads it back and plots it to the new
  `genetic_opt.runs` package. The old import paths are gone:
  - `genetic_opt.files` is `genetic_opt.runs.files`.
  - `genetic_opt.fit_result` is `genetic_opt.runs.fit_result`.
  - `genetic_opt.fit_result_io` is `genetic_opt.runs.fit_result_io`.
  - `genetic_opt.algorithms.save` is `genetic_opt.runs.save`.
  - `genetic_opt.algorithms.plots` is `genetic_opt.runs.plots`.
- `runs/save.py` imports `SaveConfig` only for type checking, as
  `algorithms.base` imports it back.
- Moved the tests of those modules to `tests/unit/runs/`.
- Added a test to `tests/unit/test_imports.py` that imports each module
  of `genetic_opt.runs` in a new interpreter, before
  `genetic_opt.algorithms`.
- Updated the paths in `README.md`, `CLAUDE.md` and the crate's doc
  comments.
- `downstream` imports `genetic_opt.files` and `genetic_opt.fit_result_io`;
  its backlog has the two lines to change.


### v7.1.0 - 18th October 2026

- `genetic_opt.algorithms` exports `BinaryGeneticAlgorithm`, as it does
  `GeneticAlgorithm`. The README example that builds one now shows the
  import.
- Added a test of the export to `tests/unit/algorithms/test_binary.py`.


### v7.0.2 - 18th October 2026

- Added `frontend/src/components/ServerError.svelte`: the "server did
  not answer" message the Knapsack, Find a maximum and How it works
  pages each had a copy of.
- Added `resetLab` to `frontend/src/lib/store.svelte.ts`, which replaces
  the `reset()` of `Knapsack.svelte` and `FunctionLab.svelte`.
- Moved the `.explain` card style and the form's button row, now
  `.actions`, from both pages to `frontend/src/app.css`. The button row
  of Find a maximum now wraps on a narrow screen, as the Knapsack one
  did.


### v7.0.1 - 18th October 2026

- Added `frontend/src/lib/chart.ts`, the drawing code the two charts of
  the explainer each had a copy of:
  - `plotSize`: the plot's size inside its padding.
  - `linearScale`: the pixel of a value on an axis.
  - `linePath`: the `d` of an SVG path through points.
- `LineChart.svelte` and `FunctionPlot.svelte` use it.
- Added `frontend/src/lib/chart.test.ts`: 7 tests.


### v7.0.0 - 18th October 2026

- Moved `BinaryFunction`, `wavy_function` and the `FUNCTION_LOW`,
  `FUNCTION_HIGH`, `FUNCTION_BITS` defaults from `web/runs.py` to
  `examples/binary.py`, next to `Knapsack`.
- Moved `saved_run` and `MAX_SAVED_RUN_BYTES` from `web/runs.py` to the
  new `web/saved_runs.py`. `web/runs.py` keeps the recorder of the
  explainer's runs and `function_curve`.
- Renamed `_metrics` in `web/runs.py` to `generation_metrics`, which
  both modules use.
- Moved the tests to match:
  - `tests/unit/examples/test_binary.py`: the `BinaryFunction` tests.
  - `tests/unit/web/test_saved_runs.py`: the `saved_run` tests.
- `downstream` imports neither `genetic_opt.web` nor
  `genetic_opt.examples`.


### v6.0.0 - 18th October 2026

- `GeneticAlgorithm.next_generation_selection` takes the run's
  `FitConfig` instead of `crossovers_prop`, `besties_prop`,
  `mutate_prob`, `selection` and `tournament_size`. `iter_func` and
  `n_jobs` stay. A subclass that overrides it now receives `config`.
- Updated `fit`, the web recorder in `web/runs.py` and
  `_tournament_parents` in `tests/unit/algorithms/test_base.py` to
  match. `downstream` neither calls nor overrides the method.


### v5.12.0 - 18th October 2026

- Added `parent_counts` to `algorithms/base.py`: how many parents a
  generation crosses and how many of them are the best. Used by
  `next_generation_selection` and by the web recorder in `web/runs.py`,
  which each worked the counts out by themselves.
- `frontend/src/pages/Guide.svelte` reads the counts from the run's
  breeding record instead of working them out again.
- Added 5 cases of `test_parent_counts_cross_an_even_number_of_parents`
  to `tests/unit/algorithms/test_base.py`.


### v5.11.2 - 18th October 2026

- Fixed `test_fast_scores_are_not_sent_to_the_workers` in
  `tests/unit/algorithms/test_base.py` failing on a busy machine: the
  test now gives `base.py` a clock where scoring takes no time, so one
  slow first score no longer sends the other 49 to the workers.


### v5.11.1 - 18th October 2026

- `gene_collection.py`:
  - Fixed `GeneSet.__init__` adding the genes it draws to the set it was
    given: it now copies the genes into a new set.
  - Fixed `GeneSet.__init__` failing on a tuple or a frozenset that
    needs more genes.
  - Fixed `GeneList.__init__` failing on a tuple that needs more genes,
    and keeping a full one as a tuple, which never equals the same genes
    as a list.
- Added 5 tests to `tests/unit/test_gene_collection.py`.


### v5.11.0 - 18th October 2026

- `fit` says why a run ended, in both implementations:
  - Added `StopReason` to `fit_result.py`: `completed`,
    `min_population`, `no_improvement`, `stale_generations`,
    `max_seconds` or `exit_condition`.
  - `FitResult` has `stop_reason`, only in what `fit` returns: the saved
    files do not hold it.
  - Added `StopReason` and `FitResult::stop_reason` to the crate, with
    `OnGeneration` for a stop asked by `on_generation`.
- `algorithms/base.py`: the five stop checks moved out of `fit` into
  `_stop_reason`. Its log lines now read as the crate's, such as "the
  run stopped after generation 0: 0 seconds reached".
- `crates/genetic_opt/src/algorithm.rs`: the stop checks moved out of
  `fit_from` into `stop_reason`.
- `web/runs.py`: `record_run` takes `stop_reason` from the result of
  `fit`, instead of checking two of the five conditions again.
- Added tests: `stop_reason` in the stop tests of `test_base.py`, and
  `the_result_says_why_the_run_stopped` in the crate.


### v5.10.13 - 17th October 2026

- `PopulationTable.svelte`: the genes of each member are turned into
  text once instead of twice to count the copies.
- `test_one_seed_gives_the_same_set_run_with_any_hash_seed` starts its
  two interpreters at the same time: 0.37 s instead of 0.75 s.
- `.pre-commit-config.yaml`: on a push, `cargo-test` runs only when
  files under `crates/` changed and `frontend-test` only when files
  under `frontend/` changed.


### v5.10.12 - 17th October 2026

- `gene_space.py`: `BinaryGeneSpace.select_random` draws with
  `randint(0, 2)` instead of `choice([0, 1])`: the same draws, in
  5.7 µs instead of 11.3 µs. One gene now comes back as an `int`
  instead of a numpy integer.
- `Chromosome.random_mutate`, `GeneList.random_mutate` and
  `GeneSet.random_mutate` copy themselves by their attributes instead
  of with `copy.copy`, in 0.8 µs instead of 2.9 µs.
- `algorithms/base.py`: `stale_generations` is counted as each
  generation's metrics are added, instead of going through every
  generation each time. At 5,000 generations the old count added up to
  0.8 s of a run.
- `web/runs.py`: `_breeding_record` compares the genes of a child one
  by one only when a mutation changed them.
- A seeded run of the Knapsack example at the explainer's limits, with
  and without `max_stale_generations`, gives the same output as before
  to the byte.
- `test_a_better_best_score_ends_the_stale_generations` adds each
  generation through `_update_metrics` instead of appending to
  `metrics`.


### v5.10.11 - 17th October 2026

- `algorithms/plots.py`: `save_current_figure` saves through the
  figure instead of `plt.savefig`, which drew the figure once more
  after saving. The same image, in 0.28 s instead of 0.41 s.
- Plot tests: the 5 that save a plot took 3.4 s and the 3 left take
  1.7 s.
  - Removed `test_fit_saves_the_plot_as_a_jpeg` from
    `tests/unit/algorithms/test_save.py`: it checked the plot is a JPEG
    with the same two parameters that
    `test_a_saved_run_gets_the_plot_that_fit_saves` runs.
  - `test_a_saved_run_gets_the_plot_that_fit_saves` checks the JPEG
    bytes instead.
- Added `pytest-xdist` to the dev group. The pre-push hook and the
  command in `CLAUDE.md` run the unit tests with `-n 4`, in 4.3 s
  instead of 6.8 s; `-n auto` took 6.5 s.
- `.claude/rules/testing-areas.md`: the recorded times are measured
  again, with the front-end tests and `cargo test` with nothing to
  compile.


### v5.10.10 - 17th October 2026

- `algorithms/base.py`: new Chromosomes are scored in the process that
  runs `fit` when the batch is expected to take less than
  `IN_PROCESS_SECONDS` (0.01 s, what a warm pool of workers took for a
  batch of any size), and in the worker processes when not. The first
  Chromosome scored times the fitness function. The README knapsack
  takes 0.01 s at the default `n_jobs` instead of 1.08 s; a fitness
  function of 20 ms takes as long as before.
  - Added `_score_new` and `_score_in_process`.
  - `config.py`: the `n_jobs` docstring says which batches go to the
    workers.
- `tests/unit/algorithms/test_base.py`:
  - Added `test_fast_scores_are_not_sent_to_the_workers` and
    `test_slow_scores_are_sent_to_the_workers_after_the_first`.
  - The tests of the workers set `IN_PROCESS_SECONDS` to 0 through the
    `score_in_workers` fixture.


### v5.10.9 - 17th October 2026

- Faster saving and a lighter explainer page:
  - `algorithms/base.py`: a run that saves no longer decodes the whole
    population every generation, which the files leave out. It is
    decoded once, when the run ends. `_get_fit_result` takes
    `decode_population`.
  - `frontend/src/lib/store.svelte.ts`: the runs are kept in raw state,
    so their generations and genes are no longer proxied. `Lab` and the
    saved run are classes.
  - `GeneStrip.svelte` builds a square's tooltip when the pointer
    reaches it, not on every redraw, and checks the changed and
    turned-off genes in sets. `PopulationTable.svelte` works out the
    turned-off genes once per row.
- Added `test_saving_decodes_the_population_only_when_the_run_ends` to
  `tests/unit/algorithms/test_save.py`.


### v5.10.8 - 17th October 2026

- Explainer runs send less: a run at the limits (200 generations,
  population 200, 40 genes) sent 15.6 MB instead of 34.3 MB.
  - `web/runs.py`: each child no longer sends `crossed` and `origins`,
    and each parent is sent as its rank in the last generation instead
    of its genes, score and `kind`. Removed `_gene_origins`.
  - Added `frontend/src/lib/breeding.ts`: `parentAt`, `crossedGenes`
    and `geneOrigins` work them out on the page, used by
    `BreedingView.svelte` and `Guide.svelte`, with tests in
    `breeding.test.ts`.
  - `tests/unit/web/test_runs.py`: the breeding tests read the parents
    from the last generation by rank.


### v5.10.7 - 17th October 2026

- `web/app.py`: lowered `MAX_GENERATIONS` from 300 to 200 and
  `MAX_POPULATION` from 400 to 200. The largest run the explainer
  allows took 2-3 s and sent 34-43 MB, against 6-8 s and 103-129 MB.
- Added tests to `tests/integration/web/test_app.py`: a run over
  `MAX_GENERATIONS` is refused, and `/api/examples` gives the limits.


### v5.10.6 - 17th October 2026

- `web/runs.py`: replaced `_chromosome` with `_Recorder.shown`, which
  works out the genes, decoded value and score of a Chromosome once per
  run. A run at the explainer's limits (40 genes, population 400, 300
  generations) took 7-8 s instead of 9-11 s, with the same response.
- Added `test_record_run_decodes_each_chromosome_once` to
  `tests/unit/web/test_runs.py`.


### v5.10.5 - 17th October 2026

- `.gitlab-ci.yml`: the publish job's `python:3.14-slim` image is
  pinned to its digest, read from Docker Hub on 17th October 2026, since
  the job holds `CI_JOB_TOKEN`.


### v5.10.4 - 17th October 2026

- `web/app.py`:
  - `FunctionRequest.low` and `high` refuse NaN, infinity and a
    magnitude over `MAX_INTERVAL_END` (1e9), which gave a 500.
  - `FitParams.min_population_size` is at most `MAX_POPULATION`, and
    knapsack `weights` and `values` refuse negative numbers.
  - Added `refuse_request`: a 422 for a request FastAPI refuses no
    longer repeats its input, so one holding a NaN is a 422, not a 500.
- `web/runs.py`: `saved_run` refuses with `ValidationException` a run
  whose files miss a parameter, or hold an empty population, instead of
  raising `KeyError` or `IndexError` (a 500 from `/api/runs/saved`).
- Declared `pydantic` in the `web` extra of `pyproject.toml`:
  `web/app.py` imports it.
- Added tests: 4 in `tests/unit/web/test_runs.py`, 8 in
  `tests/integration/web/test_app.py`.


### v5.10.3 - 17th October 2026

- `web/app.py`:
  - Added `TrustedHostMiddleware`: the API answers only requests naming
    `127.0.0.1` or `localhost`, so a page that points its own name at
    the machine (DNS rebinding) is refused with 400.
  - `/api/runs/saved` reads `GENETIC_OPT_WEB_RUNS_ROOT`, the folder a
    saved run must be inside. Any folder when it is not set.
- `web/runs.py`: `saved_run` takes `root` and `max_bytes`, and refuses
  a run whose files have more than `MAX_SAVED_RUN_BYTES` (4 GB) before
  reading them.
- Added tests: 3 host tests and 1 runs-root test in
  `tests/integration/web/test_app.py`, 4 in `tests/unit/web/test_runs.py`.
- Documented `GENETIC_OPT_WEB_RUNS_ROOT` and the size limit in `README.md`.


### v5.10.2 - 17th October 2026

- Added the `frontend-test` pre-push hook to `.pre-commit-config.yaml`,
  which runs `corepack pnpm --dir frontend test`. It needs the front
  end's packages installed first.


### v5.10.1 - 17th October 2026

- `frontend/`:
  - Added Vitest and the `test` script (`corepack pnpm --dir frontend test`).
  - Added `src/lib/format.test.ts`: 4 tests of `niceTicks`. One takes
    the best and mean scores of a saved `downstream` run, equal but for
    the last digit, which looped forever before v5.10.0; the others a
    range of one value, a range of zero and an ordinary range.
- Added the front-end test command to `CLAUDE.md`.


### v5.10.0 - 17th October 2026

- Added the explainer page "Open a saved run" (`frontend/src/pages/SavedRun.svelte`).
  It takes the folder of a run saved by `fit` or by the crate, or its
  `fit_data` folder, and shows its charts, its parameters and the
  population of each generation. The files hold no parents or
  crossovers, so it has no breeding view.
- `src/genetic_opt/web`:
  - Added `runs.saved_run`, which loads the folder with
    `load_fit_result`. A gene that is not a number or a text, such as a
    dictionary, is sent as JSON text, and the genes of a set are sorted.
    `stop_reason` is `stopped` when the run ended early for a reason
    the files do not hold.
  - Added `POST /api/runs/saved` to `app.py`.
  - `runs._metrics` gives the metrics of a generation to both kinds of
    run.
- `frontend/src/components`:
  - `RunView`: the problem view, the decoded column and the breeding
    tab are left out when a run has none.
  - `PopulationTable`: genes that are not 0 or 1 are shown as text.
    The "Where from" column is left out when it is not known.
  - `LineChart`: the left side fits the longest tick label, so labels
    such as `0.000036` are no longer cut.
- Fixed `niceTicks` in `frontend/src/lib/format.ts`: a range of float
  noise, such as best and mean scores equal but for the last digit,
  froze the page in an endless loop. Such a range, and an empty one, is
  now widened by a tenth of the values on each side, where an empty one
  was widened by 1.
- `tests/conftest.py` sets `MPLBACKEND=Agg`. With a display the plots of
  the tests used Tk, and freeing them in the worker thread of a web
  test could hold `test_run_knapsack_with_the_defaults` for 20 seconds.
- Added tests:
  - `tests/unit/web/test_runs.py`: runs saved as JSON and BSON, the
    `fit_data` folder, sets, dictionary genes, the stop reasons, and
    the refused paths.
  - `tests/integration/web/test_app.py`: the endpoint.


### v5.9.0 - 17th October 2026

- Added tournament selection, in both implementations. The parents of a
  generation that are not among the best ones are picked from the rest
  as `FitConfig.selection` says:
  - `"random"`, the default: each one at random, as before, with the
    same draws for a seed.
  - `"tournament"`: each one is the best of `tournament_size`
    Chromosomes drawn at random from the rest.
- Added `selection` and `tournament_size`, 3 by default, to `FitConfig`
  in both implementations, and to the saved `fit_parameters`. A
  `tournament_size` of 0, or another `selection`, is refused. In the
  crate `selection` is the new enum `Selection`.
- `FitParameters` in `fit_result.py` has both keys as not required:
  runs saved before 5.9.0 do not have them.
- The class doc of `GeneticAlgorithm` called the default selection a
  tournament selection. It now describes both.
- Added tests:
  - `tests/unit/algorithms/test_base.py`: the winners of the
    tournaments, the besties kept, the saved parameters and the
    refused values.
  - `tests/unit/test_fit_result.py`: the keys not required.
  - `crates/genetic_opt/tests/algorithm.rs`: the same as the first.


### v5.8.0 - 17th October 2026

- Added uniform crossover, in both implementations: each gene of a
  child comes from one parent or the other, with even odds, and the
  other child takes the other gene.
  - Added `src/genetic_opt/crossover.py`, with `uniform_crossover` and
    `single_point_crossover`, over two lists of genes.
  - `BinaryGeneticAlgorithm` takes `crossover`, the function that
    crosses the genes of two parents. It is `single_point_crossover` by
    default, which draws the same cuts as before.
  - Added `uniform_crossover` to the crate, beside
    `single_point_crossover`, for `Problem::crossover`.
- Added tests:
  - `tests/unit/test_crossover.py`: both functions.
  - `tests/unit/algorithms/test_binary.py`: the `crossover` argument,
    and a knapsack run crossed with `uniform_crossover`.
  - `crates/genetic_opt/tests/algorithm.rs`: the function, and the same
    run.


### v5.7.0 - 17th October 2026

- Added `ValuesGeneSpace` to `gene_space.py`: a gene space over any
  values it is given, each one once, beside `BinaryGeneSpace`. It
  refuses no values, or a value given twice. The values are drawn by
  position, so they keep their own types.
- Added tests:
  - `tests/unit/test_gene_space.py`: its draws in each shape, the types
    kept, the seed, a list and a set Chromosome filled from it, and the
    refused values.
  - `tests/unit/algorithms/test_base.py`: the set run over 40 words
    uses it in place of a gene space written in the test.
