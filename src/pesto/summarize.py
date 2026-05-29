"""Summarize exception classes and messages from fuzzer ``.err`` logs."""

import shutil
import sys
from collections import Counter
from pathlib import Path


def final_nonempty_line(path: Path) -> str | None:
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
    ]
    lines = [line for line in lines if line]
    if not lines:
        return None
    return lines[-1]


def find_matching_py(err_path: Path, root: Path) -> Path | None:
    candidates = []

    if root.name == "results":
        candidates.append(root.parent / err_path.relative_to(root).with_suffix(".py"))

    if err_path.parent.name == "results":
        candidates.append(err_path.parent.parent / err_path.with_suffix(".py").name)

    candidates.append(err_path.with_suffix(".py"))

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def summarize_errors(input_dir, out_dir=None) -> int:
    """Print error distributions and optionally copy TypeError programs."""
    root = Path(input_dir)
    if not root.is_dir():
        print(f"input directory not found: {root}", file=sys.stderr)
        return 2

    out_path = Path(out_dir) if out_dir else None
    if out_path:
        out_path.mkdir(parents=True, exist_ok=True)

    class_counts = Counter()
    message_counts = Counter()
    copied = 0
    missing_sources = []

    for path in sorted(root.rglob("*.err")):
        message = final_nonempty_line(path)
        if message is None:
            continue
        message_counts[message] += 1
        error_class = message.split(":", 1)[0]
        class_counts[error_class] += 1

        if out_path and error_class == "TypeError":
            source_path = find_matching_py(path, root)
            if source_path is None:
                missing_sources.append(path)
                continue
            shutil.copy2(source_path, out_path / source_path.name)
            copied += 1

    print(f"input_dir: {root}")
    print(f"err_files: {sum(message_counts.values())}")
    if out_path:
        print(f"copied_TypeError: {copied} -> {out_path}")
        if missing_sources:
            print(f"missing_sources: {len(missing_sources)}", file=sys.stderr)
            for path in missing_sources:
                print(f"  {path}", file=sys.stderr)

    print("\n[exception class distribution]")
    for name, count in class_counts.most_common():
        print(f"{name}: {count}")

    print("\n[final error message distribution]")
    for message, count in message_counts.most_common():
        print(f"{count}\t{message}")

    return 0
