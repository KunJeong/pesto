"""Reduce a crash to a one-line signature: ExceptionType | frame ; frame ; ..."""

import re
import subprocess

from . import paths

_EXCEPTION_DISPLAY_FRAMES = ("_PyErr_Display", "PyErr_Display", "sys_excepthook")

_LINUX_FRAME_RE = re.compile(r"(\S.*?)\(([^()]*)\)\s*\[")


def _darwin_frame(line: str):
    parts = line.split()
    if len(parts) < 4:
        return None
    symbol = parts[3]
    if len(parts) < 6 or parts[4] != "+":
        return None if symbol.startswith("0x") else symbol
    if symbol.startswith("0x"):
        return f"{parts[1]}+{parts[5]}"
    return f"{symbol}+{parts[5]}"


def _linux_frame(line: str):
    m = _LINUX_FRAME_RE.search(line)
    if m is None:
        return None
    content = m.group(2)  # "<symbol>+0x<off>" | "+0x<off>" | "<symbol>" | ""
    if content.startswith("+"):
        module = m.group(1).rsplit("/", 1)[-1]
        return f"{module}{content}"  # unresolved: module + offset from base
    return content or None  # named, with +offset within the symbol when present


def extract_frame(line: str):
    """A backtrace frame ``<symbol>+<offset>``"""
    return _darwin_frame(line) if paths.IS_DARWIN else _linux_frame(line)


def crash_block_frames(stderr_lines, block_re):
    """Frames of the last block matching ``block_re`` before the crash is displayed."""
    display_start = next(
        (i for i, line in enumerate(stderr_lines)
         if any(frame in line for frame in _EXCEPTION_DISPLAY_FRAMES)),
        len(stderr_lines),
    )
    blocks = block_re.findall("\n".join(stderr_lines[:display_start]))
    if not blocks:
        return None
    return [
        frame
        for line in blocks[-1].strip().splitlines()
        if (frame := extract_frame(line)) is not None
    ]


def trace_summary(target: str, sensitivity: int = 1) -> str:
    """Return the crash signature for ``target`` keeping ``sensitivity`` frames."""
    result = subprocess.run(
        [str(paths.TRACE_PYTHON), target],
        capture_output=True,
        text=True,
    )

    stderr_lines = result.stderr.splitlines()
    python_traceback_summary = next(
        line for line in reversed(stderr_lines) if line.strip()
    )
    escaping_exception_type = python_traceback_summary.split(":", 1)[0].strip()

    block_re = re.compile(
        rf"\[PESTO-BEGIN type={re.escape(escaping_exception_type)}\](.*?)\[PESTO-END\]",
        re.DOTALL,
    )
    frames = crash_block_frames(stderr_lines, block_re)
    if frames is None:
        raise ValueError(
            f"no [PESTO-BEGIN type={escaping_exception_type}] block found for {target}"
        )

    return f"{escaping_exception_type} | " + " ; ".join(frames[:sensitivity])
