# Custom Grammar-based Fuzzer

## Files

- `Grammar.g4`: combined ANTLR grammar for Grammarinator
- `fuzz.py`: runner for `proc`, `gen`
- `cases/`: generated programs (with exceptions)
- `cases/results/`: execution error logs

## Setup
Install [Grammarinator](https://github.com/renatahodovan/grammarinator#install)

tldr;
```bash
# Install Java (Grammarinator dependency), Python(>= 3.10)
pip install grammarinator
```



## Usage


At the root/fuzzer directory,

Build Program Generator (Grammarinator):

You must run this if you have modified Grammar.g4 or if you are running for the first time.
```bash
python fuzz.py proc
```

To generate Programs:
```bash
python fuzz.py gen -n [number of programs]
    --rounds [number of rounds, default: 100]
    --seed [random seed, default: random]
    --outdir [output directory, default: ./cases]
```

Example

To generate 20 programs at ../tests/fuzzing_samples/ with random seed:
```
python fuzz.py gen -n 20 --outdir ../tests/fuzzing_samples/
```

## TODO

- Various CFG support

- Error type/message statistics