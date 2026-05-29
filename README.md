## Usage

### Trace

```bash
# full trace, excluding memory location
./vendor/cpython/python.exe tests/add_1.py 2>&1 | sed 's/0x[0-9a-fA-F]*//g' > add_1.txt
# trace summary with sensitivity 10
python3 src/pesto/cli.py trace tests/add_1.py
```

### Mutate

Mutation type numbers: `1=ORRN 2=VTWD 3=VDTR 4=OASN 5=OLBN 6=SWDD 7=SSDL 8=Ccrc 9=Ccrs` (default: 1 2 3 7)

**All functions in a file (original behaviour):**
```bash
python3 src/pesto/cli.py mutate test.c [-I DIR] [-m N ...]
```

**Specific functions across multiple files via JSON config:**
```bash
python3 src/pesto/cli.py mutate --config targets.json [-I DIR] [-m N ...]
```

Config format — keys are file paths, values are function lists (`null` = all functions in that file):
```json
{
  "src/foo.c": ["add", "sub"],
  "src/bar.c": null
}
```

Output written to `pesto_mutation/`:
- `<stem>.c` and `<stem>.meta.json` per file
- `pesto.json` — unified metadata with globally unique mutation IDs across all files
- `pesto_runtime.c` — shared runtime

```bash
# compile and run
gcc pesto_mutation/foo.c pesto_mutation/bar.c pesto_mutation/pesto_runtime.c -o mutant
PESTO_MUTANT_ID=-1 ./mutant   # original
PESTO_MUTANT_ID=0  ./mutant   # mutation #0
```

### Mutate CPython

**Single file (original behaviour):**
```bash
python3 src/pesto/cli.py mutate-cpython [Objects/longobject.c] [-m N ...]
```

**Specific functions across multiple CPython files:**
```bash
python3 src/pesto/cli.py mutate-cpython --config targets.json [-m N ...]
```

Config format — paths relative to `vendor/cpython/`:
```json
{
  "Objects/longobject.c": ["PyLong_FromLong", "PyLong_AsLong"],
  "Objects/floatobject.c": ["PyFloat_AsDouble", "float_richcompare"]
}
```

Mutates files in-place, patches the Makefile, and builds:
```bash
# re-run after editing config (remove pesto.json to re-mutate)
rm vendor/cpython/pesto.json
python3 src/pesto/cli.py mutate-cpython --config targets.json
```

### Evaluate

```bash
python3 src/pesto/cli.py evaluate [--sample N] [--seed N] [--timeout S]
```

## Running Perses Reducer

Download the prebuilt Perses jar before running the reducer:

```bash
./scripts/install-perses.sh
```

The script downloads `perses_deploy.jar` from [uw-pluverse/perses](https://github.com/uw-pluverse/perses/releases/download/v2.5/perses_deploy.jar)
and stores it under `perses/`.

Run the reducer driver from the project root:

```bash
python3 scripts/run-reducers.py -o [RESULTS_DIR]
```

You can also run the reducer on all Python files in a specific directory:

```bash
python3 scripts/run-reducers.py -d [INPUT_DIR] -o [RESULTS_DIR]
```

You can also run the reducer on one specific input file:

```bash
python3 scripts/run-reducers.py -i [INPUT_PYTHON_PROGRAM] -o [RESULTS_DIR]
```

You can also specify the trace sensitivity (default is 10):

```bash
python3 scripts/run-reducers.py -i [INPUT_PYTHON_PROGRAM] -o [RESULTS_DIR] -ts [TRACE_SENSITIVITY]
```

You can also control how many input files are reduced in parallel:

```bash
python3 scripts/run-reducers.py -o [RESULTS_DIR] -j [JOBS]
```

## Deduplicating Reduced Programs

Keep one representative per unique AST:

```bash
python3 scripts/dedup.py -i reduced -o dedup
```
