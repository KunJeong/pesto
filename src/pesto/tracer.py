"""Reduce a crash to a one-line signature: ExceptionType | frame ; frame ; ..."""

import re
import subprocess

from . import paths

_EXCEPTION_DISPLAY_FRAMES = ("_PyErr_Display", "PyErr_Display", "sys_excepthook")

_LINUX_FRAME_RE = re.compile(r"\(([^+)]+)\+")


def extract_frame(line: str):
    if paths.IS_DARWIN:
        # "0   python.exe   0x...   _PyErr_SetObject + 212"
        parts = line.split()
        return parts[3] if len(parts) >= 4 else None
    # glibc: "python(_PyErr_SetObject+0x...) [0x...]"
    m = _LINUX_FRAME_RE.search(line)
    return m.group(1) if m else None


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
