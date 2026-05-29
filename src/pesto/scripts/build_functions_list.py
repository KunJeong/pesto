#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path

BEGIN_MARKER = "[PESTO-BEGIN type=TypeError]"
END_MARKER = "[PESTO-END]"
START_AFTER_LINE = 4365
TRACE_INDEX = 2
TRACE_RE = re.compile(r"^\s*(\d+)\s+\S+\s+0x[0-9a-fA-F]+\s+(\S+)\s+\+")
SOURCE_DIRS = ("Objects", "Python", "Modules", "Include")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build functions.list from PESTO TypeError logs."
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        required=True,
        type=Path,
        help="Directory containing .txt log files.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        required=True,
        type=Path,
        help="Directory where functions.list will be written.",
    )
    return parser.parse_args()


def extract_trace_function(log_path: Path) -> str | None:
    in_target_block = False

    with log_path.open(encoding="utf-8", errors="replace") as log_file:
        for line_no, line in enumerate(log_file, start=1):
            stripped = line.strip()

            if not in_target_block:
                if line_no > START_AFTER_LINE and stripped == BEGIN_MARKER:
                    in_target_block = True
                continue

            if stripped == END_MARKER:
                return None

            match = TRACE_RE.match(line)
            if match and int(match.group(1)) == TRACE_INDEX:
                return match.group(2)

    return None


def source_files(cpython_root: Path) -> list[tuple[Path, Path, list[str]]]:
    files = []
    for source_dir in SOURCE_DIRS:
        root = cpython_root / source_dir
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.suffix not in {".c", ".h"} or not path.is_file():
                continue
            rel_path = path.relative_to(cpython_root)
            text = path.read_text(encoding="utf-8", errors="replace")
            files.append(
                (rel_path, path, text.splitlines())
            )

    def priority(item: tuple[Path, Path, list[str]]) -> tuple[int, int, str]:
        rel_path = item[0]
        parts = set(rel_path.parts)
        generated = "clinic" in parts or rel_path.name.startswith("generated_")
        is_header = rel_path.suffix == ".h"
        return (int(generated), int(is_header), rel_path.as_posix())

    return sorted(files, key=priority)


def direct_definition(line: str, function: str) -> bool:
    escaped = re.escape(function)
    if line.startswith(f"{function}("):
        return True
    return bool(
        re.match(
            rf"^(?:static\s+)?(?:inline\s+)?"
            rf"(?:Py_LOCAL_INLINE\([^)]+\)|PyAPI_FUNC\([^)]+\)|[A-Za-z_][A-Za-z0-9_\s\*]*)"
            rf"\s+{escaped}\s*\(",
            line,
        )
    )


def macro_definition(line: str, function: str) -> bool:
    return bool(re.match(rf"^[A-Z][A-Z0-9_]*\(\s*{re.escape(function)}\b", line))


def clinic_alias(line: str, function: str) -> bool:
    return bool(re.search(rf"\bas\s+{re.escape(function)}\b", line))


def find_source_path(
    function: str, sources: list[tuple[Path, Path, list[str]]]
) -> str:
    source_only = [
        item
        for item in sources
        if "clinic" not in item[0].parts and not item[0].name.startswith("generated_")
    ]
    source_c_files = [item for item in source_only if item[0].suffix == ".c"]
    impl_function = f"{function}_impl"
    searches = (
        (source_c_files, lambda line: direct_definition(line, function)),
        (source_c_files, lambda line: macro_definition(line, function)),
        (source_c_files, lambda line: direct_definition(line, impl_function)),
        (source_c_files, lambda line: clinic_alias(line, function)),
        (source_only, lambda line: direct_definition(line, function)),
        (source_only, lambda line: macro_definition(line, function)),
        (source_only, lambda line: direct_definition(line, impl_function)),
        (source_only, lambda line: clinic_alias(line, function)),
        (sources, lambda line: direct_definition(line, function)),
        (sources, lambda line: direct_definition(line, impl_function)),
    )

    for search_sources, predicate in searches:
        for rel_path, _path, lines in search_sources:
            if any(predicate(line) for line in lines):
                return rel_path.as_posix()

    return "TODO"


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[3]
    cpython_root = repo_root / "vendor" / "cpython"
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not input_dir.is_dir():
        sys.exit(f"input directory not found: {input_dir}")
    if not cpython_root.is_dir():
        sys.exit(f"CPython directory not found: {cpython_root}")

    extracted = []
    missing_logs = []
    for log_path in sorted(input_dir.glob("*.txt")):
        function = extract_trace_function(log_path)
        if function is None:
            missing_logs.append(log_path)
            continue
        extracted.append(function)

    sources = source_files(cpython_root)
    functions = sorted(set(extracted))
    lines = [
        f"{function} {find_source_path(function, sources)}"
        for function in functions
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "functions.list"
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"input_dir: {input_dir}")
    print(f"output_file: {output_path}")
    print(f"log_files: {len(list(input_dir.glob('*.txt')))}")
    print(f"extracted_functions: {len(extracted)}")
    print(f"unique_functions: {len(functions)}")
    if missing_logs:
        print(f"missing_trace_functions: {len(missing_logs)}", file=sys.stderr)
        for path in missing_logs:
            print(f"  {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
