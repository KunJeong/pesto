# Custom Grammar-based Fuzzer

## Files

- `Grammar.g4`: combined ANTLR grammar for Grammarinator
- `fuzz.py`: tiny runner for `proc`, `gen`
- `cases/`: generated programs
- `results/`: execution errors

## Setup
Install [Grammarinator](https://github.com/renatahodovan/grammarinator#install)

## Usage

```bash
# Execute at the root/fuzzer directory

# Build Program Generator (Grammarinator)
python fuzz.py proc

# Generate Programs
python fuzz.py gen -n [number of programs]
    --rounds [number of rounds, default: 100]
    --seed [random seed, default: random]
    --outdir [output directory, default: ./cases]

# Example

# generate 100 programs at ../tests/fuzzing/ with random seed
python fuzz.py gen -n 100 --outdir ../tests/fuzzing/
```

## TODO

- Various CFG support

- Error type/message statistics