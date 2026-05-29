#!/usr/bin/env python3
import argparse
import ast
import shutil
import sys
from pathlib import Path


def ast_signature(source):
    tree = ast.parse(source)
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input-dir", default="reduced")
    parser.add_argument("-o", "--output-dir", default="dedup")
    parser.add_argument("--pattern", default="*.py")
    return parser.parse_args()


def main():
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.is_dir():
        sys.exit(f"input directory not found: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    seen = {}
    duplicates = []
    failed = []

    for path in sorted(input_dir.glob(args.pattern)):
        if not path.is_file():
            continue
        try:
            signature = ast_signature(path.read_text())
        except SyntaxError as e:
            failed.append((path, f"SyntaxError: {e.msg} (line {e.lineno})"))
            continue
        except OSError as e:
            failed.append((path, f"{type(e).__name__}: {e}"))
            continue

        if signature in seen:
            duplicates.append((path, seen[signature]))
        else:
            seen[signature] = path
            shutil.copy2(path, output_dir / path.name)

    print(f"[dedup] inputs:     {len(seen) + len(duplicates) + len(failed)}")
    print(f"[dedup] unique:     {len(seen)}  -> {output_dir}")
    print(f"[dedup] duplicates: {len(duplicates)}")
    if failed:
        print(f"[dedup] unparseable: {len(failed)}", file=sys.stderr)
        for path, message in failed:
            print(f"  {path.name}: {message}", file=sys.stderr)


if __name__ == "__main__":
    main()
