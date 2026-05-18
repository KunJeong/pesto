## Usage
```bash
# full trace, excluding memory location
./vendor/cpython/python.exe tests/add_1.py 2>&1 | sed 's/0x[0-9a-fA-F]*//g' > add_1.txt
# trace summary with sensitivity 10
python3 src/pesto/cli.py trace tests/add_1.py
# mutate c program (1=ORRN 2=VTWD 3=VDTR 4=OASN 5=OLBN 6=SWDD 7=SSDL 8=Ccrc 9=Ccrs, default: 1 2 3)
python3 src/pesto/cli.py mutate test.c [-I DIR] [-m N ...]
# mutate cpython longobject and build
python3 src/pesto/cli.py mutate-cpython [file] [-m N ...]
# evaluate mutation score
python3 src/pesto/cli.py evaluate [--sample N] [--seed N] [--timeout S]
```
