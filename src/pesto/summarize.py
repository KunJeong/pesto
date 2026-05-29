#!/usr/bin/env python3
import argparse
from collections import Counter
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize exception classes from .err files."
    )
    parser.add_argument("input_dir", help="Directory containing .err files")
    args = parser.parse_args()

    root = Path(args.input_dir)
    class_counts = Counter()
    message_counts = Counter()

    for path in sorted(root.rglob("*.err")):
        lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines()]
        lines = [line for line in lines if line]
        if not lines:
            continue
        message = lines[-1]
        message_counts[message] += 1
        error_class = message.split(":", 1)[0]
        class_counts[error_class] += 1

    print(f"input_dir: {root}")
    print(f"err_files: {sum(message_counts.values())}")

    print("\n[exception class distribution]")
    for name, count in class_counts.most_common():
        print(f"{name}: {count}")

    print("\n[final error message distribution]")
    for message, count in message_counts.most_common():
        print(f"{count}\t{message}")


if __name__ == "__main__":
    main()
