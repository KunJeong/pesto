## Trace Instrumentation
Usage:
```bash
# full trace, excluding memory location
./vendor/cpython/python.exe tests/add_1.py 2>&1 | sed 's/0x[0-9a-fA-F]*//g' > add_1.txt
# trace summary with sensitivity 10
python3 src/pesto/cli.py tests/add_1.py -s 10
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

You can also run the reducer on a specific input file:

```bash
python3 scripts/run-reducers.py -i [INPUT_PYTHON_PROGRAM] -o [RESULTS_DIR]
```

You can also specify the trace sensitivity (default is 10):

```bash
python3 scripts/run-reducers.py -i [INPUT_PYTHON_PROGRAM] -o [RESULTS_DIR] -ts [TRACE_SENSITIVITY]
```
