# PESTO

**P**arametric **E**xecution-path-**S**ensitivity for **T**est **O**ptimization.

PESTO fuzzes Python programs that crash CPython, reduces each one while
preserving its native crash signature, deduplicates by AST, then measures how
well the resulting suite kills mutants of a CPython core source file.

## Setup

```bash
pip install -e .                      # installs pesto + pycparser + grammarinator
./scripts/build-patched-cpython.sh    # builds the instrumented interpreter under vendor/cpython
./scripts/install-perses.sh           # downloads perses_deploy.jar into perses/
```

The reducer also needs a Java runtime (Perses) on the `PATH`.

## Usage

Run the CLI as `python src/pesto/cli.py <command>`. The commands are:

```bash
pipeline [WORKDIR]              # run the whole flow end to end
trace PROGRAM [-s N]           # print the crash signature (N native frames)
fuzz-proc                      # compile the fuzzing grammar (run once / after editing it)
fuzz -n N [--rounds R] [--seed S] [-o DIR]
reduce -o DIR [-i FILE | --input-dir DIR] [-s N] [-j JOBS]
dedup INPUT_DIR OUTPUT_DIR     # keep one program per unique AST
summarize INPUT_DIR            # exception statistics from fuzzer .err logs
mutate (FILE.c ... | --config JSON) [-I DIR] [-m N ...]
mutate-cpython ([FILE] | --config JSON) [-m N ...]
evaluate [--sample N] [--seed N] [--timeout S] [--tests-dir DIR]
```

Mutation operators for `-m` (default `1 2 3 7`):
`1=ORRN 2=VTWD 3=VDTR 4=OASN 5=OLBN 6=SWDD 7=SSDL 8=Ccrc 9=Ccrs`.

### Targeted multi-file mutation

`mutate` and `mutate-cpython` accept `--config JSON` to mutate specific
functions across several files. The config maps each file to a list of function
names, or `null` for every function in that file (`mutate-cpython` paths are
relative to `vendor/cpython/`):

```json
{
  "Objects/longobject.c": ["PyLong_FromLong", "PyLong_AsLong"],
  "Objects/floatobject.c": null
}
```

Mutation IDs are globally unique across all files, and a unified `pesto.json`
(with per-file `id_range` entries) is written alongside the per-file output.

### End-to-end pipeline

Build the mutant set once with `mutate-cpython`, then run the loop that scores a
suite against it:

```bash
python src/pesto/cli.py mutate-cpython   # one-time: build the mutated interpreter + pesto.json
python src/pesto/cli.py pipeline         # fuzz -> reduce -> dedup -> evaluate
```

Each stage writes into `<workdir>/{generated,reduced,dedup}` and any stage can
be skipped to reuse prior output, e.g. re-evaluate without re-fuzzing:

```bash
python src/pesto/cli.py pipeline --skip-fuzz --skip-reduce --skip-dedup
```

### Layout

- `src/pesto/` — the toolchain package (one module per stage + `cli`, `pipeline`, `paths`)
- `src/pesto/grammar/` — ANTLR grammar and generated Grammarinator generator
- `src/pesto/data/test-script.sh` — Perses interestingness oracle
- `scripts/` — one-time environment setup (patched CPython, Perses)
- `samples/test.c` — sample C file exercising every mutation operator
- `tests/` — sample crashing programs and fuzzer output
