"""Reduce a crash to a one-line signature: ExceptionType | frame ; frame ; ..."""

import re
import subprocess

from . import paths

# Frames before this offset are interpreter start-up noise shared by every run.
_TRACE_SKIP = 4366

_LINUX_FRAME_RE = re.compile(r"\(([^+)]+)\+")


def extract_frame(line: str):
    if paths.IS_DARWIN:
        # "0   python.exe   0x...   _PyErr_SetObject + 212"
        parts = line.split()
        return parts[3] if len(parts) >= 4 else None
    # glibc: "python(_PyErr_SetObject+0x...) [0x...]"
    m = _LINUX_FRAME_RE.search(line)
    return m.group(1) if m else None


def trace_summary(target: str, sensitivity: int = 1) -> str:
    """Return the crash signature for ``target`` keeping ``sensitivity`` frames."""
    result = subprocess.run(
        [str(paths.PATCHED_PYTHON), target],
        capture_output=True,
        text=True,
    )

    python_traceback_summary = next(
        line for line in reversed(result.stderr.splitlines()) if line.strip()
    )
    escaping_exception_type = python_traceback_summary.split(":", 1)[0].strip()

    pesto_block_re = re.compile(
        rf"\[PESTO-BEGIN type={re.escape(escaping_exception_type)}\](.*?)\[PESTO-END\]",
        re.DOTALL,
    )

    traces = "\n".join(result.stderr.splitlines()[_TRACE_SKIP:])
    first_matching_block = pesto_block_re.findall(traces)[0]

    frames = [
        f
        for line in first_matching_block.strip().splitlines()
        if (f := extract_frame(line)) is not None
    ]

    return f"{escaping_exception_type} | " + " ; ".join(frames[:sensitivity])
