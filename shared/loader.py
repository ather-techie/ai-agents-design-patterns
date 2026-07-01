"""Load a pattern's ``pattern.py`` by file path under a unique module name.

Pattern directories are named like ``07-react`` — not importable as packages
(leading digit, hyphen) — and every pattern names its implementation
``pattern.py``. Anything that needs *more than one* pattern in a single process
(the benchmark harness, the test suite) therefore can't use ``import pattern``:
the second import would collide with the first in ``sys.modules``. This helper
loads each by absolute path under a distinct synthetic name to avoid that.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PATTERNS_DIR = _REPO_ROOT / "patterns"


def load_pattern_module(pattern_dir: str) -> ModuleType:
    """Import ``patterns/<pattern_dir>/pattern.py`` under a unique module name.

    ``pattern_dir`` is the directory name, e.g. ``"07-react"``. The repo root is
    ensured on ``sys.path`` so the pattern's own ``from shared...`` imports work.
    """
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

    path = _PATTERNS_DIR / pattern_dir / "pattern.py"
    if not path.exists():
        raise FileNotFoundError(f"no pattern.py at {path}")

    module_name = f"patterns_{pattern_dir.replace('-', '_')}_pattern"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
