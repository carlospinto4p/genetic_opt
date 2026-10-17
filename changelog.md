
## Changelog - Genetic-Opt


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


### v5.6.0 - 17th October 2026

- Added `max_stale_generations` to `FitConfig`, in both
  implementations: the run stops when this many generations in a row
  have bred no better best score than the generations before them.
  `None`, the default, is no limit. It is not saved with the run. The
  default stop, `stop_without_improvement`, is unchanged.
- Added `stale_generations` to the `GeneticAlgorithm` of both
  implementations: the count that stop compares.
- Added tests:
  - `tests/unit/algorithms/test_base.py`: the stop, its log line, the
    count when maximizing and minimizing, and a negative value refused.
  - `crates/genetic_opt/tests/algorithm.rs`: the stop, its log line and
    the count.


### v5.5.0 - 17th October 2026

- Added `max_seconds` to `FitConfig`, in both implementations: the run
  stops after the first generation that ends this many seconds or more
  after the run started. `None`, the default, is no limit. A negative
  value or a NaN is refused. Like `stop_without_improvement`, it is not
  saved with the run.
- Added tests:
  - `tests/unit/algorithms/test_base.py`: the stop, its log line and the
    refused values.
  - `crates/genetic_opt/tests/algorithm.rs`: the same.


### v5.4.0 - 17th October 2026

- The Rust crate writes the progress of a run through the `log` crate,
  at level `info`, as the Python package does through its logger.
  Nothing is written until the program sets up a logger. It writes:
  - the run's parameters when it starts;
  - the best score, mean, median, different chromosomes and time of
    each generation;
  - why the run stopped.
- Added `log` to the crate's dependencies.
- Added tests in `crates/genetic_opt/tests/algorithm.rs`: the lines of
  a run, and each reason to stop.
- Updated `README.md`.


### v5.3.0 - 17th October 2026

- Added `save_fit_plots` to `src/genetic_opt/algorithms/plots.py`: it
  draws `fit_plots.jpg` from the files of a saved run, in the run's
  folder, for a run saved without the plot or by the Rust crate. It
  takes `other_metrics_to_plot` and `load_gene_func`. Checked on a
  `downstream` run saved in September 2024: the plot matches the one that
  run saved.
- Added tests:
  - `tests/unit/algorithms/test_plots.py`: the image is the one `fit`
    saves, byte for byte, with and without `other_metrics_to_plot`.
  - `tests/integration/test_rust_layout.py`: a run of the crate gets
    its plot.
- Updated `README.md`.


### v5.2.0 - 17th October 2026

- Added starting a run from a population with its scores, instead of
  random chromosomes, so a run that stopped can go on. The scores are
  not computed again.
  - `GeneticAlgorithm.fit` takes `first_population`, a list of
    `(Score, Chromosome)` such as `load_fit_result(...)["history"][-1]`,
    for a run saved by either implementation.
  - The crate's `GeneticAlgorithm::fit_from` takes the genes of each
    chromosome with its score. `fit_with` calls it with none.
  - Both refuse an empty population, a chromosome with the wrong number
    of genes and a NaN score, and keep no score of a refused one.
- Added tests:
  - `tests/unit/algorithms/test_base.py`: a run from a saved population,
    and the three refusals.
  - `tests/integration/test_rust_layout.py`: Python goes on with a run
    saved by the crate.
  - `crates/genetic_opt/tests/algorithm.rs`: the same in Rust, and a
    run that breeds from the given population.
- Updated `README.md` with both.


### v5.1.2 - 17th October 2026

- Fixed the docstring of `FitConfig.n_jobs`: since 5.1.1 a fitness
  function that uses the algorithm takes it to the workers without its
  population, history, metrics and scores.


### v5.1.1 - 17th October 2026

- Fixed `GeneticAlgorithm.__getstate__`: it leaves out `population`,
  `history`, `metrics` and the score cache, as well as the workers. A
  fitness function that is a method of the algorithm took all of them
  to the worker processes, and they grow each generation. On a real
  `downstream` `RuleOptimizer` run (27 price lists, 169 generations, 8
  jobs) the pickled function grew from 132 KB to 2.0 MB and now stays
  at 132 KB, and `fit` took 6.5 s instead of 36.8 s.
- Added `test_the_algorithm_pickles_without_its_run` to
  `tests/unit/algorithms/test_base.py`.


### v5.1.0 - 17th October 2026

- Added an explainer of the algorithm, a web page in `frontend/`
  (Svelte 5, Vite, pnpm) served on port 5208:
  - How it works: genes, chromosomes, decoding, the score, and each
    step of a generation, shown on a real run of `Knapsack`.
  - Knapsack: a run of the example with your own objects and
    `FitConfig`, stepped through generation by generation.
  - Find a maximum: the same for `BinaryFunction`, with the population
    drawn on the curve.
- Added `src/genetic_opt/web`, the server of the page, on port 5209:
  - `runs.py`: `record_run` runs an algorithm and keeps, for each
    generation, the parents picked, the gene each child took from each
    parent, the genes the mutation changed, and the children that
    stayed. `BinaryFunction`: the second example, a list of bits read
    as a number of an interval.
  - `app.py`: FastAPI routes `/api/info`, `/api/examples`,
    `/api/runs/knapsack` and `/api/runs/function`. A run is capped at
    300 generations, 400 chromosomes and 40 genes.
- Added the extra `web` (`fastapi`, `uvicorn`) and `httpx2` to the dev
  group, for FastAPI's `TestClient`.
- Added `tests/unit/web/test_runs.py` and
  `tests/integration/web/test_app.py`.


### v5.0.12 - 17th October 2026

- Made four tests check values instead of shapes:
  - `test_load_fit_result_refuses_a_file_over_the_size_limit`: under
    the limit the run loads as it does with the default one.
  - `test_get_file_size_of_a_missing_file_is_none`: a file of 1536
    bytes is `1.5 KiB`.
  - `test_now_for_file_path_is_the_utc_time_to_the_second`, before
    `test_now_for_file_path_format`: the time is UTC, not only the
    format.
  - `test_a_chromosome_builds_its_random_state_on_first_use`: the
    genes that mutate are the first draws of the seed, in place of the
    size of a pickled numpy `RandomState`.


### v5.0.11 - 17th October 2026

- Added Rust tests the Python package already had:
  - `a_run_of_0_generations_scores_the_first_population_only` in
    `tests/algorithm.rs`.
  - `a_saved_chromosome_keeps_the_time_its_score_took` in
    `tests/algorithm.rs`, with a fitness that takes 20 ms.
  - The 0, 60 and 3600 second cases of `format_seconds` in
    `src/format.rs`.
- `Watched` in `tests/algorithm.rs` takes a `fitness_delay`.


### v5.0.10 - 17th October 2026

- Added `test_the_plot_title_names_the_score_when_it_has_a_name` in
  `tests/unit/algorithms/test_plots.py`: the title of the metrics plot
  with no score name, with an empty one, and with one of two words.


### v5.0.9 - 17th October 2026

- `Score.to_dict` leaves out `name` and `extra_metrics` only when they
  are `None`, as the crate does. Before, an empty `name` or
  `extra_metrics` was left out too and loaded back as `None`.
- Added `tests/unit/test_score.py`: a Score comes back equal from its
  dict, with and without an empty `name` and `extra_metrics`.


### v5.0.8 - 17th October 2026

- `load_fit_result` refuses a folder where two files hold the same
  generation, such as `fit_data_1.json` and `fit_data_1.bson`, naming
  both. Before, the generation was in `history` and `metrics` twice.
- Added `test_load_fit_result_refuses_two_files_of_one_generation` in
  `tests/unit/test_fit_result_io.py`.


### v5.0.7 - 17th October 2026

- Added tests of saving and loading a run:
  - `test_a_run_of_set_chromosomes_loads_back_as_sets` in
    `tests/unit/algorithms/test_save.py`: a run of set Chromosomes, as
    JSON and as BSON, loads back with every Chromosome a set.
  - `test_fit_saves_each_generation_and_loads_it_back` also compares the
    `to_dict` of each Chromosome, since `Chromosome.__eq__` looks at the
    genes alone.
  - `test_a_chromosome_comes_back_whole_from_its_dict` in
    `tests/unit/test_chromosome.py`: genes, `score`, `score_time` and
    `random_seed` survive `to_dict`, JSON and `from_dict`.
- Added `load_fit_result_file` tests in `tests/unit/test_fit_result_io.py`:
  each file of a JSON and of a BSON run, `remove_duplicates`,
  `max_file_bytes` and a malformed file.
- Added `test_an_error_of_the_fitness_function_stops_the_run` in
  `tests/unit/algorithms/test_base.py`: the error of a fitness function
  comes out of `fit` as it is, with one job and with two, and the next
  run works.
- Moved `NumbersAlgorithm` and `NumbersGeneSpace` from
  `tests/unit/algorithms/test_base.py` to `tests/unit/conftest.py`.
  `NumbersAlgorithm` takes keyword arguments for `GeneticAlgorithm`.


### v5.0.6 - 17th October 2026

- Added tests of `fit` in `tests/unit/algorithms/test_base.py`:
  - `test_fit_gives_iter_func_the_generations_and_the_chromosomes_to_score`:
    `iter_func` gets the generation numbers, and then exactly the
    Chromosomes the fitness function runs on.
  - `test_proportions_at_0_and_1_breed_without_error`: `crossovers_prop`
    and `besties_prop` at 0 and 1, counting the children scored.
  - `test_a_population_of_one_breeds_no_children`.
- Added `a_population_of_one_breeds_no_children` in
  `crates/genetic_opt/tests/algorithm.rs`, the same test for the crate.


### v5.0.5 - 17th October 2026

- Fixed: a seed gives the same run of set Chromosomes in every launch
  of Python. `GeneSet.random_mutate` in `gene_collection.py` decided
  which genes mutate in the order of the set, and the order of a set
  of strings changes with the hash seed Python draws at each launch.
  It now takes the genes sorted, as `Chromosome.__repr__` already
  does. A seed gives a different set run than it did before.
- Added `test_one_seed_gives_the_same_set_run_with_any_hash_seed` in
  `tests/unit/algorithms/test_base.py`: a run of 40 words as sets, in
  two new processes with different hash seeds.
- The crate is not affected: it keeps the genes of a set in a
  `BTreeSet`, which is always sorted.


### v5.0.4 - 17th October 2026

- Fixed: a fitness function that gives a NaN score stops the run with a
  validation error naming the Chromosome, in both implementations. The
  score is refused before it is cached, so a later `fit` refuses it
  too. Before, Python left a NaN score wherever the sort put it, the
  crate ranked it best when maximizing, and the mean of the generation
  became NaN, so the stop when the mean does not change never fired.
  - `algorithms/base.py`: `_sort_population` raises
    `ValidationException`.
  - `algorithm.rs`: `GeneticAlgorithm::score` returns
    `Error::Validation`. `Problem::fitness` and `README.md` say so.
- Added tests: `test_fit_refuses_a_nan_score` in
  `tests/unit/algorithms/test_base.py`, and `a_nan_score_stops_the_run`
  in `crates/genetic_opt/tests/algorithm.rs`.


### v5.0.3 - 17th October 2026

- Fixed: an infinite `space_points` (more different chromosomes than a
  float holds) is saved as `null` by both implementations, in JSON and
  in BSON, and `load_fit_result` and `load_fit_result_file` read it
  back as infinite. Before, Python wrote `Infinity`, which is not
  standard JSON, and loaded the crate's `null` as `None`.
  - `fit_result_io.py`: `serialize_fit_result` writes `None`, and the
    loaders turn it into `inf`. A file with `Infinity` still loads.
  - `metrics.rs`: `FitnessFuncCalls.space_points` is serialized as
    `null` when infinite.
- Added tests:
  - `test_fit_result_io.py`: a run with 2 ** 1100 chromosomes, saved as
    JSON and BSON, and a file with `Infinity`.
  - `metrics.rs`: `an_infinite_space_is_saved_as_null`.


### v5.0.2 - 17th October 2026

- The crate's `numbers` example sets `extra_config` to
  `{"minimize": false}`, so a run of the crate with a `config` is loaded
  in Python. `README.md` says so.
- `tests/integration/test_rust_layout.py`:
  - Checks the `config` of both examples' runs, and the whole content
    of their `experiment_config.yml`, not only that it exists.
  - Added `test_python_loads_one_file_saved_by_the_rust_crate`:
    `load_fit_result_file` on the last file of a run of the crate, in
    JSON and in BSON.


### v5.0.1 - 17th October 2026

- `tests/integration/test_rust_layout.py`: a run of the crate loaded in
  Python is checked against the `FitResult` types: every key of
  `fit_parameters` and `fit_metrics` and the type of each value, every
  `Metric` field, each chromosome's `score`, `score_time` and
  `random_seed`, and `genetic_opt_version` equal to the package's.


### v5.0.0 - 17th October 2026

- Removed the `processing_object` parameter and attribute of
  `GeneticOptException`, and with it the "At object:" part of its
  message. Nothing in the package passed one.
- Removed the `only_hours` parameter of `format_seconds` in
  `functions.py`. Nothing in the package passed it.
- Updated the tests that used them: `test_exceptions.py`,
  `test_functions.py` and `test_gene_collection.py`.


### v4.1.2 - 17th October 2026

- Fixed: `Chromosome.from_dict` and `Metric.from_dict` build the class
  they are called on, not always the base class. Tested in
  `test_chromosome.py` and `test_metrics.py`.
- Docstrings:
  - Added module docstrings to `fit_result_io.py`, `score.py`,
    `algorithms/binary.py` and `examples/binary.py`.
  - Added class docstrings to the three classes of `exceptions.py`.
  - Fixed `gene_collection.py`, which called itself the Gene Space
    submodule, `Chromosome.get_score`, which described a `Score` as a
    tuple, and `Chromosome.to_dict`, which left out `is_gene_set`.
- Renamed `GeneticAlgorithm._get_fitted_data` to `_get_fit_result`, the
  name of what it returns.
- Removed the "Before 0.x.0" history notes from `README.md`; the
  changelog has them. It still says which old files
  `load_fit_result` reads.


### v4.1.1 - 17th October 2026

- Fixed: a broken `crossover_invariant` raises an `InvariantException`
  that says "crossed to", not "mutated to".
  `test_a_broken_invariant_stops_the_run` checks each message.
- `get_file_size` in `files.py` returns `None` explicitly for a missing
  file instead of falling off the end.
- Changed the `Args:`/`Returns:`/`Raises:` docstrings to the Sphinx
  `:param:`/`:return:`/`:raises:` form:
  - `fit_result_io.py`: `load_fit_result`, `load_fit_result_file`,
    `serialize_fit_result`.
  - `metrics.py`: `Metric.from_dict`, `Metric.to_dict`,
    `get_population_metrics`.
  - `chromosome.py`: `Chromosome.from_dict`, `Chromosome.to_dict`.
  - `algorithms/plots.py`: `plot_genetic_algo_metrics`.
- Type hints:
  - Added `| None` to `Score.name`, `Score.extra_metrics` and the
    `random_state` of `Chromosome.random_mutate`.
  - Added `-> None` to every `__init__`.
  - Annotated `identity_func`, the wrapper of `time_it_with_logger`,
    `Chromosome.__eq__`, the `data` of `save_bson` and `save_json`, and
    every `**kwargs`.


### v4.1.0 - 17th October 2026

- Added `examples::Numbers` to the crate, beside `examples::Knapsack`:
  pick 3 different numbers under 12 with the highest sum, or the
  lowest with `minimize` set. Its `Solution` is the numbers picked, and
  it saves an `experiment_config`.
- The `numbers` example runs `examples::Numbers` instead of its own copy.
- `crates/genetic_opt/tests/algorithm.rs`:
  - Uses `examples::Numbers` instead of a copy of the example. The
    tests compare the numbers picked, not their sum.
  - Replaced `CountedKnapsack` and the invariant switches of the old
    test `Numbers` with `Watched`, one wrapper around any problem that
    counts the fitness calls and holds or breaks the invariants.
- `README.md` names `examples::Numbers` and says an unknown format
  stops the examples.


### v4.0.2 - 17th October 2026

- Added `crates/genetic_opt/examples/common/mod.rs`: `save_config` and
  `print_run`, the command line and the printing that the `knapsack`
  and `numbers` examples each had a copy of.
- Fixed: the Rust examples stop with an error on a format other than
  `json` or `bson`. Before, any other word, such as `jsno`, saved the
  run as BSON.
- Added `test_the_rust_examples_refuse_an_unknown_format` to
  `tests/integration/test_rust_layout.py`.


### v4.0.1 - 17th October 2026

- `gene_collection.py`:
  - `GeneList` and `GeneSet` no longer set `size` before
    `GeneCollection.__init__` sets it. `GeneList` draws its missing
    genes with `_draw_genes`.
  - `GeneSet._complete_genes` checks the gene space against the number
    of genes it is asked for, not `size`.
  - The class docstrings of `GeneList` and `GeneSet` say what each
    one is, instead of repeating the one of `GeneCollection`.


### v4.0.0 - 17th October 2026

- Moved `plot_metrics` and `other_metrics_to_plot` from
  `GeneticAlgorithm.fit` to `SaveConfig`: only a saved run gets a
  plot. Code that passes them to `fit` must pass them to `SaveConfig`.
- Moved `save_current_figure` from `files.py` to
  `algorithms/plots.py`. It always clears and closes the figure: its
  `clear_fig` and `close_fig` arguments were never passed.
- `files.py`: `_log_saved` is now `log_saved`, as `plots.py` uses it
  too.
- `algorithms/plots.py`: the four legends share `LEGEND_PARAMS`.
- `algorithms/base.py`: the defaults of `next_generation_selection`,
  `_start_population` and `_sort_population` are the ones of
  `FitConfig`, no longer copied.
- `fit_result.py`: the `Bests` docstring cites `N_BESTS` instead of
  writing 5.
- `tests/unit/algorithms/test_save.py`: the plot test also runs with
  `other_metrics_to_plot`.


### v3.2.0 - 17th October 2026

- Renamed what was left of the `GeneticBag` name of the knapsack
  example:
  - `crates/genetic_opt/src/metrics.rs`: `FitnessCalls` is now
    `FitnessFuncCalls`, the name of the Python type and of the
    `fitness_func_calls` key it is saved under. Code that uses the
    crate must rename it too.
  - `src/genetic_opt/examples/binary.py`: the `Knapsack` functions
    `decode_bag` and `fit_bag` are now `decode` and `fitness`, the
    names of the crate's knapsack methods.
  - The unit tests: `test_genetic_bag` is now
    `test_knapsack_finds_the_best_bag`, and the `genetic_bag`
    variables are `knapsack`.


### v3.1.1 - 17th October 2026

- Split the unit tests so each file tests one source module:
  - `tests/unit/test_binary_algs.py` became
    `tests/unit/algorithms/test_base.py`,
    `tests/unit/algorithms/test_binary.py`,
    `tests/unit/examples/test_binary.py`, `test_chromosome.py` and
    `test_gene_collection.py`.
  - `tests/unit/test_fit_save.py` became
    `tests/unit/algorithms/test_save.py`,
    `tests/unit/algorithms/test_plots.py`, `test_fit_result.py` and
    `test_fit_result_io.py`.
  - The exception and logger tests of `test_functions.py` moved to
    `test_exceptions.py` and `test_logs.py`; its gene collection tests
    to `test_gene_collection.py`.
  - `test_get_space_points_counts_lists_and_sets` moved to
    `test_metrics.py`.
- Added `tests/unit/conftest.py` with the helpers the split files
  share: `ones_algorithm`, `decode_genes`, `count_ones`,
  `OnesGeneSpace` and the `saved_run` fixture.
- Every unit test file has its `# ── … Tests ──` section headers.
- Updated the paths to these tests in `crates/genetic_opt/tests/algorithm.rs`,
  `.claude/rules/testing-areas.md` and `backlog.md`.


### v3.1.0 - 17th October 2026

- `src/genetic_opt/algorithms/base.py`: `init_population` now means
  what it means in the crate.
  - `get_init_population` is renamed `init_population`. It returns
    the genes of each chromosome of the first population; a subclass
    overrides it to choose them.
  - The method that built and scored the first population, called
    `init_population` before, is now the private `_start_population`.
- Updated `tests/unit/test_binary_algs.py` for the new names.
- A subclass that overrides `get_init_population` must rename it to
  `init_population`, or its override stops being called.


### v3.0.0 - 17th October 2026

- The crate's settings now sit where the Python package has them. The
  Python package is unchanged.
- `crates/genetic_opt/src/algorithm.rs`:
  - Added `AlgorithmConfig`, given to `GeneticAlgorithm::new`, with
    `experiment_name`, `random_seed`, `extra_config` and `save`, as
    the Python algorithm takes them. `AlgorithmConfig::default()` has
    the seed 442 and nothing else set.
  - Removed `random_seed`, `extra_config` and `save` from `FitConfig`.
  - `fit` and `fit_with` take the `FitConfig` of the run, as the
    Python `fit` does.
  - `experiment_name` defaults to the name of the problem's type
    without its module path, as the Python one defaults to the class
    name. Added `GeneticAlgorithm::experiment_name`.
- `crates/genetic_opt/src/save.rs`: `SaveConfig` lost
  `experiment_name` and has `as_bson: bool` in place of `format`, as
  the Python `SaveConfig`. Removed `SaveFormat`.
- Updated the `knapsack` and `numbers` examples, the crate's tests and
  the README. Their runs are saved in the same folders as before.
- Added the crate tests `algorithm_config_default_sets_the_defaults`
  and `the_experiment_name_defaults_to_the_name_of_the_problem_type`.


### v2.2.0 - 17th October 2026

- Added `FitConfig.stop_without_improvement` in
  `src/genetic_opt/algorithms/config.py`, default `True`, like the
  crate's field of the same name. With `False`, `fit` does not call
  `no_improvement_condition`, which a subclass can still override.
  It is left out of the saved `fit_parameters`, as the crate leaves
  it out.
- Updated the tests that replaced `no_improvement_condition` on the
  instance to set `stop_without_improvement=False` instead, in
  `tests/unit/test_binary_algs.py` and `tests/unit/test_fit_save.py`.
- Added `test_fit_without_the_improvement_stop_breeds_every_generation`.


### v2.1.0 - 17th October 2026

- Removed `GeneticAlgorithm.get_chromosome_score` from
  `src/genetic_opt/algorithms/base.py`. Only the tests called it, and
  it repeated the lookup of the score cache that `_sort_population`
  does for every population of `fit`. A minor version by decision,
  though a public method is removed: no known caller uses it.
- `tests/unit/test_binary_algs.py`:
  - Removed `test_get_chromosome_score_runs_the_fitness_function_once`;
    `test_fit_scores_each_chromosome_once` covers the cache through
    `fit`.
  - `test_chromosomes_sharing_an_id_keep_their_own_scores` keeps only
    its check through `fit`.


### v2.0.6 - 17th October 2026

- `src/genetic_opt/algorithms/base.py`: `fit` checks its `FitConfig`
  and resolves `n_jobs` in a new private method, `_fit_parameters`,
  like the crate's `fit_parameters`. The checks, their messages and
  the moment they raise are unchanged: in `fit`, not when the
  `FitConfig` is built.


### v2.0.5 - 17th October 2026

- Fixed `src/genetic_opt/gene_collection.py`: a `GeneList` or `GeneSet`
  given fewer genes than its `size` and no `gene_space` failed with an
  `AttributeError` or a `TypeError`. It now raises a
  `ValidationException` naming both numbers.
- Added `test_a_chromosome_short_of_genes_needs_a_gene_space` in
  `tests/unit/test_functions.py`.


### v2.0.4 - 17th October 2026

- Fixed `src/genetic_opt/fit_result_io.py`: an error raised by the
  caller's `load_gene_func` or `load_decoded_chromosome_func` reached
  the caller as a `ValidationException` saying the file is "not a fit
  result file". `load_fit_result` and `load_fit_result_file` now let
  it out as it was raised, with its own traceback and cause.
- Added `test_an_error_of_a_load_function_is_not_a_refusal_of_the_file`
  in `tests/unit/test_fit_save.py`.


### v2.0.3 - 17th October 2026

- `.claude/rules/testing-areas.md`: "Recorded times" re-measured at
  v2.0.2: 185 unit tests in 3.9 s, 5 integration tests in 0.5 s, a
  clean `cargo build` in 7.8 s, and 42 Rust tests in 5.3 s.


### v2.0.2 - 17th October 2026

- `crates/genetic_opt/src/algorithm.rs`: `score` puts the new
  Chromosomes back in the order they were asked for by placing each at
  its position, instead of sorting them. Each is still hashed twice,
  once to look it up among the scored ones and once to find repeats in
  the batch: the two are different maps.
- `tests/unit/test_fit_save.py`:
  `test_fit_saves_each_generation_and_loads_it_back` no longer draws
  the metrics JPEG, which two other tests check. The unit suite took
  3.7 s, from 7.6 s.
- `tests/integration/test_rust_layout.py`: one session fixture,
  `examples`, builds every example of the crate with one
  `cargo build --examples`.
- Measured a `[profile.dev]` with line tables only for the crate and
  no debug information for dependencies, and left it out. A clean
  `cargo test --no-run` took 11.35 s against 11.85 s, a rebuild after
  one edit 0.78 s against 0.90 s; the build folder was 290 MB against
  498 MB.


### v2.0.1 - 17th October 2026

- `src/genetic_opt/algorithms/base.py`:
  - `fit` keeps one `joblib.Parallel` open for its whole run, instead
    of one for each generation. A 4-job `Knapsack` run (80 genes, 300
    Chromosomes, 61 generations) was 6% and 16% faster in two of
    three rounds timed against 2.0.0; the machine was busy with other
    work, so the figures are rough.
  - Added `__getstate__`, which leaves the open `Parallel` out: a
    fitness function that uses the algorithm takes it to each worker,
    and an open `Parallel` can not be pickled.
  - `_sort_population` computes `repr` once for each unscored
    Chromosome instead of twice.
- `src/genetic_opt/metrics.py`: `get_population_metrics` converts the
  scores to a numpy array once, instead of once for each of `mean`,
  `median` and `var`.
- Added tests in `tests/unit/test_binary_algs.py`:
  - `test_fit_keeps_one_pool_of_workers_for_the_whole_run`.
  - `test_fit_lets_go_of_its_pool_of_workers_when_it_raises`.
  - `test_fit_runs_a_fitness_function_that_uses_the_algorithm`.


### v2.0.0 - 16th October 2026

- A saved generation file no longer holds `last_population`, its
  population decoded a second time. Each file held the population
  twice, and only the copy of the last file was read.
  - `src/genetic_opt/fit_result_io.py`:
    - `load_fit_result` takes the algorithm's `decode_func` as its
      second argument and decodes the last population with it, as
      `fit` does. `remove_duplicates` leaves `last_population` whole,
      as before. A file saved before 2.0.0 still loads; its
      `last_population` is not read.
    - `serialize_fit_result` leaves out `last_population`.
  - `crates/genetic_opt/src/save.rs`: removed `last_population` from
    `GenerationFile`.
  - `crates/genetic_opt/src/algorithm.rs`: `save_generation` no longer
    decodes the population.
- `fit` and the crate's `fit` still return `last_population`.
- Added tests in `tests/unit/test_fit_save.py`:
  - `test_the_files_do_not_hold_the_population_decoded`.
  - `test_load_fit_result_decodes_the_last_population_loaded`.
  - `test_load_fit_result_skips_the_decoded_population_of_an_old_file`.
  - `test_remove_duplicates_leaves_the_last_population_whole`.
- `tests/integration/test_rust_layout.py` checks the decoded best of a
  Rust run's last population.
- `README.md`: documented the new argument.


### v1.0.5 - 16th October 2026

- `pyproject.toml`: added `[tool.hatch.build.targets.sdist]`, so the
  source package holds `src/genetic_opt`, `tests` and `README.md`
  instead of every file git tracks (the Claude config, the backlog,
  the changelog archive, the CI files and the Rust crate).
- The tests that read the Rust crate skip when it is missing, as it is
  in the source package:
  - `tests/unit/test_versions.py`.
  - `tests/integration/test_rust_layout.py`.


### v1.0.4 - 16th October 2026

- `src/genetic_opt/files.py`: `save_json` writes the text of
  `json.dumps` instead of calling `json.dump`, which uses the pure
  Python encoder. Saving one generation's file went from 20.8 ms to
  2.3 ms in the measurement of the v1.0.0 scan.


### v1.0.3 - 16th October 2026

- `crates/genetic_opt/src/save.rs`: `write_experiment_config` and
  `write_generation` flush their `BufWriter` and return its error. A
  write that failed when the buffer was written out (a full disk) was
  dropped, and the run went on as saved. Added the unit test
  `a_failed_write_is_returned`, which writes to `/dev/full` (Linux
  only).


### v1.0.2 - 16th October 2026

- `.gitlab-ci.yml`, the `publish-package` job:
  - Installs its tools from the new `ci/publish-requirements.txt` with
    `--require-hashes`, so the dependencies of `build` and `twine` are
    pinned and hash-checked too. `ci/publish-requirements.in` lists the
    tools and the command that compiles the file.
  - Builds with `--no-isolation`, using the pinned `hatchling` from that
    file instead of one `build` downloads unpinned.
  - The comment at the top names `genetic_opt` instead of another
    project's package, and no longer points to a "Release Tagging"
    section that does not exist.
- `changelog.md`: two blank lines between v1.0.2, v1.0.1, v1.0.0 and
  v0.17.17, as `versioning.md` asks. `scripts/changelog-add.sh` writes
  one; the fix is filed in `programme`, which keeps the script.


### v1.0.1 - 16th October 2026

- `src/genetic_opt/algorithms/save.py`: `FitSaver` now refuses an
  `experiment_name` with a Windows drive (`C:/x`, `C:x`), which left
  the save path on Windows. Two cases added to
  `test_an_experiment_name_outside_the_save_path_is_refused`.
- `src/genetic_opt/fit_result_io.py`: the `max_file_bytes` docstrings
  of `load_fit_result` and `load_fit_result_file` say that with no
  limit a file of any size is read whole into memory.
- `pyproject.toml`: a comment next to `pymongo` says `import bson`
  comes from it, and that the unrelated PyPI package `bson` would
  shadow it.


### v1.0.0 - 16th October 2026

- Renamed the Python names that differed from the Rust crate, so both
  implementations use the same ones. Saved runs keep their layout:
  runs saved by earlier versions load unchanged.
  - `GeneticAlgorithm.historial` to `history`, also the `historial`
    key of a `FitResult` and of what `load_fit_result` returns.
  - The argument and attribute `opt_is_min` to `minimize`.
  - The attribute `algo_fitness_func` to `fitness_func`, the name of
    the argument it comes from.
  - `examples.binary.GeneticBag` to `Knapsack`. A run saved without an
    `experiment_name` now goes in a `Knapsack` folder.
- Added `Best` to `src/genetic_opt/metrics.py`: a dataclass with
  `score`, `encoded` and `result`, as the crate's `Best`.
  `Metric.best` is now a `Best` in place of a dict, so
  `m.best["score"]` becomes `m.best.score`.
- Added `test_population_metrics_survive_to_dict_and_from_dict` to
  `tests/unit/test_metrics.py`.


### v0.17.17 - 16th October 2026

- Rotated changelog: archived 53 entries to `changelog/2024.md`, `changelog/2026.md`.


### v0.17.16 - 15th October 2026

- Fixed `format_seconds` printing `1 day, 0.00 seconds` for 86400
  seconds. After the days the rest is now always in hours:
  `1 day, 0:00:00 hours`, `1 day, 0:00:05 hours`. Changed in both
  `src/genetic_opt/functions.py` and `crates/genetic_opt/src/format.rs`,
  with the cases added to `tests/unit/test_functions.py` and to the
  test in `format.rs`.


### v0.17.15 - 15th October 2026

- Fixed the crate panicking in `measure` when a `Problem`'s
  `init_population` returns no chromosomes. `first_chromosomes` now
  returns an `Error::Validation`, as the Python package refuses an
  empty population. Added the case to
  `chromosomes_the_problem_cannot_hold_are_refused` in
  `crates/genetic_opt/tests/algorithm.rs`; its `FirstGenes` problem now
  takes the whole first population.


### v0.17.14 - 15th October 2026

- Regenerated `.claude/rules/00-rule-index.md`: the `testing-areas`
  line now carries that rule's current description.


### v0.17.13 - 15th October 2026

- `crates/genetic_opt`:
  - Replaced the `Error::Validation` in `breed` for parents asked of a
    population with no chromosomes left after the best ones with an
    `expect` and a comment. It could not be reached: both proportions
    are at most 1, so the rest is empty only when every parent is one
    of the best.
  - Added `proportions_at_0_and_1_breed_without_error` to
    `tests/algorithm.rs`.


### v0.17.12 - 15th October 2026

- Fixed `GeneticAlgorithm.fit` returning an empty dictionary, which is
  not a `FitResult`, when `n_generations` is negative. It now raises a
  `ValidationException` before scoring anything, as a `population_size`
  below 1 does. Added the case to
  `test_fit_refuses_parameters_out_of_range` in
  `tests/unit/test_binary_algs.py`.


### v0.17.11 - 15th October 2026

- Fixed a second `fit` on the same `GeneticAlgorithm` writing its
  `fit_data_<n>` files over those of the first run. Each `fit` after
  the first now saves in a new folder, as the Rust crate does, and
  `save_path` holds it. The first run still saves in the folder made
  when the object is built, so it can be written to before `fit`.
  - `FitSaver.start_run` in `src/genetic_opt/algorithms/save.py` gives
    the folder of a run that starts.
  - Added `test_a_second_fit_saves_in_a_new_folder` to
    `tests/unit/test_fit_save.py`.


### v0.17.10 - 15th October 2026

- Moved the "Rust crate" row of the suites table and the paragraph on
  the integration suite from `.claude/rules/testing.md` to
  `.claude/rules/testing-areas.md`. `programme` refuses to push
  `testing.md` over text added inside one of its sections, so this repo
  stopped getting its updates. Only the `paths:` header now differs
  from the shared copy, and the push keeps a project's own `paths:`.
- Updated the `testing-areas.md` row of `AGENTS.md` to match.


### v0.17.9 - 15th October 2026

- Added `AGENTS.md`, so Codex and OpenCode read `CLAUDE.md` and the
  rules in `.claude/rules/`. It points at them and copies none of them,
  in the same form as `downstream`'s.


### v0.17.8 - 15th October 2026

- Raised the `numpy` bound in `pyproject.toml` from `<2.0.0` to
  `<3.0.0`; `uv.lock` now has 2.5.4. 1.26.4 had no built wheel for
  Python 3.14, so every new environment compiled it for about 3
  minutes. `RandomState` gives the same numbers in numpy 2, so a seeded
  run gives the same result. Removed the note on that from `CLAUDE.md`.
- Fixed `_draw_genes` in `src/genetic_opt/gene_collection.py`: a gene
  drawn alone stayed a numpy scalar, which numpy 2 prints as
  `np.int64(1)`. A Chromosome holding one got another `id` than the
  same genes as `int`, so it was not found equal to them. The gene is
  now a plain Python value, as the genes drawn together already were.
- Added `test_a_gene_drawn_alone_is_a_plain_python_value` to
  `tests/unit/test_functions.py`.


### v0.17.7 - 15th October 2026

- Added `crates/genetic_opt/examples/numbers.rs`: picks 3 different
  numbers under 12 with the highest sum. Its chromosomes are sets and
  its scores have a name and extra metrics, so a run it saves has the
  parts of the layout the knapsack example leaves out. The README names
  it.
- Added tests to `tests/integration/test_rust_layout.py`:
  - `test_python_loads_sets_and_named_scores_saved_by_the_rust_crate`,
    on a run of the `numbers` example saved as BSON and as JSON.
  - `test_the_rust_example_saves_bson_when_no_format_is_given`.
- Added tests to `crates/genetic_opt/tests/algorithm.rs`:
  - `knapsack_decodes_known_bags`, with the same four bags as
    `KNOWN_BAGS` in `tests/unit/test_binary_algs.py`, and
    `knapsack_takes_nothing_after_the_first_object_that_does_not_fit`.
  - `single_point_crossover` on every cut, on fewer than two genes and
    on parents of different lengths.
  - The set and minimise runs now assert the optimum, 30 and 3. They
    run with `min_population_size` 0 and without the stalled-mean
    stop, which ended them at 28 before.
  - `Chromosome::new` on a set, the `FitConfig::new` defaults,
    `population()`, `metrics()`, `fit_parameters`, `n_jobs: None`, a
    `Problem::experiment_config` that is saved, and a save path that
    cannot be created.
- Added `each_error_names_its_kind` to `crates/genetic_opt/src/error.rs`.
- Added Python unit tests:
  - `test_binary_algs.py`: the bag decoding and scoring known bags, the
    generations of the knapsack run, an empty first population and a
    run of 0 generations.
  - `test_fit_save.py`: the content of `experiment_config.yml`, the
    `extra_config` in each saved generation, that `fit_plots.jpg` is a
    JPEG, and the panels of the plot with and without other keys.
    `count_ones` now gives extra metrics, so every save and load test
    carries them.
  - `test_files.py`: missing and corrupt JSON and BSON files, and
    `get_file_size` of a missing file.
  - `test_functions.py`: `format_seconds` at 0, 60 and 3600 seconds,
    the `YiB` case of `format_bytes`, and `log_format`.
- Fixed `test_time_it_with_logger_logs_and_returns`: it asserted
  "took 0.00 seconds" and failed when the call took 5 ms or more.


### v0.17.6 - 15th October 2026

- Fixed `median` in `crates/genetic_opt/src/metrics.rs`: with no values
  it subtracted 1 from 0 and panicked. It now returns not a number, as
  `mean` and `variance` do.
- Added tests to `tests/unit/test_binary_algs.py`:
  - `test_set_mutation_with_probability_0_keeps_every_gene` and
    `test_set_mutation_with_probability_1_replaces_every_gene`.
  - `test_one_seed_gives_the_same_run_with_any_number_of_jobs`: two
    runs with one job and one with two give the same populations.
  - `test_another_seed_gives_another_run`.
- Added `tests/unit/test_metrics.py`: `get_population_metrics` with
  known scores, an even count, equal scores and a population of one.
- Added tests to the Rust crate:
  - `metrics.rs`: `statistics_of_equal_values` and
    `statistics_of_no_values_are_not_numbers`.
  - `tests/algorithm.rs`: mutation with probability 0 and 1 for lists
    and sets, `another_seed_gives_another_run`,
    `chromosomes_the_problem_cannot_hold_are_refused` (a list of the
    wrong length, a set with a gene twice, a set longer than its gene
    space) and `more_threads_than_cores_are_refused`.
  - `a_broken_invariant_stops_the_run` now covers a false
    `crossover_invariant` and checks which invariant the message names.


### v0.17.5 - 14th October 2026

- Fixed `load_fit_result` in `fit_result_io.py`: a missing or empty
  folder raised `IndexError`. It now raises `ValidationException`.
- Added tests to `tests/unit/test_fit_save.py`:
  - `test_load_fit_result_refuses_a_folder_without_files`, for an
    empty folder and a missing one.
  - `test_load_fit_result_refuses_a_folder_with_another_file`: a file
    that is not a saved generation is refused by name.
  - `test_load_fit_result_applies_the_load_functions`, for
    `load_decoded_chromosome_func` and `load_gene_func`.
  - `test_load_fit_result_removes_duplicates_when_asked`.


### v0.17.4 - 14th October 2026

- Added tests of the stop when a population has fewer different
  Chromosomes than `min_population_size`, which had none:
  - `tests/unit/test_binary_algs.py`:
    `test_fit_stops_below_min_population_size`, at 2, 1 and 0 for a
    population with 1 different Chromosome.
  - `crates/genetic_opt/tests/algorithm.rs`: the `ZeroStart` problem,
    `the_run_stops_below_min_population_size` and
    `the_run_stops_when_the_mean_score_does_not_change`, the stalled
    mean stop of the crate, which had no test either.


### v0.17.3 - 14th October 2026

- Fixed `Chromosome.__eq__` in `chromosome.py`: comparing a Chromosome
  with something that is not one raised `AttributeError`. It now
  returns `NotImplemented`, so `chromosome != None` is true.
- Added tests for paths that had none:
  - `tests/unit/test_binary_algs.py`:
    `test_a_broken_invariant_stops_the_run` for a false
    `mutation_invariant` and `crossover_invariant`;
    `test_the_bag_refuses_weights_and_values_of_different_lengths`;
    a `min_population_size` above `population_size` in
    `test_fit_refuses_parameters_out_of_range`.
  - `tests/unit/test_fit_save.py`:
    `test_load_fit_result_orders_the_generations_by_number`, a run of
    11 saved generations, where `fit_data_10` is listed before
    `fit_data_2`.
  - `tests/unit/test_functions.py`:
    `test_a_chromosome_differs_from_what_is_not_a_chromosome`.
- Updated `tests/unit/test_binary_algs.py`:
  `test_fit_scores_each_chromosome_once` now checks that the logged
  calls match the `processed` count of `fit_metrics`.
- Updated `tests/unit/test_fit_save.py`: the save and load test now
  compares `fit_metrics` too.


### v0.17.2 - 14th October 2026

- Fixed `GeneticAlgorithm.init_population` in `algorithms/base.py`: a
  `fit` with `chromosome_as_set=True` raised `TypeError` when a row of
  the first population drew one gene twice. Each Chromosome now gets
  the gene space, and draws the genes the set lost.
- Added to `tests/unit/test_binary_algs.py`:
  - `NumbersAlgorithm`: picks 3 different numbers under 12, a set
    Chromosome, as the `Numbers` problem of the crate's tests.
  - `test_set_chromosomes_stay_sets_and_the_best_never_gets_worse`:
    the first `fit` test with set Chromosomes.
  - `test_minimize_keeps_the_lowest_scores`: the first test with
    `opt_is_min=True`.


### v0.17.1 - 14th October 2026

- `.pre-commit-config.yaml`: a pre-push hook runs `pytest tests/unit`
  and `cargo test`, since nothing else runs the tests on a push.
  `pre-commit install` now installs it with the commit hook, and the
  existing hooks run on commit only.


### v0.17.0 - 14th October 2026

- Rust crate `crates/genetic_opt`:
  - `Error` has a variant for each failure that was sent as text:
    `ThreadPool` when the scoring threads can not start, which was
    `Validation`, and `Json`, `Yaml` and `Bson` in place of
    `Serialization(String)`. Each one keeps the error it comes from.
  - Renamed the public module `problems` to `examples`, as in the
    Python package. It differed from the private module `problem` by
    one letter. `Knapsack` is now `genetic_opt::examples::Knapsack`.
- Python type hints and names:
  - `BinaryGeneSpace.select_random` is annotated as returning a numpy
    integer or array, and takes a tuple of any length.
  - `Chromosome.score_time` is annotated `float`.
  - `N_BESTS` in `algorithms/base.py` names the number of bests a
    `FitResult` reports, as in the crate.
  - `files.py` no longer imports `os.path`, which the parameter `path`
    of `save_current_figure` hid.
  - The docstrings of `algorithms/base.py` use `:param:` throughout.
- Removed stale comments: three notes and TODOs from 2021 to 2024 in
  `algorithms/base.py`, a 2024 TODO in `fit_result_io.py`, a `core`
  module named in `examples/__init__.py`, `from_dict` written for
  `to_dict` in `Metric.from_dict`, and commented-out assertions in
  `tests/unit/test_binary_algs.py`.
- Added `tests/unit/test_versions.py`: fails when the crate's version
  in `Cargo.toml` or `Cargo.lock` differs from `pyproject.toml`.


### v0.16.0 - 14th October 2026

- Removed code that nothing in this repository or in `downstream` calls:
  - `GeneticAlgorithm.get_best` and `GeneticAlgorithm.get_bests` in
    `src/genetic_opt/algorithms/base.py`. They picked the bests from
    the order of a population, not the way `fit` picks them.
  - The `gene_space_func` and `gene_space_func_kwargs` arguments of
    `Chromosome.random_mutate`, `GeneCollection.random_mutate`,
    `GeneList.random_mutate` and `GeneSet.random_mutate`. A mutation
    always draws its genes with `select_random`.
  - The `ignore_shortcuts` argument of `get_files_inside_folder` in
    `src/genetic_opt/files.py`, which left out files ending in `.lnk`.
  - In `format_seconds` with `only_hours=True`, the padding of the
    hours to two digits, which `int()` removed again. The text is the
    same as before.
- `tests/unit/test_binary_algs.py`: removed the test of
  `gene_space_func` and the `pick` method of its gene space.


### v0.15.0 - 14th October 2026

- Removed `GeneSpace` from `src/genetic_opt/gene_space.py`. It was a
  `TypeVar` bound to `AbstractGeneSpace`, used as the annotation of a
  gene space everywhere, which a type checker does not read as "any
  gene space". The annotations name `AbstractGeneSpace` in
  `chromosome.py`, `gene_collection.py`, `algorithms/base.py` and
  `algorithms/binary.py`, and an argument that defaults to `None` is
  annotated `AbstractGeneSpace | None`. `downstream` imports only
  `AbstractGeneSpace`.


### v0.14.0 - 14th October 2026

- `src/genetic_opt/files.py` handles paths with `pathlib.Path`:
  - Removed `ensure_folder_format`, `get_container_folder`,
    `get_file_extension` and `normalize_path`. `get_file_extension`
    split on the last dot of the whole path, so `"run.v2/data"` gave
    `"v2/data"`. Nothing in `downstream` imports them; it has its own
    copies in `downstream.files`.
  - `ensure_file_extension` compares `Path.suffix`, and returns the
    path as given instead of turning backslashes into slashes.
  - `get_files_inside_folder` lists the folder with `Path.glob`. Its
    non-recursive branch walked the whole tree to keep the first
    entry.
- `src/genetic_opt/algorithms/save.py` and
  `src/genetic_opt/fit_result_io.py` use `Path` in place of the
  removed functions. An experiment name written with backslashes is
  still refused when it leaves the save path.
- `tests/unit/test_files.py`: removed the tests of the removed
  functions; added a missing folder, two folders with a dot in
  `ensure_file_extension`, and a BSON file saved in a folder with a dot.


### v0.13.3 - 14th October 2026

- Every argument check raises `ValidationException`, as the Rust crate
  returns `Error::Validation` for all of them. Four raised the base
  `GeneticOptException`: in `src/genetic_opt/gene_collection.py`, no
  genes and no gene space, a size that does not match the genes, and a
  set larger than its gene space; in `src/genetic_opt/algorithms/base.py`,
  sorting an empty population. Code that catches `GeneticOptException`
  still catches them, since `ValidationException` is a subclass. The
  message now starts with `ValidationException:`.
- `tests/unit/test_functions.py`: the construction tests expect
  `ValidationException`.


### v0.13.2 - 14th October 2026

- The check that a chromosome gets genes or a gene space is written
  once, in `_check_genes_or_gene_space` of
  `src/genetic_opt/gene_collection.py`. `Chromosome`, `GeneList` and
  `GeneSet` each had a copy of it; the one in `Chromosome` ran before
  the other two and added nothing.
- `src/genetic_opt/chromosome.py`: `Chromosome.genes` and
  `Chromosome.size` are read-only properties that read the gene
  collection. They were copies of it, set by hand after each mutation.
- Added three tests to `tests/unit/test_functions.py`: a list and a set
  chromosome built with no genes and no gene space give the same
  message, and `genes` and `size` follow the gene collection after a
  mutation, for a list and a set.


### v0.13.1 - 13th October 2026

- `src/genetic_opt/algorithms/base.py`: `fit` always calls
  `callback_func` and `exit_condition` with the algorithm. It looked
  at `__self__` to call a method of the algorithm with no argument,
  and wrote the lines that end the run twice. Without a
  `callback_func` it still calls the method `default_fit_callback`,
  which a subclass overrides. A method of the algorithm passed as
  `callback_func` or `exit_condition` now gets the algorithm as an
  argument, as any other function does.
- Added two tests to `tests/unit/test_binary_algs.py`: the callback
  and the exit condition get the algorithm, and a subclass that
  overrides `default_fit_callback` has it called in each generation.


### v0.13.0 - 13th October 2026

- Renamed the module `genetic_opt.utils` to `genetic_opt.fit_result_io`.
  It holds `load_fit_result`, `load_fit_result_file` and
  `serialize_fit_result` and nothing else, which the old name did not
  say. Code that imports `genetic_opt.utils` has to import
  `genetic_opt.fit_result_io`.
- The docstrings, `README.md`, `CLAUDE.md`, `backlog.md` and two
  comments of the Rust crate name the module by its new name.


### v0.12.0 - 13th October 2026

- `src/genetic_opt/utils.py`: `load_fit_result` returns
  `last_population` too, read from the file of the last generation, so
  a loaded run has the keys `GeneticAlgorithm.fit` returns. The files
  always held it and nothing read it. `load_fit_result_file` returns
  what it did: the `last_population` of a file is its `population`,
  decoded.
- `src/genetic_opt/fit_result.py`: removed `LoadedFitResult`.
  `load_fit_result` returns a `FitResult`.
- `tests/unit/test_fit_save.py`: the loaded `last_population` and the
  keys of the loaded run are compared with those `fit` returns, and a
  `Score` of `last_population` with an unknown key is refused.
- `README.md`: says that a loaded run has the keys of `fit`.


### v0.11.1 - 13th October 2026

- `CLAUDE.md`: a change that breaks the code of `downstream` gets an
  item in the backlog of `downstream` in the same task. The changes of
  0.9.0 and 0.11.0 were only reported, and the item was filed
  afterwards.


### v0.11.0 - 13th October 2026

- `src/genetic_opt/algorithms/`:
  - Added `config.py`, with the two classes
    that replace loose arguments, as `FitConfig` and `SaveConfig` do in
    the Rust crate. `genetic_opt.algorithms` exports both. Code that
    calls `fit` or saves its runs has to be changed.
    - `FitConfig`: `n_generations`, `population_size`,
      `crossovers_prop`, `besties_prop`, `mutate_prob`,
      `min_population_size` and `n_jobs`, with the defaults `fit` had.
    - `SaveConfig`: `path`, `serialize_decoded_chromosome_func`,
      `as_bson` and `serialize_gene_func`.
  - `base.py`:
    - `GeneticAlgorithm.fit` takes a `FitConfig` in place of those seven
      arguments. `exit_condition`, `plot_metrics`,
      `other_metrics_to_plot`, `callback_func` and `iter_func` stay as
      they were.
    - `GeneticAlgorithm` takes `save`, a `SaveConfig`, in place of
      `save_path`, `save_as_bson`, `serialize_decoded_chromosome_func`
      and `serialize_gene_func`. The attribute `save_path` still holds
      the folder of the run.
    - `fit_parameters` is built from the `FitConfig`, and not key by
      key.
  - `save.py`: `FitSaver` takes a
    `SaveConfig`. A `SaveConfig` can not be built without
    `serialize_decoded_chromosome_func`, so the `ValidationException`
    for a `save_path` without one is gone.
- `README.md`: added an example of each class.
- Added `test_fit_parameters_are_the_config_with_the_seed_and_the_jobs`
  to `tests/unit/test_binary_algs.py`. The other tests and
  `sketches/genetic_bag.py` call `fit` the new way.


### v0.10.0 - 13th October 2026

- Added `src/genetic_opt/fit_result.py`, which states once the keys of
  what `GeneticAlgorithm.fit` returns and of a loaded run. They are
  typed dictionaries, so the results stay plain dictionaries:
  - `FitResult`: what `fit` returns.
  - `LoadedFitResult`: what `utils.load_fit_result` returns.
  - `FitResultFile`: what `utils.load_fit_result_file` returns.
  - `Bests`, `FitMetrics`, `FitnessFuncCalls`, `TotalFitTime`,
    `FitParameters` and `FitSummary`: their parts.
- The description of those keys was pasted into eight docstrings of
  `algorithms/base.py`, `utils.py`, `metrics.py` and
  `algorithms/plots.py`, which name the type now. The copies left out
  `min_population_size`, `n_jobs` and `genetic_opt_version`, and said
  that `population_idx` starts with 0, where it starts with 1.
- `fit`, the two load functions, `serialize_fit_result`, `FitSaver` and
  `plot_genetic_algo_metrics` are annotated with the new types.
- `metrics.py`: the docstring of `Metric` lists `size`.
- Added `test_the_fit_result_types_name_the_keys_of_each_result` to
  `tests/unit/test_fit_save.py`: the keys of each result are the ones
  its type names.


### v0.9.0 - 13th October 2026

- `src/genetic_opt/logs.py` no longer sets up logging when the
  package is imported. It added a handler on the standard output to
  the logger `genetic_opt`, set its level to `INFO` and stopped it
  passing records to the root logger. Now `logger` is
  `logging.getLogger("genetic_opt")` and nothing else, so a program
  that wants the progress of a run configures logging itself.
  - Removed `get_app_logger`, `LOG_FORMAT` and `LOG_DATEFORMAT`, and
    with them the environment variables `LOG_FORMAT` and
    `LOG_DATEFORMAT`, which the package read and nothing documented.
- `README.md`: added the section "Logs", with how to see the progress
  of a run.
- Added `test_the_package_leaves_logging_to_the_application` to
  `tests/unit/test_functions.py`. The two tests that attached `caplog`
  to the package logger by hand (there and in
  `tests/unit/test_files.py`) read it through the root logger.
