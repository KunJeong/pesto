"""Deduplicate programs, keeping one representative per unique AST."""

import ast
import shutil
import sys
from pathlib import Path


def ast_signature(source: str) -> str:
    tree = ast.parse(source)
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


def dedup(input_dir, output_dir, pattern: str = "*.py") -> int:
    """Copy unique-by-AST files from ``input_dir`` to ``output_dir``.

    Returns a process-style exit code (0 on success).
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    if not input_dir.is_dir():
        print(f"input directory not found: {input_dir}", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)

    seen = {}
    duplicates = []
    failed = []

    for path in sorted(input_dir.glob(pattern)):
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

    return 0
