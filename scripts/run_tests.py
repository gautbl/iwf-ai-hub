#!/usr/bin/env python
"""Runs tests with -W error, ignoring upstream harmless
warnings that pytest cannot filter via filterwarnings (LIFO).

Usage:
    python scripts/run_tests.py [additional pytest options]

See .scratch/hardening-ship/issues/04-warnings-and-tooling.md
for the workaround context.
"""

import subprocess
import sys

ARGS = [
    sys.executable,
    "-m",
    "pytest",
    "-W", "error",
    "-W", "ignore::PendingDeprecationWarning:langgraph",
    "-W", "ignore::DeprecationWarning:starlette.testclient",
    *sys.argv[1:],
]

sys.exit(subprocess.call(ARGS))