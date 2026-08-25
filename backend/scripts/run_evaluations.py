"""Launch the stock-agent evaluation suite from the backend scripts folder.

This wrapper keeps the reusable evaluation implementation beside its dataset in
``tests/evals`` while providing a short, stable command for developers and CI.
It can be executed from any working directory.
"""

import sys
from collections.abc import Callable
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
EVALS_DIRECTORY = BACKEND_ROOT / "tests" / "evals"
EVALUATOR_FILE = EVALS_DIRECTORY / "run_evals.py"
DEFAULT_DATASET = EVALS_DIRECTORY / "question.json"


def load_evaluation_main() -> Callable[[], int]:
    """Import and return the evaluator entry point from its source directory."""

    if not EVALUATOR_FILE.is_file():
        raise RuntimeError(f"Evaluation runner was not found: {EVALUATOR_FILE}")
    if not DEFAULT_DATASET.is_file():
        raise RuntimeError(f"Evaluation dataset was not found: {DEFAULT_DATASET}")

    evals_path = str(EVALS_DIRECTORY)
    if evals_path not in sys.path:
        sys.path.insert(0, evals_path)

    from run_evals import main as evaluation_main

    return evaluation_main


def main() -> int:
    """Run the canonical evaluator and return its process exit code."""

    return load_evaluation_main()()


if __name__ == "__main__":
    sys.exit(main())
