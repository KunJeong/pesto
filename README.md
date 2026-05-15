## Trace Instrumentation
Usage:
```bash
# full trace, excluding memory location
./vendor/cpython/python.exe tests/add_1.py 2>&1 | sed 's/0x[0-9a-fA-F]*//g' > add_1.txt
# trace summary with sensitivity 10
python3 src/pesto/cli.py tests/add_1.py -s 10
# mutate c program
python3 src/pesto/cli.py mutate test.c
```
