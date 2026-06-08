#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path


DEFAULT_INPUT = Path("measure.txt")
DEFAULT_OUTPUT = Path("measure_time_by_sensitivity.png")
SECTION_RE = re.compile(r"^=====\s+(.+?)\s+=====$")
RE_DEDUP_RE = re.compile(r"(?:^|/)re-(\d+)/dedup/?$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot CPython test-suite execution time by sensitivity."
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"measure.txt path (default: {DEFAULT_INPUT}).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output image path (default: {DEFAULT_OUTPUT}).",
    )
    return parser.parse_args()


def read_measurements(path: Path):
    if not path.is_file():
        sys.exit(f"measure file not found: {path}")

    baseline = None
    baseline_tests = None
    reduced = {}
    current = None
    py_files = None

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        match = SECTION_RE.match(line)
        if match:
            current = match.group(1)
            py_files = None
            continue

        if current is None:
            continue

        if line.startswith("py_files:"):
            py_files = int(line.split(":", 1)[1].strip())
            continue

        if not line.startswith("suite_time_s:"):
            continue

        seconds = float(line.split(":", 1)[1].strip())
        if current.rstrip("/").endswith("generated"):
            baseline = seconds
            baseline_tests = py_files
            continue

        match = RE_DEDUP_RE.search(current.rstrip("/"))
        if match:
            n = int(match.group(1))
            sensitivity = 100 if n == 100 else n - 1
            reduced[sensitivity] = seconds

    if baseline is None:
        sys.exit("baseline generated/ result not found in measure file")
    if not reduced:
        sys.exit("dedup sensitivity results not found in measure file")

    return baseline, baseline_tests, sorted(reduced.items())


def format_seconds(value: float) -> str:
    absolute = abs(value)
    if absolute < 1:
        return f"{value:.4g}"
    if absolute < 10:
        return f"{value:.3f}"
    if absolute < 100:
        return f"{value:.2f}"
    if absolute < 1000:
        return f"{value:.1f}"
    return f"{value:.0f}"


def draw_graph(baseline: float, baseline_tests: int | None, reduced, output: Path) -> int:
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
            "error: matplotlib is required. Install it with: python3 -m pip install matplotlib",
            file=sys.stderr,
        )
        return 1

    sensitivities = [sensitivity for sensitivity, _seconds in reduced]
    times = [seconds for _sensitivity, seconds in reduced]
    max_low = max(times)
    break_start = max_low * 1.18
    break_end = baseline * 0.82
    use_break = baseline > max_low * 2 and break_end > break_start

    def compress_y(value: float) -> float:
        if not use_break or value <= break_start:
            return value
        return break_start + (value - break_end) / max(baseline - break_end, 1e-9) * max_low * 0.22

    display_times = [compress_y(value) for value in times]
    baseline_display = compress_y(baseline)

    fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)

    ax.plot(
        sensitivities,
        display_times,
        marker="o",
        linewidth=2,
        color="tab:blue",
        label="Reduced",
    )
    ax.axhline(
        baseline_display,
        color="tab:red",
        linestyle="--",
        linewidth=1.6,
        label=f"Baseline ({format_seconds(baseline)} s)",
    )

    for sensitivity, seconds in reduced:
        ax.annotate(
            format_seconds(seconds),
            (sensitivity, compress_y(seconds)),
            textcoords="offset points",
            xytext=(0, 7),
            ha="center",
            fontsize=8,
        )

    ax.set_title("Execution time by sensitivity")
    ax.set_xlabel("Trace sensitivity (log scale)")
    ax.set_ylabel("Execution time (seconds)")
    ax.set_xscale("symlog", linthresh=1)
    ax.set_xlim(-0.1, 120)
    ax.xaxis.set_major_locator(ticker.FixedLocator(sensitivities))
    ax.xaxis.set_major_formatter(
        ticker.FixedFormatter(["MAX" if sensitivity == 100 else str(sensitivity) for sensitivity in sensitivities])
    )
    ax.xaxis.set_minor_formatter(ticker.NullFormatter())

    if use_break:
        low_ticks = sorted({0, round(max_low / 2), round(max_low)})
        high_ticks = [round(baseline)]
        yticks = [tick for tick in low_ticks if tick <= break_start] + [compress_y(tick) for tick in high_ticks]
        ylabels = [str(tick) for tick in low_ticks if tick <= break_start] + [str(tick) for tick in high_ticks]
        ax.set_yticks(yticks)
        ax.set_yticklabels(ylabels)
        ax.set_ylim(0, baseline_display * 1.35)
    else:
        ax.set_ylim(0, max(baseline, max_low) * 1.15)

    ax.grid(True, axis="y", linestyle=":", linewidth=0.8)
    ax.legend(loc="upper left")

    if baseline_tests is not None:
        ax.text(
            0.12,
            0.68,
            f"test suite: {baseline_tests} tests",
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

    if use_break:
        break_y = break_start + (baseline_display - break_start) * 0.08
        for y_offset in (-0.03, 0.03):
            ax.plot(
                [-0.008, 0.008],
                [break_y + y_offset, break_y + y_offset + baseline_display * 0.035],
                transform=ax.get_yaxis_transform(),
                color="black",
                linewidth=1.4,
                solid_capstyle="butt",
                clip_on=False,
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=200)
    plt.close(fig)
    print(f"Saved graph to {output}")
    return 0


def main() -> int:
    args = parse_args()
    baseline, baseline_tests, reduced = read_measurements(args.input)
    return draw_graph(baseline, baseline_tests, reduced, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
