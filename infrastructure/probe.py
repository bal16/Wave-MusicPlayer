"""Crash-safe availability probes for audio backends.

Native audio stacks (libvlc, miniaudio device probing) can abort at C
level on mismatched/broken systems — uncatchable with try/except. Running
the probe in a subprocess converts any abort into a non-zero exit code.
"""

from __future__ import annotations

import subprocess
import sys

PROBE_TIMEOUT_S = 20


def probe_in_subprocess(code: str) -> bool:
    """Run a snippet in a child interpreter. True only on clean exit.

    Args:
        code: Python source executed as `sys.executable -c code`.

    Returns:
        True when the child exits with code 0 (probe passed).
    """
    returncode, _ = run_probe(code)
    return returncode == 0


def run_probe(code: str) -> tuple[int, str]:
    """Run a snippet in a child interpreter. Return (exit code, stdout).

    Args:
        code: Python source executed as `sys.executable -c code`.

    Returns:
        A (returncode, stdout-stripped) tuple. Any launch failure
        (missing interpreter, timeout) maps to (1, "") so callers only
        branch on the code.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_S,
        )
        return result.returncode, (result.stdout or "").strip()
    except Exception:
        return 1, ""
