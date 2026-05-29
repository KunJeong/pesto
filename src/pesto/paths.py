"""Shared filesystem locations for the pesto toolchain."""

import platform
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_ROOT.parent
PROJECT_ROOT = SRC_DIR.parent

GRAMMAR_DIR = PACKAGE_ROOT / "grammar"
GRAMMAR_FILE = GRAMMAR_DIR / "Grammar.g4"
DATA_DIR = PACKAGE_ROOT / "data"
TEST_SCRIPT = DATA_DIR / "test-script.sh"
CPYTHON_HEADERS = PACKAGE_ROOT / "cpython_headers"

VENDOR_CPYTHON = PROJECT_ROOT / "vendor" / "cpython"

# The patched interpreter is built as `python.exe` on macOS and `python` on
# Linux/WSL; backtrace_symbols_fd() also formats frames differently per platform.
IS_DARWIN = platform.system() == "Darwin"
PATCHED_PYTHON = VENDOR_CPYTHON / ("python.exe" if IS_DARWIN else "python")

LONGOBJECT_META = VENDOR_CPYTHON / "pesto.json"

PERSES_JAR = PROJECT_ROOT / "perses" / "perses_deploy.jar"

DEFAULT_TESTS_DIR = PROJECT_ROOT / "tests"
DEFAULT_PIPELINE_DIR = PROJECT_ROOT / "pipeline_out"
