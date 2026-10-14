#!/usr/bin/env python
"""Exécute les tests avec -W error, en ignorant les avertissements amont
inoffensifs que pytest ne peut pas filtrer via filterwarnings (LIFO).

Usage :
    python scripts/run_tests.py [options pytest supplémentaires]

Voir .scratch/hardening-ship/issues/04-warnings-and-tooling.md
pour le contexte du contournement.
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