#!/usr/bin/env python3
import argparse
import ast
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

WD = Path(__file__).resolve().parent
GRAMMAR = WD / 'AbstractGrammar.g4'
GENERATOR = 'AbstractGrammarGenerator.AbstractGrammarGenerator'
PYTHON = 'python3'
JOBS = 4
DEPTH = 10
MAX_TOKENS = 320
TIMEOUT = 2
BATCH_MIN = 40
BATCH_FACTOR = 2
FUNC_MAX = 4


def run_cmd(cmd: list[str]):
    print('+', ' '.join(str(x) for x in cmd))
    subprocess.run(cmd, check=True)


def normalize_source(text: str) -> str | None:
    try:
        tree = ast.parse(text, mode='exec')
        text = ast.unparse(tree)
        compile(text, '<norm>', 'exec')
    except SyntaxError:
        return None
    return text.rstrip() + '\n'


def split_imports(text: str) -> tuple[list[str], list[str]]:
    tree = ast.parse(text, mode='exec')
    imports = []
    body = []
    seen_body = False
    for stmt in tree.body:
        code = ast.unparse(stmt)
        if isinstance(stmt, (ast.Import, ast.ImportFrom)) and not seen_body:
            imports.append(code)
        else:
            seen_body = True
            body.append(code)
    return imports, body


def compose_programs(programs: list[str], rng: random.Random) -> str:
    if len(programs) == 1:
        return programs[0]

    base_imports, base_body = split_imports(programs[0])
    func_defs = []
    calls = []

    for i, helper in enumerate(programs[1:], start=1):
        body = '\n'.join('    ' + line if line else '' for line in helper.rstrip().splitlines())
        func_defs.append(f'def foo{i}():\n{body}')
        if rng.choice((True, False)):
            calls.append(f'foo{i}()')

    body_stmts = list(base_body)
    for call in calls:
        pos = rng.randint(0, len(body_stmts))
        body_stmts.insert(pos, call)

    parts = []
    if base_imports:
        parts.append('\n'.join(base_imports))
    if func_defs:
        parts.append('\n\n'.join(func_defs))
    if body_stmts:
        parts.append('\n\n'.join(body_stmts))
    return '\n\n'.join(parts) + '\n'



class Session:
    def __init__(self, args: argparse.Namespace):
        self.target = int(args.n)
        self.round_limit = int(args.rounds)
        self.outdir = Path(args.outdir).resolve()
        self.base = self.outdir.parent
        self.resultdir = self.outdir / 'results'
        self.next_seed = args.seed if args.seed is not None else random.randrange(2**31)
        self.next_case_id = 0
        self.seen: set[str] = set()
        self.stats = {'ok': 0, 'runtime': 0, 'syntax': 0, 'timeout': 0}
        self.total = 0

    def setup(self):
        self.outdir.mkdir(parents=True, exist_ok=True)
        if self.resultdir.exists():
            shutil.rmtree(self.resultdir)
        self.resultdir.mkdir(parents=True, exist_ok=True)
        for path in self.outdir.glob('case_*.py'):
            path.unlink()
        for path in self.resultdir.glob('case_*.err'):
            path.unlink()

    def run_case(self, case_path: Path) -> tuple[int, str, str]:
        try:
            with tempfile.TemporaryDirectory(dir=self.base, prefix='.exec-') as execdir:
                proc = subprocess.run(
                    [PYTHON, str(case_path)],
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT,
                    cwd=execdir,
                )
            rc = proc.returncode
            err = proc.stderr
        except subprocess.TimeoutExpired:
            rc = -1
            err = 'TIMEOUT\n'

        if rc == 0:
            kind = 'ok'
        elif rc == -1:
            kind = 'timeout'
        elif any(name in err for name in ('SyntaxError', 'IndentationError', 'TabError')):
            kind = 'syntax'
        else:
            kind = 'runtime'
        return rc, err, kind

    def keep_case(self, text: str):
        case_path = self.outdir / f'case_{self.next_case_id}.py'
        err_path = self.resultdir / f'case_{self.next_case_id}.err'
        case_path.write_text(text, encoding='utf-8')
        rc, err, kind = self.run_case(case_path)
        self.total += 1
        self.stats[kind] += 1
        if kind == 'runtime':
            err_path.write_text(err, encoding='utf-8')
            self.next_case_id += 1
            return
        case_path.unlink(missing_ok=True)
        err_path.unlink(missing_ok=True)

    def generate_round(self, need: int) -> int:
        kept_before = self.next_case_id
        batch = max(need * BATCH_FACTOR * FUNC_MAX, BATCH_MIN)
        with tempfile.TemporaryDirectory(dir=self.base, prefix='.temp-') as tempdir_str:
            tempdir = Path(tempdir_str)
            run_cmd([
                'grammarinator-generate',
                GENERATOR,
                '--sys-path', str(WD),
                '-n', str(batch),
                '-o', str(tempdir / 'case_%d.py'),
                '-j', str(JOBS),
                '-r', 'file',
                '-d', str(DEPTH),
                '--max-tokens', str(MAX_TOKENS),
                '--random-seed', str(self.next_seed),
            ])
            rng = random.Random(self.next_seed)
            self.next_seed += 1
            raw_programs = []
            for raw_path in sorted(tempdir.glob('case_*.py')):
                text = normalize_source(raw_path.read_text(encoding='utf-8'))
                if text is not None:
                    raw_programs.append(text)

            i = 0
            while self.next_case_id - kept_before < need and i < len(raw_programs):
                group_size = min(rng.randint(1, FUNC_MAX), len(raw_programs) - i)
                text = compose_programs(raw_programs[i:i + group_size], rng)
                i += group_size
                text = normalize_source(text)
                if text is None or text in self.seen:
                    continue
                self.seen.add(text)
                self.keep_case(text)
        return self.next_case_id - kept_before

    def run_pipeline(self):
        self.setup()
        rounds = 0
        while self.next_case_id < self.target and (self.round_limit <= 0 or rounds < self.round_limit):
            rounds += 1
            self.generate_round(self.target - self.next_case_id)
        print(
            f'rounds={rounds} requested={self.target} kept={self.next_case_id} total={self.total}'
        )

def proc(_: argparse.Namespace):
    run_cmd([
        'grammarinator-process',
        '-g', str(GRAMMAR),
        '--language', 'py',
        '-o', str(WD),
        '-r', 'file',
    ])


def gen(args: argparse.Namespace):
    Session(args).run_pipeline()


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)

    proc_parser = sub.add_parser('proc')
    proc_parser.set_defaults(fn=proc)

    gen_parser = sub.add_parser('gen')
    gen_parser.add_argument('-n', type=int, default=20)
    gen_parser.add_argument('--rounds', type=int, default=100)
    gen_parser.add_argument('--seed', type=int)
    gen_parser.add_argument('--outdir', default=str(WD / 'abstract_cases'))
    gen_parser.set_defaults(fn=gen)

    args = parser.parse_args()
    args.fn(args)


if __name__ == '__main__':
    main()
