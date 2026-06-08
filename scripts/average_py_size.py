#!/usr/bin/env python3
"""Measure Python file sizes and draw the sensitivity/size summary graph."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path


GENERATED_AVERAGE_BYTES = 865.32
REDUCED_AVERAGE_BYTES_BY_SENSITIVITY = (
    (0, 29.23),
    (1, 32.20),
    (2, 32.64),
    (4, 34.43),
    (8, 37.24),
    (16, 37.26),
    (100, 37.26),
)
DEFAULT_GRAPH_PATH = Path("average_program_size_by_sensitivity.png")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute .py file sizes or draw the sensitivity/size graph."
    )

    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "-s",
        "--size",
        type=Path,
        metavar="DIRECTORY",
        help="Print the average byte size of .py files in DIRECTORY.",
    )
    action.add_argument(
        "-d",
        "--draw",
        action="store_true",
        help="Draw the hardcoded sensitivity/average-size graph.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_GRAPH_PATH,
        help=f"Output path for --draw (default: {DEFAULT_GRAPH_PATH}).",
    )
    return parser.parse_args()


def print_average_py_size(directory: Path) -> int:
    if not directory.exists():
        print(f"error: directory does not exist: {directory}", file=sys.stderr)
        return 1

    if not directory.is_dir():
        print(f"error: not a directory: {directory}", file=sys.stderr)
        return 1

    py_files = sorted(
        path for path in directory.iterdir() if path.is_file() and path.suffix == ".py"
    )
    if not py_files:
        print(f"error: no .py files found in: {directory}", file=sys.stderr)
        return 1

    sizes = [path.stat().st_size for path in py_files]
    total = sum(sizes)
    average = total / len(sizes)

    print(f"Average .py file size: {average:.2f} bytes")
    print(f"Files: {len(sizes)}")
    print(f"Total: {total} bytes")

    return 0


def draw_average_program_size(output_path: Path) -> int:
    cache_root = Path(tempfile.gettempdir())
    matplotlib_config_dir = cache_root / "pesto-matplotlib"
    xdg_cache_dir = cache_root / "pesto-xdg-cache"
    matplotlib_config_dir.mkdir(parents=True, exist_ok=True)
    xdg_cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_config_dir))
    os.environ.setdefault("XDG_CACHE_HOME", str(xdg_cache_dir))

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
    except ModuleNotFoundError:
        print(
            "error: matplotlib is required for --draw. "
            "Install it with: python3 -m pip install matplotlib",
            file=sys.stderr,
        )
        return 1

    sensitivities = [
        sensitivity
        for sensitivity, _average_size in REDUCED_AVERAGE_BYTES_BY_SENSITIVITY
    ]
    reduced_sizes = [
        average_size
        for _sensitivity, average_size in REDUCED_AVERAGE_BYTES_BY_SENSITIVITY
    ]

    def compress_y(value: float) -> float:
        if value < 835:
            return value

        return 44 + ((value - 835) / 60) * 6

    generated_display_size = compress_y(GENERATED_AVERAGE_BYTES)

    fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)

    ax.plot(
        sensitivities,
        reduced_sizes,
        marker="o",
        linewidth=2,
        color="tab:blue",
        label="Reduced",
    )
    ax.axhline(
        generated_display_size,
        color="tab:red",
        linestyle="--",
        linewidth=1.6,
        label=f"Generated ({GENERATED_AVERAGE_BYTES:.2f} bytes)",
    )

    for sensitivity, average_size in REDUCED_AVERAGE_BYTES_BY_SENSITIVITY:
        ax.annotate(
            f"{average_size:.2f}",
            (sensitivity, average_size),
            textcoords="offset points",
            xytext=(0, 7),
            ha="center",
            fontsize=8,
        )

    ax.set_title("Average program size by sensitivity")
    ax.set_xlabel("Trace sensitivity (log scale)")
    ax.set_ylabel("Average program size (bytes)")
    ax.set_xscale("symlog", linthresh=1)
    ax.set_xlim(-0.1, 120)
    ax.xaxis.set_major_locator(ticker.FixedLocator(sensitivities))
    ax.xaxis.set_major_formatter(
        ticker.FixedFormatter(["0", "1", "2", "4", "8", "16", "MAX"])
    )
    ax.xaxis.set_minor_formatter(ticker.NullFormatter())
    ax.set_ylim(27, 50.5)
    ax.set_yticks(
        [28, 32, 36, 40, compress_y(840), compress_y(860), compress_y(880)]
    )
    ax.set_yticklabels(["28", "32", "36", "40", "840", "860", "880"])
    ax.grid(True, axis="y", linestyle=":", linewidth=0.8)
    ax.legend(loc="upper left")
    ax.text(
        0.12,
        0.68,
        "test suite: 2000 tests",
        transform=ax.transAxes,
        color="0.5",
        fontsize=10,
        fontstyle="italic",
    )
    ax.text(
        40,
        -0.005,
        "//",
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="center",
        fontsize=18,
        clip_on=False,
    )
    for y_offset in (-0.18, 0.18):
        ax.plot(
            [-0.008, 0.008],
            [42.35 + y_offset, 42.85 + y_offset],
            transform=ax.get_yaxis_transform(),
            color="black",
            linewidth=1.4,
            solid_capstyle="butt",
            clip_on=False,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)

    print(f"Saved graph to {output_path}")
    return 0


def main() -> int:
    args = parse_args()

    if args.size is not None:
        return print_average_py_size(args.size)

    return draw_average_program_size(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
